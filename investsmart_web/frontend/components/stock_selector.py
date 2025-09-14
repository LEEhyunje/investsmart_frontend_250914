"""
Stock Selector Component - 간단한 종목 선택
"""
import streamlit as st
from typing import Optional
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.json_client import InvestSmartJSONClient


def render_stock_selector() -> Optional[str]:
    """
    종목 선택 컴포넌트 렌더링
    
    Returns:
        선택된 종목 심볼 또는 None
    """
    try:
        # data 폴더 경로 설정 (컴포넌트 기준)
        # investsmart_web/frontend/components -> investsmart_web/frontend -> data
        data_dir = os.path.join(os.path.dirname(current_dir), "data")
        data_dir = os.path.abspath(data_dir)
        json_client = InvestSmartJSONClient(data_dir)
        available_symbols = json_client.get_available_symbols()
        
        if not available_symbols:
            st.error("Cannot load stock list.")
            return None
        
        # 종목 선택
        selected_symbol = None
        
        # 실제 데이터가 있는 종목만 표시
        symbol_display_names = {
            # 한국
            "^KS11": "🇰🇷 KOSPI (Korea Stock Price Index)",
            "005930.KS": "🇰🇷 Samsung Electronics",
            
            # 미국
            "^IXIC": "🇺🇸 NASDAQ Composite",
            "^GSPC": "🇺🇸 S&P 500",
            "^DJI": "🇺🇸 Dow Jones Industrial Average",
            "AAPL": "🇺🇸 Apple Inc.",
            "MSFT": "🇺🇸 Microsoft Corporation",
            "SPY": "🇺🇸 S&P 500 ETF",
            "QQQ": "🇺🇸 NASDAQ 100 ETF",
            
            # 유럽
            "^FTSE": "🇬🇧 FTSE 100 (UK)",
            "^GDAXI": "🇩🇪 DAX (Germany)",
            "^FCHI": "🇫🇷 CAC 40 (France)",
            
            # 아시아
            "^N225": "🇯🇵 Nikkei 225 (Japan)",
            "^HSI": "🇭🇰 Hang Seng (Hong Kong)",
            "^AXJO": "🇦🇺 ASX 200 (Australia)",
            
            # 원자재
            "GC=F": "🥇 Gold Futures",
            "SI=F": "🥈 Silver Futures",
            "CL=F": "🛢️ Crude Oil Futures",
            "NG=F": "⛽ Natural Gas Futures",
            "ZC=F": "🌽 Corn Futures",
            "ZS=F": "🌾 Soybean Futures",
            
            # 채권/통화
            "TLT": "📈 TLT (20-Year Treasury Bond)",
            "USDKRW=X": "💱 USD/KRW Exchange Rate",
            "EURUSD=X": "💱 EUR/USD Exchange Rate",
            "GBPUSD=X": "💱 GBP/USD Exchange Rate",
            "USDJPY=X": "💱 USD/JPY Exchange Rate",
        }
        
        # 데이터가 있는 종목만 필터링
        available_options = []
        available_symbols_filtered = []
        
        for symbol in available_symbols:
            if symbol in symbol_display_names:
                available_options.append(symbol_display_names[symbol])
                available_symbols_filtered.append(symbol)
        
        if not available_options:
            st.error("Cannot load stock list.")
            return None
        
        # 종목 선택
        selected_symbol = None
        
        if available_options:
            selected_index = st.selectbox(
                "종목을 선택하세요:",
                range(len(available_options)),
                format_func=lambda x: available_options[x],
                key="stock_selector"
            )
            
            if selected_index is not None:
                selected_symbol = available_symbols_filtered[selected_index]
        
        return selected_symbol
        
    except Exception as e:
        st.error(f"종목 선택 중 오류가 발생했습니다: {e}")
        return None


def render_simple_stock_selector() -> Optional[str]:
    """
    간단한 종목 선택 (드롭다운)
    """
    try:
        # data 폴더 경로 설정 (컴포넌트 기준)
        # investsmart_web/frontend/components -> investsmart_web/frontend -> data
        data_dir = os.path.join(os.path.dirname(current_dir), "data")
        data_dir = os.path.abspath(data_dir)
        json_client = InvestSmartJSONClient(data_dir)
        available_symbols = json_client.get_available_symbols()
        
        if not available_symbols:
            st.error("Cannot load stock list.")
            return None
        
        # 실제 데이터가 있는 종목만 표시
        symbol_display_names = {
            # 한국
            "^KS11": "🇰🇷 KOSPI (Korea Stock Price Index)",
            "005930.KS": "🇰🇷 Samsung Electronics",
            
            # 미국
            "^IXIC": "🇺🇸 NASDAQ Composite",
            "^GSPC": "🇺🇸 S&P 500",
            "^DJI": "🇺🇸 Dow Jones Industrial Average",
            "AAPL": "🇺🇸 Apple Inc.",
            "MSFT": "🇺🇸 Microsoft Corporation",
            "SPY": "🇺🇸 S&P 500 ETF",
            "QQQ": "🇺🇸 NASDAQ 100 ETF",
            
            # 유럽
            "^FTSE": "🇬🇧 FTSE 100 (UK)",
            "^GDAXI": "🇩🇪 DAX (Germany)",
            "^FCHI": "🇫🇷 CAC 40 (France)",
            
            # 아시아
            "^N225": "🇯🇵 Nikkei 225 (Japan)",
            "^HSI": "🇭🇰 Hang Seng (Hong Kong)",
            "^AXJO": "🇦🇺 ASX 200 (Australia)",
            
            # 원자재
            "GC=F": "🥇 Gold Futures",
            "SI=F": "🥈 Silver Futures",
            "CL=F": "🛢️ Crude Oil Futures",
            "NG=F": "⛽ Natural Gas Futures",
            "ZC=F": "🌽 Corn Futures",
            "ZS=F": "🌾 Soybean Futures",
            
            # 채권/통화
            "TLT": "📈 TLT (20-Year Treasury Bond)",
            "USDKRW=X": "💱 USD/KRW Exchange Rate",
            "EURUSD=X": "💱 EUR/USD Exchange Rate",
            "GBPUSD=X": "💱 GBP/USD Exchange Rate",
            "USDJPY=X": "💱 USD/JPY Exchange Rate",
        }
        
        # 데이터가 있는 종목만 필터링
        available_options = []
        available_symbols_filtered = []
        
        for symbol in available_symbols:
            if symbol in symbol_display_names:
                available_options.append(symbol_display_names[symbol])
                available_symbols_filtered.append(symbol)
        
        if not available_options:
            st.error("Cannot load stock list.")
            return None
        
        # 드롭다운으로 선택
        selected_display = st.selectbox(
            "종목 선택",
            available_options,
            help="분석할 종목을 선택하세요."
        )
        
        # 선택된 종목의 심볼 찾기
        for i, display_name in enumerate(available_options):
            if display_name == selected_display:
                return available_symbols_filtered[i]
        
        return None
        
    except Exception as e:
        st.error(f"종목 선택 중 오류가 발생했습니다: {e}")
        return None