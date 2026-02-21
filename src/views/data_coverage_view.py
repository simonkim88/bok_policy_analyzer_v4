# pyright: basic
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / 'data'

DATA_CATEGORIES = [
    ('01_minutes', '금통위 의사록'),
    ('02_decision_statements', '통화정책방향 결정문'),
    ('03_press_conferences', '총재 기자간담회'),
    ('04_stability_reports', '금융안정보고서'),
    ('05_policy_reports', '통화신용정책보고서'),
    ('06_economic_outlook', '경제전망보고서'),
    ('07_research_papers', 'BOK 연구자료'),
    ('08_ecos', 'ECOS 경제지표'),
    ('09_market_data', '시장 데이터'),
    ('10_news_sentiment', '뉴스 감성 데이터'),
    ('11_household_finance', '금융안정 지표'),
    ('analysis', '분석 결과'),
    ('db', '데이터베이스'),
]


def _status_from_count(file_count):
    if file_count > 10:
        return '양호', '#00E676'
    if file_count > 0:
        return '부분', '#FFAB40'
    return '부족', '#FF5252'


def _scan_category(category_path):
    if not category_path.exists():
        return 0, '-', '-'

    files = [f for f in category_path.rglob('*') if f.is_file()]
    if not files:
        return 0, '-', '-'

    mtimes = sorted([datetime.fromtimestamp(f.stat().st_mtime) for f in files])
    date_range = f'{mtimes[0].strftime("%Y-%m-%d")} ~ {mtimes[-1].strftime("%Y-%m-%d")}'
    last_updated = mtimes[-1].strftime('%Y-%m-%d %H:%M')
    return len(files), date_range, last_updated


def render_data_coverage_view():
    st.markdown('''
    <div style="background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 50%, #1E1E2E 100%);
                padding: 28px; border-radius: 14px; border: 1px solid rgba(100,181,246,0.2); margin-bottom: 16px;">
        <h2 style="margin: 0; color: #E0E0E0;">데이터 커버리지 대시보드</h2>
        <p style="margin: 8px 0 0 0; color: #90A4AE;">카테고리별 파일 수, 갱신 시점, 커버리지 상태를 점검합니다.</p>
    </div>
    ''', unsafe_allow_html=True)

    records = []
    for category, label in DATA_CATEGORIES:
        category_path = DATA_DIR / category
        file_count, date_range, last_updated = _scan_category(category_path)
        status_text, status_color = _status_from_count(file_count)
        records.append(
            {
                '카테고리': category,
                '설명': label,
                '파일 수': file_count,
                '기간': date_range,
                '최종 갱신': last_updated,
                '상태': status_text,
                '색상': status_color,
            }
        )

    coverage_df = pd.DataFrame(records)

    total_files = int(coverage_df['파일 수'].sum())
    covered_categories = int((coverage_df['파일 수'] > 0).sum())
    healthy_categories = int((coverage_df['파일 수'] > 10).sum())

    m1, m2, m3 = st.columns(3)
    m1.metric('총 파일 수', f'{total_files:,}')
    m2.metric('데이터 보유 카테고리', f'{covered_categories}/{len(DATA_CATEGORIES)}')
    m3.metric('양호 카테고리', f'{healthy_categories}/{len(DATA_CATEGORIES)}')

    heatmap = go.Figure(
        data=go.Heatmap(
            z=[coverage_df['파일 수'].tolist()],
            x=coverage_df['카테고리'].tolist(),
            y=['File Coverage'],
            colorscale=[
                [0.0, '#FF5252'],
                [0.2, '#FFAB40'],
                [1.0, '#00E676'],
            ],
            colorbar=dict(title='Files'),
            hovertemplate='<b>%{x}</b><br>파일 수: %{z}<extra></extra>',
        )
    )
    heatmap.update_layout(
        title='카테고리별 파일 커버리지 히트맵',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=280,
    )
    st.plotly_chart(heatmap, use_container_width=True)

    display_df = coverage_df[['카테고리', '설명', '파일 수', '기간', '최종 갱신', '상태']].copy()

    def _status_style(value):
        if value == '양호':
            return 'color: #00E676; font-weight: 700;'
        if value == '부분':
            return 'color: #FFAB40; font-weight: 700;'
        return 'color: #FF5252; font-weight: 700;'

    styled = display_df.style.applymap(_status_style, subset=['상태'])
    st.dataframe(styled, use_container_width=True, hide_index=True)
