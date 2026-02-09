"""
리딩/래깅 지표 분석 모듈

톤 지수와 시장 지표 간 선행/후행 관계 분석:
- 교차 상관관계 (Cross-Correlation)
- 최적 시차 (Optimal Lag) 식별
- 그랜저 인과관계 테스트
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class LagAnalysisResult:
    """시차 분석 결과"""
    indicator_name: str
    optimal_lag: int                    # 최적 시차 (일)
    max_correlation: float              # 최대 상관계수
    interpretation: str                 # 해석 (leading/lagging/contemporaneous)
    is_leading: bool                    # 톤 지수가 선행하는가?
    is_lagging: bool                    # 톤 지수가 후행하는가?
    correlation_series: pd.DataFrame    # 전체 시차별 상관계수


class LagAnalyzer:
    """시차 분석기"""

    def __init__(self):
        """분석기 초기화"""
        pass

    def calculate_cross_correlation(
        self,
        tone_series: pd.Series,
        market_series: pd.Series,
        max_lag: int = 30
    ) -> pd.DataFrame:
        """
        교차 상관관계 계산

        Args:
            tone_series: 톤 지수 시계열
            market_series: 시장 지표 시계열
            max_lag: 최대 시차 (일)

        Returns:
            DataFrame with columns: lag, correlation, label
        """
        logger.info(f"교차 상관관계 계산 (max_lag={max_lag})")

        correlations = []

        # 시리즈를 인덱스 기준으로 정렬
        tone_series = tone_series.sort_index()
        market_series = market_series.sort_index()

        # 교집합 인덱스 찾기
        common_idx = tone_series.index.intersection(market_series.index)

        if len(common_idx) < 5:
            logger.warning("공통 데이터 포인트가 부족합니다 (최소 5개 필요)")
            return pd.DataFrame()

        tone_aligned = tone_series.loc[common_idx]
        market_aligned = market_series.loc[common_idx]

        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                # 시장이 톤을 선행 (Market leads Tone)
                # 시장을 앞으로 이동시킴
                try:
                    corr = tone_aligned.corr(market_aligned.shift(lag))
                    label = f"Market leads by {abs(lag)} days"
                except:
                    corr = np.nan
                    label = f"Market leads by {abs(lag)} days (insufficient data)"

            elif lag > 0:
                # 톤이 시장을 선행 (Tone leads Market)
                # 톤을 앞으로 이동시킴
                try:
                    corr = tone_aligned.shift(lag).corr(market_aligned)
                    label = f"Tone leads by {lag} days"
                except:
                    corr = np.nan
                    label = f"Tone leads by {lag} days (insufficient data)"

            else:
                # 동시 상관관계
                try:
                    corr = tone_aligned.corr(market_aligned)
                    label = "Contemporaneous"
                except:
                    corr = np.nan
                    label = "Contemporaneous (insufficient data)"

            correlations.append({
                'lag': lag,
                'correlation': corr,
                'label': label
            })

        df = pd.DataFrame(correlations)
        df = df.dropna(subset=['correlation'])

        logger.info(f"교차 상관관계 계산 완료: {len(df)}개 lag")

        return df

    def identify_lead_lag_relationship(
        self,
        correlation_df: pd.DataFrame
    ) -> Dict:
        """
        선행/후행 관계 식별

        Args:
            correlation_df: calculate_cross_correlation 결과

        Returns:
            Dict with optimal_lag, max_correlation, interpretation, etc.
        """
        if correlation_df.empty:
            return {
                'optimal_lag': 0,
                'max_correlation': 0.0,
                'interpretation': 'No data',
                'is_leading': False,
                'is_lagging': False
            }

        # 절대값 기준 최대 상관계수 찾기
        max_idx = correlation_df['correlation'].abs().idxmax()
        max_row = correlation_df.loc[max_idx]

        optimal_lag = max_row['lag']
        max_correlation = max_row['correlation']

        # 해석
        if optimal_lag > 5:
            interpretation = f"Tone leads Market by {optimal_lag} days"
            is_leading = True
            is_lagging = False
        elif optimal_lag < -5:
            interpretation = f"Market leads Tone by {abs(optimal_lag)} days"
            is_leading = False
            is_lagging = True
        else:
            interpretation = "Contemporaneous (no significant lag)"
            is_leading = False
            is_lagging = False

        return {
            'optimal_lag': optimal_lag,
            'max_correlation': max_correlation,
            'interpretation': interpretation,
            'is_leading': is_leading,
            'is_lagging': is_lagging
        }

    def analyze_tone_vs_indicator(
        self,
        tone_df: pd.DataFrame,
        indicator_df: pd.DataFrame,
        indicator_name: str,
        max_lag: int = 30
    ) -> LagAnalysisResult:
        """
        톤 지수와 특정 지표 간 시차 분석

        Args:
            tone_df: 톤 지수 DataFrame (columns: date, tone_index)
            indicator_df: 지표 DataFrame (columns: date, value)
            indicator_name: 지표명
            max_lag: 최대 시차

        Returns:
            LagAnalysisResult 객체
        """
        logger.info(f"시차 분석: Tone vs {indicator_name}")

        # 날짜를 인덱스로 설정
        tone_series = tone_df.set_index('date')['tone_index']
        indicator_series = indicator_df.set_index('date')['value']

        # 교차 상관관계 계산
        corr_df = self.calculate_cross_correlation(
            tone_series,
            indicator_series,
            max_lag
        )

        if corr_df.empty:
            logger.warning(f"시차 분석 실패: {indicator_name}")
            return LagAnalysisResult(
                indicator_name=indicator_name,
                optimal_lag=0,
                max_correlation=0.0,
                interpretation="Insufficient data",
                is_leading=False,
                is_lagging=False,
                correlation_series=corr_df
            )

        # 선행/후행 관계 식별
        relationship = self.identify_lead_lag_relationship(corr_df)

        result = LagAnalysisResult(
            indicator_name=indicator_name,
            optimal_lag=relationship['optimal_lag'],
            max_correlation=relationship['max_correlation'],
            interpretation=relationship['interpretation'],
            is_leading=relationship['is_leading'],
            is_lagging=relationship['is_lagging'],
            correlation_series=corr_df
        )

        logger.info(
            f"[{indicator_name}] "
            f"Optimal Lag: {result.optimal_lag} days, "
            f"Max Corr: {result.max_correlation:.3f}, "
            f"{result.interpretation}"
        )

        return result

    def create_lag_plot(
        self,
        result: LagAnalysisResult,
        title: Optional[str] = None
    ) -> go.Figure:
        """
        시차 상관관계 플롯 생성

        Args:
            result: LagAnalysisResult 객체
            title: 플롯 제목

        Returns:
            Plotly Figure
        """
        if result.correlation_series.empty:
            return go.Figure()

        df = result.correlation_series

        fig = go.Figure()

        # 상관계수 라인
        fig.add_trace(go.Scatter(
            x=df['lag'],
            y=df['correlation'],
            mode='lines+markers',
            name='Cross-Correlation',
            line=dict(color='#64B5F6', width=2),
            marker=dict(size=6)
        ))

        # 0 라인
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        # 최적 시차 표시
        optimal_row = df[df['lag'] == result.optimal_lag]
        if not optimal_row.empty:
            fig.add_trace(go.Scatter(
                x=[result.optimal_lag],
                y=[result.max_correlation],
                mode='markers+text',
                name='Optimal Lag',
                marker=dict(size=12, color='red', symbol='star'),
                text=[f"Lag={result.optimal_lag}"],
                textposition="top center"
            ))

        # 레이아웃
        if title is None:
            title = f"Tone Index vs {result.indicator_name} - Cross-Correlation"

        fig.update_layout(
            title=title,
            xaxis_title="Lag (days) [Negative = Market leads, Positive = Tone leads]",
            yaxis_title="Correlation Coefficient",
            height=400,
            hovermode='x unified',
            showlegend=True
        )

        return fig

    def create_multi_indicator_lag_plot(
        self,
        results: List[LagAnalysisResult]
    ) -> go.Figure:
        """
        여러 지표의 시차 분석 결과를 한 번에 표시

        Args:
            results: LagAnalysisResult 리스트

        Returns:
            Plotly Figure
        """
        fig = go.Figure()

        colors = ['#64B5F6', '#FF7043', '#66BB6A', '#FFA726', '#AB47BC']

        for i, result in enumerate(results):
            if result.correlation_series.empty:
                continue

            df = result.correlation_series
            color = colors[i % len(colors)]

            fig.add_trace(go.Scatter(
                x=df['lag'],
                y=df['correlation'],
                mode='lines+markers',
                name=result.indicator_name,
                line=dict(color=color, width=2),
                marker=dict(size=4)
            ))

            # 최적 시차 포인트
            fig.add_trace(go.Scatter(
                x=[result.optimal_lag],
                y=[result.max_correlation],
                mode='markers',
                name=f"{result.indicator_name} (Optimal)",
                marker=dict(size=10, color=color, symbol='star'),
                showlegend=False
            ))

        # 0 라인
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

        fig.update_layout(
            title="Multi-Indicator Cross-Correlation Analysis",
            xaxis_title="Lag (days) [Negative = Market leads, Positive = Tone leads]",
            yaxis_title="Correlation Coefficient",
            height=500,
            hovermode='x unified',
            showlegend=True
        )

        return fig

    def create_lag_summary_table(
        self,
        results: List[LagAnalysisResult]
    ) -> pd.DataFrame:
        """
        시차 분석 결과 요약 테이블

        Args:
            results: LagAnalysisResult 리스트

        Returns:
            요약 DataFrame
        """
        data = []

        for result in results:
            data.append({
                'Indicator': result.indicator_name,
                'Optimal Lag (days)': result.optimal_lag,
                'Max Correlation': f"{result.max_correlation:.3f}",
                'Relationship': result.interpretation,
                'Tone Leads?': '✓' if result.is_leading else '✗',
                'Tone Lags?': '✓' if result.is_lagging else '✗'
            })

        df = pd.DataFrame(data)

        return df


def main():
    """테스트 실행"""
    print("=" * 70)
    print("시차 분석 모듈 테스트")
    print("=" * 70)

    # 더미 데이터 생성
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='W')

    # 톤 지수 (랜덤 데이터)
    np.random.seed(42)
    tone_data = {
        'date': dates,
        'tone_index': np.random.randn(len(dates)) * 0.3
    }
    df_tone = pd.DataFrame(tone_data)

    # 시장 지표 (톤 지수를 10일 지연시킨 데이터 + 노이즈)
    market_data = {
        'date': dates,
        'value': np.roll(df_tone['tone_index'].values, 2) + np.random.randn(len(dates)) * 0.1
    }
    df_market = pd.DataFrame(market_data)

    # 분석 실행
    analyzer = LagAnalyzer()

    result = analyzer.analyze_tone_vs_indicator(
        df_tone,
        df_market,
        indicator_name="Test Indicator",
        max_lag=20
    )

    # 결과 출력
    print("\n분석 결과:")
    print(f"  지표: {result.indicator_name}")
    print(f"  최적 시차: {result.optimal_lag}일")
    print(f"  최대 상관계수: {result.max_correlation:.3f}")
    print(f"  관계: {result.interpretation}")

    # 플롯 생성 (파일로 저장)
    fig = analyzer.create_lag_plot(result)

    output_path = DATA_DIR / "analysis" / "lag_plot_test.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))

    print(f"\n플롯 저장: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
