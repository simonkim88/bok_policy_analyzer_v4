"""
전문가 설정 뷰

전문가가 다음 사항을 조정할 수 있는 UI:
- 키워드 가중치
- 톤 지수 모델 파라미터 (α, β, γ)
- 설정 저장 및 복원
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.sentiment_dict import SentimentDictionary
from src.data.database import DatabaseManager


def render_settings_view():
    """전문가 설정 페이지 렌더링"""

    st.title("⚙️ 전문가 설정")

    st.markdown("""
    이 페이지에서는 전문가가 통화정책 톤 분석 모델의 파라미터를 조정할 수 있습니다.
    - **키워드 가중치**: 각 키워드가 톤 지수에 미치는 영향력 조정
    - **모델 파라미터**: 텍스트, 시장, 뉴스의 가중치 조정
    """)

    st.markdown("---")

    # 데이터베이스 및 감성 사전 로드
    db = DatabaseManager()
    sentiment_dict = SentimentDictionary()

    # 세션 상태 초기화
    if 'settings_modified' not in st.session_state:
        st.session_state.settings_modified = False

    # 탭 구성
    tab1, tab2, tab3 = st.tabs([
        "📊 키워드 가중치",
        "🔧 모델 파라미터",
        "💾 설정 관리"
    ])

    # ===== 탭 1: 키워드 가중치 조정 =====
    with tab1:
        render_keyword_weights_tab(db, sentiment_dict)

    # ===== 탭 2: 모델 파라미터 =====
    with tab2:
        render_model_parameters_tab(db)

    # ===== 탭 3: 설정 관리 =====
    with tab3:
        render_settings_management_tab(db, sentiment_dict)


def render_keyword_weights_tab(db: DatabaseManager, sentiment_dict: SentimentDictionary):
    """키워드 가중치 조정 탭"""

    st.header("📊 키워드 가중치 조정")

    st.markdown("""
    키워드의 가중치를 조정하여 톤 지수 계산에 미치는 영향력을 변경할 수 있습니다.
    - 가중치가 높을수록 해당 키워드의 영향력이 큽니다.
    - 기본값은 AI가 설정한 초기 가중치입니다.
    """)

    # 현재 활성 가중치 로드
    active_weights = db.get_active_weights()

    # 전체 키워드 정보 로드
    df_keywords = db.get_all_keywords()

    # 매파/비둘기파 분리
    df_hawkish = df_keywords[df_keywords['polarity'] == 'hawkish'].sort_values('active_weight', ascending=False)
    df_dovish = df_keywords[df_keywords['polarity'] == 'dovish'].sort_values('active_weight', ascending=False)

    # 매파 키워드
    with st.expander("🔴 매파(Hawkish) 키워드", expanded=True):
        st.markdown("**금리 인상/긴축 방향의 키워드들**")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("##### 상위 15개 키워드")

        with col2:
            if st.button("모두 초기화", key="reset_hawkish"):
                # 매파 키워드 모두 기본값으로 복원
                for _, row in df_hawkish.iterrows():
                    if row['active_weight'] != row['base_weight']:
                        db.save_expert_weight(
                            row['term'],
                            row['base_weight'],
                            reason="전문가가 기본값으로 복원",
                            expert_name="User"
                        )
                st.success("매파 키워드가 모두 초기화되었습니다!")
                st.rerun()

        # 슬라이더로 가중치 조정
        hawkish_changes = {}

        for _, row in df_hawkish.head(15).iterrows():
            term = row['term']
            base_weight = row['base_weight']
            active_weight = row['active_weight']
            category = row['category']
            description = row['description']

            col_slider, col_info = st.columns([3, 1])

            with col_slider:
                new_weight = st.slider(
                    f"**{term}** ({category})",
                    min_value=0.5,
                    max_value=3.0,
                    value=float(active_weight),
                    step=0.1,
                    key=f"hawkish_{term}",
                    help=description
                )

            with col_info:
                if abs(new_weight - base_weight) > 0.01:
                    st.caption(f"기본: {base_weight:.1f}")
                    st.caption(f"↓")
                    st.caption(f"조정: {new_weight:.1f}")
                else:
                    st.caption(f"기본값")

            if abs(new_weight - active_weight) > 0.01:
                hawkish_changes[term] = new_weight

        if hawkish_changes:
            st.markdown("---")
            if st.button("💾 매파 키워드 변경사항 저장", key="save_hawkish"):
                for term, weight in hawkish_changes.items():
                    db.save_expert_weight(
                        term,
                        weight,
                        reason="전문가가 UI에서 조정",
                        expert_name="User"
                    )
                st.success(f"{len(hawkish_changes)}개 키워드 가중치가 저장되었습니다!")
                st.session_state.settings_modified = True
                st.rerun()

    # 비둘기파 키워드
    with st.expander("🟢 비둘기파(Dovish) 키워드"):
        st.markdown("**금리 인하/완화 방향의 키워드들**")
        
        # CSS Injection for Green Sliders in this specific section
        # Streamlit의 슬라이더는 기본 테마 색상을 따르지만, CSS로 강제 조정 시도
        # Hue Rotation을 사용하여 붉은색(#FF4B4B)을 초록색(#4CAF50)으로 변환 (약 100~110도 회전)
        st.markdown("""
        <style>
        /* 비둘기파 섹션(두 번째 expander)의 슬라이더 색상 변경 (Hue Rotate Hack) */
        div[data-testid="stExpander"]:nth-of-type(2) div[data-testid="stSlider"] > div {
            filter: hue-rotate(110deg) brightness(1.1) !important;
        }
        
        /* Fallback for different selector specificities */
        details:nth-of-type(2) div[data-testid="stSlider"] > div {
            filter: hue-rotate(110deg) brightness(1.1) !important;
        }
        
        /* 텍스트(라벨)는 회전되지 않도록 제외 (선택적으로) */
        div[data-testid="stExpander"]:nth-of-type(2) div[data-testid="stSlider"] label {
            filter: hue-rotate(-110deg) !important; /* 역회전으로 보정 */
        }
        </style>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("##### 상위 15개 키워드 <span style='color:#4CAF50'>(Green Region)</span>", unsafe_allow_html=True)

        with col2:
            if st.button("모두 초기화", key="reset_dovish"):
                # 비둘기파 키워드 모두 기본값으로 복원
                for _, row in df_dovish.iterrows():
                    if row['active_weight'] != row['base_weight']:
                        db.save_expert_weight(
                            row['term'],
                            row['base_weight'],
                            reason="전문가가 기본값으로 복원",
                            expert_name="User"
                        )
                st.success("비둘기파 키워드가 모두 초기화되었습니다!")
                st.rerun()

        # 슬라이더로 가중치 조정
        dovish_changes = {}

        for _, row in df_dovish.head(15).iterrows():
            term = row['term']
            base_weight = row['base_weight']
            active_weight = row['active_weight']
            category = row['category']
            description = row['description']

            col_slider, col_info = st.columns([3, 1])

            with col_slider:
                new_weight = st.slider(
                    f"**{term}** ({category})",
                    min_value=0.5,
                    max_value=3.0,
                    value=float(active_weight),
                    step=0.1,
                    key=f"dovish_{term}",
                    help=description
                )

            with col_info:
                if abs(new_weight - base_weight) > 0.01:
                    st.caption(f"기본: {base_weight:.1f}")
                    st.caption(f"↓")
                    st.caption(f"조정: {new_weight:.1f}")
                else:
                    st.caption(f"기본값")

            if abs(new_weight - active_weight) > 0.01:
                dovish_changes[term] = new_weight

        if dovish_changes:
            st.markdown("---")
            if st.button("💾 비둘기파 키워드 변경사항 저장", key="save_dovish"):
                for term, weight in dovish_changes.items():
                    db.save_expert_weight(
                        term,
                        weight,
                        reason="전문가가 UI에서 조정",
                        expert_name="User"
                    )
                st.success(f"{len(dovish_changes)}개 키워드 가중치가 저장되었습니다!")
                st.session_state.settings_modified = True
                st.rerun()

