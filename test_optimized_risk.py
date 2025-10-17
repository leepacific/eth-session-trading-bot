#!/usr/bin/env python3
"""
최적화된 리스크 설정 테스트
- 청산 확률 5%
- 레버리지 125배 유지
- 최소 주문 금액 20 USDT 고려
"""

from eth_session_strategy import ETHSessionStrategy
import pandas as pd

def test_new_risk_settings():
    """새로운 리스크 설정으로 백테스팅"""
    print("🧪 최적화된 리스크 설정 테스트")
    print("=" * 80)
    
    # 100 USDT 계좌로 테스트 (동적 리스크 조정 적용)
    strategy = ETHSessionStrategy(initial_balance=100)
    
    print("📊 새로운 리스크 설정:")
    print(f"   계좌 잔고: ${strategy.risk_manager.params.account_balance}")
    print(f"   거래당 리스크: {strategy.risk_manager.params.max_account_risk_per_trade*100}%")
    print(f"   청산 확률: {strategy.risk_manager.params.liquidation_probability*100}%")
    print(f"   최대 레버리지: {strategy.risk_manager.params.max_leverage}x")
    print(f"   최소 주문 금액: ${strategy.risk_manager.params.min_notional_usdt}")
    
    # 백테스팅 실행
    print(f"\n🚀 백테스팅 실행 중...")
    trades = strategy.run_full_backtest()
    
    if trades and len(trades) > 0:
        # 결과 분석
        df = pd.DataFrame(trades)
        
        total_return = df['pnl'].sum()
        win_rate = (df['pnl'] > 0).mean()
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if (df['pnl'] > 0).any() else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if (df['pnl'] < 0).any() else 0
        
        print(f"\n📈 백테스팅 결과:")
        print(f"   총 거래 수: {len(trades)}")
        print(f"   승률: {win_rate*100:.1f}%")
        print(f"   총 수익률: {total_return:.2f}%")
        print(f"   평균 승리: {avg_win:.2f}%")
        print(f"   평균 손실: {avg_loss:.2f}%")
        
        # 리스크 분석
        max_drawdown = df['pnl'].cumsum().expanding().max() - df['pnl'].cumsum()
        max_dd = max_drawdown.max()
        
        print(f"\n🛡️ 리스크 분석:")
        print(f"   최대 드로우다운: {max_dd:.2f}%")
        print(f"   샤프 비율: {(total_return / df['pnl'].std()) if df['pnl'].std() > 0 else 0:.2f}")
        
        # 실제 거래 시뮬레이션
        print(f"\n💰 100 USDT 계좌 시뮬레이션:")
        final_balance = 100 * (1 + total_return/100)
        print(f"   시작 잔고: $100")
        print(f"   최종 잔고: ${final_balance:.2f}")
        print(f"   절대 수익: ${final_balance - 100:.2f}")
        
        # 1000 USDT 달성 시 예상 성과
        if final_balance > 100:
            growth_rate = (final_balance / 100) - 1
            projected_1000 = 1000 * (1 + growth_rate)
            print(f"\n🚀 1000 USDT 달성 시 예상 성과:")
            print(f"   동일 수익률 적용: ${projected_1000:.2f}")
            print(f"   예상 절대 수익: ${projected_1000 - 1000:.2f}")
            print(f"   → 그때는 청산확률 7%, 거래당 리스크 5%로 전환")
        
        return {
            'trades': len(trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_dd,
            'final_balance': final_balance
        }
    else:
        print("❌ 거래가 생성되지 않았습니다")
        return None

if __name__ == "__main__":
    result = test_new_risk_settings()
    
    if result:
        print(f"\n🎯 결론:")
        if result['win_rate'] > 0.6 and result['total_return'] > 10:
            print("✅ 새로운 리스크 설정이 우수한 성과를 보입니다!")
            print("   실제 거래에 적용할 준비가 되었습니다.")
        elif result['win_rate'] > 0.5:
            print("⚠️ 괜찮은 성과이지만 추가 최적화를 고려해보세요.")
        else:
            print("❌ 성과가 부족합니다. 파라미터 재조정이 필요합니다.")