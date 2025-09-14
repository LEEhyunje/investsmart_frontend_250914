"""
Streamlit Chart Component - 원본 코드와 동일한 차트 구조
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.json_client import InvestSmartJSONClient

logger = logging.getLogger(__name__)


def resample_data_to_timeframe(data: Dict[str, Any], timeframe: str) -> Dict[str, Any]:
    """
    데이터를 지정된 시간축으로 리샘플링
    
    Args:
        data: 원본 데이터 (OHLCV + signals)
        timeframe: 'daily', 'weekly', 'monthly'
    
    Returns:
        리샘플링된 데이터
    """
    if timeframe == "daily":
        return data
    
    # DataFrame 생성 - JSON 클라이언트 데이터 구조에 맞게 수정
    stock_data = data.get('data', {})
    df = pd.DataFrame({
        'date': pd.to_datetime(data['dates']),
        'open': stock_data.get('open', []),
        'high': stock_data.get('high', []),
        'low': stock_data.get('low', []),
        'close': stock_data.get('close', []),
        'volume': stock_data.get('volume', [])
    })
    df.set_index('date', inplace=True)
    
    # 시간축별 리샘플링 규칙
    if timeframe == "weekly":
        resample_rule = 'W-FRI'  # 금요일 종가 기준 주봉
    elif timeframe == "monthly":
        resample_rule = 'M'  # 월말 기준 월봉
    else:
        return data
    
    # OHLCV 리샘플링
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    resampled_df = df.resample(resample_rule).agg(ohlc_dict).dropna()
    
    # 시그널을 리샘플링된 시간축에 매핑
    original_signals = data.get('signals', {})
    resampled_dates = resampled_df.index.strftime('%Y-%m-%d').tolist()
    mapped_signals = map_signals_to_timeframe(original_signals, data['dates'], resampled_dates, timeframe)
    
    # FCV 값들도 리샘플링에 맞게 처리
    resampled_indicators = {}
    if data.get('indicators'):
        for indicator_name, indicator_values in data['indicators'].items():
            if indicator_name == 'Final_Composite_Value' and len(indicator_values) > 0:
                # FCV는 주봉/월봉에서는 해당 기간의 마지막 값 사용
                resampled_fcv = []
                for i, resampled_date in enumerate(resampled_dates):
                    # 해당 주/월에 해당하는 원본 FCV 값들 중 마지막 값 사용
                    resampled_date_dt = pd.to_datetime(resampled_date)
                    if timeframe == "weekly":
                        week_start = resampled_date_dt - pd.Timedelta(days=6)
                        week_end = resampled_date_dt
                    elif timeframe == "monthly":
                        week_start = resampled_date_dt.replace(day=1)
                        week_end = resampled_date_dt
                    else:
                        week_start = week_end = resampled_date_dt
                    
                    # 해당 기간의 원본 데이터에서 FCV 값 찾기
                    period_fcv_values = []
                    for j, orig_date in enumerate(pd.to_datetime(data['dates'])):
                        if week_start <= orig_date <= week_end and j < len(indicator_values):
                            period_fcv_values.append(indicator_values[j])
                    
                    # 해당 기간의 마지막 FCV 값 사용
                    if period_fcv_values:
                        resampled_fcv.append(period_fcv_values[-1])
                    else:
                        resampled_fcv.append(0)
                
                resampled_indicators[indicator_name] = resampled_fcv
            else:
                resampled_indicators[indicator_name] = indicator_values
    
    # 리샘플링된 데이터로 변환 - JSON 클라이언트 구조에 맞게
    resampled_data = {
        'symbol': data['symbol'],
        'dates': resampled_dates,
        'data': {
            'open': resampled_df['open'].tolist(),
            'high': resampled_df['high'].tolist(),
            'low': resampled_df['low'].tolist(),
            'close': resampled_df['close'].tolist(),
            'volume': resampled_df['volume'].tolist()
        },
        'signals': mapped_signals,  # 매핑된 시그널 사용
        'indicators': resampled_indicators,  # 리샘플링된 지표 사용
        'trendlines': data.get('trendlines', []),  # 추세선도 그대로 유지
        'last_updated': data.get('last_updated')
    }
    
    return resampled_data


def map_signals_to_timeframe(original_signals: Dict[str, List], original_dates: List[str], 
                           resampled_dates: List[str], timeframe: str) -> Dict[str, List]:
    """
    원본 일봉 시그널을 리샘플링된 시간축에 매핑
    
    Args:
        original_signals: 원본 시그널 데이터
        original_dates: 원본 일봉 날짜들
        resampled_dates: 리샘플링된 날짜들 (주봉/월봉)
        timeframe: 'weekly' 또는 'monthly'
    
    Returns:
        리샘플링된 시간축에 맞춰진 시그널 데이터
    """
    if timeframe == "daily":
        return original_signals
    
    # 원본 날짜를 datetime으로 변환
    original_dt = pd.to_datetime(original_dates)
    resampled_dt = pd.to_datetime(resampled_dates)
    
    # 리샘플링된 시그널 초기화
    mapped_signals = {}
    for signal_name in original_signals.keys():
        mapped_signals[signal_name] = [0] * len(resampled_dates)
    
    # 각 원본 날짜에 대해 해당하는 주봉/월봉 인덱스 찾기
    for i, orig_date in enumerate(original_dt):
        # 해당 날짜가 속하는 주봉/월봉 찾기
        if timeframe == "weekly":
            # 금요일 기준으로 해당 주 찾기
            week_end = orig_date + pd.Timedelta(days=(4 - orig_date.weekday()) % 7)
            try:
                resampled_idx = resampled_dt.get_loc(week_end)
            except KeyError:
                # 정확한 날짜가 없으면 가장 가까운 날짜 찾기
                closest_idx = resampled_dt.searchsorted(week_end)
                if closest_idx > 0:
                    resampled_idx = closest_idx - 1
                else:
                    continue
        elif timeframe == "monthly":
            # 해당 월의 마지막 날 찾기
            month_end = orig_date + pd.offsets.MonthEnd(0)
            try:
                resampled_idx = resampled_dt.get_loc(month_end)
            except KeyError:
                # 정확한 날짜가 없으면 가장 가까운 날짜 찾기
                closest_idx = resampled_dt.searchsorted(month_end)
                if closest_idx > 0:
                    resampled_idx = closest_idx - 1
                else:
                    continue
        else:
            continue
        
        # 해당 시그널 값들을 매핑
        for signal_name, signal_values in original_signals.items():
            if i < len(signal_values) and signal_values[i] != 0:
                mapped_signals[signal_name][resampled_idx] = signal_values[i]
    
    return mapped_signals


@st.cache_data(ttl=0)  # 캐시 비활성화 (개발 중)
def get_cached_signals_data(symbol: str, period: str):
    """캐시된 신호 데이터 조회 - 최적화된 캐시"""
    # data 폴더 경로 설정 (컴포넌트 기준)
    # investsmart_web/frontend/components -> investsmart_web/frontend -> data
    data_dir = os.path.join(os.path.dirname(current_dir), "data")
    data_dir = os.path.abspath(data_dir)
    
    # 전역 JSON 클라이언트 사용 (중복 생성 방지)
    if 'global_json_client' not in st.session_state:
        st.session_state.global_json_client = InvestSmartJSONClient(data_dir)
    
    return st.session_state.global_json_client.get_signals_data(symbol, period)



def _get_dynamic_annotations(fcv_has_green: bool, fcv_has_red: bool) -> list:
    """FCV 배경 색칠에 따른 동적 설명 생성 - 차트 아래 고정 위치"""
    annotations = [
        dict(
            x=0.02,
            y=-0.15,  # 차트 아래로 이동
            xref='paper',
            yref='paper',
            text="● Local Dip",
            showarrow=False,
            font=dict(size=10, color='darkgreen'),
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='darkgreen',
            borderwidth=1
        )
    ]
    
    # FCV 배경 색칠 설명 추가
    if fcv_has_green:
        annotations.append(
            dict(
                x=0.25,
                y=-0.15,
                xref='paper',
                yref='paper',
                text="🟩 적극매수",
                showarrow=False,
                font=dict(size=10, color='green'),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='darkgreen',
                borderwidth=1
            )
        )
    
    if fcv_has_red:
        annotations.append(
            dict(
                x=0.48 if fcv_has_green else 0.25,
                y=-0.15,
                xref='paper',
                yref='paper',
                text="🟥 적극매도",
                showarrow=False,
                font=dict(size=10, color='red'),
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='darkred',
                borderwidth=1
            )
        )
    
    return annotations


def render_stock_chart(
    symbol: str, 
    period: str = "1y",
    settings: Optional[Dict[str, Any]] = None
):
    """
    주식 차트 렌더링 - 시간축 지원 및 캐시된 데이터 사용으로 최적화
    """
    try:
        # 선택된 지표 그룹에 따라 시간축 결정
        timeframe = "daily"  # 기본값
        if settings and 'selected_indicator_group' in settings:
            indicator_group = settings['selected_indicator_group']
            if indicator_group == "Short-term Analysis(daily chart)":
                timeframe = "daily"
            elif indicator_group == "Mid-term Analysis(weekly chart)":
                timeframe = "weekly"
            elif indicator_group == "Long-term Analysis(monthly chart)":
                timeframe = "monthly"
        
        
        # 캐시된 데이터 로딩 (JSON 파일에서 직접 읽기)
        with st.spinner(f"{symbol} 데이터를 불러오는 중... 📊 참고용 정보: 제공되는 시그널과 지표는 투자 교육 목적이며, 투자 권유가 아닙니다."):
            # 신호 데이터 조회 (JSON에서 직접 읽기)
            signals_data = get_cached_signals_data(symbol, period)
            
            # 시간축에 따라 데이터 리샘플링
            signals_data = resample_data_to_timeframe(signals_data, timeframe)
            
            # 데이터가 없는 경우 체크
            if signals_data.get('error') or not signals_data.get('dates'):
                st.warning(f"⚠️ {symbol} 종목은 아직 지원하지 않는 종목입니다.")
                st.info("현재 지원하는 종목: 코스피, 나스닥, TLT, USD/KRW 환율")
                return
            
            # 시간축 정보 표시
            timeframe_names = {
                "daily": "Daily Chart",
                "weekly": "Weekly Chart", 
                "monthly": "Monthly Chart"
            }
            timeframe_display = timeframe_names.get(timeframe, "Daily Chart")
            
            data_count = len(signals_data.get('dates', []))
            st.markdown(f"### 📈 {signals_data.get('symbol', symbol)} - {timeframe_display} ({data_count} candles)")
        
        # 차트 생성 (시그널 체크박스 변경 시에는 데이터 재다운로드 없이 차트만 재생성)
        _create_candlestick_chart(
            signals_data, 
            settings
        )
        
    except Exception as e:
        logger.error(f"차트 렌더링 실패: {symbol}, {e}")
        st.error(f"차트를 불러올 수 없습니다: {e}")


def _create_candlestick_chart(
    signals_data: Dict[str, Any],
    settings: Optional[Dict[str, Any]]
):
    """캔들스틱 차트 생성 - 인덱스 오류 방지 및 전체화면 최적화"""
    try:
        # 데이터 추출
        dates = pd.to_datetime(signals_data["dates"])
        open_prices = signals_data["data"]["open"]
        high_prices = signals_data["data"]["high"]
        low_prices = signals_data["data"]["low"]
        close_prices = signals_data["data"]["close"]
        volume = signals_data["data"]["volume"]
        
        # 데이터 길이 검증 및 정렬 (인덱스 오류 방지)
        min_length = min(len(dates), len(open_prices), len(high_prices), len(low_prices), len(close_prices))
        if min_length == 0:
            st.error("데이터가 없습니다.")
            return
            
        # 모든 데이터를 동일한 길이로 맞춤
        dates = dates[:min_length]
        open_prices = open_prices[:min_length]
        high_prices = high_prices[:min_length]
        low_prices = low_prices[:min_length]
        close_prices = close_prices[:min_length]
        
        # 단일 차트 생성 (FCV 서브차트 제거)
        fig = go.Figure()
        
        
        # 캔들스틱 차트 (메인 차트)
        fig.add_trace(
            go.Candlestick(
                x=dates,
                open=open_prices,
                high=high_prices,
                low=low_prices,
                close=close_prices,
                name="주가",
                increasing_line_color='red',
                decreasing_line_color='blue'
            )
        )
        
        # 추세선 추가 (JSON 데이터에서 읽어오기)
        if signals_data.get("trendlines"):
            trendlines = signals_data["trendlines"]
            for trendline in trendlines:
                points = trendline.get("points", [])
                if len(points) >= 2:
                    trendline_dates = [pd.to_datetime(p["date"]) for p in points]
                    trendline_prices = [p["price"] for p in points]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=trendline_dates,
                            y=trendline_prices,
                            name=trendline["name"],
                            line=dict(
                                color=trendline["color"],
                                width=2,
                                dash="dash"
                            ),
                            mode="lines"
                        )
                    )
        
        # 시그널 표시 (원본 코드와 정확히 동일 + 색깔 구분)
        if settings and settings.get('selected_signals') and signals_data.get("signals"):
            signals = signals_data["signals"]
            show_buy_signals = settings.get('show_buy_signals', True)
            show_sell_signals = settings.get('show_sell_signals', True)
            
            # 시그널별 색깔 및 스타일 정의 (매수 신호: 가로 삼각형, 반전 신호: 세로 삼각형)
            signal_styles = {
                'short_signal_v2': {
                    'buy': {'color': '#32CD32', 'size': 8, 'opacity': 0.8, 'line_width': 2, 'label': 'SHORT', 'symbol': 'circle'},
                    'sell': {'color': '#FF4444', 'size': 12, 'opacity': 0.8, 'line_width': 2, 'label': 'SHORT', 'symbol': 'triangle-left'}
                },
                'macd_signal': {
                    'buy': {'color': '#FF4444', 'size': 16, 'opacity': 0.95, 'line_width': 4, 'label': 'Rebound 가능성', 'symbol': 'circle'},
                    'sell': {'color': '#FF6666', 'size': 16, 'opacity': 0.85, 'line_width': 2, 'label': 'SHORT', 'symbol': 'triangle-down'}
                },
                'short_signal_v1': {
                    'buy': {'color': '#32CD32', 'size': 9, 'opacity': 0.8, 'line_width': 2, 'label': 'MID', 'symbol': 'circle'},
                    'sell': {'color': '#FF7777', 'size': 13, 'opacity': 0.8, 'line_width': 2, 'label': 'MID', 'symbol': 'triangle-left'}
                },
                'momentum_color_signal': {
                    'buy': {'color': '#FF4444', 'size': 18, 'opacity': 0.95, 'line_width': 4, 'label': 'Rebound 가능성', 'symbol': 'circle'},
                    'sell': {'color': '#FF8888', 'size': 17, 'opacity': 0.85, 'line_width': 2, 'label': 'MID', 'symbol': 'triangle-down'}
                },
                'long_signal': {
                    'buy': {'color': '#32CD32', 'size': 10, 'opacity': 0.8, 'line_width': 2, 'label': 'LONG', 'symbol': 'circle'},
                    'sell': {'color': '#FF9999', 'size': 14, 'opacity': 0.8, 'line_width': 2, 'label': 'LONG', 'symbol': 'triangle-left'}
                },
                'combined_signal_v1': {
                    'buy': {'color': '#FF4444', 'size': 17, 'opacity': 0.95, 'line_width': 4, 'label': 'Rebound 가능성', 'symbol': 'circle'},
                    'sell': {'color': '#FFAAAA', 'size': 15, 'opacity': 0.85, 'line_width': 2, 'label': 'LONG', 'symbol': 'triangle-down'}
                }
            }
            
            for signal_name in settings['selected_signals']:
                if signal_name in signals:
                    signal_values = signals[signal_name]
                    signal_style = signal_styles.get(signal_name, {'buy': {'color': '#00FF00', 'size': 14, 'opacity': 0.8, 'line_width': 2, 'label': 'SIGNAL', 'symbol': 'triangle-up'}, 'sell': {'color': '#FF0000', 'size': 14, 'opacity': 0.8, 'line_width': 2, 'label': 'SIGNAL', 'symbol': 'triangle-down'}})
                    
                    # 매수 신호 표시 (인덱스 오류 방지) - FCV 제외
                    # 체크박스 상태 확인
                    should_show_signal = True
                    if signal_name in ['short_signal_v2', 'short_signal_v1', 'long_signal']:
                        should_show_signal = st.session_state.get('show_local_dip', True)
                    elif signal_name in ['macd_signal', 'momentum_color_signal', 'combined_signal_v1']:
                        should_show_signal = st.session_state.get('show_rebound_potential', True)
                    
                    if show_buy_signals and signal_name != 'fcv_signal' and should_show_signal:
                        buy_signals = []
                        
                        # 주봉 기준 신호는 해당 주의 첫 번째 신호만 표시
                        if signal_name in ['momentum_color_signal']:
                            # 주별로 그룹화하여 각 주의 첫 번째 신호만 표시
                            weekly_signals = {}
                            for i, signal in enumerate(signal_values):
                                if i < min_length and signal == 1:  # 인덱스 범위 체크
                                    # 해당 날짜의 주 시작일(월요일) 계산
                                    week_start = dates[i] - pd.Timedelta(days=dates[i].weekday())
                                    week_key = week_start.strftime('%Y-%W')
                                    
                                    # 해당 주에 아직 신호가 없으면 추가
                                    if week_key not in weekly_signals:
                                        weekly_signals[week_key] = (dates[i], low_prices[i] * 0.99)
                            
                            # 각 주의 첫 번째 신호만 추가
                            buy_signals = list(weekly_signals.values())
                        else:
                            # 일반 신호는 모든 날짜에 표시
                            for i, signal in enumerate(signal_values):
                                if i < min_length and signal == 1:  # 인덱스 범위 체크
                                    buy_signals.append((dates[i], low_prices[i] * 0.97))
                        
                        # 반전 시그널에 대한 BUY! 텍스트 표시
                        reversal_signals = ['macd_signal', 'momentum_color_signal', 'combined_signal_v1']
                        if signal_name in reversal_signals:
                            # 해당 그룹의 매수 시그널 찾기
                            group_buy_signals = []
                            if signal_name == 'macd_signal':
                                group_buy_signals = ['short_signal_v2']  # 단기 그룹
                            elif signal_name == 'momentum_color_signal':
                                group_buy_signals = ['short_signal_v1']  # 중기 그룹
                            elif signal_name == 'combined_signal_v1':
                                group_buy_signals = ['long_signal']  # 장기 그룹
                            
                            buy_text_signals = []
                            if signal_name == 'momentum_color_signal':
                                # 중기 추세전환은 주별로 첫 번째 BUY!만 표시
                                weekly_buy_texts = {}
                                for i, signal in enumerate(signal_values):
                                    if i < min_length and signal == 1:  # 반전 시그널이 있는 경우
                                        # 최근 50개 데이터에서 해당 그룹의 매수 시그널 확인 (중기)
                                        start_idx = max(0, i - 50)
                                        
                                        # 해당 그룹의 매수 시그널이 있는지 확인
                                        has_buy_signal = False
                                        for group_signal in group_buy_signals:
                                            if group_signal in signals:
                                                group_values = signals[group_signal]
                                                if len(group_values) > i:
                                                    recent_group_signals = group_values[start_idx:i]
                                                    if 1 in recent_group_signals:
                                                        has_buy_signal = True
                                                        break
                                        
                                        # 매수 시그널이 있었으면 해당 주의 첫 번째 BUY!만 추가
                                        if has_buy_signal:
                                            week_start = dates[i] - pd.Timedelta(days=dates[i].weekday())
                                            week_key = week_start.strftime('%Y-%W')
                                            if week_key not in weekly_buy_texts:
                                                weekly_buy_texts[week_key] = (dates[i], low_prices[i] * 0.95)  # 위치 올림
                                
                                buy_text_signals = list(weekly_buy_texts.values())
                            else:
                                # 단기/장기는 모든 BUY! 표시
                                for i, signal in enumerate(signal_values):
                                    if i < min_length and signal == 1:  # 반전 시그널이 있는 경우
                                        # 최근 20개 데이터에서 해당 그룹의 매수 시그널 확인
                                        start_idx = max(0, i - 20)
                                        
                                        # 해당 그룹의 매수 시그널이 있는지 확인
                                        has_buy_signal = False
                                        for group_signal in group_buy_signals:
                                            if group_signal in signals:
                                                group_values = signals[group_signal]
                                                if len(group_values) > i:
                                                    recent_group_signals = group_values[start_idx:i]
                                                    if 1 in recent_group_signals:
                                                        has_buy_signal = True
                                                        break
                                        
                                        # 매수 시그널이 있었으면 BUY! 텍스트 추가
                                        if has_buy_signal:
                                            buy_text_signals.append((dates[i], low_prices[i] * 0.95))  # 위치 올림
                            
                            # BUY! 텍스트 표시 (테두리가 있는 네모 칸) - Rebound Alert 체크박스 상태 확인
                            if buy_text_signals and st.session_state.get('show_rebound_alert', True):
                                text_dates, text_prices = zip(*buy_text_signals)
                                
                                # 텍스트 박스를 위한 annotation 사용 (위치 아래로 + 선 연결)
                                for i, (date, price) in enumerate(zip(text_dates, text_prices)):
                                    # Rebound Alert 텍스트 박스 (아래쪽에 배치)
                                    fig.add_annotation(
                                        x=date,
                                        y=price - 1,  # 위치를 아래로 이동
                                        text="Rebound Alert 🚀",
                                        showarrow=True,  # 화살표 표시
                                        arrowhead=2,
                                        arrowcolor='red',
                                        arrowwidth=2,
                                        ax=0,  # 화살표 X 방향 (수직)
                                        ay=60,  # 화살표 Y 방향 (위쪽으로) - 2배로 늘림
                                        font=dict(
                                            color='white',
                                            size=12,
                                            family='Arial Black'
                                        ),
                                        bgcolor='red',
                                        bordercolor='darkred',
                                        borderwidth=2,
                                        borderpad=4,
                                        xref='x',
                                        yref='y'
                                    )
                        
                        if buy_signals:
                            buy_dates, buy_prices = zip(*buy_signals)
                            
                            # 매수 신호 표시 (가로 삼각형)
                            fig.add_trace(
                                go.Scatter(
                                    x=buy_dates,
                                    y=buy_prices,
                                    mode='markers',
                                    marker=dict(
                                        symbol=signal_style['buy']['symbol'],
                                        size=signal_style['buy']['size'],
                                        color=signal_style['buy']['color'],
                                        opacity=signal_style['buy']['opacity'],
                                        line=dict(width=signal_style['buy']['line_width'], color='darkgreen' if signal_style['buy']['color'] in ['#32CD32', '#00FFFF'] else 'darkred')
                                    ),
                                    name=f'{signal_style["buy"]["label"]} BUY'
                                )
                            )
                            
                            # low point 텍스트는 제거 (우측 상단에 설명으로 대체)
                    
                    
                    # 매도 신호 표시 (인덱스 오류 방지) - 일시적으로 비활성화
                    # if show_sell_signals:
                    #     sell_signals = []
                    #     for i, signal in enumerate(signal_values):
                    #         if i < min_length and signal == -1:  # 인덱스 범위 체크
                    #             sell_signals.append((dates[i], high_prices[i] * 1.02))
                    #     
                    #     if sell_signals:
                    #         sell_dates, sell_prices = zip(*sell_signals)
                    #         fig.add_trace(
                    #             go.Scatter(
                    #                 x=sell_dates,
                    #                 y=sell_prices,
                    #                 mode='markers',
                    #                 marker=dict(
                    #                     symbol=signal_style['sell']['symbol'],
                    #                     size=signal_style['sell']['size'],
                    #                     color=signal_style['sell']['color'],
                    #                     opacity=signal_style['sell']['opacity'],
                    #                     line=dict(width=signal_style['sell']['line_width'], color='darkred')
                    #                 ),
                    #                 name=f'{signal_style["sell"]["label"]} SELL'
                    #             )
                    #         )
        
        
        # FCV 배경 색칠 (단기중기장기 무관하게 배경에 색칠) - FCV Zones 체크박스 상태 확인
        fcv_has_green = False
        fcv_has_red = False
        
        if signals_data.get("indicators") and "Final_Composite_Value" in signals_data["indicators"] and st.session_state.get('show_fcv_zones', True):
            fcv_values = signals_data["indicators"]["Final_Composite_Value"]
            if len(fcv_values) > 0:
                # FCV >= 0.5: 녹색 배경, FCV <= -0.5: 빨간색 배경
                for i in range(min(len(fcv_values), min_length)):
                    fcv_val = fcv_values[i]
                    if fcv_val >= 0.5:
                        fcv_has_green = True
                        # 녹색 배경
                        fig.add_shape(
                            type="rect",
                            x0=dates[i], x1=dates[i+1] if i+1 < len(dates) else dates[i],
                            y0=0, y1=1,
                            yref="paper",
                            fillcolor="rgba(0, 255, 0, 0.1)",
                            line=dict(width=0)
                        )
                    elif fcv_val <= -0.5:
                        fcv_has_red = True
                        # 빨간색 배경
                        fig.add_shape(
                            type="rect",
                            x0=dates[i], x1=dates[i+1] if i+1 < len(dates) else dates[i],
                            y0=0, y1=1,
                            yref="paper",
                            fillcolor="rgba(255, 0, 0, 0.1)",
                            line=dict(width=0)
                        )
        
        # 차트 레이아웃 설정 (모바일 최적화 - 가로 스크롤)
        fig.update_layout(
            title="",  # 제목 제거
            xaxis_rangeslider_visible=False,
            height=500,  # 차트 높이 확대
            width=1200,  # 차트 가로 길이 확장
            showlegend=False,  # 기본 범례 비활성화 (동적 범례 사용)
            template="plotly_white",
            margin=dict(l=2, r=2, t=15, b=2),  # 여백 원래대로
            font=dict(size=9, color='black'),  # 폰트 크기 확대 및 색상 진하게
            plot_bgcolor='#dee2e6',  # 더욱 어두운 회색 배경
            paper_bgcolor='#dee2e6',  # 더욱 어두운 회색 배경
            # 모바일 가로 스크롤 활성화
            dragmode='pan',  # 가로 드래그 활성화
            hovermode=False,  # 호버 툴팁 완전 비활성화
            # 범례 제거 (Streamlit으로 별도 표시)
            annotations=[],
            # 가로 스크롤 설정
            xaxis=dict(
                fixedrange=False,  # X축 스크롤 허용
                showspikes=False,  # 스파이크 제거
                spikemode='across',
                spikecolor='grey',
                spikesnap='cursor',
                spikethickness=1,
                # 가로 스크롤 범위 설정
                rangeslider=dict(visible=False),
                autorange=True,  # 자동 범위 조정 활성화
                # 눈금 글자 설정
                tickfont=dict(size=11, color='black'),
                title=dict(font=dict(size=12, color='black'))
            ),
            yaxis=dict(
                fixedrange=True,  # Y축은 고정 (세로 스크롤 방지)
                showspikes=False,  # 스파이크 제거
                spikemode='across',
                spikecolor='grey',
                spikesnap='cursor',
                spikethickness=1,
                # 눈금 글자 설정
                tickfont=dict(size=11, color='black'),
                title=dict(font=dict(size=12, color='black'))
            )
        )
        
        # Y축 설정 (제목 제거로 공간 확보 + 인터랙티브 제한)
        fig.update_yaxes(
            title_text="", 
            fixedrange=True,  # 주가 축 고정
            showspikes=False
        )
        
        # 차트 표시 (모바일 최적화)
        st.plotly_chart(
            fig, 
            use_container_width=False,  # 컨테이너 너비 사용 안함 (고정 크기 사용)
            config={
                'displayModeBar': False,  # 툴바 숨김
                'scrollZoom': True,  # 스크롤 줌 활성화
                'doubleClick': 'reset+autosize',  # 더블클릭으로 리셋
                'showTips': False,  # 팁 숨김
                'responsive': False  # 반응형 비활성화 (고정 크기 유지)
            }
        )
        
        # 차트 아래 범례 표시 (Streamlit) - 체크박스 상태에 따라 동적 표시
        legend_cols = []
        if st.session_state.get('show_local_dip', True):
            legend_cols.append(1)
        if st.session_state.get('show_rebound_potential', True):
            legend_cols.append(1)
        if fcv_has_green and st.session_state.get('show_fcv_zones', True):
            legend_cols.append(1)
        if fcv_has_red and st.session_state.get('show_fcv_zones', True):
            legend_cols.append(1)
        
        if legend_cols:
            cols = st.columns(len(legend_cols))
            col_idx = 0
            
            if st.session_state.get('show_local_dip', True):
                with cols[col_idx]:
                    st.markdown("**<span style='color: #32CD32; border: 2px solid #004000; border-radius: 50%; padding: 0px; background-color: rgba(50, 205, 50, 0.1); font-size: 0.6em;'>●</span> Local Dip**", unsafe_allow_html=True)
                col_idx += 1
            
            if st.session_state.get('show_rebound_potential', True):
                with cols[col_idx]:
                    st.markdown("**<span style='color: #FF4444; border: 2px solid #660000; border-radius: 50%; padding: 0px; background-color: rgba(255, 68, 68, 0.1); font-size: 0.7em;'>●</span> Rebound Potential**", unsafe_allow_html=True)
                col_idx += 1
            
            if fcv_has_green and st.session_state.get('show_fcv_zones', True):
                with cols[col_idx]:
                    st.markdown("**<span style='background-color: #90EE90; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>Value Zone!!!</span>**", unsafe_allow_html=True)
                col_idx += 1
            
            if fcv_has_red and st.session_state.get('show_fcv_zones', True):
                with cols[col_idx]:
                    st.markdown("**<span style='background-color: #FFB6C1; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>Risk Zone!!!</span>**", unsafe_allow_html=True)
        
        # 신호 해석 가이드 추가
        st.markdown("---")
        st.markdown("### 📈 **Signal Interpretation Guide**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **🔍 Signal Meanings**
            - **● Local Dip**: Short-term buy opportunities (green circles)
            - **● Rebound Potential**: Reversal signals indicating rebound chances (red circles)
            - **🚀 Rebound Alert**: Strong buy signals with arrow pointing to exact location
            """)
        with col2:
            st.markdown("""
            **🎯 FCV Background Colors**
            - **🟩 Value Zone!!!**: FCV ≥ 0.5, Strong buy signal
            - **🟥 Risk Zone!!!**: FCV ≤ -0.5, Strong sell signal
            - **⚪ Neutral Zone**: FCV -0.5 ~ 0.5, Wait and see recommended
            """)
        
        # 시그널 표시/숨김 컨트롤
        st.markdown("---")
        st.markdown("### 🎛️ **Signal Display Controls**")
        
        # 세션 상태 초기화
        if 'show_local_dip' not in st.session_state:
            st.session_state.show_local_dip = True
        if 'show_rebound_potential' not in st.session_state:
            st.session_state.show_rebound_potential = True
        if 'show_rebound_alert' not in st.session_state:
            st.session_state.show_rebound_alert = True
        if 'show_fcv_zones' not in st.session_state:
            st.session_state.show_fcv_zones = True
        
        # 체크박스들 (임시 상태로 저장)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            temp_local_dip = st.checkbox(
                "● Local Dip", 
                value=st.session_state.show_local_dip,
                key="local_dip_checkbox"
            )
        with col2:
            temp_rebound_potential = st.checkbox(
                "● Rebound Potential", 
                value=st.session_state.show_rebound_potential,
                key="rebound_potential_checkbox"
            )
        with col3:
            temp_rebound_alert = st.checkbox(
                "🚀 Rebound Alert", 
                value=st.session_state.show_rebound_alert,
                key="rebound_alert_checkbox"
            )
        with col4:
            temp_fcv_zones = st.checkbox(
                "🎯 FCV Zones", 
                value=st.session_state.show_fcv_zones,
                key="fcv_zones_checkbox"
            )
        
        # Apply 버튼
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Apply Signal Settings", use_container_width=True, type="primary"):
                st.session_state.show_local_dip = temp_local_dip
                st.session_state.show_rebound_potential = temp_rebound_potential
                st.session_state.show_rebound_alert = temp_rebound_alert
                st.session_state.show_fcv_zones = temp_fcv_zones
                st.rerun()  # 페이지 새로고침으로 차트 업데이트
        
    except Exception as e:
        logger.error(f"Candlestick chart generation failed: {e}")
        st.error(f"An error occurred while generating the chart: {e}")
        st.error(f"차트 생성 중 오류가 발생했습니다: {e}")