#!/usr/bin/env python3
"""
켈리 포지션 사이징 시스템 구현
- 계좌 잔고 1000USDT 미만 시 20USDT 최소 주문 로직
- 계좌 잔고 1000USDT 이상 시 켈리 0.5 계산
- 최소 주문금액 20USDT 보장
- DD 10%마다 베팅 20% 축소 로직
"""

import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from dd_scaling_system import DDScalingConfig, DDScalingSystem

from ..core.performance_evaluator import PerformanceEvaluator, PerformanceMetrics


@dataclass
class KellyParameters:
    """켈리 포지션 사이징 파라미터"""

    min_balance_threshold: float = 1000.0  # 켈리 적용 최소 잔고
    min_order_amount: float = 20.0  # 최소 주문 금액 (USDT)
    kelly_fraction: float = 0.5  # 켈리 분수 (보수적)
    max_position_risk: float = 0.05  # 최대 포지션 리스크 (5%)
    dd_scaling_threshold: float = 0.10  # DD 스케일링 임계값 (10%)
    dd_scaling_factor: float = 0.20  # DD당 베팅 축소 비율 (20%)
    max_dd_scaling: float = 0.50  # 최대 DD 스케일링 (50%)


@dataclass
class PositionInfo:
    """포지션 정보"""

    balance: float
    kelly_fraction: float
    raw_position_size: float
    adjusted_position_size: float
    risk_amount: float
    max_loss: float
    dd_scaling_applied: float
    min_order_applied: bool
    confidence_level: float


@dataclass
class TradeStatistics:
    """거래 통계"""

    win_rate: float
    avg_win: float
    avg_loss: float
    total_trades: int
    profit_factor: float
    expectancy: float
    kelly_optimal: float


