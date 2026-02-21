# pyright: basic
import ast
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _parse_meeting_label(meeting_date_str):
    date_str = str(meeting_date_str or '')
    parts = date_str.split('_')
    try:
        if len(parts) == 3:
            return datetime.strptime(date_str, '%Y_%m_%d').strftime('%Y-%m-%d')
        if len(parts) == 2:
            return datetime.strptime(date_str, '%Y_%m').strftime('%Y-%m')
    except ValueError:
        return date_str.replace('_', '-')
    return date_str.replace('_', '-')


def _parse_keywords(raw_value, limit=5):
    if raw_value is None:
        return []
    text = str(raw_value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(',') if item.strip()][:limit]


def _extract_sentence_tones(row):
    keys = ['sentence_tones', 'sentence_tone_values', 'tone_distribution', 'sentence_level_tones']
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue
        if isinstance(value, list):
            tones = [_safe_float(v, 0.0) for v in value]
            return tones if tones else None
        text = str(value).strip()
        if not text:
            continue
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                tones = [_safe_float(v, 0.0) for v in parsed]
                return tones if tones else None
        except (ValueError, SyntaxError):
            pass
        if ',' in text:
            tones = [_safe_float(v.strip(), 0.0) for v in text.split(',') if v.strip()]
            if tones:
                return tones
    return None


def _render_metric_card(title, value, color):
    st.markdown(
        f'<div style="background: linear-gradient(145deg, #1E1E2E 0%, #1B263B 100%); border-left: 4px solid {color}; padding: 16px; border-radius: 12px; min-height: 120px; box-shadow: 0 6px 20px rgba(0,0,0,0.25);"><p style="margin: 0; color: #90A4AE; font-size: 0.82rem;">{title}</p><h3 style="margin: 10px 0 0 0; color: #E0E0E0; font-size: 1.8rem;">{value}</h3></div>',
        unsafe_allow_html=True,
    )


def _load_macro_data(meeting_date_str: str) -> dict:
    """Load macro indicators from ECOS CSVs closest to meeting date."""
    import os

    base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', '08_ecos')
    result = {}

    try:
        br = pd.read_csv(os.path.join(base_path, 'base_rate', 'base_rate.csv'))
        br['DATA_VALUE'] = pd.to_numeric(br['DATA_VALUE'], errors='coerce')
        values = br['DATA_VALUE'].dropna()
        result['base_rate'] = values.iloc[-1] if not values.empty else None
        result['base_rate_prev'] = values.iloc[-2] if len(values) > 1 else None
    except Exception:
        result['base_rate'] = None
        result['base_rate_prev'] = None

    try:
        cpi = pd.read_csv(os.path.join(base_path, 'cpi', 'cpi_total.csv'))
        cpi['DATA_VALUE'] = pd.to_numeric(cpi['DATA_VALUE'], errors='coerce')
        cpi = cpi.sort_values('TIME')
        cpi['YoY'] = cpi['DATA_VALUE'].pct_change(12) * 100
        yoy = cpi['YoY'].dropna()
        result['cpi_yoy'] = yoy.iloc[-1] if not yoy.empty else None
    except Exception:
        result['cpi_yoy'] = None

    try:
        gdp = pd.read_csv(os.path.join(base_path, 'gdp', 'gdp_real.csv'))
        gdp['DATA_VALUE'] = pd.to_numeric(gdp['DATA_VALUE'], errors='coerce')
        gdp = gdp.sort_values('TIME')
        gdp['YoY'] = gdp['DATA_VALUE'].pct_change(4) * 100
        yoy = gdp['YoY'].dropna()
        result['gdp_yoy'] = yoy.iloc[-1] if not yoy.empty else None
    except Exception:
        result['gdp_yoy'] = None

    try:
        fx = pd.read_csv(os.path.join(base_path, 'exchange_rates', 'usd_krw.csv'))
        fx['DATA_VALUE'] = pd.to_numeric(fx['DATA_VALUE'], errors='coerce')
        values = fx['DATA_VALUE'].dropna()
        result['usd_krw'] = values.iloc[-1] if not values.empty else None
    except Exception:
        result['usd_krw'] = None

    try:
        hc = pd.read_csv(os.path.join(base_path, 'household_debt', 'household_credit.csv'))
        hc['DATA_VALUE'] = pd.to_numeric(hc['DATA_VALUE'], errors='coerce')
        values = hc['DATA_VALUE'].dropna()
        result['household_credit'] = values.iloc[-1] if not values.empty else None
    except Exception:
        result['household_credit'] = None

    try:
        ktb = pd.read_csv(os.path.join(base_path, 'bond_yields', 'ktb_3y.csv'))
        ktb['DATA_VALUE'] = pd.to_numeric(ktb['DATA_VALUE'], errors='coerce')
        values = ktb['DATA_VALUE'].dropna()
        result['ktb_3y'] = values.iloc[-1] if not values.empty else None
    except Exception:
        result['ktb_3y'] = None

    if meeting_date_str:
        return result
    return result


