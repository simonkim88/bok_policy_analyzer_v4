"""
한국은행 경제통계시스템(ECOS) API 연동 모듈

ECOS API를 통해 기준금리, 시장금리, 물가지수 등 거시경제 지표를 수집합니다.
API 키는 https://ecos.bok.or.kr/api/ 에서 발급받을 수 있습니다.
"""

import requests
import pandas as pd
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
import json
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ECOS_DIR = DATA_DIR / "ecos"


@dataclass
class StatCode:
    """ECOS 통계 코드 정의"""
    # 기준금리 및 여수신금리
    BASE_RATE = "722Y001"  # 한국은행 기준금리

    # 시장금리
    MARKET_RATE = "817Y002"  # 시장금리 (국고채 등)

    # 물가지수
    CPI = "901Y009"  # 소비자물가지수

    # 심리지수
    CSI = "511Y002"  # 소비자동향조사 (Consumer Sentiment Index)
    BSI = "512Y014"  # 기업경기실사지수 (Business Survey Index)

    # 환율
    EXCHANGE_RATE = "731Y003"  # 원/달러 환율

    # 주가지수
    STOCK_INDEX = "802Y001"  # KOSPI


class EcosAPI:
    """한국은행 ECOS API 클라이언트"""

    BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

    def __init__(self, api_key: Optional[str] = None):
        """
        ECOS API 클라이언트 초기화

        Args:
            api_key: ECOS API 인증키. None이면 환경변수 ECOS_API_KEY에서 읽음
        """
        # TODO: Remove hardcoded fallback key in production
        self.api_key = api_key or os.environ.get('ECOS_API_KEY', 'LZUNMUPZQ4FFUITEF1R7')

        if not self.api_key:
            logger.warning("ECOS API 키가 설정되지 않았습니다. 환경변수 ECOS_API_KEY를 설정하거나 api_key를 전달해주세요.")

        # 디렉토리 생성
        ECOS_DIR.mkdir(parents=True, exist_ok=True)

    def _build_url(
        self,
        stat_code: str,
        period_type: str,  # D: 일, M: 월, Q: 분기, A: 연
        start_date: str,
        end_date: str,
        item_code1: str = "?",
        item_code2: str = "?",
        item_code3: str = "?",
        item_code4: str = "?",
        count: int = 100000
    ) -> str:
        """API 요청 URL 생성"""
        # URL 형식: BASE_URL/API_KEY/json/kr/시작/끝/통계코드/주기/시작일/종료일/항목1/항목2/항목3/항목4
        return (
            f"{self.BASE_URL}/{self.api_key}/json/kr/1/{count}/"
            f"{stat_code}/{period_type}/{start_date}/{end_date}/"
            f"{item_code1}/{item_code2}/{item_code3}/{item_code4}"
        )

    def fetch_data(
        self,
        stat_code: str,
        period_type: str = "M",
        start_date: str = "201501",
        end_date: Optional[str] = None,
        item_code1: str = "?",
        item_code2: str = "?",
        item_code3: str = "?",
        item_code4: str = "?",
    ) -> Optional[pd.DataFrame]:
        """
        ECOS API에서 데이터 조회

        Args:
            stat_code: 통계코드
            period_type: 주기 (D: 일, M: 월, Q: 분기, A: 연)
            start_date: 시작일 (YYYYMM 또는 YYYYMMDD)
            end_date: 종료일 (기본값: 현재)
            item_code1~4: 항목 코드 (기본값: ? = 전체)

        Returns:
            DataFrame 또는 None
        """
        if not self.api_key:
            logger.error("API 키가 설정되지 않았습니다.")
            return None

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m")

        url = self._build_url(
            stat_code=stat_code,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            item_code1=item_code1,
            item_code2=item_code2,
            item_code3=item_code3,
            item_code4=item_code4
        )

        try:
            logger.info(f"ECOS API 요청: {stat_code}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # API 에러 체크
            if "StatisticSearch" not in data:
                error_msg = data.get("RESULT", {}).get("MESSAGE", "Unknown error")
                logger.error(f"API 에러: {error_msg}")
                return None

            # 데이터 추출
            rows = data["StatisticSearch"].get("row", [])
            if not rows:
                logger.warning(f"데이터 없음: {stat_code}")
                return None

            df = pd.DataFrame(rows)
            logger.info(f"데이터 수신: {len(df)}건")

            return df

        except requests.RequestException as e:
            logger.error(f"API 요청 실패: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return None

    def get_base_rate(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        한국은행 기준금리 조회

        Returns:
            날짜, 기준금리가 포함된 DataFrame
        """
        df = self.fetch_data(
            stat_code=StatCode.BASE_RATE,
            period_type="D",
            start_date=start_date,
            end_date=end_date,
            item_code1="0101000"  # 한국은행 기준금리
        )

        if df is not None:
            df = df[["TIME", "DATA_VALUE"]].copy()
            df.columns = ["date", "base_rate"]
            df["base_rate"] = pd.to_numeric(df["base_rate"], errors="coerce")
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

        return df

    def get_ktb_rates(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        국고채 금리 조회 (3년물, 10년물)

        Returns:
            날짜, 3년물 금리, 10년물 금리가 포함된 DataFrame
        """
        # 국고채 3년
        df_3y = self.fetch_data(
            stat_code=StatCode.MARKET_RATE,
            period_type="D",
            start_date=start_date,
            end_date=end_date,
            item_code1="010200000"  # 국고채(3년)
        )

        # 국고채 10년
        df_10y = self.fetch_data(
            stat_code=StatCode.MARKET_RATE,
            period_type="D",
            start_date=start_date,
            end_date=end_date,
            item_code1="010200001"  # 국고채(10년)
        )

        if df_3y is None or df_10y is None:
            return None

        df_3y = df_3y[["TIME", "DATA_VALUE"]].copy()
        df_3y.columns = ["date", "ktb_3y"]

        df_10y = df_10y[["TIME", "DATA_VALUE"]].copy()
        df_10y.columns = ["date", "ktb_10y"]

        df = pd.merge(df_3y, df_10y, on="date", how="outer")
        df["ktb_3y"] = pd.to_numeric(df["ktb_3y"], errors="coerce")
        df["ktb_10y"] = pd.to_numeric(df["ktb_10y"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df["term_spread"] = df["ktb_10y"] - df["ktb_3y"]  # 장단기 금리차

        return df.sort_values("date")

    def get_cpi(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        소비자물가지수 조회

        Returns:
            날짜, CPI, 전년동월비가 포함된 DataFrame
        """
        df = self.fetch_data(
            stat_code=StatCode.CPI,
            period_type="M",
            start_date=start_date,
            end_date=end_date,
            item_code1="0"  # 총지수
        )

        if df is not None:
            df = df[["TIME", "DATA_VALUE"]].copy()
            df.columns = ["date", "cpi"]
            df["cpi"] = pd.to_numeric(df["cpi"], errors="coerce")
            df["date"] = pd.to_datetime(df["date"] + "01", format="%Y%m%d")
            # 전년동월비 계산
            df["cpi_yoy"] = df["cpi"].pct_change(12) * 100

        return df

    def get_csi(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        소비자심리지수(CSI) 조회

        Returns:
            날짜, CSI가 포함된 DataFrame
        """
        df = self.fetch_data(
            stat_code=StatCode.CSI,
            period_type="M",
            start_date=start_date,
            end_date=end_date,
            item_code1="FME"  # 소비자심리지수
        )

        if df is not None:
            df = df[["TIME", "DATA_VALUE"]].copy()
            df.columns = ["date", "csi"]
            df["csi"] = pd.to_numeric(df["csi"], errors="coerce")
            df["date"] = pd.to_datetime(df["date"] + "01", format="%Y%m%d")

        return df

    def get_exchange_rate(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        원/달러 환율 조회

        Returns:
            날짜, 환율이 포함된 DataFrame
        """
        df = self.fetch_data(
            stat_code=StatCode.EXCHANGE_RATE,
            period_type="D",
            start_date=start_date,
            end_date=end_date,
            item_code1="0000001"  # 원/미달러
        )

        if df is not None:
            df = df[["TIME", "DATA_VALUE"]].copy()
            df.columns = ["date", "usd_krw"]
            df["usd_krw"] = pd.to_numeric(df["usd_krw"], errors="coerce")
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

        return df

    def get_all_indicators(
        self,
        start_date: str = "201501",
        end_date: Optional[str] = None,
        save: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        모든 주요 경제지표 일괄 조회

        Args:
            start_date: 시작일
            end_date: 종료일
            save: 파일로 저장 여부

        Returns:
            지표별 DataFrame 딕셔너리
        """
        indicators = {}

        logger.info("경제지표 수집 시작...")

        # 기준금리
        df = self.get_base_rate(start_date, end_date)
        if df is not None:
            indicators["base_rate"] = df
            logger.info(f"기준금리: {len(df)}건")

        # 국고채 금리
        df = self.get_ktb_rates(start_date, end_date)
        if df is not None:
            indicators["ktb_rates"] = df
            logger.info(f"국고채 금리: {len(df)}건")

        # CPI
        df = self.get_cpi(start_date, end_date)
        if df is not None:
            indicators["cpi"] = df
            logger.info(f"소비자물가지수: {len(df)}건")

        # CSI
        df = self.get_csi(start_date, end_date)
        if df is not None:
            indicators["csi"] = df
            logger.info(f"소비자심리지수: {len(df)}건")

        # 환율
        df = self.get_exchange_rate(start_date, end_date)
        if df is not None:
            indicators["exchange_rate"] = df
            logger.info(f"원/달러 환율: {len(df)}건")

        # 저장
        if save and indicators:
            for name, df in indicators.items():
                filepath = ECOS_DIR / f"{name}.csv"
                df.to_csv(filepath, index=False, encoding="utf-8-sig")
                logger.info(f"저장 완료: {filepath}")

        return indicators


def main():
    """테스트 실행"""
    api = EcosAPI()

    if not api.api_key:
        print("=" * 60)
        print("ECOS API 사용을 위해 API 키가 필요합니다.")
        print("1. https://ecos.bok.or.kr/api/ 에서 API 키 발급")
        print("2. 환경변수 설정: set ECOS_API_KEY=your_api_key")
        print("   또는 코드에서: EcosAPI(api_key='your_api_key')")
        print("=" * 60)
        return

    # 모든 지표 수집
    indicators = api.get_all_indicators(start_date="202101")

    print("\n" + "=" * 60)
    print("수집 완료")
    print("=" * 60)
    for name, df in indicators.items():
        print(f"{name}: {len(df)}건")


if __name__ == "__main__":
    main()
