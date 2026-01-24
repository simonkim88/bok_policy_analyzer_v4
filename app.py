"""
한국은행 통화정책 톤 분석 대시보드

Streamlit 기반 실시간 분석 및 예측 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
from datetime import datetime

# 프로젝트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.sentiment_dict import SentimentDictionary
from src.nlp.tone_analyzer import ToneAnalyzer
from src.models.rate_predictor import RatePredictor
from src.utils.styles import get_custom_css
from src.views.analysis_view import render_analysis_view

# 페이지 설정
st.set_page_config(
    page_title="한국은행 통화정책 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 디렉토리
DATA_DIR = PROJECT_ROOT / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"


@st.cache_data
def load_tone_data():
    """톤 분석 결과 로드"""
    tone_path = ANALYSIS_DIR / "tone_index_results.csv"
    if not tone_path.exists():
        st.error("톤 분석 결과 파일이 없습니다. 먼저 분석을 실행해주세요.")
        return None
    return pd.read_csv(tone_path)


@st.cache_resource
def load_predictor():
    """금리 예측 모델 로드"""
    predictor = RatePredictor()
    try:
        df = load_tone_data()
        if df is not None:
            predictor.train(df)
        return predictor
    except Exception as e:
        st.warning(f"예측 모델 로드 실패: {e}")
        return predictor


def create_tone_gauge(tone_value):
    """톤 게이지 차트 생성"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=tone_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "BOK Tone Index", 'font': {'size': 24}},
        delta={'reference': 0, 'increasing': {'color': "red"}, 'decreasing': {'color': "blue"}},
        gauge={
            'axis': {'range': [-1, 1], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [-1, -0.3], 'color': '#1f77b4'},  # Strong Dovish
                {'range': [-0.3, -0.1], 'color': '#aec7e8'},  # Moderate Dovish
                {'range': [-0.1, 0.1], 'color': '#f0f0f0'},  # Neutral
                {'range': [0.1, 0.3], 'color': '#ffbb78'},  # Moderate Hawkish
                {'range': [0.3, 1], 'color': '#ff7f0e'},  # Strong Hawkish
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': tone_value
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        font={'size': 16}
    )

    return fig


def create_timeline_chart(df):
    """시계열 톤 지수 차트"""
    fig = go.Figure()

    # 톤 지수 라인
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(df['meeting_date']),
        y=df['tone_index'],
        mode='lines+markers',
        name='Tone Index',
        line=dict(color='royalblue', width=3),
        marker=dict(size=8),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Tone: %{y:.3f}<extra></extra>'
    ))

    # 중립선
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="중립")
    fig.add_hline(y=0.3, line_dash="dot", line_color="orange", annotation_text="강한 매파")
    fig.add_hline(y=-0.3, line_dash="dot", line_color="blue", annotation_text="강한 비둘기파")

    fig.update_layout(
        title="BOK Tone Index 시계열 추이",
        xaxis_title="회의 날짜",
        yaxis_title="Tone Index",
        hovermode='x unified',
        height=400,
        showlegend=False
    )

    return fig


