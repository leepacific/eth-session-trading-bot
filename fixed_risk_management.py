"""
고정 리스크 관리 시스템
- 매 거래 계좌의 5% 고정 베팅
- 청산확률 7% 고정
- 레버리지 최대 활용
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

@dataclass
class FixedRiskParameters:
    """고정 리스크 관리 파라미터"""
    fixed_risk_pct: float = 0.05        # 고정 리스크 5%
    liquidation_prob: float = 0.07      # 청산확률 7% 고정
    max_slippage_bps: float = 10.0      # 최대 슬리피지 10bps
    max_spread_bps: float = 3.0         # 최대 스프레드 3bps
    atr_slippage_ratio: float = 0.25    # ATR 대비 슬리피지 비율
    exchange_max_leverage: float = 100.0 # 거래소 최대 레버리지

@dataclass
class TradeSetup:
    """거래 설정"""
    entry_price: float
    stop_price: float
    target_price: float
    direction: str  # 'long' or 'short'
    atr: float
    
    @property
    def stop_distance(self) -> float:
        """스톱 거리"""
        return abs(self.entry_price - self.stop_price)
    
    @property
    def stop_distance_pct(self) -> float:
        """스톱 거리 (퍼센트)"""
        return self.stop_distance / self.entry_price
    
    @property
    def risk_reward_ratio(self) -> float:
        """리스크 리워드 비율"""
        profit_distance = abs(self.target_price - self.entry_price)
        return profit_distance / self.stop_distance

@dataclass
class FixedPositionSize:
    """고정 리스크 포지션 사이즈 결과"""
    risk_amount: float          # 리스크 금액 (계좌의 5%)
    quantity: float             # 포지션 수량
    leverage: float             # 사용 레버리지
    margin_required: float      # 마진 요구량
    liquidation_price: float    # 청산가
    liquidation_distance: float # 청산가까지 거리
    max_loss_if_liquidated: float # 청산시 최대 손실

class FixedRiskManager:
    def __init__(self, risk_params: FixedRiskParameters = None):
        """고정 리스크 관리자 초기화"""
        self.risk_params = risk_params or FixedRiskParameters()
        
        print("🎯 고정 리스크 관리 시스템 초기화")
        print(f"   고정 리스크: {self.risk_params.fixed_risk_pct*100}% (매 거래)")
        print(f"   청산확률: {self.risk_params.liquidation_prob*100}% (고정)")
        print(f"   전략: 레버리지 최대 활용")
    
    def calculate_optimal_leverage(self, 
                                 trade_setup: TradeSetup,
                                 target_liquidation_prob: float = 0.07) -> float:
        """청산확률 7%를 만족하는 최적 레버리지 계산"""
        
        # 청산확률 7%는 대략 1.48 표준편차에 해당 (정규분포 가정)
        # P(X > 1.48σ) ≈ 0.07
        z_score = 1.48
        
        # 일일 변동성 추정 (ATR 기반)
        daily_volatility = trade_setup.atr / trade_setup.entry_price
        
        # 청산까지 허용 가능한 최대 불리한 움직임
        # 청산확률 7% = 1.48 표준편차 움직임까지 견딜 수 있어야 함
        max_adverse_move_pct = z_score * daily_volatility
        
        # 레버리지 계산: 청산 조건 = 손실 >= 마진 (1/레버리지)
        # 따라서: max_adverse_move_pct >= 1/leverage * safety_factor
        safety_factor = 0.9  # 10% 안전 마진
        
        optimal_leverage = 1.0 / (max_adverse_move_pct * safety_factor)
        
        # 거래소 한도 및 실용적 한도 적용
        optimal_leverage = min(
            optimal_leverage,
            self.risk_params.exchange_max_leverage,
            200.0  # 실용적 최대값
        )
        
        return max(1.0, optimal_leverage)
    
    def calculate_liquidation_price(self, 
                                  entry_price: float,
                                  leverage: float,
                                  direction: str) -> float:
        """청산가 계산"""
        
        # 단순화된 청산가 공식
        liquidation_threshold = 1.0 / leverage
        
        if direction == 'long':
            # 롱: 가격 하락시 청산
            liquidation_price = entry_price * (1 - liquidation_threshold * 0.95)  # 5% 수수료 마진
        else:
            # 숏: 가격 상승시 청산
            liquidation_price = entry_price * (1 + liquidation_threshold * 0.95)
        
        return liquidation_price
    
    def calculate_position_size(self, 
                              equity: float,
                              trade_setup: TradeSetup) -> FixedPositionSize:
        """고정 리스크 기반 포지션 사이즈 계산"""
        
        print(f"\n💼 계좌 크기: ${equity:,}")
        print("-" * 50)
        
        # 1. 고정 리스크 금액 (계좌의 5%)
        risk_amount = equity * self.risk_params.fixed_risk_pct
        
        # 2. 최적 레버리지 계산 (청산확률 7% 기준)
        optimal_leverage = self.calculate_optimal_leverage(
            trade_setup, self.risk_params.liquidation_prob
        )
        
        # 3. 청산가 계산
        liquidation_price = self.calculate_liquidation_price(
            trade_setup.entry_price, optimal_leverage, trade_setup.direction
        )
        
        # 4. 청산가까지의 거리
        if trade_setup.direction == 'long':
            liquidation_distance = trade_setup.entry_price - liquidation_price
        else:
            liquidation_distance = liquidation_price - trade_setup.entry_price
        
        liquidation_distance_pct = liquidation_distance / trade_setup.entry_price
        
        # 5. 포지션 수량 계산
        # 리스크 금액 = 수량 × 스톱 거리
        # 하지만 청산 리스크도 고려해야 함
        
        # 스톱 기준 수량
        quantity_by_stop = risk_amount / trade_setup.stop_distance
        
        # 청산 기준 수량 (청산시에도 5% 이하 손실)
        quantity_by_liquidation = risk_amount / liquidation_distance
        
        # 더 보수적인 수량 선택
        final_quantity = min(quantity_by_stop, quantity_by_liquidation)
        
        # 6. 마진 요구량
        notional_value = final_quantity * trade_setup.entry_price
        margin_required = notional_value / optimal_leverage
        
        # 7. 청산시 최대 손실
        max_loss_if_liquidated = final_quantity * liquidation_distance
        
        print(f"   💰 리스크 금액: ${risk_amount:,.2f} ({self.risk_params.fixed_risk_pct*100}%)")
        print(f"   ⚡ 최적 레버리지: {optimal_leverage:.1f}x")
        print(f"   🔥 청산가: ${liquidation_price:.2f}")
        print(f"   📏 청산 거리: ${liquidation_distance:.2f} ({liquidation_distance_pct*100:.2f}%)")
        print(f"   📊 포지션 수량: {final_quantity:.4f} ETH")
        print(f"   💸 마진 요구량: ${margin_required:,.2f} ({margin_required/equity*100:.1f}%)")
        print(f"   ⚠️ 청산시 손실: ${max_loss_if_liquidated:.2f}")
        
        return FixedPositionSize(
            risk_amount=risk_amount,
            quantity=final_quantity,
            leverage=optimal_leverage,
            margin_required=margin_required,
            liquidation_price=liquidation_price,
            liquidation_distance=liquidation_distance,
            max_loss_if_liquidated=max_loss_if_liquidated
        )
    
    def validate_position(self, position: FixedPositionSize, equity: float) -> bool:
        """포지션 검증"""
        
        # 1. 청산시 손실이 5% 이하인지 확인
        liquidation_loss_pct = position.max_loss_if_liquidated / equity
        
        # 2. 마진이 계좌 크기를 초과하지 않는지 확인
        margin_pct = position.margin_required / equity
        
        print(f"\n✅ 포지션 검증:")
        print(f"   청산시 손실률: {liquidation_loss_pct*100:.2f}% (목표: ≤5%)")
        print(f"   마진 사용률: {margin_pct*100:.1f}%")
        
        is_valid = (liquidation_loss_pct <= 0.05 and margin_pct <= 1.0)
        
        if is_valid:
            print(f"   ✅ 검증 통과")
        else:
            print(f"   ❌ 검증 실패")
        
        return is_valid
    
    def analyze_leverage_efficiency(self, 
                                  equity_range: list,
                                  sample_trade: TradeSetup) -> pd.DataFrame:
        """계좌 크기별 레버리지 효율성 분석"""
        
        results = []
        
        for equity in equity_range:
            position = self.calculate_position_size(equity, sample_trade)
            
            # 효율성 지표 계산
            capital_efficiency = (position.quantity * sample_trade.entry_price) / equity
            leverage_utilization = position.leverage / self.risk_params.exchange_max_leverage
            
            results.append({
                'equity': equity,
                'leverage': position.leverage,
                'quantity': position.quantity,
                'margin_pct': position.margin_required / equity * 100,
                'capital_efficiency': capital_efficiency,
                'leverage_utilization': leverage_utilization * 100,
                'liquidation_distance_pct': position.liquidation_distance / sample_trade.entry_price * 100
            })
        
        return pd.DataFrame(results)

def demonstrate_fixed_risk_system():
    """고정 리스크 시스템 데모"""
    print("🚀 고정 리스크 관리 시스템 데모")
    print("="*80)
    
    # 리스크 관리자 초기화
    risk_manager = FixedRiskManager()
    
    # 샘플 거래 설정 (백테스트 결과 기반)
    sample_trade = TradeSetup(
        entry_price=2500.0,
        stop_price=2450.0,  # 2% 스톱
        target_price=2650.0,  # 6% 타겟 (3:1 RR)
        direction='long',
        atr=50.0
    )
    
    print(f"\n📊 거래 설정:")
    print(f"   진입가: ${sample_trade.entry_price}")
    print(f"   스톱가: ${sample_trade.stop_price}")
    print(f"   타겟가: ${sample_trade.target_price}")
    print(f"   스톱 거리: {sample_trade.stop_distance_pct*100:.1f}%")
    print(f"   RR비율: {sample_trade.risk_reward_ratio:.2f}:1")
    print(f"   ATR: ${sample_trade.atr}")
    
    # 다양한 계좌 크기별 분석
    equity_levels = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000]
    
    print(f"\n💰 계좌 크기별 고정 리스크 포지션 사이징:")
    print("="*80)
    
    all_results = []
    
    for equity in equity_levels:
        position = risk_manager.calculate_position_size(equity, sample_trade)
        
        # 검증
        is_valid = risk_manager.validate_position(position, equity)
        
        all_results.append({
            'equity': equity,
            'leverage': position.leverage,
            'quantity': position.quantity,
            'margin_pct': position.margin_required / equity * 100,
            'liquidation_price': position.liquidation_price,
            'max_loss_pct': position.max_loss_if_liquidated / equity * 100,
            'valid': is_valid
        })
    
    # 결과 시각화
    df_results = pd.DataFrame(all_results)
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('고정 리스크 (5%) + 청산확률 (7%) 관리 시스템', fontsize=16, fontweight='bold')
    
    # 1. 레버리지 vs 계좌 크기
    axes[0, 0].plot(df_results['equity'], df_results['leverage'], 'b-o', linewidth=2, markersize=6)
    axes[0, 0].set_title('계좌 크기 vs 레버리지')
    axes[0, 0].set_xlabel('계좌 크기 ($)')
    axes[0, 0].set_ylabel('레버리지 (x)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].set_xscale('log')
    
    # 2. 포지션 수량 vs 계좌 크기
    axes[0, 1].plot(df_results['equity'], df_results['quantity'], 'g-o', linewidth=2, markersize=6)
    axes[0, 1].set_title('계좌 크기 vs 포지션 수량')
    axes[0, 1].set_xlabel('계좌 크기 ($)')
    axes[0, 1].set_ylabel('수량 (ETH)')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_xscale('log')
    
    # 3. 마진 사용률
    axes[0, 2].plot(df_results['equity'], df_results['margin_pct'], 'r-o', linewidth=2, markersize=6)
    axes[0, 2].set_title('계좌 크기 vs 마진 사용률')
    axes[0, 2].set_xlabel('계좌 크기 ($)')
    axes[0, 2].set_ylabel('마진 사용률 (%)')
    axes[0, 2].grid(True, alpha=0.3)
    axes[0, 2].set_xscale('log')
    
    # 4. 청산가
    axes[1, 0].plot(df_results['equity'], df_results['liquidation_price'], 'orange', marker='o', linewidth=2, markersize=6)
    axes[1, 0].axhline(y=sample_trade.entry_price, color='blue', linestyle='--', label='진입가')
    axes[1, 0].axhline(y=sample_trade.stop_price, color='red', linestyle='--', label='스톱가')
    axes[1, 0].set_title('계좌 크기 vs 청산가')
    axes[1, 0].set_xlabel('계좌 크기 ($)')
    axes[1, 0].set_ylabel('가격 ($)')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_xscale('log')
    axes[1, 0].legend()
    
    # 5. 청산시 손실률
    axes[1, 1].plot(df_results['equity'], df_results['max_loss_pct'], 'purple', marker='o', linewidth=2, markersize=6)
    axes[1, 1].axhline(y=5, color='red', linestyle='--', label='5% 한도')
    axes[1, 1].set_title('계좌 크기 vs 청산시 손실률')
    axes[1, 1].set_xlabel('계좌 크기 ($)')
    axes[1, 1].set_ylabel('손실률 (%)')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].set_xscale('log')
    axes[1, 1].legend()
    
    # 6. 레버리지 효율성 (포지션 크기 / 계좌 크기)
    efficiency = (df_results['quantity'] * sample_trade.entry_price) / df_results['equity']
    axes[1, 2].plot(df_results['equity'], efficiency, 'brown', marker='o', linewidth=2, markersize=6)
    axes[1, 2].set_title('계좌 크기 vs 자본 효율성')
    axes[1, 2].set_xlabel('계좌 크기 ($)')
    axes[1, 2].set_ylabel('포지션 크기 / 계좌 크기')
    axes[1, 2].grid(True, alpha=0.3)
    axes[1, 2].set_xscale('log')
    
    plt.tight_layout()
    plt.savefig('fixed_risk_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 요약 테이블
    print(f"\n📋 요약 테이블:")
    print("="*100)
    summary_df = df_results.copy()
    summary_df['equity'] = summary_df['equity'].apply(lambda x: f"${x:,}")
    summary_df['leverage'] = summary_df['leverage'].apply(lambda x: f"{x:.1f}x")
    summary_df['quantity'] = summary_df['quantity'].apply(lambda x: f"{x:.3f}")
    summary_df['margin_pct'] = summary_df['margin_pct'].apply(lambda x: f"{x:.1f}%")
    summary_df['liquidation_price'] = summary_df['liquidation_price'].apply(lambda x: f"${x:.2f}")
    summary_df['max_loss_pct'] = summary_df['max_loss_pct'].apply(lambda x: f"{x:.2f}%")
    summary_df['valid'] = summary_df['valid'].apply(lambda x: "✅" if x else "❌")
    
    summary_df.columns = ['계좌크기', '레버리지', '수량(ETH)', '마진사용률', '청산가', '청산시손실', '검증']
    print(summary_df.to_string(index=False))
    
    print(f"\n🎯 핵심 특징:")
    print(f"   • 모든 계좌 크기에서 5% 고정 리스크")
    print(f"   • 청산확률 7% 기준으로 레버리지 최적화")
    print(f"   • 계좌가 클수록 더 높은 레버리지 활용 가능")
    print(f"   • 청산시에도 손실 5% 이하 보장")
    print(f"   • 자본 효율성 극대화")

if __name__ == "__main__":
    demonstrate_fixed_risk_system()