def _render_macro_card(title, value, subtitle, bg_color):
    st.markdown(
        f'''<div style="background: {bg_color}; padding: 20px; border-radius: 12px; text-align: center; min-height: 100px;">
        <p style="margin: 0; color: rgba(255,255,255,0.85); font-size: 0.8rem;">{title}</p>
        <h2 style="margin: 8px 0 4px 0; color: white; font-size: 1.9rem;">{value}</h2>
        <p style="margin: 0; color: rgba(255,255,255,0.75); font-size: 0.78rem;">{subtitle}</p>
        </div>''',
        unsafe_allow_html=True,
    )


def _generate_key_summary(row, macro, meeting_label):
    tone = _safe_float(row.get('tone_index'))
    br = macro.get('base_rate')
    cpi = macro.get('cpi_yoy')

    br_str = f'{br:.2f}%' if br is not None else 'N/A'
    cpi_str = f'{cpi:.1f}%' if cpi is not None else 'N/A'

    if tone > 0.1:
        tone_desc = '매파적(긴축적) 성향'
    elif tone < -0.1:
        tone_desc = '비둘기파적(완화적) 성향'
    else:
        tone_desc = '중립적 성향'

    summary = f'한국은행 금융통화위원회는 {meeting_label} 회의에서 기준금리를 {br_str}로 유지하기로 결정했습니다. '
    summary += f'톤 분석 결과 {tone_desc}을 보이고 있으며, 소비자물가 상승률은 {cpi_str} 수준입니다.'
    return summary


def _render_background_card(title, subtitle, items):
    items_html = ''.join(f'<li style="color: #B0BEC5; margin: 4px 0;">{item}</li>' for item in items)
    return f'''<div style="background: #1E1E2E; border-radius: 10px; padding: 20px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;">
        <h4 style="color: #E0E0E0; margin: 0 0 12px 0;">{title}</h4>
        <p style="color: #78909C; font-weight: 600; margin: 0 0 6px 0;">{subtitle}</p>
        <ul style="padding-left: 20px; margin: 0;">{items_html}</ul>
    </div>'''


def _render_risk_card(icon, title, line1, line2, bg_color):
    st.markdown(
        f'''<div style="background: {bg_color}; padding: 24px; border-radius: 12px; text-align: center; min-height: 140px;">
        <p style="font-size: 2rem; margin: 0;">{icon}</p>
        <h3 style="color: white; margin: 8px 0;">{title}</h3>
        <p style="color: rgba(255,255,255,0.8); font-size: 0.82rem; margin: 4px 0;">{line1}</p>
        <p style="color: rgba(255,255,255,0.8); font-size: 0.82rem; margin: 4px 0;">{line2}</p>
        </div>''',
        unsafe_allow_html=True,
    )


