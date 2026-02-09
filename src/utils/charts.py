"""
고도화된 차트 생성 모듈

McKinsey 스타일 차트 및 전문적인 시각화:
- 시장 반응 차트 (의사록 발표 전후)
- 키워드 영향력 분석
- 워드클라우드
- 다변량 시계열 차트
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent


def create_market_reaction_chart(
    meeting_date: str,
    market_data: Dict[str, pd.DataFrame],
    days_before: int = 5,
    days_after: int = 10
) -> go.Figure:
    """
    의사록 발표 전후 시장 반응 차트

    Args:
        meeting_date: 회의 날짜 (YYYY-MM-DD)
        market_data: {지표명: DataFrame(date, value)} 딕셔너리
        days_before: T-n일
        days_after: T+m일

    Returns:
        Plotly Figure (3개 subplot)
    """
    # 3개 지표를 서브플롯으로 표시
    indicators = list(market_data.keys())[:3]  # 최대 3개

    fig = make_subplots(
        rows=len(indicators),
        cols=1,
        shared_xaxes=True,
        subplot_titles=[ind.replace('_', ' ').title() for ind in indicators],
        vertical_spacing=0.08
    )

    meeting_dt = pd.to_datetime(meeting_date)

    for i, indicator in enumerate(indicators, start=1):
        df = market_data[indicator]

        if df.empty:
            continue

        # 날짜 필터링
        df['date'] = pd.to_datetime(df['date'])
        start_date = meeting_dt - timedelta(days=days_before)
        end_date = meeting_dt + timedelta(days=days_after)

        df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        if df_filtered.empty:
            continue

        # 라인 추가
        fig.add_trace(
            go.Scatter(
                x=df_filtered['date'],
                y=df_filtered['value'],
                mode='lines+markers',
                name=indicator,
                line=dict(width=2),
                marker=dict(size=5)
            ),
            row=i,
            col=1
        )

        # 발표일 수직선
        fig.add_vline(
            x=meeting_dt.timestamp() * 1000,  # Plotly uses milliseconds
            line_dash="dash",
            line_color="red",
            annotation_text="의사록 발표" if i == 1 else "",
            row=i,
            col=1
        )

    fig.update_layout(
        height=600,
        title=f"의사록 발표 전후 시장 반응 ({meeting_date})",
        hovermode='x unified',
        showlegend=False
    )

    fig.update_xaxes(title_text="날짜", row=len(indicators), col=1)

    return fig


def create_keyword_impact_chart(
    df_results: pd.DataFrame,
    sentiment_dict
) -> go.Figure:
    """
    키워드의 톤 변화 기여도 분석 차트

    Args:
        df_results: 톤 분석 결과 DataFrame
        sentiment_dict: SentimentDictionary 객체

    Returns:
        Plotly Figure (horizontal bar chart)
    """
    # 모든 키워드 수집
    all_keywords = (
        list(sentiment_dict.hawkish_terms.keys()) +
        list(sentiment_dict.dovish_terms.keys())
    )

    impacts = []

    for keyword in all_keywords:
        # 해당 키워드가 등장한 회의만 필터링
        if 'raw_text' in df_results.columns:
            text_col = 'raw_text'
        else:
            # 텍스트가 없으면 top_hawkish, top_dovish에서 확인
            text_col = None

        if text_col:
            with_keyword = df_results[df_results[text_col].str.contains(keyword, na=False)]
            without_keyword = df_results[~df_results[text_col].str.contains(keyword, na=False)]
        else:
            # 간단히 top_hawkish/top_dovish에서 찾기
            with_keyword = df_results[
                df_results['top_hawkish'].str.contains(keyword, na=False) |
                df_results['top_dovish'].str.contains(keyword, na=False)
            ]
            without_keyword = df_results[
                ~(df_results['top_hawkish'].str.contains(keyword, na=False) |
                  df_results['top_dovish'].str.contains(keyword, na=False))
            ]

        if len(with_keyword) > 3 and len(without_keyword) > 3:
            tone_diff = with_keyword['tone_index'].mean() - without_keyword['tone_index'].mean()

            polarity = 'Hawkish' if keyword in sentiment_dict.hawkish_terms else 'Dovish'

            impacts.append({
                'keyword': keyword,
                'tone_impact': tone_diff,
                'frequency': len(with_keyword),
                'polarity': polarity
            })

    df_impacts = pd.DataFrame(impacts)

    if df_impacts.empty:
        logger.warning("키워드 영향력 데이터가 부족합니다")
        return go.Figure()

    # 상위 15개만 표시
    df_impacts = df_impacts.reindex(
        df_impacts['tone_impact'].abs().sort_values(ascending=False).index
    ).head(15)

    # 차트 생성
    colors = ['#ff7f0e' if p == 'Hawkish' else '#1f77b4' for p in df_impacts['polarity']]

    fig = go.Figure(data=[
        go.Bar(
            y=df_impacts['keyword'],
            x=df_impacts['tone_impact'],
            orientation='h',
            marker=dict(color=colors),
            text=[f"{v:+.3f}" for v in df_impacts['tone_impact']],
            textposition='auto'
        )
    ])

    fig.update_layout(
        title="키워드별 톤 변화 기여도 (Keyword Impact on Tone Index)",
        xaxis_title="Tone Impact (평균 톤 차이)",
        yaxis_title="키워드",
        height=600,
        showlegend=False
    )

    return fig


def create_tone_wordcloud(
    hawkish_terms: Dict,
    dovish_terms: Dict,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    매파/비둘기파 키워드 워드클라우드

    Args:
        hawkish_terms: {term: SentimentEntry} 매파 키워드
        dovish_terms: {term: SentimentEntry} 비둘기파 키워드
        save_path: 저장 경로 (None이면 저장 안 함)

    Returns:
        Matplotlib Figure
    """
    # 가중치 기반 빈도
    word_freq = {}

    for term, entry in hawkish_terms.items():
        word_freq[term] = entry.weight * 100  # 크기 조정

    for term, entry in dovish_terms.items():
        word_freq[term] = entry.weight * 100

    # 색상 함수
    def color_func(word, **kwargs):
        if word in hawkish_terms:
            return "#ff7f0e"  # 오렌지 (매파)
        else:
            return "#1f77b4"  # 파랑 (비둘기파)

    # 한글 폰트 찾기
    font_path = None
    possible_fonts = [
        "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
        "C:/Windows/Fonts/NanumGothic.ttf",  # 나눔고딕
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
    ]

    for font in possible_fonts:
        if Path(font).exists():
            font_path = font
            break

    # 워드클라우드 생성
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        background_color="white",
        color_func=color_func,
        relative_scaling=0.5,
        min_font_size=10
    ).generate_from_frequencies(word_freq)

    # Figure 생성
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('BOK Tone Keywords WordCloud\n(Orange=Hawkish, Blue=Dovish)', fontsize=14)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"워드클라우드 저장: {save_path}")

    return fig


