"""
ECOS API 고도화 모듈

기존 ecos_api.py를 확장하여 다음 기능 추가:
- 시차(Lag) 효과 분석
- 상관관계 계산
- 데이터베이스 통합
- 추가 지표 수집
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sys

# 기존 ECOS API 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.data.ecos_api import EcosAPI, StatCode
from src.data.database import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ecos"


class EcosConnector:
    """ECOS API 고도화 커넥터"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_manager: Optional[DatabaseManager] = None
    ):
        """
        커넥터 초기화

        Args:
            api_key: ECOS API 키
            db_manager: 데이터베이스 매니저
        """
        self.ecos_api = EcosAPI(api_key)
        self.db = db_manager or DatabaseManager()

    def fetch_and_save_all_indicators(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ):
        """
        모든 지표 수집 및 데이터베이스 저장

        Args:
            start_date: 시작일 (YYYYMM)
            end_date: 종료일 (YYYYMM)
        """
        logger.info("ECOS 지표 수집 및 DB 저장 시작")

        # 모든 지표 수집
        indicators = self.ecos_api.get_all_indicators(start_date, end_date, save=True)

        # 데이터베이스에 저장
        for name, df in indicators.items():
            if df.empty:
                continue

            # 날짜 컬럼 이름 통일
            if 'date' not in df.columns:
                continue

            # 각 지표별로 처리
            if name == "base_rate":
                self._save_indicator(df, 'base_rate', 'base_rate')

            elif name == "ktb_rates":
                self._save_indicator(df, 'ktb_3y', 'ktb_3y')
                self._save_indicator(df, 'ktb_10y', 'ktb_10y')
                self._save_indicator(df, 'term_spread', 'term_spread')

            elif name == "cpi":
                self._save_indicator(df, 'cpi', 'cpi')
                if 'cpi_yoy' in df.columns:
                    self._save_indicator(df, 'cpi_yoy', 'cpi_yoy')

            elif name == "csi":
                self._save_indicator(df, 'csi', 'csi')

            elif name == "exchange_rate":
                self._save_indicator(df, 'usd_krw', 'usd_krw')

        logger.info("ECOS 지표 DB 저장 완료")

    def _save_indicator(
        self,
        df: pd.DataFrame,
        value_column: str,
        indicator_name: str
    ):
        """
        개별 지표를 데이터베이스에 저장

        Args:
            df: DataFrame (must have 'date' column)
            value_column: 값이 있는 컬럼명
            indicator_name: 지표명
        """
        if value_column not in df.columns:
            return

        # 데이터 준비
        df_save = df[['date', value_column]].copy()
        df_save.columns = ['date', 'value']
        df_save = df_save.dropna()

        # DB 저장
        self.db.save_market_data(df_save, indicator_name, source='ECOS')

        logger.info(f"저장: {indicator_name} ({len(df_save)}개 레코드)")

    def calculate_lag_correlation(
        self,
        tone_df: pd.DataFrame,
        indicator_name: str,
        max_lag: int = 30
    ) -> pd.DataFrame:
        """
        톤 지수와 시장 지표 간 시차 상관관계 계산

        Args:
            tone_df: 톤 지수 DataFrame (columns: meeting_date, tone_index)
            indicator_name: 시장 지표명
            max_lag: 최대 시차 (일)

        Returns:
            DataFrame with columns: lag, correlation, p_value
        """
        logger.info(f"시차 상관관계 계산: {indicator_name}")

        # 시장 지표 데이터 로드
        market_df = self.db.get_market_data(indicator_name)

        if market_df.empty:
            logger.warning(f"시장 데이터 없음: {indicator_name}")
            return pd.DataFrame()

        # 날짜 형식 통일
        tone_df['meeting_date'] = pd.to_datetime(tone_df['meeting_date'])
        market_df['indicator_date'] = pd.to_datetime(market_df['indicator_date'])

        # 상관관계 계산
        correlations = []

        for lag in range(-max_lag, max_lag + 1):
            # 시장 지표를 lag만큼 이동
            market_shifted = market_df.copy()
            market_shifted['indicator_date'] = market_shifted['indicator_date'] + timedelta(days=lag)

            # 톤 지수와 조인
            merged = pd.merge(
                tone_df[['meeting_date', 'tone_index']],
                market_shifted[['indicator_date', 'value']],
                left_on='meeting_date',
                right_on='indicator_date',
                how='inner'
            )

            if len(merged) < 5:  # 최소 5개 데이터 필요
                continue

            # 상관계수 계산
            corr = merged['tone_index'].corr(merged['value'])

            correlations.append({
                'lag': lag,
                'correlation': corr,
                'n_samples': len(merged)
            })

        df_corr = pd.DataFrame(correlations)

        logger.info(f"시차 상관관계 계산 완료: {len(df_corr)}개 lag")

        return df_corr

    def calculate_market_reaction(
        self,
        meeting_date: str,
        days_before: int = 5,
        days_after: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        회의 전후 시장 반응 점수 계산

        Market_Reaction = Weighted_Sum[
            w_fx · ΔExchange_Rate,
            w_rate · ΔInterest_Rate,
            w_equity · ΔStock_Index,
            w_credit · ΔCredit_Spread
        ]

        Args:
            meeting_date: 회의 날짜 (YYYY-MM-DD)
            days_before: 기준일 (T-n)
            days_after: 측정일 (T+m)
            weights: 지표별 가중치 (None이면 기본값 사용)

        Returns:
            -1 ~ +1 범위의 시장 반응 점수
        """
        # 기본 가중치
        if weights is None:
            weights = {
                'usd_krw': 0.25,     # 환율
                'ktb_3y': 0.35,      # 금리 (국고채 3년)
                'kospi': 0.20,       # 주가
                'term_spread': 0.20  # 신용 스프레드
            }

        # 날짜 계산
        meeting_dt = pd.to_datetime(meeting_date)
        date_before = (meeting_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
        date_after = (meeting_dt + timedelta(days=days_after)).strftime('%Y-%m-%d')

        # 각 지표의 변화율 계산
        changes = {}

        for indicator, weight in weights.items():
            df = self.db.get_market_data(indicator, date_before, date_after)

            if df.empty or len(df) < 2:
                changes[indicator] = 0.0
                continue

            # 첫 값과 마지막 값의 변화율
            value_before = df.iloc[0]['value']
            value_after = df.iloc[-1]['value']

            if value_before == 0:
                pct_change = 0.0
            else:
                pct_change = (value_after - value_before) / value_before

            # 지표별로 방향 조정
            # 환율 상승 = 긴축 신호 = 매파 (+)
            # 금리 상승 = 긴축 신호 = 매파 (+)
            # 주가 상승 = 완화 신호 = 비둘기파 (-)
            # 스프레드 확대 = 긴축 우려 = 매파 (+)

            if indicator == 'kospi':
                pct_change = -pct_change  # 주가는 반대

            changes[indicator] = pct_change

        # 가중 평균 계산
        market_reaction = sum(
            changes[indicator] * weight
            for indicator, weight in weights.items()
        )

        # -1 ~ +1 범위로 정규화 (임의로 스케일링)
        market_reaction = np.tanh(market_reaction * 10)

        logger.info(
            f"[{meeting_date}] 시장 반응: {market_reaction:.3f} "
            f"(변화: {changes})"
        )

        return market_reaction

    def get_indicator_for_date_range(
        self,
        indicator_name: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        특정 기간의 지표 데이터 조회

        Args:
            indicator_name: 지표명
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            DataFrame
        """
        return self.db.get_market_data(indicator_name, start_date, end_date)

    def get_correlation_matrix(
        self,
        tone_df: pd.DataFrame,
        indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        톤 지수와 여러 지표 간 상관관계 행렬

        Args:
            tone_df: 톤 지수 DataFrame
            indicators: 지표 리스트 (None이면 주요 지표 사용)

        Returns:
            상관관계 행렬 DataFrame
        """
        if indicators is None:
            indicators = ['base_rate', 'ktb_3y', 'usd_krw', 'cpi_yoy']

        # 모든 지표 데이터 수집
        all_data = tone_df[['meeting_date', 'tone_index']].copy()
        all_data['meeting_date'] = pd.to_datetime(all_data['meeting_date'])

        for indicator in indicators:
            df_indicator = self.db.get_market_data(indicator)

            if df_indicator.empty:
                continue

            df_indicator['indicator_date'] = pd.to_datetime(df_indicator['indicator_date'])

            # 가장 가까운 날짜로 매칭
            merged = pd.merge_asof(
                all_data.sort_values('meeting_date'),
                df_indicator.sort_values('indicator_date'),
                left_on='meeting_date',
                right_on='indicator_date',
                direction='nearest'
            )

            all_data[indicator] = merged['value'].values

        # 상관관계 행렬 계산
        corr_matrix = all_data[['tone_index'] + indicators].corr()

        logger.info(f"상관관계 행렬 계산 완료")

        return corr_matrix


def main():
    """테스트 실행"""
    print("=" * 70)
    print("ECOS 커넥터 테스트")
    print("=" * 70)

    # 커넥터 초기화
    connector = EcosConnector()

    # 데이터 수집 및 저장 (최근 1년)
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m')
    end_date = datetime.now().strftime('%Y%m')

    print(f"\n수집 기간: {start_date} ~ {end_date}")

    try:
        connector.fetch_and_save_all_indicators(start_date, end_date)

        print("\n데이터베이스 저장 완료")

        # 저장된 데이터 확인
        indicators = ['base_rate', 'ktb_3y', 'usd_krw']

        for indicator in indicators:
            df = connector.get_indicator_for_date_range(
                indicator,
                (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d')
            )

            print(f"\n[{indicator}]")
            print(f"  레코드 수: {len(df)}")
            if not df.empty:
                print(f"  최근값: {df.iloc[-1]['value']:.2f}")

    except Exception as e:
        logger.error(f"테스트 실패: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
