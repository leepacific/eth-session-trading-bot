#!/usr/bin/env python3
"""
DD 연동 감쇠 시스템 구현
- DD 10%마다 베팅 20% 축소 로직
- 동적 포지션 사이징 조정 시스템
- 리스크 관리 통합
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")


@dataclass
class DDScalingConfig:
    """DD 스케일링 설정"""

    dd_threshold: float = 0.10  # DD 임계값 (10%)
    scaling_factor: float = 0.20  # 축소 비율 (20%)
    max_scaling: float = 0.80  # 최대 축소 (80%)
    recovery_threshold: float = 0.05  # 회복 임계값 (5%)
    min_position_ratio: float = 0.10  # 최소 포지션 비율 (10%)
    lookback_days: int = 30  # 회복 판단 기간 (30일)


@dataclass
class DDState:
    """DD 상태"""

    current_balance: float
    peak_balance: float
    current_dd: float
    max_dd: float
    dd_duration_days: int
    scaling_applied: float
    last_update: datetime
    recovery_started: bool


@dataclass
class ScalingResult:
    """스케일링 결과"""

    original_position: float
    scaled_position: float
    scaling_factor: float
    dd_level: float
    reason: str
    confidence: float


class DDScalingSystem:
    def __init__(self, config: DDScalingConfig = None):
        """DD 연동 감쇠 시스템 초기화"""
        self.config = config or DDScalingConfig()
        self.dd_history: List[DDState] = []
        self.current_state: Optional[DDState] = None

        print("📉 DD 연동 감쇠 시스템 초기화")
        print(f"   DD 임계값: {self.config.dd_threshold*100}%")
        print(f"   축소 비율: {self.config.scaling_factor*100}%")
        print(f"   최대 축소: {self.config.max_scaling*100}%")
        print(f"   회복 임계값: {self.config.recovery_threshold*100}%")

    def update_balance(self, new_balance: float, timestamp: datetime = None) -> DDState:
        """잔고 업데이트 및 DD 상태 계산"""
        if timestamp is None:
            timestamp = datetime.now()

        # 첫 번째 업데이트
        if self.current_state is None:
            self.current_state = DDState(
                current_balance=new_balance,
                peak_balance=new_balance,
                current_dd=0.0,
                max_dd=0.0,
                dd_duration_days=0,
                scaling_applied=0.0,
                last_update=timestamp,
                recovery_started=False,
            )
            print(f"💰 초기 잔고 설정: ${new_balance:,.2f}")
            return self.current_state

        # 새로운 최고점 갱신
        if new_balance > self.current_state.peak_balance:
            self.current_state.peak_balance = new_balance
            self.current_state.recovery_started = True
            print(f"🎉 신고점 달성: ${new_balance:,.2f}")

        # 현재 DD 계산
        current_dd = (self.current_state.peak_balance - new_balance) / self.current_state.peak_balance
        current_dd = max(0.0, current_dd)

        # 최대 DD 갱신
        max_dd = max(self.current_state.max_dd, current_dd)

        # DD 지속 기간 계산
        if current_dd > 0.01:  # 1% 이상 DD
            if self.current_state.current_dd <= 0.01:
                # DD 시작
                dd_start_date = timestamp
            else:
                # DD 지속
                dd_start_date = self.current_state.last_update

            dd_duration = (timestamp - dd_start_date).days
        else:
            dd_duration = 0

        # 스케일링 계산
        scaling_applied = self._calculate_scaling(current_dd)

        # 상태 업데이트
        self.current_state = DDState(
            current_balance=new_balance,
            peak_balance=self.current_state.peak_balance,
            current_dd=current_dd,
            max_dd=max_dd,
            dd_duration_days=dd_duration,
            scaling_applied=scaling_applied,
            last_update=timestamp,
            recovery_started=self.current_state.recovery_started,
        )

        # 히스토리 저장
        self.dd_history.append(self.current_state)

        # 상태 출력
        if current_dd > 0.01:
            print(f"📉 DD 상태: {current_dd*100:.1f}% (최대: {max_dd*100:.1f}%)")
            print(f"   스케일링: -{scaling_applied*100:.1f}%")
            print(f"   지속 기간: {dd_duration}일")

        return self.current_state

    def _calculate_scaling(self, current_dd: float) -> float:
        """DD 기반 스케일링 계산"""
        if current_dd <= 0:
            return 0.0

        # DD 10%마다 20% 축소
        dd_levels = current_dd / self.config.dd_threshold
        scaling = dd_levels * self.config.scaling_factor

        # 최대 축소 제한
        scaling = min(scaling, self.config.max_scaling)

        return scaling

    def apply_scaling(self, original_position: float, reason: str = "DD 기반 축소") -> ScalingResult:
        """포지션에 스케일링 적용"""
        if self.current_state is None:
            return ScalingResult(
                original_position=original_position,
                scaled_position=original_position,
                scaling_factor=0.0,
                dd_level=0.0,
                reason="DD 상태 없음",
                confidence=1.0,
            )

        scaling_factor = self.current_state.scaling_applied
        scaled_position = original_position * (1 - scaling_factor)

        # 최소 포지션 보장
        min_position = original_position * self.config.min_position_ratio
        scaled_position = max(scaled_position, min_position)

        # 실제 적용된 스케일링 계산
        actual_scaling = 1 - (scaled_position / original_position)

        # 신뢰도 계산
        confidence = self._calculate_confidence()

        print(f"⚖️ 포지션 스케일링 적용:")
        print(f"   원본 포지션: ${original_position:.2f}")
        print(f"   스케일링 후: ${scaled_position:.2f}")
        print(f"   축소 비율: {actual_scaling*100:.1f}%")
        print(f"   신뢰도: {confidence*100:.1f}%")

        return ScalingResult(
            original_position=original_position,
            scaled_position=scaled_position,
            scaling_factor=actual_scaling,
            dd_level=self.current_state.current_dd,
            reason=reason,
            confidence=confidence,
        )

    def _calculate_confidence(self) -> float:
        """스케일링 신뢰도 계산"""
        if self.current_state is None:
            return 1.0

        base_confidence = 0.8

        # DD가 클수록 신뢰도 감소
        dd_penalty = min(self.current_state.current_dd * 2, 0.5)

        # DD 지속 기간이 길수록 신뢰도 감소
        duration_penalty = min(self.current_state.dd_duration_days / 60, 0.3)

        # 회복 시작되면 신뢰도 증가
        recovery_bonus = 0.2 if self.current_state.recovery_started else 0.0

        confidence = base_confidence - dd_penalty - duration_penalty + recovery_bonus
        return max(0.1, min(1.0, confidence))

    def check_recovery_signal(self) -> bool:
        """회복 신호 확인"""
        if self.current_state is None or len(self.dd_history) < 5:
            return False

        # 최근 DD가 회복 임계값 이하로 감소
        recent_dd_improvement = self.current_state.current_dd < self.config.recovery_threshold

        # 최근 며칠간 지속적 개선
        recent_states = self.dd_history[-5:]
        dd_trend_improving = all(
            recent_states[i].current_dd >= recent_states[i + 1].current_dd for i in range(len(recent_states) - 1)
        )

        recovery_signal = recent_dd_improvement and dd_trend_improving

        if recovery_signal:
            print("🌱 회복 신호 감지: DD 축소 및 개선 추세")

        return recovery_signal

    def get_dynamic_scaling_recommendation(self, base_position: float) -> Dict:
        """동적 스케일링 추천"""
        if self.current_state is None:
            return {
                "recommended_position": base_position,
                "scaling_applied": 0.0,
                "reason": "DD 상태 없음",
                "confidence": 1.0,
                "action": "maintain",
            }

        # 현재 스케일링 적용
        scaling_result = self.apply_scaling(base_position)

        # 회복 신호 확인
        recovery_signal = self.check_recovery_signal()

        # 액션 결정
        if self.current_state.current_dd > 0.20:  # 20% 이상 DD
            action = "reduce_aggressive"
            reason = "심각한 DD: 공격적 축소"
        elif self.current_state.current_dd > 0.10:  # 10% 이상 DD
            action = "reduce_moderate"
            reason = "중간 DD: 적당한 축소"
        elif recovery_signal:
            action = "gradual_increase"
            reason = "회복 신호: 점진적 증가"
        elif self.current_state.current_dd < 0.05:  # 5% 미만 DD
            action = "maintain"
            reason = "정상 범위: 유지"
        else:
            action = "monitor"
            reason = "관찰 필요: 신중 대기"

        return {
            "recommended_position": scaling_result.scaled_position,
            "scaling_applied": scaling_result.scaling_factor,
            "reason": reason,
            "confidence": scaling_result.confidence,
            "action": action,
            "dd_level": self.current_state.current_dd,
            "recovery_signal": recovery_signal,
        }

    def analyze_dd_patterns(self) -> Dict:
        """DD 패턴 분석"""
        if len(self.dd_history) < 10:
            return {"error": "insufficient_data"}

        dd_values = [state.current_dd for state in self.dd_history]

        # 기본 통계
        max_dd = max(dd_values)
        avg_dd = np.mean(dd_values)
        dd_volatility = np.std(dd_values)

        # DD 지속 기간 분석
        dd_durations = []
        current_duration = 0

        for dd in dd_values:
            if dd > 0.01:  # 1% 이상 DD
                current_duration += 1
            else:
                if current_duration > 0:
                    dd_durations.append(current_duration)
                current_duration = 0

        avg_dd_duration = np.mean(dd_durations) if dd_durations else 0
        max_dd_duration = max(dd_durations) if dd_durations else 0

        # 회복 패턴 분석
        recovery_count = sum(1 for state in self.dd_history if state.recovery_started)
        recovery_rate = recovery_count / len(self.dd_history)

        print(f"📊 DD 패턴 분석:")
        print(f"   최대 DD: {max_dd*100:.1f}%")
        print(f"   평균 DD: {avg_dd*100:.1f}%")
        print(f"   DD 변동성: {dd_volatility*100:.1f}%")
        print(f"   평균 DD 지속: {avg_dd_duration:.1f}일")
        print(f"   최대 DD 지속: {max_dd_duration}일")
        print(f"   회복 비율: {recovery_rate*100:.1f}%")

        return {
            "max_dd": max_dd,
            "avg_dd": avg_dd,
            "dd_volatility": dd_volatility,
            "avg_dd_duration": avg_dd_duration,
            "max_dd_duration": max_dd_duration,
            "recovery_rate": recovery_rate,
            "total_observations": len(self.dd_history),
        }

    def export_dd_history(self) -> pd.DataFrame:
        """DD 히스토리 내보내기"""
        if not self.dd_history:
            return pd.DataFrame()

        data = []
        for state in self.dd_history:
            data.append(
                {
                    "timestamp": state.last_update,
                    "balance": state.current_balance,
                    "peak_balance": state.peak_balance,
                    "current_dd": state.current_dd,
                    "max_dd": state.max_dd,
                    "dd_duration_days": state.dd_duration_days,
                    "scaling_applied": state.scaling_applied,
                    "recovery_started": state.recovery_started,
                }
            )

        return pd.DataFrame(data)

    def reset_state(self, initial_balance: float):
        """상태 초기화"""
        self.current_state = None
        self.dd_history = []
        self.update_balance(initial_balance)
        print(f"🔄 DD 상태 초기화: ${initial_balance:,.2f}")


def main():
    """테스트 실행"""
    print("🚀 DD 연동 감쇠 시스템 테스트")
    print("=" * 80)

    # DD 스케일링 시스템 초기화
    dd_system = DDScalingSystem()

    # 시뮬레이션 데이터 생성 (계좌 잔고 변화)
    np.random.seed(42)
    initial_balance = 10000
    current_balance = initial_balance
    base_position = 500  # 기본 포지션 크기

    print(f"\n📈 시뮬레이션 시작:")
    print(f"   초기 잔고: ${initial_balance:,}")
    print(f"   기본 포지션: ${base_position}")

    # 60일간 시뮬레이션
    simulation_results = []

    for day in range(60):
        # 랜덤 수익률 생성 (변동성 있는 시장)
        if day < 20:
            # 초기 20일: 상승 추세
            daily_return = np.random.normal(0.005, 0.02)  # 0.5% ± 2%
        elif day < 40:
            # 중간 20일: 하락 추세 (DD 발생)
            daily_return = np.random.normal(-0.01, 0.03)  # -1% ± 3%
        else:
            # 마지막 20일: 회복 추세
            daily_return = np.random.normal(0.008, 0.025)  # 0.8% ± 2.5%

        # 잔고 업데이트
        current_balance *= 1 + daily_return
        current_balance = max(current_balance, initial_balance * 0.5)  # 최대 50% 손실 제한

        # DD 상태 업데이트
        timestamp = datetime.now() + timedelta(days=day)
        dd_state = dd_system.update_balance(current_balance, timestamp)

        # 동적 스케일링 추천
        recommendation = dd_system.get_dynamic_scaling_recommendation(base_position)

        # 결과 저장
        simulation_results.append(
            {
                "day": day + 1,
                "balance": current_balance,
                "dd": dd_state.current_dd,
                "scaling": dd_state.scaling_applied,
                "recommended_position": recommendation["recommended_position"],
                "action": recommendation["action"],
                "confidence": recommendation["confidence"],
            }
        )

        # 주요 이벤트 출력
        if day % 10 == 0 or dd_state.current_dd > 0.1:
            print(f"\n📅 Day {day+1}:")
            print(f"   잔고: ${current_balance:,.2f}")
            print(f"   DD: {dd_state.current_dd*100:.1f}%")
            print(f"   추천 포지션: ${recommendation['recommended_position']:.2f}")
            print(f"   액션: {recommendation['action']}")

    # 시뮬레이션 결과 분석
    results_df = pd.DataFrame(simulation_results)

    print(f"\n📊 시뮬레이션 결과 요약:")
    print("=" * 80)
    print(f"   최종 잔고: ${current_balance:,.2f}")
    print(f"   총 수익률: {(current_balance/initial_balance-1)*100:.1f}%")
    print(f"   최대 DD: {results_df['dd'].max()*100:.1f}%")
    print(f"   평균 스케일링: {results_df['scaling'].mean()*100:.1f}%")
    print(f"   최대 스케일링: {results_df['scaling'].max()*100:.1f}%")

    # DD 패턴 분석
    dd_analysis = dd_system.analyze_dd_patterns()

    # 액션 분포
    action_counts = results_df["action"].value_counts()
    print(f"\n🎯 액션 분포:")
    for action, count in action_counts.items():
        print(f"   {action}: {count}회 ({count/len(results_df)*100:.1f}%)")

    # 히스토리 내보내기
    dd_history_df = dd_system.export_dd_history()

    print(f"\n💾 DD 히스토리: {len(dd_history_df)}개 기록")
    print(f"   최대 DD 지속: {dd_analysis.get('max_dd_duration', 0)}일")
    print(f"   회복 비율: {dd_analysis.get('recovery_rate', 0)*100:.1f}%")

    print(f"\n🎯 핵심 특징:")
    print(f"   • DD 10%마다 포지션 20% 축소")
    print(f"   • 최대 80% 축소 제한")
    print(f"   • 회복 신호 자동 감지")
    print(f"   • 동적 신뢰도 계산")
    print(f"   • 최소 포지션 10% 보장")


if __name__ == "__main__":
    main()