def render_model_parameters_tab(db: DatabaseManager):
    """모델 파라미터 조정 탭"""

    st.header("🔧 톤 지수 모델 파라미터")

    st.markdown("""
    향상된 톤 지수는 다음 공식으로 계산됩니다:

    **Tone_Adjusted = α · Tone_Text + β · Market_Reaction + γ · News_Sentiment**

    각 요소의 가중치를 조정하여 모델의 예측 성능을 개선할 수 있습니다.
    """)

    # 현재 파라미터 로드
    params = db.get_model_parameters()

    alpha = params.get('alpha', 0.5)
    beta = params.get('beta', 0.3)
    gamma = params.get('gamma', 0.2)

    st.markdown("---")

    # 파라미터 조정
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### α (Text Tone)")
        new_alpha = st.slider(
            "텍스트 톤 가중치",
            min_value=0.0,
            max_value=1.0,
            value=alpha,
            step=0.05,
            key="alpha_slider",
            help="의사록 텍스트 분석 결과의 가중치"
        )
        st.caption("의사록 텍스트 분석")

    with col2:
        st.markdown("##### β (Market Reaction)")
        new_beta = st.slider(
            "시장 반응 가중치",
            min_value=0.0,
            max_value=1.0,
            value=beta,
            step=0.05,
            key="beta_slider",
            help="의사록 발표 전후 시장 반응의 가중치"
        )
        st.caption("시장 반응")

    with col3:
        st.markdown("##### γ (News Sentiment)")
        new_gamma = st.slider(
            "뉴스 감성 가중치",
            min_value=0.0,
            max_value=1.0,
            value=gamma,
            step=0.05,
            key="gamma_slider",
            help="뉴스 감성 분석 결과의 가중치"
        )
        st.caption("뉴스 감성")

    # 합계 검증
    total = new_alpha + new_beta + new_gamma

    st.markdown("---")

    st.metric("가중치 합계", f"{total:.2f}", delta=f"{total - 1.0:+.2f}" if abs(total - 1.0) > 0.01 else None)

    if abs(total - 1.0) > 0.01:
        st.error(f"⚠️ 가중치 합계는 1.0이어야 합니다. 현재: {total:.2f}")
        st.info("자동 정규화하려면 아래 버튼을 클릭하세요.")

        if st.button("🔄 자동 정규화"):
            # 정규화
            new_alpha_norm = new_alpha / total
            new_beta_norm = new_beta / total
            new_gamma_norm = new_gamma / total

            db.save_model_parameter('alpha', new_alpha_norm, 'Text Tone Weight (Normalized)')
            db.save_model_parameter('beta', new_beta_norm, 'Market Reaction Weight (Normalized)')
            db.save_model_parameter('gamma', new_gamma_norm, 'News Sentiment Weight (Normalized)')

            st.success(f"정규화 완료! α={new_alpha_norm:.2f}, β={new_beta_norm:.2f}, γ={new_gamma_norm:.2f}")
            st.session_state.settings_modified = True
            st.rerun()
    else:
        st.success("✓ 가중치 합계가 정확합니다.")

        # 변경사항이 있으면 저장 버튼 표시
        if abs(new_alpha - alpha) > 0.01 or abs(new_beta - beta) > 0.01 or abs(new_gamma - gamma) > 0.01:
            if st.button("💾 모델 파라미터 저장", key="save_params"):
                db.save_model_parameter('alpha', new_alpha, 'Text Tone Weight')
                db.save_model_parameter('beta', new_beta, 'Market Reaction Weight')
                db.save_model_parameter('gamma', new_gamma, 'News Sentiment Weight')

                st.success("모델 파라미터가 저장되었습니다!")
                st.session_state.settings_modified = True
                st.rerun()


