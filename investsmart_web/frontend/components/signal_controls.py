"""
Signal Controls Component - 간단한 시그널 컨트롤
"""
import streamlit as st
from typing import Dict, Any, Optional
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.api_client import get_api_client


def render_signal_controls(symbol: str) -> Optional[Dict[str, Any]]:
    """
    시그널 컨트롤 컴포넌트 렌더링
    
    Args:
        symbol: 종목 심볼
        
    Returns:
        시그널 설정 딕셔너리 또는 None
    """
    try:
        api_client = get_api_client()
        available_indicators = api_client.get_available_indicators()
        
        if not available_indicators:
            st.error("지표 목록을 불러올 수 없습니다.")
            return None
        
        settings = {}
        
        # 시그널 선택
        st.subheader("🚨 시그널 선택")
        signals_list = available_indicators.get("signals", [])
        
        if signals_list:
            # 핵심 시그널들을 기본값으로 설정
            core_signals = [
                "fcv_signal",
                "short_signal_v1", 
                "short_signal_v2",
                "long_signal",
                "combined_signal_v0",
                "combined_signal_v1",
                "macd_signal",
                "momentum_color_signal"
            ]
            
            selected_signals = st.multiselect(
                "시그널 선택",
                [signal["name"] for signal in signals_list],
                default=core_signals,
                key=f"signals_{symbol}"
            )
            settings["signals"] = selected_signals
        
        # 매수/매도 시그널 표시
        st.subheader("📈 시그널 표시 옵션")
        show_buy_signals = st.checkbox("매수 시그널 표시", value=True, key=f"buy_{symbol}")
        show_sell_signals = st.checkbox("매도 시그널 표시", value=False, key=f"sell_{symbol}")
        
        settings["show_buy_signals"] = show_buy_signals
        settings["show_sell_signals"] = show_sell_signals
        
        # 추세선 표시
        st.subheader("📏 추세선 설정")
        show_trendlines = st.checkbox("추세선 표시", value=False, key=f"trendlines_{symbol}")
        settings["show_trendlines"] = show_trendlines
        
        return settings
        
    except Exception as e:
        st.error(f"시그널 설정 중 오류가 발생했습니다: {e}")
        return None


def render_simple_signal_controls() -> Dict[str, Any]:
    """
    간단한 시그널 컨트롤 (기본값 사용)
    """
    return {
        "signals": [
            "fcv_signal",
            "short_signal_v1", 
            "short_signal_v2",
            "long_signal"
        ],
        "show_buy_signals": True,
        "show_sell_signals": False,
        "show_trendlines": False
    }