def _generate_ai_commentary(row, macro, previous_row):
    tone = _safe_float(row.get('tone_index'))
    prev_tone = _safe_float(previous_row.get('tone_index')) if previous_row else None
    cpi = macro.get('cpi_yoy')
    gdp = macro.get('gdp_yoy')
    fx = macro.get('usd_krw')

    p1 = f'톤 분석 결과, Tone Index는 {tone:+.3f}로 '
    if tone > 0.3:
        p1 += '강한 매파적 성향을 보였습니다.'
    elif tone > 0.1:
        p1 += '온건 매파적 성향을 보였습니다.'
    elif tone > -0.1:
        p1 += '중립적 성향을 보였습니다.'
    elif tone > -0.3:
        p1 += '온건 비둘기파적 성향을 보였습니다.'
    else:
        p1 += '강한 비둘기파적(완화적) 성향을 보였습니다.'

    if prev_tone is not None:
        p1 += f' 직전 대비 변화폭은 {tone - prev_tone:+.3f}p입니다.'
    if cpi is not None:
        p1 += f' 물가({cpi:.1f}%)가 목표 수준에 근접하고 '
    if gdp is not None:
        p1 += f'성장률({gdp:.1f}%)을 고려한 결과입니다.'

    p2 = ''
    if fx is not None and fx > 1400:
        p2 += f'다만, 아직 {fx:,.0f}원대 중후반에 머물고 있는 환율과 수도권 부동산 가격 불안이 조기 완화를 제약하는 핵심 요인입니다. '
    p2 += "위원들은 '성장과 물가 안정'을 강조하면서도 '금융안정'을 동시에 고려하여 신중한 접근이 필요하다는 시각을 보였습니다."

    return p1, p2


def _generate_implication(row, previous_row, macro):
    tone = _safe_float(row.get('tone_index'))
    prev_tone = _safe_float(previous_row.get('tone_index')) if previous_row else 0
    tone_shift = tone - prev_tone

    if tone_shift > 0.05:
        direction = '긴축 기조 충분히 유지하되, 향후 호율을 경기 부양으로 이동하고 있음을 시사'
    elif tone_shift < -0.05:
        direction = '통화정책의 초점이 경기 부양으로 이동하고 있음을 시사'
    else:
        direction = '통화정책 기조가 유지되고 있음을 시사'

    text = f'금번 회의에서는 물가 안정에 대한 자신감을 바탕으로 {direction}합니다. '
    text += '다만, 금융안정(환율, 가계부채)에 대한 경계감은 여전히 유지되고 있어 신중한 접근이 예상됩니다.'
    if macro.get('ktb_3y') is not None:
        text += f' 국고채 3년물은 {macro.get("ktb_3y"):.2f}%로 금리 경로 민감도가 높은 구간입니다.'
    return text


def _render_asset_card(icon, title, outlook, outlook_color, points):
    border_color = {
        'BULLISH': '#4CAF50',
        'NEUTRAL': '#FFC107',
        'BEARISH': '#F44336',
        'VOLATILE': '#F44336',
        'POLARIZED': '#FFC107',
        'STABLE': '#4CAF50',
    }
    bg_bar = {
        'BULLISH': '#1B5E20',
        'NEUTRAL': '#F57F17',
        'BEARISH': '#B71C1C',
        'VOLATILE': '#B71C1C',
        'POLARIZED': '#F57F17',
        'STABLE': '#1B5E20',
    }
    final_border = border_color.get(outlook, outlook_color)
    final_bar = bg_bar.get(outlook, '#424242')
    pts_html = ''.join(f'<li style="color: #B0BEC5; font-size: 0.78rem; margin: 3px 0;">•{p}</li>' for p in points)
    st.markdown(
        f'''
    <div style="background: #1E1E2E; border: 2px solid {final_border}; border-radius: 12px; padding: 20px; text-align: center; min-height: 250px;">
        <p style="font-size: 1.8rem; margin: 0;">{icon}</p>
        <h4 style="color: white; margin: 8px 0;">{title}</h4>
        <div style="background: {final_bar}; padding: 6px; border-radius: 6px; margin: 8px 0;">
            <span style="color: white; font-weight: 700; font-size: 0.85rem;">{outlook}</span>
        </div>
        <ul style="list-style: none; padding: 0; text-align: left; margin-top: 12px;">{pts_html}</ul>
    </div>''',
        unsafe_allow_html=True,
    )


def _tone_badge_html(value):
    if value > 0.1:
        return '<span style="background:#E65100;color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;">Hawkish</span>'
    if value < -0.1:
        return '<span style="background:#1565C0;color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;">Dovish</span>'
    return '<span style="background:#455A64;color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;">Neutral</span>'


