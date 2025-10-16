"""
고급 리스크 관리 시스템
- 청산 확률 7% 유지
- 포지션당 계좌의 5% 투입
- 최대 레버리지 활용
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
import math

@dataclass
class RiskParameters:
    """리스크 파라미터"""
    account_balance: float = 100000  # 계좌 잔고
    max_account_risk_per_trade: float = 0.05  # 거래당 최대 계좌 리스크 (5%)
    liquidation_probability: float = 0.07  # 청산 확률 (7%)
    max_leverage: float = 125  # 바이낸스 최대 레버리지
    maintenance_margin_rate: float = 0.004  # 유지증거금률 (0.4%)
    
class AdvancedRiskManager:
    def __init__(self, risk_params: RiskParameters = None):
        """고급 리스크 관리자 초기화"""
        self.params = risk_params or RiskParameters()
        
        print("🛡️ 고급 리스크 관리 시스템 초기화")
        print(f"   계좌 잔고: ${self.params.account_balance:,.2f}")
        print(f"   포지션당 리스크: {self.params.max_account_risk_per_trade*100}%")
        print(f"   목표 청산 확률: {self.params.liquidation_probability*100}%")
        print(f"   최대 레버리지: {self.params.max_leverage}x")
    
    def calculate_optimal_position(self, entry_price: float, stop_price: float, 
                                 atr: float, direction: str) -> dict:
        """최적 포지션 계산"""
        
        # 1. 기본 리스크 계산
        price_risk = abs(entry_price - stop_price) / entry_price
        max_risk_amount = self.params.account_balance * self.params.max_account_risk_per_trade
        
        # 2. ATR 기반 변동성 조정
        volatility_multiplier = self._calculate_volatility_multiplier(atr, entry_price)
        
        # 3. 청산 거리 계산 (7% 확률 기준)
        liquidation_distance = self._calculate_liquidation_distance(atr, entry_price)
        
        # 4. 최적 레버리지 계산
        optimal_leverage = self._calculate_optimal_leverage(
            price_risk, liquidation_distance, volatility_multiplier
        )
        
        # 5. 포지션 사이즈 계산
        position_value = max_risk_amount / price_risk
        position_size = position_value / entry_price
        
        # 6. 실제 증거금 계산
        required_margin = position_value / optimal_leverage
        
        # 7. 청산 가격 계산
        liquidation_price = self._calculate_liquidation_price(
            entry_price, optimal_leverage, direction
        )
        
        return {
            'position_size': position_size,
            'leverage': optimal_leverage,
            'position_value': position_value,
            'required_margin': required_margin,
            'liquidation_price': liquidation_price,
            'liquidation_distance': liquidation_distance,
            'risk_amount': max_risk_amount,
            'volatility_multiplier': volatility_multiplier,
            'margin_utilization': required_margin / self.params.account_balance
        }
    
    def _calculate_volatility_multiplier(self, atr: float, price: float) -> float:
        """변동성 기반 승수 계산"""
        atr_percentage = atr / price
        
        # ATR이 높을수록 포지션 크기 감소
        if atr_percentage > 0.03:  # 3% 이상
            return 0.7
        elif atr_percentage > 0.02:  # 2-3%
            return 0.85
        elif atr_percentage > 0.01:  # 1-2%
            return 1.0
        else:  # 1% 미만
            return 1.2
    
    def _calculate_liquidation_distance(self, atr: float, price: float) -> float:
        """청산 거리 계산 (7% 확률 기준)"""
        # 정규분포 가정하에 7% 확률은 약 1.48 표준편차
        z_score = 1.48
        
        # ATR을 일일 변동성으로 변환 (15분봉 -> 일일)
        daily_volatility = atr * math.sqrt(96)  # 96 = 24시간 / 15분
        
        # 청산까지의 거리 (가격 대비 비율)
        liquidation_distance = z_score * (daily_volatility / price)
        
        return min(liquidation_distance, 0.15)  # 최대 15%로 제한
    
    def _calculate_optimal_leverage(self, price_risk: float, liquidation_distance: float, 
                                  volatility_multiplier: float) -> float:
        """최적 레버리지 계산"""
        
        # 기본 레버리지: 청산 거리 기반
        base_leverage = 0.8 / liquidation_distance  # 안전 마진 20%
        
        # 변동성 조정
        adjusted_leverage = base_leverage * volatility_multiplier
        
        # 최대 레버리지 제한
        optimal_leverage = min(adjusted_leverage, self.params.max_leverage)
        
        # 최소 레버리지 보장
        optimal_leverage = max(optimal_leverage, 2.0)
        
        return round(optimal_leverage, 1)
    
    def _calculate_liquidation_price(self, entry_price: float, leverage: float, 
                                   direction: str) -> float:
        """청산 가격 계산"""
        maintenance_margin_rate = self.params.maintenance_margin_rate
        
        if direction == 'long':
            # 롱 포지션 청산 가격
            liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)
        else:
            # 숏 포지션 청산 가격
            liquidation_price = entry_price * (1 + (1/leverage) - maintenance_margin_rate)
        
        return liquidation_price
    
    def validate_position(self, position_info: dict, entry_price: float, 
                         stop_price: float, direction: str) -> dict:
        """포지션 검증 및 조정"""
        
        liquidation_price = position_info['liquidation_price']
        
        # 스톱로스가 청산가보다 안전한지 확인
        if direction == 'long':
            if stop_price <= liquidation_price:
                print(f"⚠️ 스톱로스({stop_price:.2f})가 청산가({liquidation_price:.2f})보다 위험함")
                # 레버리지 조정
                safe_leverage = self._calculate_safe_leverage(entry_price, stop_price, direction)
                position_info['leverage'] = safe_leverage
                position_info['liquidation_price'] = self._calculate_liquidation_price(
                    entry_price, safe_leverage, direction
                )
        else:
            if stop_price >= liquidation_price:
                print(f"⚠️ 스톱로스({stop_price:.2f})가 청산가({liquidation_price:.2f})보다 위험함")
                safe_leverage = self._calculate_safe_leverage(entry_price, stop_price, direction)
                position_info['leverage'] = safe_leverage
                position_info['liquidation_price'] = self._calculate_liquidation_price(
                    entry_price, safe_leverage, direction
                )
        
        return position_info
    
    def _calculate_safe_leverage(self, entry_price: float, stop_price: float, 
                               direction: str) -> float:
        """안전한 레버리지 계산"""
        price_diff_ratio = abs(entry_price - stop_price) / entry_price
        
        # 스톱로스 거리의 80%를 안전 마진으로 사용
        safe_leverage = 0.8 / price_diff_ratio
        
        return min(max(safe_leverage, 2.0), self.params.max_leverage)
    
    def calculate_pnl(self, position_info: dict, entry_price: float, 
                     exit_price: float, direction: str) -> dict:
        """PnL 계산 (레버리지 적용)"""
        
        position_size = position_info['position_size']
        leverage = position_info['leverage']
        
        # 가격 변화율
        if direction == 'long':
            price_change_pct = (exit_price - entry_price) / entry_price
        else:
            price_change_pct = (entry_price - exit_price) / entry_price
        
        # 레버리지 적용된 수익률
        leveraged_return_pct = price_change_pct * leverage
        
        # 실제 PnL (증거금 기준)
        margin_used = position_info['required_margin']
        pnl_amount = margin_used * leveraged_return_pct
        
        # ROE (Return on Equity)
        roe_pct = leveraged_return_pct * 100
        
        return {
            'pnl_amount': pnl_amount,
            'roe_pct': roe_pct,
            'margin_used': margin_used,
            'position_value': position_size * entry_price,
            'leverage_used': leverage
        }
    
    def update_account_balance(self, pnl_amount: float):
        """계좌 잔고 업데이트"""
        self.params.account_balance += pnl_amount
        
        # 최소 잔고 보호
        if self.params.account_balance < 1000:
            print("⚠️ 계좌 잔고가 최소 한도에 도달했습니다.")
            self.params.account_balance = max(self.params.account_balance, 1000)
    
    def get_account_status(self) -> dict:
        """계좌 상태 조회"""
        return {
            'balance': self.params.account_balance,
            'max_position_risk': self.params.account_balance * self.params.max_account_risk_per_trade,
            'available_margin': self.params.account_balance * 0.8  # 80%만 사용
        }

def main():
    """테스트 실행"""
    risk_manager = AdvancedRiskManager()
    
    # 테스트 케이스
    entry_price = 2500.0
    stop_price = 2480.0
    atr = 25.0
    direction = 'long'
    
    print(f"\n📊 테스트 케이스:")
    print(f"   진입가: ${entry_price}")
    print(f"   스톱가: ${stop_price}")
    print(f"   ATR: ${atr}")
    print(f"   방향: {direction}")
    
    # 포지션 계산
    position = risk_manager.calculate_optimal_position(entry_price, stop_price, atr, direction)
    position = risk_manager.validate_position(position, entry_price, stop_price, direction)
    
    print(f"\n🎯 최적 포지션:")
    print(f"   포지션 크기: {position['position_size']:.4f} ETH")
    print(f"   레버리지: {position['leverage']}x")
    print(f"   포지션 가치: ${position['position_value']:,.2f}")
    print(f"   필요 증거금: ${position['required_margin']:,.2f}")
    print(f"   청산 가격: ${position['liquidation_price']:.2f}")
    print(f"   증거금 사용률: {position['margin_utilization']*100:.1f}%")

if __name__ == "__main__":
    main()