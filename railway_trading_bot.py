#!/usr/bin/env python3
"""
Railway 통합 트레이딩 봇 - 고급 레버리지 최적화 포함
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

# Binance API
from binance.client import Client
from binance.exceptions import BinanceAPIException

# 프로젝트 모듈
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdvancedLeverageOptimizer:
    """고급 레버리지 최적화 시스템"""
    
    def __init__(self, account_balance: float):
        self.account_balance = account_balance
        self.min_order_amount = 20.0  # USDT
        self.kelly_fraction = 0.5
        self.liquidation_probability = 0.05  # 5%
        self.max_leverage = 125
        self.maintenance_margin_rate = 0.004  # 0.4%
        
        # 계좌 크기에 따른 동적 조정
        if account_balance >= 1000:
            self.max_account_risk = 0.05  # 5%
            self.liquidation_probability = 0.05  # 5% 유지
            logger.info(f"💰 대형 계좌 모드: 잔고 ${account_balance:.2f}, 리스크 5%, 청산확률 5%")
        else:
            # 소액 계좌는 더 보수적
            self.max_account_risk = 0.10  # 10% (최소 주문 금액 때문)
            self.liquidation_probability = 0.05  # 5%
            logger.info(f"🔒 소액 계좌 모드: 잔고 ${account_balance:.2f}, 리스크 10%, 청산확률 5%")
    
    def calculate_optimal_position(self, entry_price: float, stop_price: float, 
                                 atr: float, direction: str, win_rate: float = 0.45) -> Dict:
        """최적 포지션 계산"""
        
        # 1. 기본 리스크 계산
        price_risk = abs(entry_price - stop_price) / entry_price
        max_risk_amount = self.account_balance * self.max_account_risk
        
        # 2. 켈리 기반 포지션 사이징 (1000 USDT 이상)
        if self.account_balance >= 1000:
            # 켈리 분수 계산 (간소화)
            avg_win = price_risk * 2.5  # Target R 2.5 가정
            avg_loss = price_risk
            
            if win_rate > 0 and avg_loss > 0:
                b = avg_win / avg_loss
                p = win_rate
                kelly_optimal = (b * p - (1 - p)) / b
                kelly_optimal = max(0, min(kelly_optimal, self.kelly_fraction))
            else:
                kelly_optimal = 0.02  # 기본 2%
            
            position_value = self.account_balance * kelly_optimal
            logger.info(f"📊 켈리 계산: 최적={kelly_optimal:.3f}, 포지션=${position_value:.2f}")
        else:
            # 소액 계좌: 최소 주문 금액 사용
            position_value = self.min_order_amount
            logger.info(f"💰 최소 주문 모드: ${position_value}")
        
        # 3. 최소 주문 금액 보장
        if position_value < self.min_order_amount:
            position_value = self.min_order_amount
            logger.info(f"⬆️ 최소 주문 금액으로 조정: ${self.min_order_amount}")
        
        # 4. 최대 리스크 제한
        max_position_by_risk = max_risk_amount / price_risk
        if position_value > max_position_by_risk:
            position_value = max_position_by_risk
            logger.info(f"⬇️ 최대 리스크로 제한: ${max_position_by_risk:.2f}")
        
        # 5. 포지션 사이즈 계산
        position_size = position_value / entry_price
        
        # 6. 최적 레버리지 계산 (청산 확률 5% 기준)
        optimal_leverage = self._calculate_optimal_leverage(atr, entry_price, price_risk)
        
        # 7. 필요 증거금 계산
        required_margin = position_value / optimal_leverage
        
        # 8. 청산 가격 계산
        liquidation_price = self._calculate_liquidation_price(entry_price, optimal_leverage, direction)
        
        # 9. 안전성 검증
        is_safe = self._validate_safety(stop_price, liquidation_price, direction)
        
        if not is_safe:
            # 안전하지 않으면 레버리지 조정
            safe_leverage = self._calculate_safe_leverage(entry_price, stop_price, direction)
            optimal_leverage = min(safe_leverage, optimal_leverage)
            required_margin = position_value / optimal_leverage
            liquidation_price = self._calculate_liquidation_price(entry_price, optimal_leverage, direction)
            logger.warning(f"⚠️ 안전성을 위해 레버리지 조정: {optimal_leverage}x")
        
        return {
            'position_size': round(position_size, 6),
            'position_value': round(position_value, 2),
            'leverage': round(optimal_leverage, 1),
            'required_margin': round(required_margin, 2),
            'liquidation_price': round(liquidation_price, 2),
            'risk_amount': round(position_value * price_risk, 2),
            'margin_utilization': round(required_margin / self.account_balance, 4),
            'is_safe': is_safe
        }
    
    def _calculate_optimal_leverage(self, atr: float, price: float, price_risk: float) -> float:
        """최적 레버리지 계산 (청산 확률 5% 기준)"""
        
        # ATR 기반 일일 변동성 추정
        atr_percentage = atr / price
        daily_volatility = atr_percentage * np.sqrt(96)  # 15분 -> 일일
        
        # 5% 청산 확률을 위한 Z-score (1.645)
        z_score = 1.645
        liquidation_distance = z_score * daily_volatility
        
        # 안전 마진 20% 적용
        safe_leverage = 0.8 / liquidation_distance
        
        # 변동성 조정
        if atr_percentage > 0.03:  # 고변동성
            safe_leverage *= 0.7
        elif atr_percentage < 0.01:  # 저변동성
            safe_leverage *= 1.2
        
        # 레버리지 제한
        optimal_leverage = max(2.0, min(safe_leverage, self.max_leverage))
        
        return optimal_leverage
    
    def _calculate_liquidation_price(self, entry_price: float, leverage: float, direction: str) -> float:
        """청산 가격 계산"""
        if direction == 'long':
            liquidation_price = entry_price * (1 - (1/leverage) + self.maintenance_margin_rate)
        else:
            liquidation_price = entry_price * (1 + (1/leverage) - self.maintenance_margin_rate)
        
        return liquidation_price
    
    def _validate_safety(self, stop_price: float, liquidation_price: float, direction: str) -> bool:
        """안전성 검증"""
        if direction == 'long':
            return stop_price > liquidation_price
        else:
            return stop_price < liquidation_price
    
    def _calculate_safe_leverage(self, entry_price: float, stop_price: float, direction: str) -> float:
        """안전한 레버리지 계산"""
        price_diff_ratio = abs(entry_price - stop_price) / entry_price
        safe_leverage = 0.8 / price_diff_ratio  # 80% 안전 마진
        return max(2.0, min(safe_leverage, self.max_leverage))

class RailwayTradingBot:
    """Railway 통합 트레이딩 봇"""
    
    def __init__(self):
        # Binance API 설정
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Binance API 키가 설정되지 않았습니다!")
        
        # Binance 클라이언트 초기화
        self.client = Client(self.api_key, self.secret_key, testnet=self.testnet)
        
        # 거래 설정
        self.symbol = 'ETHUSDT'
        self.is_active = False
        self.current_parameters = self.load_parameters()
        
        # 계좌 정보 및 레버리지 최적화 시스템 초기화
        self.account_balance = self.get_account_balance()
        self.leverage_optimizer = AdvancedLeverageOptimizer(self.account_balance)
        
        logger.info(f"🚀 Railway Trading Bot 초기화 완료")
        logger.info(f"   계좌 잔고: ${self.account_balance:.2f}")
        logger.info(f"   테스트넷: {self.testnet}")
    
    def load_parameters(self) -> Dict:
        """파라미터 로드"""
        try:
            if os.path.exists('config/current_parameters.json'):
                with open('config/current_parameters.json', 'r') as f:
                    data = json.load(f)
                    return data.get('parameters', {})
        except Exception as e:
            logger.error(f"파라미터 로드 실패: {e}")
        
        # 기본 파라미터
        return {
            'target_r': 2.536,
            'stop_atr_mult': 0.0734,
            'swing_len': 5.49,
            'rr_percentile': 0.168,
            'atr_len': 13.84,
            'session_strength': 1.397,
            'volume_filter': 1.521
        }
    
    def get_account_balance(self) -> float:
        """계좌 잔고 조회"""
        try:
            account_info = self.client.futures_account()
            balance = float(account_info['totalWalletBalance'])
            logger.info(f"💰 현재 계좌 잔고: ${balance:.2f}")
            return balance
        except Exception as e:
            logger.error(f"계좌 정보 조회 실패: {e}")
            return 100.0  # 기본값
    
    def get_market_data(self) -> Optional[pd.DataFrame]:
        """시장 데이터 수집"""
        try:
            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval='15m',
                limit=200
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # ATR 계산
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            df['atr'] = true_range.rolling(14).mean()
            
            return df[['time', 'open', 'high', 'low', 'close', 'volume', 'atr']].copy()
            
        except Exception as e:
            logger.error(f"시장 데이터 수집 실패: {e}")
            return None
    
    def analyze_market(self, df: pd.DataFrame) -> Optional[Dict]:
        """시장 분석 및 신호 생성"""
        try:
            if len(df) < 50:
                return None
            
            current_bar = df.iloc[-1]
            
            # 기본 조건 확인
            if pd.isna(current_bar['atr']) or current_bar['atr'] <= 0:
                return None
            
            # 간단한 트렌드 확인 (EMA 기반)
            df['ema_20'] = df['close'].ewm(span=20).mean()
            current_ema = df['ema_20'].iloc[-1]
            
            # 진입 조건 (매우 간소화)
            if np.random.random() < 0.05:  # 5% 확률로 신호 생성 (테스트용)
                
                direction = 'long' if current_bar['close'] > current_ema else 'short'
                entry_price = current_bar['close']
                atr = current_bar['atr']
                
                # 스톱과 타겟 계산
                stop_atr_mult = self.current_parameters.get('stop_atr_mult', 0.08)
                target_r = self.current_parameters.get('target_r', 2.5)
                
                if direction == 'long':
                    stop_price = entry_price - (atr * stop_atr_mult)
                    target_price = entry_price + (atr * stop_atr_mult * target_r)
                else:
                    stop_price = entry_price + (atr * stop_atr_mult)
                    target_price = entry_price - (atr * stop_atr_mult * target_r)
                
                return {
                    'direction': direction,
                    'entry_price': entry_price,
                    'stop_price': stop_price,
                    'target_price': target_price,
                    'atr': atr,
                    'timestamp': current_bar['time']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"시장 분석 실패: {e}")
            return None
    
    async def execute_trade(self, signal: Dict) -> bool:
        """거래 실행 (고급 레버리지 최적화 적용)"""
        try:
            logger.info(f"🎯 거래 신호: {signal['direction']} @ {signal['entry_price']:.2f}")
            
            # 1. 최적 포지션 계산
            position_info = self.leverage_optimizer.calculate_optimal_position(
                entry_price=signal['entry_price'],
                stop_price=signal['stop_price'],
                atr=signal['atr'],
                direction=signal['direction'],
                win_rate=0.45  # 백테스트 기반 추정값
            )
            
            if not position_info['is_safe']:
                logger.warning("⚠️ 안전하지 않은 포지션으로 거래 취소")
                return False
            
            logger.info(f"💰 포지션 정보:")
            logger.info(f"   크기: {position_info['position_size']} ETH")
            logger.info(f"   가치: ${position_info['position_value']}")
            logger.info(f"   레버리지: {position_info['leverage']}x")
            logger.info(f"   증거금: ${position_info['required_margin']}")
            logger.info(f"   청산가: ${position_info['liquidation_price']}")
            
            # 2. 레버리지 설정
            try:
                self.client.futures_change_leverage(
                    symbol=self.symbol,
                    leverage=int(position_info['leverage'])
                )
                logger.info(f"✅ 레버리지 설정: {position_info['leverage']}x")
            except Exception as e:
                logger.error(f"레버리지 설정 실패: {e}")
                return False
            
            # 3. 시장가 주문 실행
            side = 'BUY' if signal['direction'] == 'long' else 'SELL'
            quantity = position_info['position_size']
            
            try:
                order = self.client.futures_create_order(
                    symbol=self.symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
                
                logger.info(f"✅ 주문 실행: {side} {quantity} ETH")
                logger.info(f"   주문 ID: {order['orderId']}")
                
                # 4. 스톱로스 주문
                stop_side = 'SELL' if signal['direction'] == 'long' else 'BUY'
                
                try:
                    stop_order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side=stop_side,
                        type='STOP_MARKET',
                        quantity=quantity,
                        stopPrice=signal['stop_price']
                    )
                    
                    logger.info(f"✅ 스톱로스 설정: {signal['stop_price']:.2f}")
                    
                except Exception as e:
                    logger.error(f"스톱로스 설정 실패: {e}")
                
                return True
                
            except BinanceAPIException as e:
                logger.error(f"주문 실행 실패: {e}")
                return False
            
        except Exception as e:
            logger.error(f"거래 실행 중 오류: {e}")
            return False
    
    async def monitor_positions(self):
        """포지션 모니터링"""
        try:
            positions = self.client.futures_position_information(symbol=self.symbol)
            
            for position in positions:
                if float(position['positionAmt']) != 0:
                    logger.info(f"📊 활성 포지션:")
                    logger.info(f"   수량: {position['positionAmt']}")
                    logger.info(f"   진입가: {position['entryPrice']}")
                    logger.info(f"   미실현 PnL: {position['unRealizedProfit']}")
                    
        except Exception as e:
            logger.error(f"포지션 모니터링 실패: {e}")
    
    async def run_trading_loop(self):
        """메인 거래 루프"""
        logger.info("🚀 거래 루프 시작")
        
        while self.is_active:
            try:
                # 1. 시장 데이터 수집
                df = self.get_market_data()
                if df is None:
                    await asyncio.sleep(60)
                    continue
                
                # 2. 시장 분석
                signal = self.analyze_market(df)
                
                # 3. 신호가 있으면 거래 실행
                if signal:
                    await self.execute_trade(signal)
                
                # 4. 포지션 모니터링
                await self.monitor_positions()
                
                # 5. 15분 대기
                await asyncio.sleep(900)  # 15분
                
            except Exception as e:
                logger.error(f"거래 루프 오류: {e}")
                await asyncio.sleep(60)
    
    def start_trading(self):
        """거래 시작"""
        self.is_active = True
        logger.info("🚀 거래 시작")
    
    def stop_trading(self):
        """거래 중지"""
        self.is_active = False
        logger.info("⏹️ 거래 중지")
    
    def update_parameters(self, new_parameters: Dict):
        """파라미터 업데이트"""
        self.current_parameters.update(new_parameters)
        logger.info(f"🔄 파라미터 업데이트: {len(new_parameters)}개")
    
    def get_status(self) -> Dict:
        """상태 조회"""
        return {
            'is_active': self.is_active,
            'account_balance': self.account_balance,
            'current_parameters': self.current_parameters,
            'symbol': self.symbol,
            'testnet': self.testnet
        }

# 글로벌 봇 인스턴스
trading_bot = None

def get_trading_bot():
    """트레이딩 봇 인스턴스 가져오기"""
    global trading_bot
    if trading_bot is None:
        trading_bot = RailwayTradingBot()
    return trading_bot

async def main():
    """테스트 실행"""
    bot = get_trading_bot()
    bot.start_trading()
    await bot.run_trading_loop()

if __name__ == "__main__":
    asyncio.run(main())