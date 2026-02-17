import streamlit as st

def render_analysis_2026_01(row):
    """2026년 1월 15일 발표에 대한 전문가 수준의 상세 분석"""
    
    # 기본값 (의사록 기반)
    gdp_forecast = 1.8
    cpi_forecast = 2.1
    rate_decision = 2.50
    
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
                2026년 1월 통화정책방향<br/>
                <span style="font-size: 1.8rem; color: #90CAF9;">심층 분석 리포트</span>
            </h1>
            <div style="margin-top: 25px; display: flex; gap: 30px; flex-wrap: wrap;">
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">발표일</span><br/>
                    <span style="color: white; font-size: 1.2rem; font-weight: 600;">2026년 1월 15일</span>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">기준금리</span><br/>
                    <span style="color: #4CAF50; font-size: 1.2rem; font-weight: 600;">2.50% (동결)</span>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px;">
                    <span style="color: #90CAF9; font-size: 0.8rem;">금통위 결정</span><br/>
                    <span style="color: white; font-size: 1.2rem; font-weight: 600;">만장일치 동결</span>
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
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(21,101,192,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">기준금리</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">{rate_decision:.2f}%</h2>
            <p style="color: #81D4FA; margin: 0; font-size: 0.9rem;">▬ 동결 유지</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(46,125,50,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">소비자물가(Dec)</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">2.3%</h2>
            <p style="color: #A5D6A7; margin: 0; font-size: 0.9rem;">안정화 추세</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F57C00 0%, #E65100 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(245,124,0,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">성장률 전망(2026)</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">~{gdp_forecast}%</h2>
            <p style="color: #FFCC80; margin: 0; font-size: 0.9rem;">▲ 상방 리스크</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #7B1FA2 0%, #4A148C 100%); 
                    padding: 25px; border-radius: 12px; text-align: center;
                    box-shadow: 0 8px 25px rgba(123,31,162,0.3);">
            <p style="color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem;">Tone Index</p>
            <h2 style="color: white; margin: 10px 0 5px 0; font-size: 2.2rem;">{row['tone_index']:.2f}</h2>
            <p style="color: #CE93D8; margin: 0; font-size: 0.9rem;">강한 비둘기파</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Summary Text
    st.markdown("""
    <div style="background-color: #1A1A2E; padding: 30px; border-radius: 12px; 
                border-left: 5px solid #64B5F6; margin: 20px 0;">
        <h3 style="color: #64B5F6; margin-top: 0; font-size: 1.3rem;">🎯 핵심 요약</h3>
        <p style="color: #E0E0E0; font-size: 1.1rem; line-height: 1.9; margin-bottom: 0;">
            한국은행 금융통화위원회는 2026년 1월 15일 회의에서 기준금리를 연 <strong style="color: #4CAF50;">2.50%</strong>로 
            동결하기로 결정했습니다. 만장일치 결정으로, 물가 안정세와 성장 개선 흐름을 확인하며 금융안정 리스크를 고려한 결과입니다.<br><br>
            주요 포인트:
        </p>
        <ul style="color: #E0E0E0; font-size: 1.05rem; line-height: 2; margin-top: 15px;">
            <li><strong style="color: #FFB74D;">경기 회복세:</strong> 반도체 등 수출 호조로 개선 흐름 지속, AI 투자 확대로 성장 상방 리스크 증대.</li>
            <li><strong style="color: #FFB74D;">물가 둔화:</strong> 12월 소비자물가 2.3%, 근원물가 2.0%로 안정화 추세 이어짐.</li>
            <li><strong style="color: #FFB74D;">금융안정 경계:</strong> 수도권 주택가격 상승세 지속, 환율 변동성(1,400원대) 등 리스크 요인 상존.</li>
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
            <h4 style="color: #4CAF50; margin-top: 0;">긍정적 요인/기회</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>반도체 경기 호조 및 AI 관련 설비투자 확대</li>
                <li>수출 중심의 경기 개선세 지속</li>
                <li>민간소비의 완만한 회복 조짐</li>
            </ul>
            <h4 style="color: #FF7043; margin-top: 20px;">우려 요인</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>건설투자 부진 장기화</li>
                <li>내수 회복 속도의 부문별 차별화(양극화)</li>
                <li>주요국 통상환경 변화(관세 등) 불확실성</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 🏷️ 물가 동향")
        st.markdown(f"""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 10px; min-height: 280px;">
            <h4 style="color: #4CAF50; margin-top: 0;">안정화 요인</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>농축수산물 가격 오름세 둔화</li>
                <li>국제유가 안정세</li>
                <li>근원물가 2.0% 수준 유지</li>
            </ul>
            <h4 style="color: #FFC107; margin-top: 20px;">상방 리스크</h4>
            <ul style="color: #C0C0C0; line-height: 1.9;">
                <li>고환율(1,400원대) 지속에 따른 수입물가 압력</li>
                <li>공공요금 인상 가능성</li>
                <li>기대인플레이션(2.6%)의 경직성</li>
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
            <h4 style="color: white; margin: 15px 0 10px 0;">고환율 기조</h4>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.95rem; line-height: 1.6;">
                달러/원 1,477원 수준<br/>
                거주자 해외투자 확대 영향
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_house:
        st.markdown("""
        <div style="background: linear-gradient(180deg, #E65100 0%, #BF360C 100%); 
                    padding: 25px; border-radius: 12px; text-align: center; min-height: 200px;">
            <p style="font-size: 2.5rem; margin: 0;">🏠</p>
            <h4 style="color: white; margin: 15px 0 10px 0;">주택가격</h4>
            <p style="color: rgba(255,255,255,0.85); font-size: 0.95rem; line-height: 1.6;">
                수도권 중심 상승세 지속<br/>
                공급 부족 우려에 따른 불안
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
                증가세 둔화되었으나<br/>
                수도권 주택담보대출 우려
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==================== EXPERT COMMENTARY ====================
    st.markdown("## 👨‍💼 전문가 코멘터리 (AI Analysis)")
    
    # Expert Commentary
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
        st.markdown(f"#### BOK Policy Analyzer AI Insight")
        st.markdown(f"""
        > "2026년 1월 의사록 분석 결과, **Tone Index는 -0.38로 강한 비둘기파적 성향**을 보였습니다. 
        > 금리는 2.50%로 동결되었으나, 물가(2.3%)가 목표 수준에 근접하고 내수 회복이 더딘 점은 
        > **향후 금리 인하 압력**으로 작용할 것입니다.
        > 
        > 다만, 아직 1,400원대 중후반에 머물고 있는 **환율**과 **수도권 집값 불안**이 조기 인하를 제약하는 
        > 핵심 요인입니다. 위원들은 '성장세 회복 지원'을 강조하면서도 '금융안정'을 동시에 고려하고 있어,
        > 환율 및 부동산 시장이 안정되는 시점에 **금리 인하(Pivot)**가 단행될 가능성이 높습니다."
        """)
    
    st.markdown("---")

    # ==================== DECISION STATEMENT CHANGE ANALYSIS ====================
    st.markdown("## 📝 결정문 문구 변화 분석 (Statement Analysis)")

    st.markdown("""
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <thead>
            <tr style="background-color: #1E3A5F;">
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 15%; border-bottom: 2px solid #42A5F5;">항목</th>
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 40%; border-bottom: 2px solid #42A5F5;">11월 표현 (직전)</th>
                <th style="padding: 15px; text-align: left; color: #90CAF9; width: 45%; border-bottom: 2px solid #42A5F5;">1월 표현 (금번 변화)</th>
            </tr>
        </thead>
        <tbody>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>성장</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"국내경제는 내수 회복 지연에도 불구하고 수출 호조에 힘입어 완만한 성장세를 이어갔다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "국내경제는 <strong style="color: #4FC3F7;">반도체 경기 호조와 설비투자 확대</strong>로 성장세가 확대되었으나, <strong style="color: #EF5350;">건설투자 부진</strong>은 지속되었다."
                    <span style="background-color: rgba(33,150,243,0.2); color: #42A5F5; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Mixed/Neutral</span>
                </td>
            </tr>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>물가</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"소비자물가 상승률은 2% 중반 수준을 유지하였으며, 유가 상승에 따른 잠재 리스크를 주시해야 한다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "소비자물가 상승률이 <strong style="color: #4CAF50;">2.3%로 낮아지며 둔화 흐름이 지속</strong>되었고, 근원물가도 2.0% 수준에서 안정되었다."
                    <span style="background-color: rgba(76,175,80,0.2); color: #81C784; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Dovish</span>
                </td>
            </tr>
            <tr style="background-color: #0D1B2A;">
                <td style="padding: 15px; color: #E0E0E0; border-bottom: 1px solid #333;"><strong>정책방향</strong></td>
                <td style="padding: 15px; color: #B0B0B0; border-bottom: 1px solid #333;">"물가 안정에 중점을 두어 긴축 기조를 충분히 유지하되, 향후 흐름을 면밀히 점검할 것이다."</td>
                <td style="padding: 15px; color: #81D4FA; border-bottom: 1px solid #333;">
                    "물가 안정세가 확고해질 때까지 긴축 기조를 유지하되, <strong style="color: #FFB74D;">성장과 금융안정 리스크를 균형 있게 고려</strong>하여 운용할 것이다."
                    <span style="background-color: rgba(255,167,38,0.2); color: #FFB74D; 
                                 padding: 3px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 10px;">Dovish Pivot Hint</span>
                </td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)


    st.markdown("""
    <div style="background-color: #1B263B; padding: 20px; border-radius: 10px; margin-top: 20px;">
        <h4 style="color: #FFC107; margin-top: 0;">💡 시사점 (Implication)</h4>
        <p style="color: #E0E0E0; line-height: 1.8; margin-bottom: 0;">
            1월 결정문에서는 "긴축 기조 충분히 유지"라는 표현이 약화되고, "성장과 금융안정 균형 고려"라는 
            표현이 새로 등장했습니다. 이는 <strong style="color: #81D4FA;">물가 안정에 대한 자신감을 바탕으로 통화정책의 초점이 
            경기 부양으로 이동하고 있음</strong>을 시사하는 중요한 신호입니다. 다만, 금융안정(환율, 가계부채)에 대한 
            경계감은 여전히 유지되고 있어 신중한 접근이 예상됩니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # ==================== ASSET OUTLOOK ====================
    st.markdown("## 🔮 향후 자산시장 전망 (Asset Outlook)")
    
    # Impact Matrix
    col_bond, col_stock, col_fx, col_re = st.columns(4)
    
    with col_bond:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #4CAF50; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">📉</p>
            <h4 style="color: #4CAF50; margin: 15px 0 10px 0; font-size: 1.3rem;">채권 (Bonds)</h4>
            <div style="background-color: rgba(76,175,80,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #4CAF50; font-weight: bold; font-size: 1.1rem;">BULLISH</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 금리 인하 기대감 선반영 지속<br/>
                • WGBI 자금 유입 본격화 (수급 호재)<br/>
                • 국고채 금리 하향 안정화 전망
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_stock:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #FFC107; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">📊</p>
            <h4 style="color: #FFC107; margin: 15px 0 10px 0; font-size: 1.3rem;">주식 (Stocks)</h4>
            <div style="background-color: rgba(255,193,7,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #FFC107; font-weight: bold; font-size: 1.1rem;">NEUTRAL</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 반도체/AI 관련주 강세 지속<br/>
                • 내수주 회복은 금리 인하 시차 존재<br/>
                • 미 관세 정책 등 대외 불확실성 상존
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_fx:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #F44336; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">💱</p>
            <h4 style="color: #F44336; margin: 15px 0 10px 0; font-size: 1.3rem;">환율 (KRW/USD)</h4>
            <div style="background-color: rgba(244,67,54,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #F44336; font-weight: bold; font-size: 1.1rem;">VOLATILE</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 단기적 1,400원 후반대 유지 가능성<br/>
                • 거주자 해외투자 수요가 하단 지지<br/>
                • 피벗 가시화 시 점진적 하락 전환
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_re:
        st.markdown("""
        <div style="background-color: #1E1E2E; padding: 25px; border-radius: 12px; 
                    border-top: 4px solid #FF9800; text-align: center; min-height: 320px;">
            <p style="font-size: 2.5rem; margin: 0;">🏠</p>
            <h4 style="color: #FF9800; margin: 15px 0 10px 0; font-size: 1.3rem;">부동산 (Real Estate)</h4>
            <div style="background-color: rgba(255,152,0,0.2); padding: 8px; border-radius: 6px; margin: 10px 0;">
                <span style="color: #FF9800; font-weight: bold; font-size: 1.1rem;">POLARIZED</span>
            </div>
            <p style="color: #B0B0B0; font-size: 0.95rem; line-height: 1.7; text-align: left; margin-top: 15px;">
                • 서울/수도권: 공급부족 우려로 강세<br/>
                • 지방: 미분양 누적으로 약세 지속<br/>
                • 금리 인하 기대가 수도권 자극 우려
            </p>
        </div>
        """, unsafe_allow_html=True)