def create_multivariate_tone_chart(
    df: pd.DataFrame,
    indicators: List[str] = None
) -> go.Figure:
    """
    톤 지수와 여러 경제 지표를 함께 표시

    Args:
        df: DataFrame with columns: meeting_date, tone_index, [indicators...]
        indicators: 표시할 지표 컬럼 리스트

    Returns:
        Plotly Figure with dual y-axes
    """
    if indicators is None:
        indicators = ['base_rate', 'cpi_yoy']

    # subplot 생성
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Tone Index", "Economic Indicators"),
        vertical_spacing=0.1
    )

    # 톤 지수
    fig.add_trace(
        go.Scatter(
            x=df['meeting_date'],
            y=df['tone_index'],
            mode='lines+markers',
            name='Tone Index',
            line=dict(color='royalblue', width=3),
            marker=dict(size=8)
        ),
        row=1,
        col=1
    )

    # 중립선
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    # 경제 지표들
    colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for i, indicator in enumerate(indicators):
        if indicator not in df.columns:
            continue

        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=df['meeting_date'],
                y=df[indicator],
                mode='lines+markers',
                name=indicator.replace('_', ' ').title(),
                line=dict(color=color, width=2),
                marker=dict(size=6)
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        height=700,
        title="Tone Index vs Economic Indicators",
        hovermode='x unified',
        showlegend=True
    )

    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Tone Index", row=1, col=1)
    fig.update_yaxes(title_text="Indicator Value", row=2, col=1)

    return fig


def create_correlation_heatmap(
    corr_matrix: pd.DataFrame
) -> go.Figure:
    """
    상관관계 행렬 히트맵

    Args:
        corr_matrix: 상관관계 행렬 DataFrame

    Returns:
        Plotly Figure (heatmap)
    """
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))

    fig.update_layout(
        title="Correlation Matrix: Tone Index vs Economic Indicators",
        height=600,
        xaxis_title="Indicators",
        yaxis_title="Indicators"
    )

    return fig


def main():
    """테스트 실행"""
    print("=" * 70)
    print("차트 모듈 테스트")
    print("=" * 70)

    # 더미 데이터 생성
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='M')
    df = pd.DataFrame({
        'meeting_date': dates,
        'tone_index': np.random.randn(len(dates)) * 0.3,
        'base_rate': [3.5 + i * 0.05 for i in range(len(dates))],
        'cpi_yoy': [3.0 + np.random.randn() * 0.5 for _ in range(len(dates))]
    })

    # 다변량 차트 생성
    fig = create_multivariate_tone_chart(df)

    output_path = PROJECT_ROOT / "data" / "analysis" / "multivariate_chart_test.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path))

    print(f"\n차트 저장: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