def render_analysis_view(row, previous_row=None):
    row = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
    if previous_row is not None and hasattr(previous_row, 'to_dict'):
        previous_row = previous_row.to_dict()

    meeting_label = _parse_meeting_label(row.get('meeting_date_str'))
    tone_index = _safe_float(row.get('tone_index'))
    interpretation = str(row.get('interpretation', 'N/A'))
    hawkish_score = _safe_float(row.get('hawkish_score'))
    dovish_score = _safe_float(row.get('dovish_score'))
    total_sentences = int(_safe_float(row.get('total_sentences'), 0))
    top_hawkish = _parse_keywords(row.get('top_hawkish'))
    top_dovish = _parse_keywords(row.get('top_dovish'))

    st.markdown(
        f'<div style="background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 48%, #1E1E2E 100%); padding: 36px 30px; border-radius: 16px; margin-bottom: 24px; border: 1px solid rgba(100,181,246,0.2);"><p style="margin: 0; color: #64B5F6; letter-spacing: 2px; font-size: 0.82rem;">POLICY ANALYSIS REPORT</p><h1 style="margin: 10px 0 8px 0; color: white;">{meeting_label} 통화정책 톤 분석</h1><p style="margin: 0; color: #E0E0E0; font-size: 1.05rem;">판단: <span style="color: #00E676; font-weight: 700;">{interpretation}</span></p></div>',
        unsafe_allow_html=True,
    )

    st.markdown('## Executive Summary')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_metric_card('Tone Index', f'{tone_index:+.3f}', '#00E676')
    with c2:
        _render_metric_card('Hawkish Score', f'{hawkish_score:.1f}', '#FFAB40')
    with c3:
        _render_metric_card('Dovish Score', f'{dovish_score:.1f}', '#64B5F6')
    with c4:
        _render_metric_card('Sentence Count', f'{total_sentences:,}', '#CFD8DC')

    st.markdown('## Tone Decomposition')
    fig_decomp = go.Figure(go.Bar(y=['Hawkish', 'Dovish'], x=[hawkish_score, dovish_score], orientation='h', marker_color=['#FFAB40', '#64B5F6'], text=[f'{hawkish_score:.1f}', f'{dovish_score:.1f}'], textposition='outside'))
    fig_decomp.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, showlegend=False, xaxis_title='Keyword Weighted Score', yaxis_title='')
    st.plotly_chart(fig_decomp, use_container_width=True)

    st.markdown('## Top Keywords')
    k1, k2 = st.columns(2)
    hawk_df = pd.DataFrame({'Keyword': top_hawkish, 'Rank': range(1, len(top_hawkish) + 1)})
    dove_df = pd.DataFrame({'Keyword': top_dovish, 'Rank': range(1, len(top_dovish) + 1)})

    with k1:
        st.markdown('**Hawkish Top 5**')
        if hawk_df.empty:
            st.info('Hawkish keywords unavailable.')
        else:
            fig_hawk = go.Figure(go.Bar(x=list(reversed(hawk_df['Rank'].tolist())), y=list(reversed(hawk_df['Keyword'].tolist())), orientation='h', marker_color='#FFAB40', text=list(reversed(hawk_df['Rank'].tolist())), textposition='inside'))
            fig_hawk.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title='Relative Rank', yaxis_title='', showlegend=False, height=320)
            st.plotly_chart(fig_hawk, use_container_width=True)

    with k2:
        st.markdown('**Dovish Top 5**')
        if dove_df.empty:
            st.info('Dovish keywords unavailable.')
        else:
            fig_dove = go.Figure(go.Bar(x=list(reversed(dove_df['Rank'].tolist())), y=list(reversed(dove_df['Keyword'].tolist())), orientation='h', marker_color='#64B5F6', text=list(reversed(dove_df['Rank'].tolist())), textposition='inside'))
            fig_dove.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title='Relative Rank', yaxis_title='', showlegend=False, height=320)
            st.plotly_chart(fig_dove, use_container_width=True)

    st.markdown('## Comparison With Previous')
    if previous_row:
        p_tone = _safe_float(previous_row.get('tone_index'))
        p_hawk = _safe_float(previous_row.get('hawkish_score'))
        p_dove = _safe_float(previous_row.get('dovish_score'))
        p_sent = int(_safe_float(previous_row.get('total_sentences'), 0))

        d1, d2, d3, d4 = st.columns(4)
        d1.metric('Tone Index Delta', f'{tone_index:+.3f}', delta=f'{tone_index - p_tone:+.3f}')
        d2.metric('Hawkish Score Delta', f'{hawkish_score:.1f}', delta=f'{hawkish_score - p_hawk:+.1f}')
        d3.metric('Dovish Score Delta', f'{dovish_score:.1f}', delta=f'{dovish_score - p_dove:+.1f}')
        d4.metric('Sentence Count Delta', f'{total_sentences:,}', delta=f'{total_sentences - p_sent:+d}')

        compare_df = pd.DataFrame({'Metric': ['Tone Index', 'Hawkish Score', 'Dovish Score'], 'Previous': [p_tone, p_hawk, p_dove], 'Current': [tone_index, hawkish_score, dovish_score]})
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(name='Previous', x=compare_df['Metric'], y=compare_df['Previous'], marker_color='#78909C'))
        fig_comp.add_trace(go.Bar(name='Current', x=compare_df['Metric'], y=compare_df['Current'], marker_color='#00E676'))
        fig_comp.update_layout(barmode='group', template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=360, xaxis_title='', yaxis_title='Score', legend=dict(orientation='h', y=1.02, yanchor='bottom', x=1, xanchor='right'))
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info('직전 회의 데이터가 없어 비교를 생략합니다.')

    macro = _load_macro_data(str(row.get('meeting_date_str', '')))

    st.markdown('## 매크로 경제 지표')
    m1, m2, m3, m4 = st.columns(4)

    base_rate = macro.get('base_rate')
    base_rate_prev = macro.get('base_rate_prev')
    cpi_yoy = macro.get('cpi_yoy')
    gdp_yoy = macro.get('gdp_yoy')

    if base_rate is None:
        base_subtitle = '데이터 없음'
        base_value = 'N/A'
    else:
        base_value = f'{base_rate:.2f}%'
        if base_rate_prev is None:
            base_subtitle = '기준 추세 확인'
        elif base_rate > base_rate_prev:
            base_subtitle = '인상'
        elif base_rate < base_rate_prev:
            base_subtitle = '인하'
        else:
            base_subtitle = '동결 유지'

    if cpi_yoy is None:
        cpi_value = 'N/A'
        cpi_subtitle = '데이터 없음'
    else:
        cpi_value = f'{cpi_yoy:.1f}%'
        if cpi_yoy > 2.5:
            cpi_subtitle = '상방 압력'
        elif cpi_yoy >= 1.5:
            cpi_subtitle = '안정화 추세'
        else:
            cpi_subtitle = '하방 안정'

    if gdp_yoy is None:
        gdp_value = 'N/A'
        gdp_subtitle = '데이터 없음'
    else:
        gdp_value = f'{gdp_yoy:.1f}%'
        if gdp_yoy > 2:
            gdp_subtitle = '회복 기조'
        elif gdp_yoy >= 0:
            gdp_subtitle = '▲ 상방 리스크'
        else:
            gdp_subtitle = '경기 위축'

    with m1:
        _render_macro_card('기준금리', base_value, base_subtitle, '#1565C0')
    with m2:
        _render_macro_card('소비자물가(YoY)', cpi_value, cpi_subtitle, '#2E7D32')
    with m3:
        _render_macro_card('GDP 성장률(YoY)', gdp_value, gdp_subtitle, '#E65100')
    with m4:
        _render_macro_card('Tone Index', f'{tone_index:+.3f}', interpretation, '#7B1FA2')

    st.markdown('## 🎯 핵심 요약')
    summary_text = _generate_key_summary(row, macro, meeting_label)
    fx = macro.get('usd_krw')
    household_credit = macro.get('household_credit')

    hawk_for_points = top_hawkish[:2] if len(top_hawkish) >= 2 else (top_hawkish + ['매파 키워드'])[:2]
    dove_for_points = top_dovish[:2] if len(top_dovish) >= 2 else (top_dovish + ['비둘기파 키워드'])[:2]
    fx_text = f'{fx:,.0f}원대' if fx is not None else 'N/A'
    debt_text = f'{household_credit / 10000:.1f}조원' if household_credit is not None else 'N/A'

    key_points_html = ''.join(
        [
            f'<li style="color:#CFD8DC; margin:6px 0;"><span style="color:#66BB6A; font-weight:700;">경기 회복세:</span> {hawk_for_points[0]}, {hawk_for_points[1]} 등 매파적 요인 포착</li>',
            f'<li style="color:#CFD8DC; margin:6px 0;"><span style="color:#FFD54F; font-weight:700;">물가:</span> {dove_for_points[0]}, {dove_for_points[1]} 등 비둘기파적 요인 존재</li>',
            f'<li style="color:#CFD8DC; margin:6px 0;"><span style="color:#EF5350; font-weight:700;">금융안정:</span> 환율 {fx_text}, 가계신용 {debt_text} 등 리스크 요인 상존</li>',
        ]
    )

    st.markdown(
        f'''<div style="background: linear-gradient(145deg, #1E1E2E, #1B263B); border: 1px solid rgba(100,181,246,0.15); border-radius: 12px; padding: 24px;">
            <p style="color: #E0E0E0; line-height: 1.8;">{summary_text}</p>
            <p style="color: #90A4AE; margin-top: 16px;">주요 포인트:</p>
            <ul style="margin: 8px 0 0 0; padding-left: 18px;">{key_points_html}</ul>
        </div>''',
        unsafe_allow_html=True,
    )

    st.markdown('## 🔍 결정 배경 상세 분석')
    col_growth, col_price = st.columns(2)

    growth_positive = [f'{kw} 관련 상방 요인' for kw in top_hawkish[:3]] or ['상방 요인 데이터 부족']
    growth_concern = [f'{kw} 관련 하방 요인' for kw in top_dovish[:3]] or ['하방 요인 데이터 부족']
    cpi_trend = f'CPI YoY {cpi_yoy:.1f}%로 안정화 구간' if cpi_yoy is not None else 'CPI 추세 데이터 부족'
    price_stabilization = [cpi_trend] + [f'{kw} 중심 완화 신호' for kw in top_dovish[:2]]
    inflation_risk = [f'{kw} 중심 상방 압력' for kw in top_hawkish[:3]] or ['물가 상방 압력 데이터 부족']

    with col_growth:
        st.markdown(_render_background_card('📊 경제 성장', '긍정적 요인/기회', growth_positive), unsafe_allow_html=True)
        st.markdown(_render_background_card('📊 경제 성장', '우려 요인', growth_concern), unsafe_allow_html=True)

    with col_price:
        st.markdown(_render_background_card('🔥 물가 동향', '안정화 요인', price_stabilization), unsafe_allow_html=True)
        st.markdown(_render_background_card('🔥 물가 동향', '상방 리스크', inflation_risk), unsafe_allow_html=True)

    st.markdown('## 🏦 금융안정 리스크 요인')
    r1, r2, r3 = st.columns(3)
    with r1:
        line1 = f'달러/원 {fx:,.0f}원 수준' if fx is not None else '달러/원 데이터 없음'
        _render_risk_card('💱', '고환율 기조', line1, '거주자 해외투자 확대 영향', '#E65100')
    with r2:
        _render_risk_card('🏠', '주택가격', '수도권 중심 상승세 지속', '공급 부족 우려에 따른 불안', '#0277BD')
    with r3:
        debt_line = f'가계신용 {household_credit / 10000:.1f}조원' if household_credit is not None else '가계신용 데이터 없음'
        _render_risk_card('📈', '가계부채', debt_line, '수도권 주택담보대출 우려', '#7B1FA2')

    st.markdown('## 🎙️ 전문가 코멘터리 (AI Analysis)')
    p1, p2 = _generate_ai_commentary(row, macro, previous_row)
    st.markdown(
        f'''<div style="background:#1E1E2E; border-radius:12px; padding:24px; border:1px solid rgba(255,255,255,0.08);">
            <p style="margin:0; color:#90CAF9; font-weight:700;">🤖 BOK Policy Analyzer AI Insight</p>
            <p style="color:#E0E0E0; line-height:1.85; margin:12px 0 0 0;">{p1}</p>
            <p style="color:#B0BEC5; line-height:1.85; margin:12px 0 0 0;">{p2}</p>
        </div>''',
        unsafe_allow_html=True,
    )

    if previous_row:
        st.markdown('## 📝 결정문 문구 변화 분석 (Statement Analysis)')
        prev_label = _parse_meeting_label(previous_row.get('meeting_date_str'))
        prev_hawk = _parse_keywords(previous_row.get('top_hawkish'))
        prev_dove = _parse_keywords(previous_row.get('top_dovish'))

        prev_context_tone = _safe_float(previous_row.get('context_adjusted_tone'), _safe_float(previous_row.get('tone_index')))
        prev_policy_tone = _safe_float(previous_row.get('policy_intent_tone'), _safe_float(previous_row.get('tone_index')))
        curr_context_tone = _safe_float(row.get('context_adjusted_tone'), tone_index)
        curr_policy_tone = _safe_float(row.get('policy_intent_tone'), tone_index)

        prev_hawk_text = ', '.join(prev_hawk[:2]) if prev_hawk else 'N/A'
        prev_dove_text = ', '.join(prev_dove[:2]) if prev_dove else 'N/A'
        curr_hawk_text = ', '.join(top_hawkish[:2]) if top_hawkish else 'N/A'
        curr_dove_text = ', '.join(top_dovish[:2]) if top_dovish else 'N/A'

        table_html = f'''<div style="background:#1E1E2E;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px;">
            <table style="width:100%; border-collapse: collapse;">
                <thead>
                    <tr>
                        <th style="text-align:left; padding:10px; color:#CFD8DC; border-bottom:1px solid rgba(255,255,255,0.1);">항목</th>
                        <th style="text-align:left; padding:10px; color:#B0BEC5; border-bottom:1px solid rgba(255,255,255,0.1);">{prev_label} 표현 (직전)</th>
                        <th style="text-align:left; padding:10px; color:#90CAF9; border-bottom:1px solid rgba(255,255,255,0.1);">{meeting_label} 표현 (금번 변화)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding:10px; color:#E0E0E0; border-bottom:1px solid rgba(255,255,255,0.06);">성장</td>
                        <td style="padding:10px; color:#B0BEC5; border-bottom:1px solid rgba(255,255,255,0.06);">매파 키워드: {prev_hawk_text}, 비둘기파: {prev_dove_text} <span style="background:#6D4C41;color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;">Mixed</span></td>
                        <td style="padding:10px; color:#CFD8DC; border-bottom:1px solid rgba(255,255,255,0.06);">매파 키워드: {curr_hawk_text}, 비둘기파: {curr_dove_text} <span style="background:#6D4C41;color:white;padding:2px 8px;border-radius:999px;font-size:0.72rem;">Mixed</span></td>
                    </tr>
                    <tr>
                        <td style="padding:10px; color:#E0E0E0; border-bottom:1px solid rgba(255,255,255,0.06);">물가</td>
                        <td style="padding:10px; color:#B0BEC5; border-bottom:1px solid rgba(255,255,255,0.06);">물가 톤: {prev_context_tone:+.3f} {_tone_badge_html(prev_context_tone)}</td>
                        <td style="padding:10px; color:#CFD8DC; border-bottom:1px solid rgba(255,255,255,0.06);">물가 톤: {curr_context_tone:+.3f} {_tone_badge_html(curr_context_tone)}</td>
                    </tr>
                    <tr>
                        <td style="padding:10px; color:#E0E0E0;">정책방향</td>
                        <td style="padding:10px; color:#B0BEC5;">정책의도 톤: {prev_policy_tone:+.3f} {_tone_badge_html(prev_policy_tone)}</td>
                        <td style="padding:10px; color:#CFD8DC;">정책의도 톤: {curr_policy_tone:+.3f} {_tone_badge_html(curr_policy_tone)}</td>
                    </tr>
                </tbody>
            </table>
        </div>'''
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown('## 💡 시사점 (Implication)')
    implication_text = _generate_implication(row, previous_row, macro)
    st.markdown(
        f'''<div style="background:#1E1E2E;border:1px solid rgba(100,181,246,0.16);border-radius:12px;padding:22px;">
            <p style="margin:0;color:#E0E0E0;line-height:1.85;">{implication_text}</p>
            <p style="margin:12px 0 0 0;color:#90A4AE;">핵심 키워드: <span style="color:#64B5F6;font-weight:700;">물가 안정</span> · <span style="color:#FFB74D;font-weight:700;">정책 기조 유지</span> · <span style="color:#EF9A9A;font-weight:700;">금융안정 경계</span></p>
        </div>''',
        unsafe_allow_html=True,
    )

    st.markdown('## 🏛️ 향후 자산시장 전망 (Asset Outlook)')
    a1, a2, a3, a4 = st.columns(4)

    if tone_index < 0:
        bonds_outlook = 'BULLISH'
    elif tone_index > 0.2:
        bonds_outlook = 'BEARISH'
    else:
        bonds_outlook = 'NEUTRAL'

    if gdp_yoy is not None and gdp_yoy > 1.5 and tone_index < 0.1:
        stocks_outlook = 'BULLISH'
    else:
        stocks_outlook = 'NEUTRAL'

    if fx is not None and fx > 1400:
        fx_outlook = 'VOLATILE'
    else:
        fx_outlook = 'STABLE'

    real_estate_outlook = 'BEARISH' if tone_index > 0 else 'POLARIZED'

    stocks_points = [
        '반도체/AI 관련주 강세 지속',
        '내수주 흐름은 금리 인하 시차 존재',
        '미 관세 정책 등 대외 불확실성 상존',
    ]
    fx_points = [
        f'단기적 {fx:,.0f}원 후반대 유지 가능성' if fx is not None else '단기 환율 레인지 변동 가능성',
        '거주자 해외투자 수요가 하단 지지',
        '피벗 가시화 시 점진적 하락 전환',
    ]

    with a1:
        _render_asset_card('💵', '채권 (Bonds)', bonds_outlook, '#4CAF50', ['금리 인하 기대감 선반영 지속', '국채 자금 유입 본격화(수급 호재)', '중고채 금리 하향 안정화 전망'])
    with a2:
        _render_asset_card('📊', '주식 (Stocks)', stocks_outlook, '#FFC107', stocks_points)
    with a3:
        _render_asset_card('💱', '환율 (KRW/USD)', fx_outlook, '#F44336', fx_points)
    with a4:
        _render_asset_card('🏘️', '부동산 (Real Estate)', real_estate_outlook, '#FFC107', ['서울·수도권: 공급부족 우려로 강세', '지방: 미분양 누적으로 약세 지속', '금리 인하기 진입 시 수도권 자극 우려'])

    st.markdown('## Sentence Tone Distribution')
    sentence_tones = _extract_sentence_tones(row)
    if sentence_tones:
        hist = go.Figure(go.Histogram(x=sentence_tones, nbinsx=20, marker_color='#64B5F6', opacity=0.85))
        hist.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, xaxis_title='Sentence Tone Score', yaxis_title='Count', bargap=0.05)
        st.plotly_chart(hist, use_container_width=True)
    else:
        st.info('문장 단위 톤 분포 데이터가 없어 히스토그램을 표시하지 않습니다.')

    st.markdown('---')
    st.markdown(
        '<div style="background-color: #1E1E2E; border-radius: 10px; padding: 16px; border: 1px solid rgba(255,255,255,0.08);"><p style="margin: 0; color: #90A4AE; font-size: 0.88rem;">본 리포트는 텍스트 기반 정량 분석 결과이며 투자 판단의 직접적 근거로 사용될 수 없습니다.</p></div>',
        unsafe_allow_html=True,
    )