class KellyPositionSizer:
    def __init__(self, kelly_params: KellyParameters = None):
        """켈리 포지션 사이징 시스템 초기화"""
        self.params = kelly_params or KellyParameters()
        self.performance_evaluator = PerformanceEvaluator()

        # DD 스케일링 시스템 통합
        dd_config = DDScalingConfig(
            dd_threshold=self.params.dd_scaling_threshold,
            scaling_factor=self.params.dd_scaling_factor,
            max_scaling=self.params.max_dd_scaling,
        )
        self.dd_system = DDScalingSystem(dd_config)

        print("💰 켈리 포지션 사이징 시스템 초기화")
        print(f"   최소 잔고 임계값: ${self.params.min_balance_threshold:,.0f}")
        print(f"   최소 주문 금액: ${self.params.min_order_amount}")
        print(f"   켈리 분수: {self.params.kelly_fraction}")
        print(f"   DD 스케일링: {self.params.dd_scaling_threshold*100}%마다 {self.params.dd_scaling_factor*100}% 축소")

    def calculate_trade_statistics(self, trades: List[Dict]) -> TradeStatistics:
        """거래 통계 계산"""
        if not trades:
            return TradeStatistics(0.5, 1.0, 1.0, 0, 1.0, 0.0, 0.0)

        # 거래 결과 분석
        returns = [trade.get("pnl_pct", 0) for trade in trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]

        # 기본 통계
        total_trades = len(returns)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0.5
        avg_win = np.mean(wins) if wins else 0.01
        avg_loss = abs(np.mean(losses)) if losses else 0.01

        # 수익 팩터
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0.01
        profit_factor = total_wins / total_losses if total_losses > 0 else 1.0

        # 기댓값
        expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss

        # 켈리 최적값 계산
        kelly_optimal = self._calculate_kelly_optimal(win_rate, avg_win, avg_loss)

        print(f"📊 거래 통계:")
        print(f"   총 거래 수: {total_trades}")
        print(f"   승률: {win_rate*100:.1f}%")
        print(f"   평균 승리: {avg_win*100:.2f}%")
        print(f"   평균 손실: {avg_loss*100:.2f}%")
        print(f"   수익 팩터: {profit_factor:.2f}")
        print(f"   기댓값: {expectancy*100:.2f}%")
        print(f"   켈리 최적값: {kelly_optimal:.3f}")

        return TradeStatistics(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_trades=total_trades,
            profit_factor=profit_factor,
            expectancy=expectancy,
            kelly_optimal=kelly_optimal,
        )

    def _calculate_kelly_optimal(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """켈리 최적 분수 계산"""
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        # 켈리 공식: f* = (bp - q) / b
        # 여기서 b = avg_win/avg_loss (승률 대비), p = win_rate, q = 1-win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate

        kelly_optimal = (b * p - q) / b

        # 음수이면 0으로 설정 (베팅하지 않음)
        kelly_optimal = max(0.0, kelly_optimal)

        # 실용적 한계 적용 (25% 이하)
        kelly_optimal = min(kelly_optimal, 0.25)

        return kelly_optimal

    def calculate_position_size(self, balance: float, trade_stats: TradeStatistics, current_dd: float = 0.0) -> PositionInfo:
        """포지션 사이즈 계산"""
        print(f"\n💼 포지션 사이징 계산:")
        print(f"   계좌 잔고: ${balance:,.2f}")
        print(f"   현재 DD: {current_dd*100:.1f}%")

        # 1. 기본 켈리 분수 결정
        if balance < self.params.min_balance_threshold:
            # 소액 계좌: 최소 주문 금액 사용
            kelly_fraction = 0.0  # 켈리 적용 안함
            raw_position_size = self.params.min_order_amount
            min_order_applied = True

            print(f"   🔒 소액 계좌 모드: 최소 주문 ${self.params.min_order_amount}")
        else:
            # 대형 계좌: 켈리 0.5 적용
            kelly_optimal = trade_stats.kelly_optimal
            kelly_fraction = min(kelly_optimal, self.params.kelly_fraction)

            # 켈리가 너무 작으면 최소값 적용
            if kelly_fraction < 0.01:
                kelly_fraction = 0.02  # 최소 2%

            raw_position_size = balance * kelly_fraction
            min_order_applied = False

            print(f"   📈 켈리 모드: 최적={kelly_optimal:.3f}, 적용={kelly_fraction:.3f}")

        # 2. DD 연동 감쇠 적용
        dd_scaling_applied = self._calculate_dd_scaling(current_dd)
        adjusted_position_size = raw_position_size * (1 - dd_scaling_applied)

        if dd_scaling_applied > 0:
            print(f"   📉 DD 스케일링: -{dd_scaling_applied*100:.1f}% 적용")

        # 3. 최소 주문 금액 보장
        if adjusted_position_size < self.params.min_order_amount:
            adjusted_position_size = self.params.min_order_amount
            min_order_applied = True
            print(f"   ⬆️ 최소 주문 금액으로 조정: ${self.params.min_order_amount}")

        # 4. 최대 리스크 제한
        max_risk_amount = balance * self.params.max_position_risk
        if adjusted_position_size > max_risk_amount:
            adjusted_position_size = max_risk_amount
            print(f"   ⬇️ 최대 리스크로 제한: ${max_risk_amount:.2f} (5%)")

        # 5. 리스크 계산
        risk_amount = adjusted_position_size
        max_loss = risk_amount  # 최악의 경우 전액 손실 가정

        # 6. 신뢰도 계산
        confidence_level = self._calculate_confidence_level(trade_stats, dd_scaling_applied)

        print(f"   💰 최종 포지션: ${adjusted_position_size:.2f}")
        print(f"   🎯 리스크 금액: ${risk_amount:.2f} ({risk_amount/balance*100:.1f}%)")
        print(f"   📊 신뢰도: {confidence_level*100:.1f}%")

        return PositionInfo(
            balance=balance,
            kelly_fraction=kelly_fraction,
            raw_position_size=raw_position_size,
            adjusted_position_size=adjusted_position_size,
            risk_amount=risk_amount,
            max_loss=max_loss,
            dd_scaling_applied=dd_scaling_applied,
            min_order_applied=min_order_applied,
            confidence_level=confidence_level,
        )

    def _calculate_dd_scaling(self, current_dd: float) -> float:
        """DD 연동 감쇠 계산"""
        if current_dd <= 0:
            return 0.0

        # DD 10%마다 20% 축소
        dd_levels = current_dd / self.params.dd_scaling_threshold
        scaling = dd_levels * self.params.dd_scaling_factor

        # 최대 스케일링 제한
        scaling = min(scaling, self.params.max_dd_scaling)

        return scaling

    def _calculate_confidence_level(self, trade_stats: TradeStatistics, dd_scaling: float) -> float:
        """신뢰도 계산"""
        base_confidence = 0.5

        # 거래 수가 많을수록 신뢰도 증가
        trade_confidence = min(trade_stats.total_trades / 200, 1.0) * 0.3

        # 수익 팩터가 높을수록 신뢰도 증가
        pf_confidence = min((trade_stats.profit_factor - 1.0) / 2.0, 1.0) * 0.2

        # DD 스케일링이 적용되면 신뢰도 감소
        dd_penalty = dd_scaling * 0.3

        confidence = base_confidence + trade_confidence + pf_confidence - dd_penalty
        return max(0.1, min(1.0, confidence))

    def update_dd_scaling(self, current_balance: float, peak_balance: float) -> float:
        """현재 DD 계산"""
        if peak_balance <= 0:
            return 0.0

        current_dd = max(0.0, (peak_balance - current_balance) / peak_balance)
        return current_dd

    def validate_position(self, position_info: PositionInfo) -> bool:
        """포지션 검증"""
        print(f"\n✅ 포지션 검증:")

        # 1. 최소 주문 금액 확인
        min_order_ok = position_info.adjusted_position_size >= self.params.min_order_amount
        print(
            f"   최소 주문 금액: {'✅' if min_order_ok else '❌'} ${position_info.adjusted_position_size:.2f} >= ${self.params.min_order_amount}"
        )

        # 2. 최대 리스크 확인
        risk_ratio = position_info.risk_amount / position_info.balance
        max_risk_ok = risk_ratio <= self.params.max_position_risk
        print(f"   최대 리스크: {'✅' if max_risk_ok else '❌'} {risk_ratio*100:.1f}% <= {self.params.max_position_risk*100}%")

        # 3. 켈리 분수 확인
        kelly_ok = position_info.kelly_fraction <= 1.0
        print(f"   켈리 분수: {'✅' if kelly_ok else '❌'} {position_info.kelly_fraction:.3f} <= 1.0")

        # 4. 신뢰도 확인
        confidence_ok = position_info.confidence_level >= 0.3
        print(f"   신뢰도: {'✅' if confidence_ok else '❌'} {position_info.confidence_level*100:.1f}% >= 30%")

        all_ok = min_order_ok and max_risk_ok and kelly_ok and confidence_ok
        print(f"   전체 검증: {'✅ 통과' if all_ok else '❌ 실패'}")

        return all_ok

    def analyze_kelly_efficiency(self, balance_range: List[float], sample_trades: List[Dict]) -> pd.DataFrame:
        """켈리 효율성 분석"""
        print(f"\n📈 켈리 효율성 분석 ({len(balance_range)}개 잔고 수준)")

        trade_stats = self.calculate_trade_statistics(sample_trades)
        results = []

        for balance in balance_range:
            # 다양한 DD 수준에서 테스트
            for dd_level in [0.0, 0.05, 0.10, 0.20, 0.30]:
                position_info = self.calculate_position_size(balance, trade_stats, dd_level)

                results.append(
                    {
                        "balance": balance,
                        "dd_level": dd_level,
                        "kelly_fraction": position_info.kelly_fraction,
                        "position_size": position_info.adjusted_position_size,
                        "risk_ratio": position_info.risk_amount / balance,
                        "dd_scaling": position_info.dd_scaling_applied,
                        "min_order_applied": position_info.min_order_applied,
                        "confidence": position_info.confidence_level,
                    }
                )

        return pd.DataFrame(results)

    def get_position_recommendation(self, balance: float, trades: List[Dict], current_dd: float = 0.0) -> Dict:
        """포지션 추천 (DD 시스템 통합)"""
        # DD 시스템 업데이트
        self.dd_system.update_balance(balance)

        # 기본 켈리 계산
        trade_stats = self.calculate_trade_statistics(trades)
        position_info = self.calculate_position_size(balance, trade_stats, current_dd)

        # DD 시스템의 동적 스케일링 적용
        dd_recommendation = self.dd_system.get_dynamic_scaling_recommendation(position_info.adjusted_position_size)

        # 최종 포지션 크기 (DD 시스템 권장사항 적용)
        final_position_size = dd_recommendation["recommended_position"]

        # 검증
        position_info.adjusted_position_size = final_position_size
        is_valid = self.validate_position(position_info)

        return {
            "position_size": final_position_size,
            "risk_amount": position_info.risk_amount,
            "kelly_fraction": position_info.kelly_fraction,
            "confidence": position_info.confidence_level,
            "valid": is_valid,
            "recommendation": self._generate_recommendation(position_info, trade_stats),
            "dd_scaling": dd_recommendation["scaling_applied"],
            "dd_action": dd_recommendation["action"],
            "dd_confidence": dd_recommendation["confidence"],
        }

    def _generate_recommendation(self, position_info: PositionInfo, trade_stats: TradeStatistics) -> str:
        """추천 메시지 생성"""
        if position_info.balance < self.params.min_balance_threshold:
            return f"소액 계좌: 최소 주문 ${self.params.min_order_amount} 사용 권장"

        if trade_stats.profit_factor < 1.5:
            return "수익 팩터가 낮음: 전략 개선 후 포지션 증가 권장"

        if position_info.dd_scaling_applied > 0.3:
            return "높은 DD: 포지션 축소 상태, 회복 후 정상화 권장"

        if position_info.confidence_level < 0.5:
            return "낮은 신뢰도: 보수적 포지션 사이징 권장"

        return "정상 범위: 켈리 기반 포지션 사이징 적용"


def main():
    """테스트 실행"""
    print("🚀 켈리 포지션 사이징 시스템 테스트")
    print("=" * 80)

    # 켈리 포지션 사이저 초기화
    kelly_sizer = KellyPositionSizer()

    # 샘플 거래 데이터 생성 (백테스트 결과 시뮬레이션)
    np.random.seed(42)
    sample_trades = []

    for i in range(100):
        # 60% 승률, 평균 승리 3%, 평균 손실 1.5% (2:1 RR)
        if np.random.random() < 0.6:
            pnl_pct = np.random.normal(0.03, 0.01)  # 승리
        else:
            pnl_pct = np.random.normal(-0.015, 0.005)  # 손실

        sample_trades.append({"pnl_pct": pnl_pct, "trade_id": i + 1})

    # 다양한 계좌 크기와 DD 수준에서 테스트
    test_scenarios = [
        (500, 0.0),  # 소액 계좌, DD 없음
        (1000, 0.0),  # 임계값, DD 없음
        (5000, 0.0),  # 중형 계좌, DD 없음
        (10000, 0.05),  # 대형 계좌, 5% DD
        (25000, 0.15),  # 대형 계좌, 15% DD
        (50000, 0.25),  # 대형 계좌, 25% DD
    ]

    print(f"\n📊 시나리오별 포지션 사이징 테스트:")
    print("=" * 80)

    for balance, dd_level in test_scenarios:
        print(f"\n💰 시나리오: 잔고 ${balance:,}, DD {dd_level*100:.0f}%")
        print("-" * 50)

        recommendation = kelly_sizer.get_position_recommendation(balance, sample_trades, dd_level)

        print(f"   추천 포지션: ${recommendation['position_size']:.2f}")
        print(f"   리스크 금액: ${recommendation['risk_amount']:.2f}")
        print(f"   켈리 분수: {recommendation['kelly_fraction']:.3f}")
        print(f"   신뢰도: {recommendation['confidence']*100:.1f}%")
        print(f"   검증 결과: {'✅ 통과' if recommendation['valid'] else '❌ 실패'}")
        print(f"   추천사항: {recommendation['recommendation']}")

    # 효율성 분석
    balance_range = [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
    efficiency_df = kelly_sizer.analyze_kelly_efficiency(balance_range, sample_trades)

    print(f"\n📈 켈리 효율성 분석 요약:")
    print("=" * 80)

    # DD 0% 기준으로 요약
    summary = efficiency_df[efficiency_df["dd_level"] == 0.0].copy()
    summary["balance_str"] = summary["balance"].apply(lambda x: f"${x:,}")
    summary["risk_pct"] = (summary["risk_ratio"] * 100).round(1)
    summary["kelly_pct"] = (summary["kelly_fraction"] * 100).round(1)
    summary["confidence_pct"] = (summary["confidence"] * 100).round(0)

    display_cols = ["balance_str", "kelly_pct", "position_size", "risk_pct", "confidence_pct", "min_order_applied"]
    display_summary = summary[display_cols].copy()
    display_summary.columns = ["잔고", "켈리%", "포지션($)", "리스크%", "신뢰도%", "최소주문"]

    print(display_summary.to_string(index=False))

    print(f"\n🎯 핵심 특징:")
    print(f"   • 1000 USDT 미만: 최소 주문 20 USDT 고정")
    print(f"   • 1000 USDT 이상: 켈리 0.5 기반 동적 사이징")
    print(f"   • DD 10%마다 베팅 20% 축소")
    print(f"   • 최대 리스크 5% 제한")
    print(f"   • 신뢰도 기반 검증")


if __name__ == "__main__":
    main()