def render_settings_management_tab(db: DatabaseManager, sentiment_dict: SentimentDictionary):
    """설정 관리 탭"""

    st.header("💾 설정 관리")

    # 키워드 통계
    df_keywords = db.get_all_keywords()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("전체 키워드", len(df_keywords))

    with col2:
        adjusted_count = len(df_keywords[df_keywords['adjustment_count'] > 0])
        st.metric("조정된 키워드", adjusted_count)

    with col3:
        hawkish_count = len(df_keywords[df_keywords['polarity'] == 'hawkish'])
        dovish_count = len(df_keywords[df_keywords['polarity'] == 'dovish'])
        st.metric("매파/비둘기파", f"{hawkish_count} / {dovish_count}")

    st.markdown("---")

    # 모든 설정 초기화
    st.subheader("🔄 설정 초기화")

    st.warning("모든 키워드 가중치와 모델 파라미터를 기본값으로 복원합니다.")

    if st.button("⚠️ 모든 설정 초기화", key="reset_all"):
        confirm = st.checkbox("정말로 모든 설정을 초기화하시겠습니까?", key="confirm_reset")

        if confirm:
            # 모든 키워드 기본값으로
            for _, row in df_keywords.iterrows():
                if row['active_weight'] != row['base_weight']:
                    db.save_expert_weight(
                        row['term'],
                        row['base_weight'],
                        reason="전체 초기화",
                        expert_name="System"
                    )

            # 모델 파라미터 기본값으로
            db.save_model_parameter('alpha', 0.5, 'Text Tone Weight (Reset)')
            db.save_model_parameter('beta', 0.3, 'Market Reaction Weight (Reset)')
            db.save_model_parameter('gamma', 0.2, 'News Sentiment Weight (Reset)')

            st.success("모든 설정이 초기화되었습니다!")
            st.session_state.settings_modified = False
            st.rerun()

    st.markdown("---")

    # 설정 내보내기/가져오기
    st.subheader("📤 설정 내보내기/가져오기")

    if st.button("📥 현재 설정 다운로드 (CSV)", key="export_settings"):
        df_export = df_keywords[['term', 'polarity', 'base_weight', 'active_weight', 'category']]

        csv = df_export.to_csv(index=False)

        st.download_button(
            label="💾 CSV 파일 다운로드",
            data=csv,
            file_name="bok_keyword_weights.csv",
            mime="text/csv"
        )


def main():
    """테스트용 메인"""
    st.set_page_config(
        page_title="전문가 설정",
        page_icon="⚙️",
        layout="wide"
    )

    render_settings_view()


if __name__ == "__main__":
    main()
