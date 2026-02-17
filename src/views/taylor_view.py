import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.taylor_rule import calculate_taylor_rule

def create_taylor_chart(df):
    """Creates the interactive Taylor Rule vs Base Rate chart."""
    fig = go.Figure()

    # 1. Base Rate (Actual)
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['Base_Rate'],
        mode='lines',
        name='Actual Base Rate (기준금리)',
        line=dict(color='#CFD8DC', width=2, dash='dot'),
        hovertemplate='<b>Actual: %{y:.2f}%</b><extra></extra>'
    ))

    # 2. Taylor Rule Rate (Calculated)
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['Taylor_Rate'],
        mode='lines',
        name='Taylor Rule Rate (적정금리)',
        line=dict(color='#00E676', width=4),
        hovertemplate='<b>Taylor: %{y:.2f}%</b><extra></extra>'
    ))

    # 3. Inflation Rate (Context) - Optional, maybe on secondary axis?
    # Let's keep it simple focused on Rate for now.

    fig.update_layout(
        title="<b>Taylor Rule Rate vs Actual Base Rate</b>",
        title_font=dict(size=20, color="white"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(showgrid=True, gridcolor='#444', color="white", title="Interest Rate (%)"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right", font=dict(color="white")),
        hovermode="x unified",
        height=500
    )
    
    return fig

def render_taylor_view():
    """Renders the Taylor Rule Analysis page."""
    
    st.markdown("""
    <h1 style='color: #00E676;'>📈 테일러 룰 기반 통화정책 분석</h1>
    <p style='color: #B0BEC5;'>
        테일러 룰(Taylor Rule)은 인플레이션 갭과 GDP 갭을 토대로 적정 기준금리를 산출하는 통화정책 준칙입니다.<br>
        아래 파라미터를 조정하여 다양한 시나리오(매파/비둘기파)를 시뮬레이션 해보세요.
    </p>
    <hr style='border-color: #37474F;'>
    """, unsafe_allow_html=True)

    # --- Controls Section ---
    with st.container():
        st.markdown("### ⚙️ 모델 파라미터 설정 (Model Parameters)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**정책 성향 (Weights)**")
            alpha = st.slider("물가 가중치 (α)", 0.0, 2.0, 0.5, 0.1, help="인플레이션 갭에 대한 가중치")
            beta = st.slider("경기 가중치 (β)", 0.0, 2.0, 0.5, 0.1, help="GDP 갭에 대한 가중치")
            
        with col2:
            st.markdown("**경제 구조 (Structural)**")
            r_star = st.number_input("중립 금리 (r*)", 1.0, 5.0, 2.0, 0.25, help="인플레이션이 안정적일 때의 실질 금리")
            pi_star = st.number_input("물가 목표 (π*)", 1.0, 5.0, 2.0, 0.1, help="중앙은행의 물가안정 목표치")

        with col3:
             st.markdown("**시나리오 프리셋**")
             preset = st.radio("Preset Selection", ["기본 (Standard)", "매파 (Hawkish)", "비둘기파 (Dovish)"], label_visibility="collapsed")
             
             if preset == "매파 (Hawkish)":
                 alpha = 1.0 # 물가 중시
                 beta = 0.5
             elif preset == "비둘기파 (Dovish)":
                 alpha = 0.5
                 beta = 1.0 # 경기 중시
                 
        with col4:
            st.markdown("### 🔍 현재 값")
            st.markdown(f"""
            <div style="background: #263238; padding: 10px; border-radius: 8px; border: 1px solid #546E7A;">
                <div style="display:flex; justify-content:space-between;"><span>α (Inflation):</span> <span style="color:#FFAB40;">{alpha}</span></div>
                <div style="display:flex; justify-content:space-between;"><span>β (Output):</span> <span style="color:#40C4FF;">{beta}</span></div>
            </div>
            """, unsafe_allow_html=True)

    # --- Calculation & Visualization ---
    try:
        with st.spinner("ECOS 데이터 로딩 및 테일러 룰 계산 중..."):
            df = calculate_taylor_rule(alpha, beta, r_star, pi_star)
        
        st.plotly_chart(create_taylor_chart(df), use_container_width=True)
        
        # --- Analysis Text ---
        last_row = df.iloc[-1]
        gap = last_row['Taylor_Rate'] - last_row['Base_Rate']
        
        gap_color = "#FF5252" if gap > 0.5 else ("#448AFF" if gap < -0.5 else "#B0BEC5")
        action = "인상 압력 (Hike Pressure)" if gap > 0.25 else ("인하 압력 (Cut Pressure)" if gap < -0.25 else "적정 수준 (Neutral)")
        
        st.markdown(f"""
        <div style="padding: 20px; background-color: #1E1E1E; border-radius: 12px; border: 1px solid #333; margin-top: 20px;">
            <h3 style="margin-top:0;">📊 분석 요약 ({last_row['Date'].strftime('%Y-%m')})</h3>
            <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                <div>
                    <div style="color: #90A4AE; font-size: 0.9em;">실제 기준금리</div>
                    <div style="font-size: 1.8em; font-weight: bold; color:white;">{last_row['Base_Rate']:.2f}%</div>
                </div>
                <div>
                    <div style="color: #90A4AE; font-size: 0.9em;">테일러 준칙 금리</div>
                    <div style="font-size: 1.8em; font-weight: bold; color: #00E676;">{last_row['Taylor_Rate']:.2f}%</div>
                </div>
                <div>
                    <div style="color: #90A4AE; font-size: 0.9em;">금리 갭 (Taylor - Actual)</div>
                    <div style="font-size: 1.8em; font-weight: bold; color: {gap_color};">{gap:+.2f}%p</div>
                </div>
                <div style="flex-grow: 1; text-align: right;">
                    <div style="color: #90A4AE; font-size: 0.9em;">시사점</div>
                    <div style="font-size: 1.5em; font-weight: bold; color: {gap_color};">{action}</div>
                </div>
            </div>
            <hr style="border-color: #444;">
            <div style="font-size: 0.95em; color: #CCC;">
                <ul>
                    <li><b>인플레이션 ({last_row['Inflation']:.2f}%)</b>: 목표치({pi_star}%) 대비 차이 <span style="color:#FFAB40;">{last_row['Inflation_Gap']:.2f}%p</span></li>
                    <li><b>GDP 갭 ({last_row['Output_Gap']:.2f}%)</b>: 잠재성장률 대비 경제가 { "과열" if last_row['Output_Gap'] > 0 else "침체" } 상태</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"계산 중 오류 발생: {e}")

    # --- Correlation Analysis Section ---
    st.markdown("---")
    st.markdown("### 🔗 Tone Index vs Taylor Rule 상관관계 분석")
    st.markdown("""
    통화정책 기조를 나타내는 **Tone Index**(어조)와 경제 지표 기반의 **Taylor Rule Rate**(적정 금리) 간의 
    연관성을 분석합니다. 일반적으로 매파적(높은 Tone Index)일수록 테일러 준칙 금리도 높게 나타나는 경향이 있습니다.
    """)
    
    # Load Tone Index Data
    try:
        tone_path = "data/analysis/tone_index_results.csv"
        df_tone = pd.read_csv(tone_path)
        df_tone['Date'] = pd.to_datetime(df_tone['meeting_date'])
        
        # Merge Data
        # df (Taylor Rule) is monthly, df_tone is by meeting date
        # Resample df_tone to monthly or match nearest? 
        # Let's use meeting dates as the base and map Taylor rates to them (nearest month)
        
        df_analysis = df_tone[['Date', 'tone_index', 'meeting_date_str']].copy()
        
        # Create Year-Month column for joining
        df_analysis['YM'] = df_analysis['Date'].dt.to_period('M')
        df['YM'] = df['Date'].dt.to_period('M')
        
        # Merge
        merged = pd.merge(df_analysis, df[['YM', 'Taylor_Rate', 'Base_Rate']], on='YM', how='inner')
        
        if len(merged) > 5:
            # Correlation Coefficient
            corr = merged['tone_index'].corr(merged['Taylor_Rate'])
            
            # Scatter Plot
            fig_corr = go.Figure()
            
            fig_corr.add_trace(go.Scatter(
                x=merged['tone_index'],
                y=merged['Taylor_Rate'],
                mode='markers',
                marker=dict(
                    size=12,
                    color=merged['Taylor_Rate'], # Color by rate
                    colorscale='Viridis',
                    showscale=True
                ),
                text=merged['meeting_date_str'],
                hovertemplate='<b>%{text}</b><br>Tone: %{x:.3f}<br>Taylor Rate: %{y:.2f}%<extra></extra>'
            ))
            
            # Trend Line
            # Simple linear regression
            import numpy as np
            z = np.polyfit(merged['tone_index'], merged['Taylor_Rate'], 1)
            p = np.poly1d(z)
            
            x_range = np.linspace(merged['tone_index'].min(), merged['tone_index'].max(), 100)
            fig_corr.add_trace(go.Scatter(
                x=x_range,
                y=p(x_range),
                mode='lines',
                name='Trend Line',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig_corr.update_layout(
                title=f"Tone Index vs Taylor Rule Rate (Correlation: {corr:.2f})",
                xaxis_title="Tone Index (Hawkish + / Dovish -)",
                yaxis_title="Taylor Rule Rate (%)",
                height=500,
                showlegend=False,
                template='plotly_dark'
            )
            
            col_chart, col_desc = st.columns([2, 1])
            
            with col_chart:
                st.plotly_chart(fig_corr, use_container_width=True)
                
            with col_desc:
                st.markdown(f"""
                #### 📊 분석 결과
                
                **상관계수 (Correlation): <span style="color: #FFEB3B;">{corr:.2f}</span>**
                
                - **{corr:.2f} > 0.5**: 강한 양의 상관관계
                - **0.3 < {corr:.2f} ≤ 0.5**: 뚜렷한 양의 상관관계
                - **{corr:.2f} ≤ 0.3**: 약한 상관관계
                
                **해석:**
                - Tone Index가 높을수록(매파적), 테일러 준칙 금리도 { "높게" if corr > 0 else "낮게" } 형성되는 경향이 있습니다.
                - 이는 한국은행의 커뮤니케이션(어조)이 실제 경제 지표 기반의 적정 금리 산출 결과와 { "잘 동조하고 있음" if abs(corr) > 0.3 else "괴리가 있음" }을 의미합니다.
                """)
                
                # Time Series Comparison (Dual Axis)
                st.markdown("#### 📈 시계열 비교")
                
                fig_dual = go.Figure()
                
                # Axis 1: Taylor Rate
                fig_dual.add_trace(go.Scatter(
                    x=merged['Date'],
                    y=merged['Taylor_Rate'],
                    name='Taylor Rate',
                    line=dict(color='#00E676', width=2)
                ))
                
                # Axis 2: Tone Index
                fig_dual.add_trace(go.Scatter(
                    x=merged['Date'],
                    y=merged['tone_index'],
                    name='Tone Index',
                    line=dict(color='#FFAB40', width=2),
                    yaxis='y2'
                ))
                
                fig_dual.update_layout(
                    title="Time Series Comparison",
                    yaxis=dict(title="Taylor Rate (%)", title_font=dict(color="#00E676"), tickfont=dict(color="#00E676")),
                    yaxis2=dict(title="Tone Index", overlaying='y', side='right', title_font=dict(color="#FFAB40"), tickfont=dict(color="#FFAB40")),
                    legend=dict(x=0, y=1.1, orientation='h'),
                    height=300,
                    margin=dict(l=50, r=50, t=50, b=50),
                    template='plotly_dark'
                )
                
                st.plotly_chart(fig_dual, use_container_width=True)
                
        else:
            st.warning("데이터가 부족하여 상관분석을 수행할 수 없습니다.")
            
    except Exception as e:
        st.error(f"상관분석 데이터 로드 중 오류: {e}")