def create_prediction_chart(prediction):
    """금리 결정 확률 차트"""
    data = {
        '결정': ['인상', '동결', '인하'],
        '확률': [prediction.prob_hike * 100, prediction.prob_hold * 100, prediction.prob_cut * 100]
    }

    colors = ['#ff7f0e', '#f0f0f0', '#1f77b4']

    fig = go.Figure(data=[
        go.Bar(
            x=data['결정'],
            y=data['확률'],
            marker_color=colors,
            text=[f"{p:.1f}%" for p in data['확률']],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title="다음 금통위 금리 결정 확률",
        yaxis_title="확률 (%)",
        height=350,
        showlegend=False
    )

    return fig


def create_keyword_chart(tone_result):
    """주요 키워드 차트"""
    # 상위 키워드 추출
    top_hawkish = tone_result['top_hawkish'].split(", ")[:5]
    top_dovish = tone_result['top_dovish'].split(", ")[:5]

    # 데이터프레임 생성
    keywords = top_hawkish + top_dovish
    types = ['매파'] * len(top_hawkish) + ['비둘기파'] * len(top_dovish)
    values = list(range(len(top_hawkish), 0, -1)) + list(range(len(top_dovish), 0, -1))

    df_keywords = pd.DataFrame({
        '키워드': keywords,
        '유형': types,
        '빈도': values
    })

    fig = px.bar(
        df_keywords,
        x='빈도',
        y='키워드',
        color='유형',
        orientation='h',
        title="주요 키워드 분포",
        color_discrete_map={'매파': '#ff7f0e', '비둘기파': '#1f77b4'}
    )

    fig.update_layout(height=400)

    return fig


def main():
    """메인 대시보드"""
    
    # Custom CSS 적용
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # 헤더
    st.markdown("""
        <h1 style='text-align: center; margin-bottom: 2rem;'>
            🏦 한국은행 통화정책 톤 분석 대시보드 <span style="font-size: 0.5em; color: #ff6b6b;">(주의: 비공식/테스트용임!)</span>
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # 데이터 로드
    df = load_tone_data()
    if df is None:
        st.stop()

    predictor = load_predictor()
    
    # Session State 초기화
    if 'show_analysis' not in st.session_state:
        st.session_state.show_analysis = False
    if 'selected_meeting' not in st.session_state:
        st.session_state.selected_meeting = '2025_11_27'  # 기본값: 2025년 11월 27일
    
    # --- 상단 Meeting Selection Area ---
    meeting_dates = df['meeting_date_str'].tolist()
    
    # 최신 5개 회의만 선택 (역순 정렬)
    recent_meetings = sorted(meeting_dates, reverse=True)[:5]
    
    # 날짜를 더 보기 좋게 포맷팅 (2025_11_27 -> Nov 27, 2025)
    def format_date_short(date_str):
        """날짜 문자열을 짧게 포맷팅"""
        parts = date_str.split('_')
        if len(parts) == 3:
            year, month, day = parts
            months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            try:
                return f"{months[int(month)]} {int(day)}, {year}"
            except:
                return date_str.replace('_', '-')
        return date_str.replace('_', '-')
    
    # Custom CSS for meeting buttons and analysis button
    st.markdown("""
    <style>
    /* Meeting Date Buttons with Checkbox */
    .meeting-btn {
        background: linear-gradient(135deg, #1E3A5F 0%, #0D2137 100%);
        border: 2px solid #2C5282;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
    }
    .meeting-btn:hover {
        border-color: #4299E1;
        box-shadow: 0 0 20px rgba(66, 153, 225, 0.4);
    }
    .meeting-btn.selected {
        border: 3px solid #00D9FF;
        box-shadow: 0 0 25px rgba(0, 217, 255, 0.6);
        background: linear-gradient(135deg, #1A4A7A 0%, #0D3A5F 100%);
    }
    
    /* Checkbox styling */
    .checkbox-visual {
        width: 24px;
        height: 24px;
        border: 2px solid #4299E1;
        border-radius: 6px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(0,0,0,0.2);
    }
    .checkbox-visual.checked {
        background: linear-gradient(135deg, #00D9FF 0%, #00B4D8 100%);
        border-color: #00D9FF;
    }
    .checkbox-visual .checkmark {
        color: white;
        font-size: 16px;
        font-weight: bold;
    }
    
    .meeting-btn-date {
        font-size: 1rem;
        font-weight: 700;
        color: white;
        margin-bottom: 3px;
    }
    .meeting-btn-label {
        font-size: 0.7rem;
        color: #90CAF9;
    }
    
    /* Earlier meetings button */
    .earlier-btn {
        background: linear-gradient(135deg, #2D3748 0%, #1A202C 100%);
        border: 2px dashed #4A5568;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .earlier-btn:hover {
        border-color: #718096;
        background: linear-gradient(135deg, #3D4A5C 0%, #2A3441 100%);
    }
    
    /* Hide selection buttons but keep them clickable over the checkbox area */
    .stColumn > div > div > div[data-testid="stButton"] {
        position: relative;
        margin-top: -100px;
        height: 100px;
        z-index: 10;
    }
    .stColumn > div > div > div[data-testid="stButton"] > button {
        background: transparent !important;
        border: none !important;
        color: transparent !important;
        height: 100px !important;
        width: 100% !important;
        cursor: pointer !important;
        box-shadow: none !important;
    }
    .stColumn > div > div > div[data-testid="stButton"] > button:hover {
        background: transparent !important;
        box-shadow: none !important;
    }
    
    /* Main Analysis Button - Matching header font size (1.5rem) */
    .main-analysis-container div[data-testid="stButton"] {
        margin-top: 0 !important;
        height: auto !important;
    }
    .main-analysis-container div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #FF6B00 0%, #FF8C00 50%, #FFA500 100%) !important;
        color: white !important;
        border: 4px solid #FFDD00 !important;
        padding: 30px 40px !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        letter-spacing: 2px !important;
        border-radius: 20px !important;
        min-height: 100px !important;
        box-shadow: 
            0 0 20px #FFDD00,
            0 0 40px rgba(255, 221, 0, 0.6),
            0 0 60px rgba(255, 221, 0, 0.4),
            0 20px 40px rgba(0, 0, 0, 0.4) !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3) !important;
        animation: float-glow 2s ease-in-out infinite !important;
        transition: all 0.4s ease !important;
        transform: translateY(-5px) !important;
    }
    .main-analysis-container div[data-testid="stButton"] > button:hover {
        transform: translateY(-15px) scale(1.03) !important;
        border-color: #FFFFFF !important;
        box-shadow: 
            0 0 30px #FFFFFF,
            0 0 60px rgba(255, 255, 255, 0.6),
            0 0 90px rgba(255, 221, 0, 0.5),
            0 30px 50px rgba(0, 0, 0, 0.5) !important;
        background: linear-gradient(135deg, #FF8C00 0%, #FFA500 50%, #FFB700 100%) !important;
    }
    
    @keyframes float-glow {
        0%, 100% { 
            transform: translateY(-5px);
            box-shadow: 0 0 20px #FFDD00, 0 0 40px rgba(255, 221, 0, 0.6), 0 0 60px rgba(255, 221, 0, 0.4), 0 20px 40px rgba(0, 0, 0, 0.4);
        }
        50% { 
            transform: translateY(-12px);
            box-shadow: 0 0 30px #FFDD00, 0 0 50px rgba(255, 221, 0, 0.7), 0 0 80px rgba(255, 221, 0, 0.5), 0 25px 50px rgba(0, 0, 0, 0.5);
        }
    }

    /* Container alignment */
    .selection-container {
        background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 100%);
        padding: 30px;
        border-radius: 16px;
        margin-bottom: 30px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Session state for earlier meetings
    if 'show_earlier' not in st.session_state:
        st.session_state.show_earlier = False
    
    st.markdown('<div class="selection-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 25px;">
        <span style="font-size: 2rem; margin-right: 15px;">📅</span>
        <span style="font-size: 1.5rem; color: #64B5F6; font-weight: 600;">
            분석 대상 회의 선택
    </div>
    """, unsafe_allow_html=True)
    
    # Meeting selection with styled checkboxes + clickable buttons
    cols = st.columns(6)
    
    for i, meeting_date in enumerate(recent_meetings):
        with cols[i]:
            is_selected = st.session_state.selected_meeting == meeting_date
            selected_class = "selected" if is_selected else ""
            formatted = format_date_short(meeting_date)
            checkbox_class = "checked" if is_selected else ""
            checkmark = "✓" if is_selected else ""
            
            # Display styled meeting button with checkbox visual
            st.markdown(f"""
            <div class="meeting-btn {selected_class}">
                <div class="checkbox-visual {checkbox_class}">
                    <span class="checkmark">{checkmark}</span>
                </div>
                <div class="meeting-btn-date">{formatted}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Clickable button (invisible) that selects this meeting
            if st.button(" ", key=f"btn_{meeting_date}"):
                st.session_state.selected_meeting = meeting_date
                st.session_state.show_analysis = False
                st.rerun()
    
    # "Earlier meetings" button in 6th column
    with cols[5]:
        st.markdown("""
        <div class="earlier-btn">
            <span style="font-size: 1.5rem; margin-bottom: 5px;">📂</span>
            <span style="color: #A0AEC0; font-size: 0.85rem; font-weight: 600;">더 이전</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("펼치기", key="btn_earlier_toggle"):
            st.session_state.show_earlier = not st.session_state.show_earlier
            st.rerun()
    
    # Earlier meetings section (if expanded)
    if st.session_state.show_earlier:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="color: #90CAF9; font-size: 1rem; margin-bottom: 15px; font-weight: 600;">
            📁 더 이전 발표들
        </div>
        """, unsafe_allow_html=True)
        
        # Get next 5 older meetings
        earlier_meetings = sorted(meeting_dates, reverse=True)[5:10]
        earlier_cols = st.columns(5)
        
        for i, meeting_date in enumerate(earlier_meetings):
            with earlier_cols[i]:
                is_selected = st.session_state.selected_meeting == meeting_date
                selected_class = "selected" if is_selected else ""
                formatted = format_date_short(meeting_date)
                checkbox_class = "checked" if is_selected else ""
                checkmark = "✓" if is_selected else ""
                
                st.markdown(f"""
                <div class="meeting-btn {selected_class}">
                    <div class="checkbox-visual {checkbox_class}">
                        <span class="checkmark">{checkmark}</span>
                    </div>
                    <div class="meeting-btn-date">{formatted}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(" ", key=f"btn_earlier_{meeting_date}"):
                    st.session_state.selected_meeting = meeting_date
                    st.session_state.show_analysis = False
                    st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # BIG ANALYSIS BUTTON with glowing border and floating effect
    selected_formatted = format_date_short(st.session_state.selected_meeting)
    
    # Apply CSS with high specificity right before the button
    st.markdown("""
    <style>
    /* Force apply to the main analysis button with very high specificity */
    section.main > div > div > div > div > div[data-testid="stButton"]:last-of-type > button,
    [data-testid="stButton"] > button[kind="secondary"] {
        background: linear-gradient(135deg, #1E5799 0%, #2989D8 50%, #207cca 100%) !important;
        color: white !important;
        border: 3px solid #64B5F6 !important;
        padding: 30px 40px !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        letter-spacing: 2px !important;
        border-radius: 20px !important;
        min-height: 100px !important;
        box-shadow: 
            0 0 20px rgba(100, 181, 246, 0.6),
            0 0 40px rgba(100, 181, 246, 0.3),
            0 10px 30px rgba(0, 0, 0, 0.3) !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important;
        transform: translateY(-3px) !important;
        transition: all 0.3s ease !important;
    }
    
    section.main > div > div > div > div > div[data-testid="stButton"]:last-of-type > button:hover,
    [data-testid="stButton"] > button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #2989D8 0%, #3498db 50%, #5dade2 100%) !important;
        border-color: #90CAF9 !important;
        box-shadow: 
            0 0 30px rgba(144, 202, 249, 0.7),
            0 0 60px rgba(100, 181, 246, 0.4),
            0 15px 40px rgba(0, 0, 0, 0.4) !important;
        transform: translateY(-6px) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button(f"🔍 {selected_formatted} 발표 심층 분석 보기", key="main_analysis_btn", use_container_width=True):
        st.session_state.show_analysis = not st.session_state.show_analysis
        st.rerun()
    
    # 선택된 회의 데이터
    selected_meeting = st.session_state.selected_meeting

    # 선택된 회의 데이터
    selected_row = df[df['meeting_date_str'] == selected_meeting].iloc[0]
    
    # --- Analysis View 또는 Dashboard View 표시 ---
    
    if st.session_state.show_analysis:
        # 분석 리포트 화면
        if st.button("← 대시보드로 돌아가기 (Back to Dashboard)"):
             st.session_state.show_analysis = False
             st.rerun()
             
        render_analysis_view(selected_row)
        
    else:
        # 기존 대시보드 화면
        tone_value = selected_row['tone_index']
        interpretation = selected_row['interpretation']

        # 사이드바 (설정 메뉴 유지, 회의 선택은 제거)
        with st.sidebar:
            st.header("⚙️ 설정")
            # 통계 정보
            st.subheader("📊 전체 통계")
            st.metric("분석 회의 수", f"{len(df)}회")
            st.metric("평균 톤 지수", f"{df['tone_index'].mean():+.3f}")
            st.metric("최근 톤 지수", f"{df.iloc[-1]['tone_index']:+.3f}")

            st.markdown("---")
            st.markdown("### 💡 정보")
            st.markdown("""
            **Tone Index 해석:**
            - **+0.3 이상**: 강한 매파 (긴축)
            - **+0.1 ~ +0.3**: 온건 매파
            - **-0.1 ~ +0.1**: 중립
            - **-0.3 ~ -0.1**: 온건 비둘기파
            - **-0.3 이하**: 강한 비둘기파 (완화)
            """)

        # Row 1: 현재 톤 및 예측
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📍 현재 통화정책 톤")
            st.plotly_chart(create_tone_gauge(tone_value), use_container_width=True)

            st.markdown(f"""
            <div style="text-align: center; padding: 20px; background-color: #2C2C2C; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); color: #E0E0E0;">
                <p style="margin: 0; font-size: 0.9em; color: #B0B0B0;">회의: {selected_meeting.replace('_', '-')}</p>
                <h2 style="margin: 15px 0; font-family: sans-serif; color: {'#ff7f0e' if tone_value > 0 else '#1f77b4'}; text-shadow: 0 1px 1px rgba(0,0,0,0.5);">
                    {interpretation}
                </h2>
                <div style="font-size: 1.2em; margin-top: 10px; font-weight: bold; padding: 5px 15px; background: rgba(255,255,255,0.1); display: inline-block; border-radius: 20px;">
                    Tone: {tone_value:+.3f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.subheader("🔮 다음 금통위 예측")

            # 예측 실행
            prediction = predictor.predict(selected_row.to_dict())

            if prediction:
                st.plotly_chart(create_prediction_chart(prediction), use_container_width=True)

                # 예측 결과 카드 (다크 테마 적용)
                st.markdown(f"""
                <div style="padding: 20px; background-color: #1E1E1E; border-radius: 10px; border-left: 5px solid #1976d2; box-shadow: 0 4px 6px rgba(0,0,0,0.3); color: #E0E0E0;">
                    <h3 style="margin-top: 0; color: #448aff;">예상 결정: {prediction.predicted_action}</h3>
                    <div style="margin: 15px 0; font-size: 1.1em;">
                        신뢰도: <span style="font-weight: bold; color: {'#ef5350' if prediction.confidence < 0.6 else '#66bb6a'};">{prediction.confidence:.1%}</span>
                    </div>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.9em; color: #B0B0B0;">
                        <span style="color: #ff9800;">인상 {prediction.prob_hike:.1%}</span> | 
                        <span style="color: #9e9e9e;">동결 {prediction.prob_hold:.1%}</span> | 
                        <span style="color: #42a5f5;">인하 {prediction.prob_cut:.1%}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Row 2: 시계열 차트 및 키워드
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📈 Tone Index 시계열 추이")
            st.plotly_chart(create_timeline_chart(df), use_container_width=True)

        with col2:
            st.subheader("🔑 주요 키워드")
            st.plotly_chart(create_keyword_chart(selected_row), use_container_width=True)

        st.markdown("---")

        # Row 3: 상세 데이터 테이블
        st.subheader("📋 전체 데이터")

        # 데이터 표시 옵션
        show_details = st.checkbox("상세 정보 표시", value=False)

        if show_details:
            display_cols = ['meeting_date_str', 'tone_index', 'interpretation',
                           'hawkish_score', 'dovish_score', 'total_sentences']
        else:
            display_cols = ['meeting_date_str', 'tone_index', 'interpretation']

        st.dataframe(
            df.sort_values('meeting_date', ascending=False)[display_cols],
            use_container_width=True,
            height=400
        )

    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>한국은행 통화정책 텍스트 분석 기반 AI 예측 모델</p>
        <p>데이터 출처: 한국은행 금융통화위원회 의사록</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
