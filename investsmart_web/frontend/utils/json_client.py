"""
JSON 데이터 클라이언트
JSON 파일에서 직접 데이터를 읽어오는 간단한 클라이언트
"""
import json
import streamlit as st
from typing import Dict, List, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class InvestSmartJSONClient:
    """InvestSmart JSON 데이터 클라이언트"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._cache = {}  # 종목별 데이터 캐시
    
    def _get_symbol_filename(self, symbol: str) -> str:
        """종목 심볼을 파일명으로 변환"""
        # 특수 문자를 안전한 문자로 변환
        safe_symbol = symbol.replace('^', '').replace('=', '').replace('/', '_')
        return f"signals_{safe_symbol}.json"
    
    def _load_symbol_data(self, symbol: str) -> List[Dict]:
        """특정 종목의 JSON 파일에서 데이터 로드"""
        try:
            filename = self._get_symbol_filename(symbol)
            file_path = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"파일이 존재하지 않음: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 파일 로드 실패: {symbol}, {e}")
            return []
    
    def get_signals_data(self, symbol: str, period: str = "1y") -> Dict[str, Any]:
        """특정 종목의 신호 데이터 조회 - 최적화된 버전"""
        try:
            # 캐시에서 먼저 확인
            if symbol in self._cache:
                symbol_data = self._cache[symbol]
            else:
                # 파일에서 로드 (최근 데이터만 우선 로드)
                symbol_data = self._load_symbol_data(symbol)
                # 캐시에 저장
                self._cache[symbol] = symbol_data
            
            if not symbol_data:
                return {
                    'symbol': symbol,
                    'dates': [],
                    'signals': {},
                    'indicators': {},
                    'error': '데이터를 찾을 수 없습니다'
                }
            
            # 데이터 구조화 - 최적화된 버전 (한 번에 처리)
            dates = []
            stock_data = {'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
            signals_data = {
                'short_signal_v1': [], 'short_signal_v2': [], 'long_signal': [],
                'combined_signal_v1': [], 'macd_signal': [], 'momentum_color_signal': []
            }
            indicators_data = {'Final_Composite_Value': []}
            
            # 한 번의 루프로 모든 데이터 처리 (성능 최적화)
            for item in symbol_data:
                dates.append(item['date'])
                stock_data['open'].append(item.get('open', 0))
                stock_data['high'].append(item.get('high', 0))
                stock_data['low'].append(item.get('low', 0))
                stock_data['close'].append(item.get('close', 0))
                stock_data['volume'].append(item.get('volume', 0))
                signals_data['short_signal_v1'].append(item.get('short_signal_v1', 0))
                signals_data['short_signal_v2'].append(item.get('short_signal_v2', 0))
                signals_data['long_signal'].append(item.get('long_signal', 0))
                signals_data['combined_signal_v1'].append(item.get('combined_signal_v1', 0))
                signals_data['macd_signal'].append(item.get('macd_signal', 0))
                signals_data['momentum_color_signal'].append(item.get('momentum_color_signal', 0))
                indicators_data['Final_Composite_Value'].append(item.get('fcv', 0))
            
            return {
                'symbol': symbol,
                'dates': dates,
                'data': stock_data,
                'signals': signals_data,
                'indicators': indicators_data,
                'trendlines': [],  # 추세선 데이터 (나중에 추가 예정)
                'last_updated': symbol_data[-1].get('last_updated', dates[-1]) if symbol_data else None
            }
            
        except Exception as e:
            logger.error(f"신호 데이터 조회 실패: {symbol}, {e}")
            return {
                'symbol': symbol,
                'dates': [],
                'signals': {},
                'indicators': {},
                'error': f'데이터 조회 실패: {e}'
            }
    
    def get_available_symbols(self) -> List[str]:
        """사용 가능한 종목 목록 조회"""
        try:
            symbols = []
            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    if filename.startswith("signals_") and filename.endswith(".json"):
                        # 파일명에서 심볼 추출
                        symbol = filename.replace("signals_", "").replace(".json", "")
                        # 특수 문자 복원
                        if symbol == "KS11":
                            symbol = "^KS11"
                        elif symbol == "IXIC":
                            symbol = "^IXIC"
                        elif symbol == "GSPC":
                            symbol = "^GSPC"
                        elif symbol == "DJI":
                            symbol = "^DJI"
                        elif symbol == "FTSE":
                            symbol = "^FTSE"
                        elif symbol == "GDAXI":
                            symbol = "^GDAXI"
                        elif symbol == "FCHI":
                            symbol = "^FCHI"
                        elif symbol == "N225":
                            symbol = "^N225"
                        elif symbol == "HSI":
                            symbol = "^HSI"
                        elif symbol == "AXJO":
                            symbol = "^AXJO"
                        elif symbol == "GCF":
                            symbol = "GC=F"
                        elif symbol == "SIF":
                            symbol = "SI=F"
                        elif symbol == "CLF":
                            symbol = "CL=F"
                        elif symbol == "NGF":
                            symbol = "NG=F"
                        elif symbol == "ZCF":
                            symbol = "ZC=F"
                        elif symbol == "ZSF":
                            symbol = "ZS=F"
                        elif symbol == "USDKRWX":
                            symbol = "USDKRW=X"
                        elif symbol == "EURUSDX":
                            symbol = "EURUSD=X"
                        elif symbol == "GBPUSDX":
                            symbol = "GBPUSD=X"
                        elif symbol == "USDJPYX":
                            symbol = "USDJPY=X"
                        elif symbol == "005930KS":
                            symbol = "005930.KS"
                        symbols.append(symbol)
            return sorted(symbols)
        except Exception as e:
            logger.error(f"종목 목록 조회 실패: {e}")
            return []
    
    def get_data_info(self) -> Dict[str, Any]:
        """데이터 정보 조회"""
        try:
            symbols = self.get_available_symbols()
            total_records = 0
            last_updated = None
            
            for symbol in symbols:
                symbol_data = self._load_symbol_data(symbol)
                total_records += len(symbol_data)
                if symbol_data:
                    symbol_last_updated = max([item.get('last_updated', '') for item in symbol_data])
                    if not last_updated or symbol_last_updated > last_updated:
                        last_updated = symbol_last_updated
            
            return {
                'total_records': total_records,
                'symbols': symbols,
                'last_updated': last_updated
            }
        except Exception as e:
            logger.error(f"데이터 정보 조회 실패: {e}")
            return {'total_records': 0, 'symbols': [], 'last_updated': None}