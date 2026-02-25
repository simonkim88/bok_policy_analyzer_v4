from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.models.expectation_divergence import ExpectationDivergenceAnalyzer
from src.models.term_premium import TermPremiumAnalyzer
from src.taylor_rule import ExtendedTaylorRule

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _chart_layout(title, y_title):
    return dict(
        title=f"<b>{title}</b>",
        title_font=dict(size=20, color="white"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(showgrid=True, gridcolor="#444", color="white", title=y_title),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right", font=dict(color="white")),
        hovermode="x unified",
        height=500,
        template="plotly_dark",
    )


def create_taylor_chart(df, model_type):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Base_Rate"],
            mode="lines",
            name="Actual Base Rate",
            line=dict(color="#CFD8DC", width=2, dash="dot"),
            hovertemplate="<b>Actual: %{y:.2f}%</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Taylor_Rate"],
            mode="lines",
            name=f"Taylor Rate ({model_type.title()})",
            line=dict(color="#00E676", width=4),
            hovertemplate="<b>Taylor: %{y:.2f}%</b><extra></extra>",
        )
    )

    if "Taylor_Rate_Standard" in df.columns and model_type != "standard":
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["Taylor_Rate_Standard"],
                mode="lines",
                name="Standard Baseline",
                line=dict(color="#40C4FF", width=2),
                hovertemplate="<b>Standard: %{y:.2f}%</b><extra></extra>",
            )
        )

    fig.update_layout(_chart_layout("Taylor Rule Rate vs Actual Base Rate", "Interest Rate (%)"))
    return fig


def create_fsi_component_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Credit_Component"], name="Credit", line=dict(color="#FFAB40", width=2)))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["FX_Component"], name="FX Level", line=dict(color="#40C4FF", width=2)))
    if "FX_Volatility_Component" in df.columns:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["FX_Volatility_Component"], name="FX Volatility", line=dict(color="#E040FB", width=2)))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Spread_Component"], name="Spread", line=dict(color="#CFD8DC", width=2)))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["FSI"], name="FSI Composite", line=dict(color="#00E676", width=4)))
    fig.update_layout(_chart_layout("Financial Stability Index Components", "Normalized Score (-1 to 1)"))
    return fig


def create_fsi_heatmap(df):
    comp_cols = ["Credit_Component", "FX_Component", "Spread_Component"]
    if "FX_Volatility_Component" in df.columns:
        comp_cols.append("FX_Volatility_Component")
    valid = df.dropna(subset=comp_cols)
    latest = valid.iloc[-1] if not valid.empty else df.iloc[-1]
    fx_vol = float(latest.get("FX_Volatility_Component", 0.0)) if "FX_Volatility_Component" in df.columns else 0.0
    z = [[latest["Credit_Component"], latest["FX_Component"], fx_vol, latest["Spread_Component"], latest["FSI"]]]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["Credit", "FX Level", "FX Vol", "Spread", "Composite"],
            y=[latest["Date"].strftime("%Y-%m")],
            zmin=-1,
            zmax=1,
            colorscale="RdYlGn_r",
            colorbar=dict(title="Risk"),
        )
    )
    fig.update_layout(
        title="FSI Risk Heatmap (Latest)",
        template="plotly_dark",
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_term_premium_chart(simple_df, model_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=simple_df["Date"], y=simple_df["KTB_3Y"], name="KTB 3Y", line=dict(color="#40C4FF", width=2)))
    fig.add_trace(go.Scatter(x=simple_df["Date"], y=simple_df["KTB_10Y"], name="KTB 10Y", line=dict(color="#CFD8DC", width=2)))
    fig.add_trace(go.Scatter(x=model_df["Date"], y=model_df["TermPremium"], name="Model Term Premium", line=dict(color="#00E676", width=3), yaxis="y2"))
    fig.update_layout(
        title="Bond Yield Decomposition",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(title="Yield (%)", showgrid=True, gridcolor="#444", color="white"),
        yaxis2=dict(title="Term Premium", overlaying="y", side="right", color="#00E676"),
        legend=dict(orientation="h"),
        hovermode="x unified",
        height=500,
    )
    return fig


