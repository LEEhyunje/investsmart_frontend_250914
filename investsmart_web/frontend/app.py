"""
Streamlit Main App - 원본 코드와 동일한 단순한 차트 화면 (탭 없음)
"""
import streamlit as st
import sys
import os
import logging
from typing import Dict, Any, Optional

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 페이지 설정 (모바일 최적화)
st.set_page_config(
    page_title="InvestSmart",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",  # 모바일에서 사이드바 기본 접힘
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "InvestSmart - Educational Chart Analysis Tool"
    }
)

# 컴포넌트 import
from components.stock_selector import render_simple_stock_selector
from utils.json_client import InvestSmartJSONClient
from components.chart import render_stock_chart

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def render_disclaimer():
    """면책조항 표시 - 처음 체크하면 아예 없어짐"""
    if 'disclaimer_agreed' not in st.session_state:
        st.session_state.disclaimer_agreed = False
    
    if not st.session_state.disclaimer_agreed:
        with st.expander("⚠️ Investment Disclaimer", expanded=True):
            st.markdown("""
            **📋 Service Nature**
            - This service is designed for **investment education and information provision**
            - It is a **learning platform** providing technical analysis tools and market information
            
            **⚠️ Investment Risk Warning**
            - **All investments carry the risk of principal loss**
            - Past performance does not guarantee future returns
            - The provided information is not investment advice
            
            **📊 Limitations of Provided Information**
            - Technical indicators and signals are for reference only
            - Accuracy may vary depending on market conditions
            - All investment decisions are **your own judgment and responsibility**
            
            **🔒 Disclaimer**
            - We are not responsible for investment losses from using this service
            - We do not guarantee the accuracy of provided information
            - We recommend thorough review and expert consultation before investing
            """)
            
            agreed = st.checkbox(
                "I fully understand the above content and acknowledge the investment risks", 
                key="disclaimer_checkbox"
            )
            
            if agreed:
                st.session_state.disclaimer_agreed = True
                st.rerun()
            else:
                st.warning("⚠️ You must agree to the risk disclosure to use this service.")
                st.stop()

def get_json_client() -> InvestSmartJSONClient:
    """JSON 클라이언트 인스턴스 반환"""
    if 'json_client' not in st.session_state:
        # data 폴더 경로 설정 (프론트엔드 기준)
        # investsmart_web/frontend -> data
        data_dir = os.path.join(current_dir, "data")
        data_dir = os.path.abspath(data_dir)
        st.session_state.json_client = InvestSmartJSONClient(data_dir)
    return st.session_state.json_client


def test_json_connection() -> bool:
    """JSON 파일 연결 테스트"""
    try:
        client = get_json_client()
        # 디버깅 정보 출력 (주석처리)
        # st.write(f"🔍 데이터 폴더 경로: {client.data_dir}")
        # st.write(f"🔍 폴더 존재 여부: {os.path.exists(client.data_dir)}")
        
        # if os.path.exists(client.data_dir):
        #     files = os.listdir(client.data_dir)
        #     st.write(f"🔍 폴더 내 파일들: {files}")
        
        # 간단한 데이터 확인
        info = client.get_data_info()
        # st.write(f"🔍 데이터 정보: {info}")
        return info['total_records'] > 0
    except Exception as e:
        logger.error(f"JSON 파일 연결 실패: {e}")
        st.error(f"❌ 오류 상세: {e}")
        return False

def main():
    """주식 분석 메인 페이지 - 단계별 사용자 인터페이스"""
    # JSON 파일 연결 테스트
    if not test_json_connection():
        st.error("🚨 Signal data files not found. Please check if signal data files exist.")
        st.stop()
    
    # 면책조항 표시 (메인 페이지 상단)
    render_disclaimer()
    
    # 세션 상태 초기화
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = None
    if 'selected_indicator_group' not in st.session_state:
        st.session_state.selected_indicator_group = None
    
    # 단계별 인터페이스
    if st.session_state.step == 1:
        render_step1_symbol_selection()
    elif st.session_state.step == 2:
        render_step2_indicator_selection()
    elif st.session_state.step == 3:
        render_step3_chart_display()
    
    # 하단 면책 문구 (항상 표시)
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 12px; margin-top: 20px;'>"
        "※ This information is a data report, not investment advice. All investment decisions should be made under the investor's own responsibility."
        "</div>", 
        unsafe_allow_html=True
    )


