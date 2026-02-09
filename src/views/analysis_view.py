"""
View module for rendering the detailed analysis report.
Uses Streamlit native components with professional economic consulting aesthetics.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from pathlib import Path

def render_analysis_view(row, previous_row=None):
    """
    Renders the detailed analysis view for a specific meeting.
    
    Args:
        row: The dataframe row for the selected meeting.
        previous_row: The dataframe row for the previous meeting (for comparison).
    """
    meeting_date = row['meeting_date_str'].replace('_', '-')
    
    # 2025-11-27 샘플 데이터 하드코딩 (요청사항 반영)
    if meeting_date == '2025-11-27':
        render_sample_2025_11_27(row)
    else:
        # 일반적인 데이터에 대한 템플릿 (향후 확장 가능)
        render_generic_analysis(row)

def render_sample_2025_11_27(row):
    """2025년 11월 27일 발표에 대한 전문가 수준의 상세 분석"""
    
    # ==================== REPORT HEADER ====================
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 50%, #415A77 100%); 
                padding: 50px 40px; border-radius: 16px; margin-bottom: 40px;
                box-shadow: 0 15px 50px rgba(0,0,0,0.4); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; right: 0; width: 300px; height: 300px; 
                    background: radial-gradient(circle, rgba(100,181,246,0.15) 0%, transparent 70%);"></div>
        <div style="position: relative; z-index: 1;">
            <p style="color: #64B5F6; font-size: 0.9rem; letter-spacing: 3px; margin-bottom: 10px; 
                      text-transform: uppercase; font-weight: 600;">Policy Analysis Report</p>
            <h1 style="color: white; margin: 0; font-size: 3rem; font-weight: 700; 
                       letter-spacing: 1px; line-height: 1.2;">
                2025년 11월 통화정책방향<br/>
                <span style="font-size: 1.8rem; color: #90CAF9;">심층 분석 리포트</span>
            </h1>
            <div style="margin-top: 25px; display: flex; gap: 30px; flex-wrap: wrap;">
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">발표일</span><br/>
                    <span style="color: white; font-size: 1.2rem; font-weight: 600;">2025년 11월 27일</span>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">기준금리</span><br/>
                    <span style="color: #4CAF50; font-size: 1.2rem; font-weight: 600;">2.50% (동결)</span>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">연속 동결</span><br/>
                    <span style="color: white; font-size: 1.2rem; font-weight: 600;">4회차</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==================== EXECUTIVE SUMMARY ====================
    st.markdown("## 📋 Executive Summary")
    
    # Key Metrics in Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(21,101,192,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">기준금리</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">2.50%</h2>
            <p style="color: #81D4FA; margin: 0; font-size: 0.9rem;">▬ 동결 (5월 이후)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(46,125,50,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">소비자물가</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">2.3%</h2>
            <p style="color: #A5D6A7; margin: 0; font-size: 0.9rem;">목표(2%) 근접</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #F57C00 0%, #E65100 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(245,124,0,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">GDP 성장률 전망</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">1.9%</h2>
            <p style="color: #FFCC80; margin: 0; font-size: 0.9rem;">▼ 하향 조정</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #7B1FA2 0%, #4A148C 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(123,31,162,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">Tone Index</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">{row['tone_index']:.2f}</h2>
            <p style="color: #CE93D8; margin: 0; font-size: 0.9rem;">비둘기파 (Dovish)</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Summary Text
    st.markdown("""
    <div style="background-color: #1A1A2E; padding: 30px; border-radius: 12px; 
                border-left: 5px solid #64B5F6; margin: 20px 0;">
        <h3 style="color: #64B5F6; margin-top: 0; font-size: 1.3rem;">🎯 핵심 요약</h3>
        <p style="color: #E0E0E0; font-size: 1.1rem; line-height: 1.9; margin-bottom: 0;">
            한국은행 금융통화위원회는 2025년 11월 27일 회의에서 기준금리를 연 <strong style="color: #4CAF50;">2.50%</strong>로 
            동결하기로 결정했습니다. 이는 2025년 5월 25bp 인하 이후 <strong>4회 연속 동결</strong>입니다.<br><br>
            이번 결정의 핵심 배경은 다음과 같습니다:
        </p>
        <ul style="color: #E0E0E0; font-size: 1.05rem; line-height: 2; margin-top: 15px;">
            <li><strong style="color: #FFB74D;">물가 안정세 확인:</strong> 소비자물가 상승률이 2% 초반대로 안정화되며 목표 수준에 근접</li>
            <li><strong style="color: #FFB74D;">성장 불확실성:</strong> 소비와 수출은 개선세이나, 대외 불확실성과 내수 회복 지연 우려 상존</li>
            <li><strong style="color: #FFB74D;">금융안정 리스크:</strong> 원/달러 환율 변동성, 수도권 주택시장 불안, 가계대출 증가세 경계</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== DECISION RATIONALE ====================
    st.markdown("## 🔍 결정 배경 상세 분석")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📈 경제 성장")
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 10px; min-height: 280px;">
            <h4 style="color: #4CAF50; margin-top: 0;">긍정적 요인</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>민간소비가 서비스 중심으로 회복세 지속</li>
                <li>수출이 반도체, 자동차 등 주력 품목 호조로 증가세 유지</li>
                <li>설비투자 개선 조짐 (IT 부문 중심)</li>
            </ul>
            <h4 style="color: #FF7043; margin-top: 20px;">부정적 요인</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>건설투자 부진 장기화</li>
                <li>중국 경기 회복 지연으로 수출 증가폭 축소 우려</li>
                <li>고금리 장기화에 따른 내수 회복 지연</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 🏷️ 물가 동향")
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 10px; min-height: 280px;">
            <h4 style="color: #4CAF50; margin-top: 0;">안정화 신호</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>헤드라인 CPI: 2.3% (전년동월대비)</li>
                <li>근원물가: 2.1%대로 안정화</li>
                <li>기대인플레이션: 2.5% 내외로 안착</li>
            </ul>
            <h4 style="color: #FFC107; margin-top: 20px;">잠재 리스크</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>국제유가 변동성 (지정학적 리스크)</li>
                <li>원/달러 환율 상승에 따른 수입물가 압력</li>
                <li>농산물가격 불안정 요인 상존</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Financial Stability Section
    st.markdown("### 🏦 금융안정 리스크 요인")
    
    col_fx, col_house, col_debt = st.columns(3)
    
    with col_fx:
        st.markdown("""
        <div style="background: linear-gradient(180deg, #B71C1C 0%, #7F0000 100%); 
                    padding: 25px; border-radius: 12px; text-align: center; min-height: 200px;">
            <p style="font-size: 2.5rem; margin: 0;">💱</p>
            <h4 style="color: white; margin: 15px 0 10px 0;">환율 변동성</h4>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.95rem; line-height: 1.6;">
                원/달러 환율 1,380원대 등락<br/>
                미 연준 정책 불확실성 반영
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_house:
        st.markdown("""
        <div style="background: linear-gradient(180deg, #E65100 0%, #BF360C 100%); 
                    padding: 25px; border-radius: 12px; text-align: center; min-height: 200px;">
            <p style="font-size: 2.5rem; margin: 0;">🏠</p>
            <h4 style="color: white; margin: 15px 0 10px 0;">주택시장</h4>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.95rem; line-height: 1.6;">
                수도권 아파트 가격 상승세<br/>
                투기 수요 재점화 우려
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_debt:
        st.markdown("""
        <div style="background: linear-gradient(180deg, #6A1B9A 0%, #4A148C 100%); 
                    padding: 25px; border-radius: 12px; text-align: center; min-height: 200px;">
            <p style="font-size: 2.5rem; margin: 0;">💳</p>
            <h4 style="color: white; margin: 15px 0 10px 0;">가계부채</h4>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.95rem; line-height: 1.6;">
                가계대출 증가세 지속<br/>
                DSR 규제 강화에도 불구
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== COMPARISON WITH PREVIOUS ====================
    st.markdown("## 🔄 직전 회의(10월) 대비 주요 변화")
    
    # Comparison Chart
    comparison_data = pd.DataFrame({
        'Category': ['경제 성장 평가', '물가 전망', '금융안정', '정책 기조'],
        'Previous': [0.3, -0.1, 0.4, 0.2],
        'Current': [0.1, -0.3, 0.3, -0.1],
    })
    
    fig_comparison = go.Figure()
    
    fig_comparison.add_trace(go.Bar(
        name='10월 회의',
        x=comparison_data['Category'],
        y=comparison_data['Previous'],
        marker_color='#78909C',
        text=['+0.3', '-0.1', '+0.4', '+0.2'],
        textposition='outside'
    ))
    
    fig_comparison.add_trace(go.Bar(
        name='11월 회의',
        x=comparison_data['Category'],
        y=comparison_data['Current'],
        marker_color='#42A5F5',
        text=['+0.1', '-0.3', '+0.3', '-0.1'],
        textposition='outside'
    ))
    
    fig_comparison.update_layout(
        title="Tone Index 변화 비교 (양수=매파, 음수=비둘기파)",
        barmode='group',
        template='plotly_dark',
        height=400,
        yaxis_range=[-0.6, 0.6],
        yaxis_title="Tone Score",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Text Comparison Table
    st.markdown("### 📝 결정문 문구 변화 분석")
    
    st.markdown("""
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <thead>
            <tr style="background-color: #1E3A5F;">
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 15%; border-bottom: 2px solid #42A5F5;">항목</th>
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 40%; border-bottom: 2px solid #42A5F5;">10월 표현</th>
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 45%; border-bottom: 2px solid #42A5F5;">11월 표현 (변화)</th>
            </tr>
        </thead>
        <tbody>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>성장</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"국내경제는 건설투자 부진에도 소비 회복세 지속, 양호한 수출 증가세 등으로 개선 흐름을 이어갔다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "국내경제는 건설투자 부진에도 <strong style="color: #4FC3F7;">소비 회복세와 수출 증가세</strong>가 이어지면서 개선세를 지속하였다."
                    <span style="background-color: rgba(33,150,243,0.2); color: #42A5F5; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Dovish</span>
                </td>
            </tr>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>물가</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"9월 중 소비자물가 상승률이 2.1%, 근원물가 상승률이 2.0% ... 안정적인 흐름을 이어갔다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "소비자물가 및 근원물가 상승률이 <strong style="color: #EF5350;">2.4% 및 2.2%로 높아졌다.</strong>"
                    <span style="background-color: rgba(244,67,54,0.2); color: #EF5350; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Hawkish (Fact Check)</span>
                </td>
            </tr>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>정책방향</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"성장의 하방리스크 완화를 위한 금리인하 기조를 이어나가되 ... 기준금리의 추가 인하 시기 및 속도 등을 결정해 나갈 것이다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "향후 통화정책은 <strong style="color: #4FC3F7;">금리인하 가능성</strong>을 열어두되 ... 기준금리의 추가 인하 여부 및 시기를 결정해 나갈 것이다."
                    <span style="background-color: rgba(33,150,243,0.2); color: #42A5F5; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Dovish Pivot</span>
                </td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    if st.button("📄 원문 PDF 보기 (2025년 11월 의사록)", key="btn_view_pdf_2025_11", use_container_width=True):
        try:
            pdf_path = Path("data/pdfs/minutes_2025_11_27.pdf").resolve()
            if pdf_path.exists():
                os.startfile(pdf_path)
                st.success(f"파일을 열었습니다: {pdf_path.name}")
            else:
                st.error(f"파일을 찾을 수 없습니다: {pdf_path}")
        except Exception as e:
            st.error(f"파일 열기 실패: {e}")
    
    st.markdown("""
    <div style="background-color: #1B263B; padding: 20px; border-radius: 10px; margin-top: 20px;">
        <h4 style="color: #FFC107; margin-top: 0;">💡 시사점</h4>
        <p style="color: #E0E0E0; line-height: 1.8; margin-bottom: 0;">
            11월 결정문에서는 "충분한 기간 유지" 대신 "유연하게 대응"이라는 표현이 사용되었습니다. 
            이는 한국은행이 <strong style="color: #81D4FA;">긴축 기조에서 벗어나 완화 쪽으로 선회할 준비</strong>를 시사하는 
            중요한 레토릭 변화로 해석됩니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== FUTURE OUTLOOK ====================
    st.markdown("## 🔮 향후 전망 및 예측")
    
    # Rate Path Prediction Chart
    rate_path_data = pd.DataFrame({
        'Date': ['2025.05', '2025.07', '2025.08', '2025.10', '2025.11', '2026.01(E)', '2026.02(E)', '2026.04(E)'],
        'Rate': [2.75, 2.50, 2.50, 2.50, 2.50, 2.25, 2.25, 2.00],
        'Type': ['Actual', 'Actual', 'Actual', 'Actual', 'Actual', 'Forecast', 'Forecast', 'Forecast']
    })
    
    fig_path = go.Figure()
    
    # Actual rates
    actual_data = rate_path_data[rate_path_data['Type'] == 'Actual']
    fig_path.add_trace(go.Scatter(
        x=actual_data['Date'],
        y=actual_data['Rate'],
        mode='lines+markers',
        name='실제 기준금리',
        line=dict(color='#42A5F5', width=3),
        marker=dict(size=10)
    ))
    
    # Forecast rates
    forecast_data = rate_path_data[rate_path_data['Type'] == 'Forecast']
    fig_path.add_trace(go.Scatter(
        x=['2025.11'] + forecast_data['Date'].tolist(),
        y=[2.50] + forecast_data['Rate'].tolist(),
        mode='lines+markers',
        name='예상 경로',
        line=dict(color='#FFA726', width=3, dash='dash'),
        marker=dict(size=10, symbol='diamond')
    ))
    
    fig_path.update_layout(
        title="기준금리 추이 및 전망",
        template='plotly_dark',
        height=400,
        yaxis_title="기준금리 (%)",
        yaxis_range=[1.8, 3.0],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_path, use_container_width=True)
    
    # Prediction Cards
    col_pred1, col_pred2 = st.columns(2)
    
    with col_pred1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%); 
                    padding: 30px; border-radius: 12px; min-height: 250px;
                    box-shadow: 0 10px 30px rgba(21,101,192,0.4);">
            <h3 style="color: white; margin-top: 0;">🎯 기준금리 전망</h3>
            <div style="display: flex; align-items: baseline; margin: 20px 0;">
                <span style="font-size: 3rem; font-weight: bold; color: white;">65%</span>
                <span style="font-size: 1.2rem; color: #90CAF9; margin-left: 10px;">확률</span>
            </div>
            <p style="color: #B3E5FC; font-size: 1.1rem; line-height: 1.7;">
                <strong>2026년 1분기 중 25bp 인하</strong> 예상<br/>
                • 1월 동결 후 2월 인하 가능성 高<br/>
                • 경기 둔화 확인 시 연속 인하 가능
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_pred2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); 
                    padding: 30px; border-radius: 12px; min-height: 250px;
                    box-shadow: 0 10px 30px rgba(46,125,50,0.4);">
            <h3 style="color: white; margin-top: 0;">📊 2026년 말 기준금리</h3>
            <div style="display: flex; align-items: baseline; margin: 20px 0;">
                <span style="font-size: 3rem; font-weight: bold; color: white;">2.00%</span>
                <span style="font-size: 1.2rem; color: #A5D6A7; margin-left: 10px;">전망</span>
            </div>
            <p style="color: #C8E6C9; font-size: 1.1rem; line-height: 1.7;">
                연간 <strong>50bp 인하</strong> 예상 (2회)<br/>
                • 상반기: 25bp × 1회<br/>
                • 하반기: 25bp × 1회
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== MARKET IMPACT ====================
    st.markdown("## 💹 자산별 영향 분석")
    
    # Impact Matrix
    col_bond, col_stock, col_fx, col_re = st.columns(4)
    
    with col_bond:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #4CAF50; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">📈</p>
            <h4 style="color: #4CAF50; margin: 15px 0 10px 0; font-size: 1.3rem;">채권</h4>
            <div style="background-color: rgba(76,175,80,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #4CAF50; font-weight: bold; font-size: 1.1rem;">BULLISH</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 금리 인하 기대로 채권 가격 상승 예상<br/>
                • 국고채 3년물 금리 2.8% → 2.5% 전망<br/>
                • 장기물 선호 전략 유효
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_stock:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #FFC107; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">📊</p>
            <h4 style="color: #FFC107; margin: 15px 0 10px 0; font-size: 1.3rem;">주식</h4>
            <div style="background-color: rgba(255,193,7,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #FFC107; font-weight: bold; font-size: 1.1rem;">NEUTRAL</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 금리 인하는 긍정적이나 경기 둔화 우려<br/>
                • 금융주 약세, 성장주 강세 차별화<br/>
                • 섹터 선별 투자 필요
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_fx:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #F44336; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">💱</p>
            <h4 style="color: #F44336; margin: 15px 0 10px 0; font-size: 1.3rem;">환율</h4>
            <div style="background-color: rgba(244,67,54,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #F44336; font-weight: bold; font-size: 1.1rem;">VOLATILE</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 원/달러 1,350~1,420원 박스권 전망<br/>
                • 한미 금리차 확대 시 원화 약세 압력<br/>
                • 미 연준 정책에 연동 가능성
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_re:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #9C27B0; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">🏠</p>
            <h4 style="color: #9C27B0; margin: 15px 0 10px 0; font-size: 1.3rem;">부동산</h4>
            <div style="background-color: rgba(156,39,176,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #9C27B0; font-weight: bold; font-size: 1.1rem;">CAUTIOUS</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 금리 인하 시 수요 자극 가능성<br/>
                • 수도권 vs 지방 양극화 지속 전망<br/>
                • 정부 규제 정책 변수 주시
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== EXPERT COMMENTARY ====================
    st.markdown("## 👨‍💼 전문가 코멘터리")
    
    # Expert Commentary using Streamlit columns instead of complex HTML
    expert_col1, expert_col2 = st.columns([1, 8])
    
    with expert_col1:
        st.markdown("""
        <div style="width: 70px; height: 70px; background: linear-gradient(135deg, #42A5F5, #1976D2); 
                    border-radius: 50%; display: flex; align-items: center; justify-content: center;
                    margin-top: 10px;">
            <span style="font-size: 2rem;">🤖</span>
        </div>
        """, unsafe_allow_html=True)
    
    with expert_col2:
        st.markdown("#### BOK Policy Analyzer AI")
        st.markdown("""
        > "11월 통화정책방향 결정문의 텍스트를 분석한 결과, **Tone Index가 -0.34로 명확한 비둘기파 영역**에 
        > 진입했습니다. 특히 '유연하게 대응'이라는 표현의 등장은 2024년 하반기 긴축 사이클 이후 처음으로 
        > 나타난 것으로, 통화정책의 **피봇(Pivot) 가능성**을 강하게 시사합니다.
        > 
        > 다만, 환율 변동성과 가계부채 리스크에 대한 언급이 여전히 강조되고 있어, 인하 시점은 
        > **2026년 1~2월로 예상**됩니다. 연간 인하 폭은 50bp(2회 인하)가 기본 시나리오이며, 
        > 글로벌 경기 둔화 가속 시 75bp까지 확대될 수 있습니다."
        """)
    
    # ==================== FOOTER ====================
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 30px 0;">
        <p style="margin-bottom: 10px;">
            <strong style="color: #64B5F6;">BOK Policy Analyzer</strong> | AI-Powered Monetary Policy Analysis
        </p>
        <p style="font-size: 0.85rem; color: #888;">
            본 분석은 AI 모델에 의해 생성되었으며, 투자 조언이 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_generic_analysis(row):
    """일반적인 데이터에 대한 분석 뷰 (향후 구현)"""
    st.info("이 회의에 대한 상세 분석 리포트는 준비 중입니다.")
    st.markdown(f"**Tone Index:** {row['tone_index']:.3f}")
    st.markdown(f"**해석:** {row['interpretation']}")