def create_expectation_chart(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Expected_Rate"], name="Expected Rate", line=dict(color="#FFAB40", width=2)))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Actual_Rate"], name="Actual Rate", line=dict(color="#CFD8DC", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Cumulative_Divergence"], name="Cumulative Divergence", line=dict(color="#00E676", width=3), yaxis="y2"))
    fig.update_layout(
        title="Market Expectations vs Actual BOK Decisions",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(title="Rate (%)", showgrid=True, gridcolor="#444", color="white"),
        yaxis2=dict(title="Cumulative Divergence", overlaying="y", side="right", color="#00E676"),
        legend=dict(orientation="h"),
        hovermode="x unified",
        height=500,
    )
    return fig


def render_taylor_view():
    st.markdown(
        """
    <h1 style='color: #00E676;'>Taylor Rule Policy Analyzer</h1>
    <p style='color: #B0BEC5;'>
        Standard and enhanced Taylor Rule models with financial stability and communication tone signals.
    </p>
    <hr style='border-color: #37474F;'>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("### Model Configuration")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        model_type = st.radio("Model Type", ["standard", "extended", "augmented"], horizontal=False)
        alpha = st.slider("Inflation Weight (alpha)", 0.0, 2.0, 0.5, 0.1)
        beta = st.slider("Output Weight (beta)", 0.0, 2.0, 0.5, 0.1)

    with col2:
        r_star = st.number_input("Neutral Rate (r*)", 0.0, 6.0, 2.0, 0.25)
        pi_star = st.number_input("Inflation Target (pi*)", 0.0, 6.0, 2.0, 0.1)
        gamma = st.slider("FSI Weight (gamma)", 0.0, 1.5, 0.3, 0.05)

    with col3:
        delta = st.slider("Tone Weight (delta)", 0.0, 1.5, 0.2, 0.05)
        rho = st.slider("Policy Inertia (rho)", 0.0, 0.99, 0.8, 0.05)
        preset = st.selectbox("Policy Preset", ["Baseline", "Hawkish", "Dovish"])
        if preset == "Hawkish":
            alpha, beta = 1.0, 0.4
        elif preset == "Dovish":
            alpha, beta = 0.4, 1.0

    with col4:
        st.markdown("#### Current Parameters")
        st.metric("alpha", f"{alpha:.2f}")
        st.metric("beta", f"{beta:.2f}")
        st.metric("gamma", f"{gamma:.2f}")
        st.metric("delta", f"{delta:.2f}")
        st.metric("rho", f"{rho:.2f}")

    try:
        with st.spinner("Calculating Taylor models and derived analytics..."):
            engine = ExtendedTaylorRule(alpha=alpha, beta=beta, r_star=r_star, pi_star=pi_star, gamma=gamma, delta=delta, rho=rho)
            selected_result = engine.calculate(model_type=model_type)
            extended_result = engine.calculate(model_type="extended")

            term_analyzer = TermPremiumAnalyzer()
            term_simple = term_analyzer.calculate_simple()
            term_model = term_analyzer.calculate_expectations()
            term_summary = term_analyzer.get_summary()

            exp_analyzer = ExpectationDivergenceAnalyzer()
            divergence_df = exp_analyzer.calculate_divergence()
            surprise_df = exp_analyzer.get_surprise_events()

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Taylor Rule Analysis", "Financial Stability", "Term Premium", "Market Expectations", "Time Series", "Correlation"]
        )

        with tab1:
            st.plotly_chart(create_taylor_chart(selected_result.df, model_type), use_container_width=True)
            latest = selected_result.df.iloc[-1]
            gap = float(latest["Taylor_Rate"] - latest["Base_Rate"])
            gap_color = "#FF5252" if gap > 0.5 else ("#448AFF" if gap < -0.5 else "#B0BEC5")
            action = "Hike Pressure" if gap > 0.25 else ("Cut Pressure" if gap < -0.25 else "Neutral")

            st.markdown(
                f'''
                <div style="padding: 20px; background-color: #1E1E1E; border-radius: 12px; border: 1px solid #333;">
                    <h3 style="margin-top:0;">Latest Signal ({latest['Date'].strftime('%Y-%m')})</h3>
                    <p>Actual: <b>{latest['Base_Rate']:.2f}%</b> | Taylor: <b style="color:#00E676;">{latest['Taylor_Rate']:.2f}%</b></p>
                    <p>Gap: <b style="color:{gap_color};">{gap:+.2f}%p</b> | Regime: <b style="color:{gap_color};">{action}</b></p>
                </div>
                ''',
                unsafe_allow_html=True,
            )

            # --- Tab1 Korean Analysis ---
            st.markdown("---")
            inflation_val = float(latest.get("Inflation", 0))
            output_gap_val = float(latest.get("Output_Gap", 0))
            action_kr = "인상 압력" if gap > 0.25 else ("인하 압력" if gap < -0.25 else "적정 수준")
            gap_interpret = "테일러 준칙 금리가 실제 기준금리보다 높아, 금리 인상이 필요한 상황" if gap > 0.25 else ("테일러 준칙 금리가 실제 기준금리보다 낮아, 금리 인하 여력이 있는 상황" if gap < -0.25 else "테일러 준칙 금리와 실제 금리가 유사하여, 현행 금리가 적정 수준")

            st.markdown(
                f"""
                <div style="padding: 16px; background-color: #1a2332; border-radius: 10px; border-left: 4px solid #00E676; margin-top: 10px;">
                    <h4 style="color: #00E676; margin-top: 0;">해석 안내</h4>
                    <p style="color: #B0BEC5; line-height: 1.8;">
                        테일러 준칙(Taylor Rule)은 인플레이션 갱과 GDP 갱을 기반으로 적정 기준금리를 산출하는 통화정책 준칙입니다.
                        차트의 <span style="color:#00E676;">녹색 실선</span>이 테일러 준칙 금리, <span style="color:#CFD8DC;">회색 점선</span>이 실제 기준금리를 나타냅니다.
                    </p>
                    <p style="color: #E0E0E0; line-height: 1.8;">
                        <b>현재 상황:</b> {gap_interpret}을 시사합니다.
                        금리 갱({gap:+.2f}%p)은 <b style="color:{gap_color};">{action_kr}</b>을 의미합니다.
                    </p>
                    <p style="color: #90A4AE; font-size: 0.85em; margin-bottom: 0;">
                        ※ 테일러 준칙은 참고 지표이며, 실제 통화정책은 금융안정, 환율, 가계부채 등 다양한 요소를 종합적으로 고려하여 결정됩니다.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab2:
            fsi_df = extended_result.df
            st.plotly_chart(create_fsi_component_chart(fsi_df), use_container_width=True)
            st.plotly_chart(create_fsi_heatmap(fsi_df), use_container_width=True)

            # --- Tab2 Korean Analysis ---
            fsi_latest = fsi_df.dropna(subset=["FSI"]).iloc[-1] if not fsi_df.dropna(subset=["FSI"]).empty else fsi_df.iloc[-1]
            fsi_val = float(fsi_latest.get("FSI", 0))
            credit_val = float(fsi_latest.get("Credit_Component", 0))
            fx_val = float(fsi_latest.get("FX_Component", 0))
            spread_val = float(fsi_latest.get("Spread_Component", 0))

            fsi_level = "위험 수준" if fsi_val > 0.5 else ("주의 필요" if fsi_val > 0 else "안정적")
            fsi_color = "#FF5252" if fsi_val > 0.5 else ("#FFAB40" if fsi_val > 0 else "#00E676")

            max_risk_name = "신용 갱"
            max_risk_val = credit_val
            if abs(fx_val) > abs(max_risk_val):
                max_risk_name = "환율"
                max_risk_val = fx_val
            if abs(spread_val) > abs(max_risk_val):
                max_risk_name = "금리 스프레드"
                max_risk_val = spread_val

            st.markdown(
                f"""
                <div style="padding: 16px; background-color: #1a2332; border-radius: 10px; border-left: 4px solid {fsi_color}; margin-top: 10px;">
                    <h4 style="color: {fsi_color}; margin-top: 0;">금융안정성 해석</h4>
                    <p style="color: #B0BEC5; line-height: 1.8;">
                        금융안정성지수(FSI)는 신용 갱, 환율 수준/변동성, 금리 스프레드 등을 종합하여 금융시장의 안정성을 평가합니다.
                        위 차트는 각 구성요소의 시계열 변화를, 아래 히트맵은 최신 시점의 위험 수준을 보여줍니다.
                    </p>
                    <p style="color: #E0E0E0; line-height: 1.8;">
                        <b>현재 FSI:</b> <span style="color:{fsi_color};">{fsi_val:.3f}</span> (<b style="color:{fsi_color};">{fsi_level}</b>)<br>
                        <b>주요 위험 요인:</b> {max_risk_name} 부문이 {abs(max_risk_val):.3f}으로 가장 높은 위험 기여도를 보이고 있습니다.
                    </p>
                    <p style="color: #90A4AE; font-size: 0.85em; margin-bottom: 0;">
                        ※ FSI > 0은 금융불안정 압력을, FSI < 0은 안정적 환경을 의미합니다. 확장된 테일러 준칙에서는 FSI가 높을수록 적정 금리를 상향 조정합니다.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab3:
            st.plotly_chart(create_term_premium_chart(term_simple, term_model), use_container_width=True)
            st.info(term_summary["interpretation"])

            # --- Tab3 Korean Analysis ---
            tp_latest = term_model.iloc[-1] if not term_model.empty else None
            ktb3_latest = term_simple.iloc[-1]["KTB_3Y"] if not term_simple.empty else 0
            ktb10_latest = term_simple.iloc[-1]["KTB_10Y"] if not term_simple.empty else 0
            spread_10_3 = ktb10_latest - ktb3_latest
            tp_val = float(tp_latest["TermPremium"]) if tp_latest is not None and "TermPremium" in tp_latest else 0

            spread_signal = "경기 회복/확장 기대" if spread_10_3 > 0.5 else ("경기 둘화/침체 우려" if spread_10_3 < 0 else "중립적 신호")
            spread_color = "#00E676" if spread_10_3 > 0.5 else ("#FF5252" if spread_10_3 < 0 else "#FFAB40")
            tp_interpret = "투자자들이 장기 불확실성에 대해 높은 보상을 요구" if tp_val > 0.5 else ("장기 금리에 대한 불확실성 프리미엄이 낮은 상황" if tp_val < 0.2 else "정상적 수준의 기간 프리미엄")

            st.markdown(
                f"""
                <div style="padding: 16px; background-color: #1a2332; border-radius: 10px; border-left: 4px solid #40C4FF; margin-top: 10px;">
                    <h4 style="color: #40C4FF; margin-top: 0;">기간 프리미엄 해석</h4>
                    <p style="color: #B0BEC5; line-height: 1.8;">
                        기간 프리미엄(Term Premium)은 장기 채권 금리에서 단기 금리 기대치를 제외한 추가 보상 부분입니다.
                        <span style="color:#40C4FF;">KTB 3년</span>과 <span style="color:#CFD8DC;">KTB 10년</span> 금리의 차이(스프레드)는 경기 전망에 대한 시장의 기대를 반영합니다.
                    </p>
                    <p style="color: #E0E0E0; line-height: 1.8;">
                        <b>현재 장단기 스프레드:</b> <span style="color:{spread_color};">{spread_10_3:.2f}%p</span> → <b style="color:{spread_color};">{spread_signal}</b><br>
                        <b>모델 기간 프리미엄:</b> {tp_val:.3f} → {tp_interpret}
                    </p>
                    <p style="color: #90A4AE; font-size: 0.85em; margin-bottom: 0;">
                        ※ 장단기 금리 역전(스프레드 < 0)은 전통적으로 경기침체의 선행 신호로 해석됩니다. 기간 프리미엄 상승은 장기 금리 상승 압력을 의미합니다.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab4:
            st.plotly_chart(create_expectation_chart(divergence_df), use_container_width=True)
            if not surprise_df.empty:
                st.markdown("#### Surprise Events")
                st.dataframe(
                    surprise_df[
                        [
                            "Date",
                            "meeting_date_str",
                            "Divergence",
                            "Surprise_Magnitude",
                            "Surprise_Type",
                        ]
                    ],
                    use_container_width=True,
                )
            else:
                st.info("No large surprise events detected in current sample.")

            # --- Tab4 Korean Analysis ---
            if not divergence_df.empty:
                div_latest = divergence_df.iloc[-1]
                expected_latest = float(div_latest.get("Expected_Rate", 0))
                actual_latest = float(div_latest.get("Actual_Rate", 0))
                cum_div = float(div_latest.get("Cumulative_Divergence", 0))
                n_surprises = len(surprise_df) if not surprise_df.empty else 0

                div_direction = "시장 기대보다 더 매파적" if cum_div > 0 else ("시장 기대보다 더 비둡기파적" if cum_div < 0 else "시장 기대와 일치")
                div_color = "#FF5252" if abs(cum_div) > 0.5 else "#FFAB40" if abs(cum_div) > 0.2 else "#00E676"

                st.markdown(
                    f"""
                    <div style="padding: 16px; background-color: #1a2332; border-radius: 10px; border-left: 4px solid #FFAB40; margin-top: 10px;">
                        <h4 style="color: #FFAB40; margin-top: 0;">시장 기대 분석</h4>
                        <p style="color: #B0BEC5; line-height: 1.8;">
                            이 차트는 금리 선물시장 등에서 파생된 <span style="color:#FFAB40;">시장 기대 금리</span>와 <span style="color:#CFD8DC;">한국은행의 실제 기준금리 결정</span> 간의 괴리를 보여줍니다.
                            누적 괴리(춤적 디버전스)가 클수록 시장의 예측과 실제 정책 간 불일치가 커짐을 의미합니다.
                        </p>
                        <p style="color: #E0E0E0; line-height: 1.8;">
                            <b>최신 시점:</b> 기대 금리 {expected_latest:.2f}% vs 실제 금리 {actual_latest:.2f}%<br>
                            <b>누적 괴리:</b> <span style="color:{div_color};">{cum_div:+.2f}%p</span> → 한국은행이 {div_direction}으로 평가됩니다.<br>
                            <b>서프라이즈 이벤트:</b> {n_surprises}회 발생 (시장 예상과 크게 다른 정책 결정)
                        </p>
                        <p style="color: #90A4AE; font-size: 0.85em; margin-bottom: 0;">
                            ※ 서프라이즈 이벤트가 빈번하면 중앙은행의 커뮤니케이션이 시장과 괴리되고 있음을, 적으면 정책 예측 가능성이 높음을 의미합니다.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- Load tone data for Time Series and Correlation tabs ---
        try:
            tone_path = PROJECT_ROOT / "data" / "analysis" / "tone_index_results.csv"
            df_tone = pd.read_csv(tone_path)
            df_tone["Date"] = pd.to_datetime(df_tone["meeting_date"])

            df_taylor = selected_result.df.copy()
            df_analysis = df_tone[["Date", "tone_index", "meeting_date_str"]].copy()
            df_analysis["YM"] = df_analysis["Date"].dt.to_period("M")
            df_taylor["YM"] = df_taylor["Date"].dt.to_period("M")

            tone_merged = pd.merge(df_analysis, df_taylor[["YM", "Taylor_Rate", "Base_Rate"]], on="YM", how="inner")
            tone_corr = tone_merged["tone_index"].corr(tone_merged["Taylor_Rate"]) if len(tone_merged) > 5 else None
        except Exception:
            tone_merged = pd.DataFrame()
            tone_corr = None

        with tab5:
            st.markdown("""
            **Tone Index**(통화정책 어조)와 **Taylor Rule Rate**(적정 금리)의 시간에 따른 변화를 비교합니다.
            두 지표의 동조 여부를 시각적으로 확인할 수 있습니다.
            """)

            if tone_corr is not None and len(tone_merged) > 5:
                col_ts_chart, col_ts_desc = st.columns([2, 1])

                with col_ts_chart:
                    fig_dual = go.Figure()
                    fig_dual.add_trace(go.Scatter(
                        x=tone_merged["Date"], y=tone_merged["Taylor_Rate"],
                        name="Taylor Rate", line=dict(color="#00E676", width=2),
                    ))
                    fig_dual.add_trace(go.Scatter(
                        x=tone_merged["Date"], y=tone_merged["tone_index"],
                        name="Tone Index", line=dict(color="#FFAB40", width=2), yaxis="y2",
                    ))
                    fig_dual.update_layout(
                        title="Time Series Comparison",
                        yaxis=dict(title="Taylor Rate (%)", title_font=dict(color="#00E676"), tickfont=dict(color="#00E676")),
                        yaxis2=dict(title="Tone Index", overlaying="y", side="right", title_font=dict(color="#FFAB40"), tickfont=dict(color="#FFAB40")),
                        legend=dict(x=0, y=1.1, orientation="h"),
                        height=500, margin=dict(l=50, r=50, t=50, b=50),
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_dual, use_container_width=True)

                with col_ts_desc:
                    tone_mean = tone_merged["tone_index"].mean()
                    tone_std = tone_merged["tone_index"].std()
                    taylor_mean = tone_merged["Taylor_Rate"].mean()
                    taylor_std = tone_merged["Taylor_Rate"].std()
                    tone_latest = tone_merged.iloc[-1]["tone_index"]
                    taylor_latest = tone_merged.iloc[-1]["Taylor_Rate"]
                    tone_trend = "\ub9e4\ud30c\uc801" if tone_latest > tone_mean else "\ube44\ub458\uae30\ud30c\uc801"
                    taylor_trend = "\ub192\uc740" if taylor_latest > taylor_mean else "\ub0ae\uc740"

                    st.markdown(
                        f"""
                    #### \uc2dc\uacc4\uc5f4 \ubd84\uc11d \uacb0\uacfc

                    **\uae30\uac04:** {tone_merged["Date"].min().strftime("%Y-%m")} ~ {tone_merged["Date"].max().strftime("%Y-%m")}
                    ({len(tone_merged)}\uac1c \ud68c\uc758)

                    ---

                    **Tone Index \ud1b5\uacc4:**
                    - \ud3c9\uade0: <span style="color: #FFAB40;">{tone_mean:.3f}</span>
                    - \ud45c\uc900\ud3b8\ucc28: {tone_std:.3f}
                    - \ucd5c\uc2e0\uac12: <span style="color: #FFAB40;">{tone_latest:.3f}</span> ({tone_trend})

                    **Taylor Rate \ud1b5\uacc4:**
                    - \ud3c9\uade0: <span style="color: #00E676;">{taylor_mean:.2f}%</span>
                    - \ud45c\uc900\ud3b8\ucc28: {taylor_std:.2f}%
                    - \ucd5c\uc2e0\uac12: <span style="color: #00E676;">{taylor_latest:.2f}%</span> ({taylor_trend} \uc218\uc900)

                    ---

                    **\uc0c1\uad00\uacc4\uc218:** <span style="color: #FFEB3B;">{tone_corr:.2f}</span>

                    **\ud574\uc11d:**
                    - \ub450 \uc9c0\ud45c\uac00 {"\uc720\uc0ac\ud55c \ubc29\ud5a5\uc73c\ub85c \uc6c0\uc9c1\uc774\ub294 \uacbd\ud5a5" if tone_corr > 0.3 else ("\uc57d\ud55c \uc5f0\uad00\uc131\uc744 \ubcf4\uc774\uba70" if tone_corr > 0 else "\ubc18\ub300 \ubc29\ud5a5\uc73c\ub85c \uc6c0\uc9c1\uc774\ub294 \uacbd\ud5a5")}\uc774 \uad00\ucc30\ub429\ub2c8\ub2e4.
                    - \ud55c\uad6d\uc740\ud589\uc758 \ucee4\ubba4\ub2c8\ucf00\uc774\uc158 \uc5b4\uc870\uac00 \uacbd\uc81c \ud380\ub354\uba58\ud138\uc5d0 \uae30\ubc18\ud55c \uc801\uc815 \uae08\ub9ac\uc640 {"\ub3d9\uc870" if abs(tone_corr) > 0.3 else "\uad34\ub9ac"}\ud558\uace0 \uc788\uc2b5\ub2c8\ub2e4.
                    """,
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("\ub370\uc774\ud130\uac00 \ubd80\uc871\ud558\uc5ec \uc2dc\uacc4\uc5f4 \ube44\uad50\ub97c \uc218\ud589\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")

        with tab6:
            st.markdown("""
            \ud1b5\ud654\uc815\ucc45 \uae30\uc870\ub97c \ub098\ud0c0\ub0b4\ub294 **Tone Index**(\uc5b4\uc870)\uc640 \uacbd\uc81c \uc9c0\ud45c \uae30\ubc18\uc758 **Taylor Rule Rate**(\uc801\uc815 \uae08\ub9ac) \uac04\uc758
            \uc5f0\uad00\uc131\uc744 \ubd84\uc11d\ud569\ub2c8\ub2e4. \uc77c\ubc18\uc801\uc73c\ub85c \ub9e4\ud30c\uc801(\ub192\uc740 Tone Index)\uc77c\uc218\ub85d \ud14c\uc77c\ub7ec \uc900\uce59 \uae08\ub9ac\ub3c4 \ub192\uac8c \ub098\ud0c0\ub098\ub294 \uacbd\ud5a5\uc774 \uc788\uc2b5\ub2c8\ub2e4.
            """)

            if tone_corr is not None and len(tone_merged) > 5:
                fig_corr = go.Figure()
                fig_corr.add_trace(go.Scatter(
                    x=tone_merged["tone_index"],
                    y=tone_merged["Taylor_Rate"],
                    mode="markers",
                    marker=dict(size=12, color=tone_merged["Taylor_Rate"], colorscale="Viridis", showscale=True),
                    text=tone_merged["meeting_date_str"],
                    hovertemplate="<b>%{text}</b><br>Tone: %{x:.3f}<br>Taylor Rate: %{y:.2f}%<extra></extra>",
                ))

                z = np.polyfit(tone_merged["tone_index"], tone_merged["Taylor_Rate"], 1)
                p = np.poly1d(z)
                x_range = np.linspace(tone_merged["tone_index"].min(), tone_merged["tone_index"].max(), 100)
                fig_corr.add_trace(go.Scatter(
                    x=x_range, y=p(x_range), mode="lines", name="Trend Line",
                    line=dict(color="red", width=2, dash="dash"),
                ))

                fig_corr.update_layout(
                    title=f"Tone Index vs Taylor Rule Rate (Correlation: {tone_corr:.2f})",
                    xaxis_title="Tone Index (Hawkish + / Dovish -)",
                    yaxis_title="Taylor Rule Rate (%)",
                    height=500, showlegend=False, template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                )

                col_chart, col_desc = st.columns([2, 1])

                with col_chart:
                    st.plotly_chart(fig_corr, use_container_width=True)

                with col_desc:
                    corr_level = "\uac15\ud55c \uc591\uc758" if tone_corr > 0.5 else ("\ub6a3\ub837\ud55c \uc591\uc758" if tone_corr > 0.3 else "\uc57d\ud55c")
                    trend_dir = "\ub192\uac8c" if tone_corr > 0 else "\ub0ae\uac8c"
                    sync_msg = "\uc798 \ub3d9\uc870\ud558\uace0 \uc788\uc74c" if abs(tone_corr) > 0.3 else "\uad34\ub9ac\uac00 \uc788\uc74c"

                    st.markdown(
                        f"""
                    #### \ubd84\uc11d \uacb0\uacfc

                    **\uc0c1\uad00\uacc4\uc218 (Correlation): <span style="color: #FFEB3B;">{tone_corr:.2f}</span>**

                    - **{tone_corr:.2f} > 0.5**: \uac15\ud55c \uc591\uc758 \uc0c1\uad00\uad00\uacc4
                    - **0.3 < {tone_corr:.2f} <= 0.5**: \ub6a3\ub837\ud55c \uc591\uc758 \uc0c1\uad00\uad00\uacc4
                    - **{tone_corr:.2f} <= 0.3**: \uc57d\ud55c \uc0c1\uad00\uad00\uacc4

                    **\ud574\uc11d:**
                    - Tone Index\uac00 \ub192\uc744\uc218\ub85d(\ub9e4\ud30c\uc801), \ud14c\uc77c\ub7ec \uc900\uce59 \uae08\ub9ac\ub3c4 {trend_dir} \ud615\uc131\ub418\ub294 \uacbd\ud5a5\uc774 \uc788\uc2b5\ub2c8\ub2e4.
                    - \uc774\ub294 \ud55c\uad6d\uc740\ud589\uc758 \ucee4\ubba4\ub2c8\ucf00\uc774\uc158(\uc5b4\uc870)\uc774 \uc2e4\uc81c \uacbd\uc81c \uc9c0\ud45c \uae30\ubc18\uc758 \uc801\uc815 \uae08\ub9ac \uc0b0\ucd9c \uacb0\uacfc\uc640 {sync_msg}\uc744 \uc758\ubbf8\ud569\ub2c8\ub2e4.
                    """,
                        unsafe_allow_html=True,
                    )
            else:
                st.warning("\ub370\uc774\ud130\uac00 \ubd80\uc871\ud558\uc5ec \uc0c1\uad00\ubd84\uc11d\uc744 \uc218\ud589\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")


    except Exception as exc:
        st.error(f"Failed to render Taylor view: {exc}")


if __name__ == "__main__":
    render_taylor_view()
