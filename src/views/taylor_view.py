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

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Taylor Rule Analysis", "Financial Stability", "Term Premium", "Market Expectations"]
        )

        with tab1:
            st.plotly_chart(create_taylor_chart(selected_result.df, model_type), use_container_width=True)
            latest = selected_result.df.iloc[-1]
            gap = float(latest["Taylor_Rate"] - latest["Base_Rate"])
            gap_color = "#FF5252" if gap > 0.5 else ("#448AFF" if gap < -0.5 else "#B0BEC5")
            action = "Hike Pressure" if gap > 0.25 else ("Cut Pressure" if gap < -0.25 else "Neutral")

            st.markdown(
                f"""
                <div style="padding: 20px; background-color: #1E1E1E; border-radius: 12px; border: 1px solid #333;">
                    <h3 style="margin-top:0;">Latest Signal ({latest['Date'].strftime('%Y-%m')})</h3>
                    <p>Actual: <b>{latest['Base_Rate']:.2f}%</b> | Taylor: <b style="color:#00E676;">{latest['Taylor_Rate']:.2f}%</b></p>
                    <p>Gap: <b style="color:{gap_color};">{gap:+.2f}%p</b> | Regime: <b style="color:{gap_color};">{action}</b></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with tab2:
            fsi_df = extended_result.df
            st.plotly_chart(create_fsi_component_chart(fsi_df), use_container_width=True)
            st.plotly_chart(create_fsi_heatmap(fsi_df), use_container_width=True)

        with tab3:
            st.plotly_chart(create_term_premium_chart(term_simple, term_model), use_container_width=True)
            st.info(term_summary["interpretation"])

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

    except Exception as exc:
        st.error(f"Failed to render Taylor view: {exc}")


if __name__ == "__main__":
    render_taylor_view()