def render_step1_symbol_selection():
    """1단계: 종목 선택"""
    st.title("📈 InvestSmart - Stock Analysis")
    st.markdown("### Step 1: Which stock (or index) are you curious about?")
    
    # 종목 선택
    symbol = render_simple_stock_selector()
    
    if symbol:
        st.session_state.selected_symbol = symbol
        st.success(f"✅ Selected Stock: **{symbol}**")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Next Step", type="primary", use_container_width=True):
                st.session_state.step = 2
                st.rerun()


def render_step2_indicator_selection():
    """2단계: 지표 그룹 선택"""
    st.title("📈 InvestSmart - Indicator Analysis")
    st.markdown("### Step 2: Which indicators are you curious about?")
    
    # 이전 단계로 돌아가기
    if st.button("← Previous Step"):
        st.session_state.step = 1
        st.rerun()
    
    st.info(f"Selected Stock: **{st.session_state.selected_symbol}**")
    
    # 지표 그룹 선택
    indicator_groups = {
        "Short-term Analysis(daily chart)": {
            "description": "Short-term trading indicators",
            "signals": ["short_signal_v2", "macd_signal"],
            "color": "#00FFFF"
        },
        "Mid-term Analysis(weekly chart)": {
            "description": "Mid-term investment indicators", 
            "signals": ["short_signal_v1", "momentum_color_signal"],
            "color": "#32CD32"
        },
        "Long-term Analysis(monthly chart)": {
            "description": "Long-term investment indicators",
            "signals": ["long_signal", "combined_signal_v1"],
            "color": "#4169E1"
        }
    }
    
    # 지표 그룹 선택 버튼들
    cols = st.columns(3)
    for i, (group_name, group_info) in enumerate(indicator_groups.items()):
        with cols[i]:
            # 각 그룹별 상세 설명 추가
            if group_name == "Short-term Analysis(daily chart)":
                st.markdown("### 🔵 Short-term")
                st.markdown("**Investment Period:** ██░░░░ (few weeks)")
                st.markdown("**Success Rate:** ████░░")
                st.markdown("""
                **Analysis:** precise timing  
                **Purpose:** Quick volatility capture and short-term trading timing  
                **Use Case:** Fast entry/exit signals during rapid rise/fall periods
                """)
            elif group_name == "Mid-term Analysis(weekly chart)":
                st.markdown("### 🟡 Mid-term")
                st.markdown("**Investment Period:** ████░░ (few months)")
                st.markdown("**Success Rate:** █████░")
                st.markdown("""
                **Analysis:** Trend Analysis  
                **Purpose:** Trend confirmation and mid-term investment direction  
                **Use Case:** Position entry after confirming weekly uptrend reversal
                """)
            elif group_name == "Long-term Analysis(monthly chart)":
                st.markdown("### 🔴 Long-term")
                st.markdown("**Investment Period:** ██████ (few years)")
                st.markdown("**Success Rate:** █████░")
                st.markdown("""
                **Analysis:** macro trends  
                **Purpose:** Value investing and portfolio strategy development  
                **Use Case:** Long-term investment, asset allocation, risk management
                """)
            
            if st.button(
                f"Select {group_name}", 
                key=f"group_{group_name}",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.selected_indicator_group = group_name
                st.session_state.selected_signals = group_info['signals']
                st.session_state.step = 3
                st.rerun()


def render_step3_chart_display():
    """3단계: 차트만 표시"""
    # 이전 단계로 돌아가기 버튼만 표시
    if st.button("← Previous Step"):
        st.session_state.step = 2
        st.rerun()
    
    # 모바일 사용 안내
    # 차트 표시 설정
    settings = {
        'selected_signals': st.session_state.selected_signals,
        'show_buy_signals': True,
        'show_sell_signals': True,
        'show_trendlines': True,
        'selected_indicators': [],
        'selected_indicator_group': st.session_state.selected_indicator_group
    }
    
    # 차트 렌더링 (3년 기본 기간) - 차트만 표시
    render_stock_chart(st.session_state.selected_symbol, "3y", settings)

if __name__ == "__main__":
    main()