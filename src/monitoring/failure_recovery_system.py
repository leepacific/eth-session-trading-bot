#!/usr/bin/env python3
"""
장애 대응 시스템 구현
- 비용 2× 스트레스 테스트 재검증
- 장애시 안전축소/청산 플래그 시스템
- 자동 복구 및 알림 시스템
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore')

from realtime_monitoring_system import RealtimeMonitor, TradingState, AlertLevel

class FailureType(Enum):
    """장애 유형"""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    DATA_ERROR = "data_error"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COST_SPIKE = "cost_spike"

class RecoveryAction(Enum):
    """복구 액션"""
    RETRY = "retry"
    REDUCE_POSITION = "reduce_position"
    LIQUIDATE_ALL = "liquidate_all"
    SWITCH_BACKUP = "switch_backup"
    MANUAL_INTERVENTION = "manual_intervention"
    STRESS_TEST = "stress_test"

@dataclass
class FailureRecoveryConfig:
    """장애 복구 설정"""
    # 스트레스 테스트 설정
    cost_multiplier_stress: float = 2.0          # 비용 2배 스트레스 테스트
    performance_threshold: float = 0.8           # 성능 임계값 80%
    
    # 복구 시도 설정
    max_retry_attempts: int = 3                  # 최대 재시도 횟수
    retry_delay_seconds: float = 30.0            # 재시도 간격
    exponential_backoff: bool = True             # 지수 백오프
    
    # 안전 조치 설정
    auto_reduce_threshold: float = 0.05          # 자동 축소 임계값 5%
    emergency_liquidation_threshold: float = 0.10 # 긴급 청산 임계값 10%
    
    # 알림 설정
    notification_channels: List[str] = field(default_factory=lambda: ['console', 'log'])
    escalation_delay_minutes: int = 15           # 에스컬레이션 지연

@dataclass
class FailureEvent:
    """장애 이벤트"""
    timestamp: datetime
    failure_type: FailureType
    description: str
    severity: AlertLevel
    affected_systems: List[str]
    error_data: Dict = field(default_factory=dict)
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class StressTestResult:
    """스트레스 테스트 결과"""
    test_timestamp: datetime
    original_cost: float
    stressed_cost: float
    cost_multiplier: float
    performance_impact: float
    passed: bool
    recommendations: List[str] = field(default_factory=list)

class FailureRecoverySystem:
    def __init__(self, config: FailureRecoveryConfig = None, monitor: RealtimeMonitor = None):
        """장애 대응 시스템 초기화"""
        self.config = config or FailureRecoveryConfig()
        self.monitor = monitor
        
        # 장애 추적
        self.active_failures: Dict[str, FailureEvent] = {}
        self.failure_history: List[FailureEvent] = []
        
        # 복구 상태
        self.recovery_active = False
        self.recovery_thread: Optional[threading.Thread] = None
        
        # 시스템 상태
        self.system_health: Dict[str, float] = {}  # 시스템별 건강도 (0-1)
        self.backup_systems: Dict[str, bool] = {}  # 백업 시스템 가용성
        
        # 스트레스 테스트 결과
        self.stress_test_results: List[StressTestResult] = []
        
        # 콜백 함수들
        self.failure_callbacks: List[Callable[[FailureEvent], None]] = []
        self.recovery_callbacks: List[Callable[[FailureEvent], None]] = []
        
        # 안전 플래그
        self.safe_mode_enabled = False
        self.liquidation_flag = False
        
        print("🛡️ 장애 대응 시스템 초기화")
        print(f"   비용 스트레스 테스트: {self.config.cost_multiplier_stress}x")
        print(f"   최대 재시도: {self.config.max_retry_attempts}회")
        print(f"   자동 축소 임계값: {self.config.auto_reduce_threshold*100}%")
        print(f"   긴급 청산 임계값: {self.config.emergency_liquidation_threshold*100}%")
    
    def start_recovery_system(self):
        """복구 시스템 시작"""
        self.recovery_active = True
        self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self.recovery_thread.start()
        
        print("🚀 장애 복구 시스템 시작")
    
    def stop_recovery_system(self):
        """복구 시스템 중지"""
        self.recovery_active = False
        if self.recovery_thread:
            self.recovery_thread.join(timeout=5.0)
        
        print("⏹️ 장애 복구 시스템 중지")
    
    def report_failure(self, failure_type: FailureType, description: str, 
                      affected_systems: List[str], error_data: Dict = None) -> str:
        """장애 신고"""
        failure_id = f"{failure_type.value}_{int(time.time())}"
        
        # 심각도 결정
        severity = self._determine_severity(failure_type, affected_systems)
        
        failure_event = FailureEvent(
            timestamp=datetime.now(),
            failure_type=failure_type,
            description=description,
            severity=severity,
            affected_systems=affected_systems,
            error_data=error_data or {},
            recovery_attempts=0,
            resolved=False
        )
        
        self.active_failures[failure_id] = failure_event
        self.failure_history.append(failure_event)
        
        # 즉시 대응 조치
        self._immediate_response(failure_event)
        
        # 콜백 호출
        for callback in self.failure_callbacks:
            try:
                callback(failure_event)
            except Exception as e:
                print(f"장애 콜백 오류: {e}")
        
        print(f"🚨 장애 신고: {failure_type.value} - {description}")
        return failure_id
    
    def _determine_severity(self, failure_type: FailureType, affected_systems: List[str]) -> AlertLevel:
        """심각도 결정"""
        # 중요 시스템 영향도 체크
        critical_systems = ['trading_engine', 'risk_manager', 'order_system']
        has_critical_impact = any(sys in affected_systems for sys in critical_systems)
        
        if failure_type in [FailureType.SYSTEM_ERROR] and has_critical_impact:
            return AlertLevel.EMERGENCY
        elif failure_type in [FailureType.API_ERROR, FailureType.COST_SPIKE]:
            return AlertLevel.CRITICAL
        elif failure_type in [FailureType.NETWORK_ERROR, FailureType.DATA_ERROR]:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    def _immediate_response(self, failure_event: FailureEvent):
        """즉시 대응"""
        if failure_event.severity == AlertLevel.EMERGENCY:
            # 긴급 상황: 즉시 안전 모드
            self.enable_safe_mode("긴급 장애 발생")
            
        elif failure_event.severity == AlertLevel.CRITICAL:
            # 중요 상황: 포지션 축소 고려
            if failure_event.failure_type == FailureType.COST_SPIKE:
                self._trigger_cost_stress_test()
            
        # 모니터링 시스템에 알림
        if self.monitor:
            self.monitor._send_alert(
                failure_event.severity,
                f"장애 발생: {failure_event.description}",
                {
                    'failure_type': failure_event.failure_type.value,
                    'affected_systems': failure_event.affected_systems
                }
            )
    
    def _recovery_loop(self):
        """복구 루프"""
        while self.recovery_active:
            try:
                # 활성 장애들에 대한 복구 시도
                for failure_id, failure_event in list(self.active_failures.items()):
                    if not failure_event.resolved:
                        self._attempt_recovery(failure_id, failure_event)
                
                # 시스템 건강도 체크
                self._check_system_health()
                
                # 체크 간격
                time.sleep(30.0)  # 30초마다
                
            except Exception as e:
                print(f"복구 루프 오류: {e}")
                time.sleep(5.0)
    
    def _attempt_recovery(self, failure_id: str, failure_event: FailureEvent):
        """복구 시도"""
        if failure_event.recovery_attempts >= self.config.max_retry_attempts:
            # 최대 시도 횟수 초과
            self._escalate_failure(failure_id, failure_event)
            return
        
        failure_event.recovery_attempts += 1
        
        # 복구 액션 결정
        recovery_action = self._determine_recovery_action(failure_event)
        
        print(f"🔧 복구 시도 {failure_event.recovery_attempts}/{self.config.max_retry_attempts}: {recovery_action.value}")
        
        # 복구 액션 실행
        success = self._execute_recovery_action(recovery_action, failure_event)
        
        if success:
            # 복구 성공
            failure_event.resolved = True
            failure_event.resolution_time = datetime.now()
            del self.active_failures[failure_id]
            
            # 콜백 호출
            for callback in self.recovery_callbacks:
                try:
                    callback(failure_event)
                except Exception as e:
                    print(f"복구 콜백 오류: {e}")
            
            print(f"✅ 복구 성공: {failure_event.description}")
        else:
            # 복구 실패, 다음 시도까지 대기
            delay = self._calculate_retry_delay(failure_event.recovery_attempts)
            print(f"❌ 복구 실패, {delay}초 후 재시도")
    
    def _determine_recovery_action(self, failure_event: FailureEvent) -> RecoveryAction:
        """복구 액션 결정"""
        if failure_event.failure_type == FailureType.COST_SPIKE:
            return RecoveryAction.STRESS_TEST
        elif failure_event.failure_type == FailureType.NETWORK_ERROR:
            return RecoveryAction.RETRY
        elif failure_event.failure_type == FailureType.API_ERROR:
            if failure_event.recovery_attempts < 2:
                return RecoveryAction.RETRY
            else:
                return RecoveryAction.SWITCH_BACKUP
        elif failure_event.failure_type == FailureType.SYSTEM_ERROR:
            if failure_event.severity == AlertLevel.EMERGENCY:
                return RecoveryAction.LIQUIDATE_ALL
            else:
                return RecoveryAction.REDUCE_POSITION
        else:
            return RecoveryAction.RETRY
    
    def _execute_recovery_action(self, action: RecoveryAction, failure_event: FailureEvent) -> bool:
        """복구 액션 실행"""
        try:
            if action == RecoveryAction.RETRY:
                return self._retry_operation(failure_event)
            
            elif action == RecoveryAction.REDUCE_POSITION:
                return self._reduce_positions(failure_event)
            
            elif action == RecoveryAction.LIQUIDATE_ALL:
                return self._emergency_liquidation(failure_event)
            
            elif action == RecoveryAction.SWITCH_BACKUP:
                return self._switch_to_backup(failure_event)
            
            elif action == RecoveryAction.STRESS_TEST:
                return self._execute_stress_test(failure_event)
            
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return self._request_manual_intervention(failure_event)
            
            else:
                return False
                
        except Exception as e:
            print(f"복구 액션 실행 오류: {e}")
            return False
    
    def _retry_operation(self, failure_event: FailureEvent) -> bool:
        """작업 재시도"""
        # 시뮬레이션: 70% 확률로 성공
        success = np.random.random() > 0.3
        
        if success:
            print(f"🔄 재시도 성공: {failure_event.description}")
        else:
            print(f"🔄 재시도 실패: {failure_event.description}")
        
        return success
    
    def _reduce_positions(self, failure_event: FailureEvent) -> bool:
        """포지션 축소"""
        reduction_ratio = 0.5  # 50% 축소
        
        print(f"📉 포지션 {reduction_ratio*100}% 축소 실행")
        
        # 모니터링 시스템에 알림
        if self.monitor:
            self.monitor._send_alert(
                AlertLevel.WARNING,
                f"장애 대응: 포지션 {reduction_ratio*100}% 축소",
                {'reason': failure_event.description}
            )
        
        return True  # 시뮬레이션에서는 항상 성공
    
    def _emergency_liquidation(self, failure_event: FailureEvent) -> bool:
        """긴급 청산"""
        self.liquidation_flag = True
        
        print(f"🚨 긴급 청산 실행")
        
        # 모니터링 시스템에 알림
        if self.monitor:
            self.monitor.emergency_stop(f"장애 대응 긴급 청산: {failure_event.description}")
        
        return True
    
    def _switch_to_backup(self, failure_event: FailureEvent) -> bool:
        """백업 시스템 전환"""
        affected_systems = failure_event.affected_systems
        
        for system in affected_systems:
            if system in self.backup_systems and self.backup_systems[system]:
                print(f"🔄 백업 시스템 전환: {system}")
                return True
        
        print(f"❌ 사용 가능한 백업 시스템 없음")
        return False
    
    def _execute_stress_test(self, failure_event: FailureEvent) -> bool:
        """스트레스 테스트 실행"""
        return self._trigger_cost_stress_test()
    
    def _request_manual_intervention(self, failure_event: FailureEvent) -> bool:
        """수동 개입 요청"""
        print(f"👨‍💻 수동 개입 요청: {failure_event.description}")
        
        # 알림 전송 (실제로는 이메일, SMS 등)
        if self.monitor:
            self.monitor._send_alert(
                AlertLevel.CRITICAL,
                "수동 개입 필요",
                {
                    'failure_type': failure_event.failure_type.value,
                    'description': failure_event.description,
                    'attempts': failure_event.recovery_attempts
                }
            )
        
        return False  # 수동 개입이므로 자동 복구는 실패
    
    def _trigger_cost_stress_test(self) -> bool:
        """비용 스트레스 테스트 실행"""
        print(f"🧪 비용 스트레스 테스트 시작 (비용 {self.config.cost_multiplier_stress}배)")
        
        # 현재 비용 시뮬레이션
        original_cost = np.random.uniform(100, 500)  # $100-500
        stressed_cost = original_cost * self.config.cost_multiplier_stress
        
        # 성능 영향 계산
        performance_impact = min(1.0, stressed_cost / (original_cost * 3))  # 3배 이상시 100% 영향
        
        # 테스트 통과 여부
        passed = performance_impact <= (1 - self.config.performance_threshold)
        
        # 추천사항 생성
        recommendations = []
        if not passed:
            recommendations.extend([
                "포지션 크기 축소 권장",
                "거래 빈도 감소 고려",
                "비용 효율적 전략으로 전환"
            ])
        
        # 결과 저장
        result = StressTestResult(
            test_timestamp=datetime.now(),
            original_cost=original_cost,
            stressed_cost=stressed_cost,
            cost_multiplier=self.config.cost_multiplier_stress,
            performance_impact=performance_impact,
            passed=passed,
            recommendations=recommendations
        )
        
        self.stress_test_results.append(result)
        
        print(f"📊 스트레스 테스트 결과:")
        print(f"   원본 비용: ${original_cost:.2f}")
        print(f"   스트레스 비용: ${stressed_cost:.2f}")
        print(f"   성능 영향: {performance_impact*100:.1f}%")
        print(f"   테스트 {'통과' if passed else '실패'}")
        
        if not passed:
            # 자동 포지션 축소
            self._reduce_positions(FailureEvent(
                timestamp=datetime.now(),
                failure_type=FailureType.COST_SPIKE,
                description="스트레스 테스트 실패",
                severity=AlertLevel.WARNING,
                affected_systems=['trading_engine']
            ))
        
        return passed
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """재시도 지연 계산"""
        if self.config.exponential_backoff:
            return self.config.retry_delay_seconds * (2 ** (attempt - 1))
        else:
            return self.config.retry_delay_seconds
    
    def _escalate_failure(self, failure_id: str, failure_event: FailureEvent):
        """장애 에스컬레이션"""
        print(f"⬆️ 장애 에스컬레이션: {failure_event.description}")
        
        # 심각도 상승
        if failure_event.severity == AlertLevel.WARNING:
            failure_event.severity = AlertLevel.CRITICAL
        elif failure_event.severity == AlertLevel.CRITICAL:
            failure_event.severity = AlertLevel.EMERGENCY
        
        # 수동 개입 요청
        self._request_manual_intervention(failure_event)
    
    def _check_system_health(self):
        """시스템 건강도 체크"""
        # 시뮬레이션: 랜덤 건강도
        systems = ['trading_engine', 'data_feed', 'risk_manager', 'order_system']
        
        for system in systems:
            # 기존 건강도가 있으면 점진적 변화, 없으면 초기값
            if system in self.system_health:
                change = np.random.normal(0, 0.05)  # ±5% 변화
                self.system_health[system] = np.clip(
                    self.system_health[system] + change, 0.0, 1.0
                )
            else:
                self.system_health[system] = np.random.uniform(0.8, 1.0)
            
            # 건강도가 낮으면 장애 신고
            if self.system_health[system] < 0.7:
                self.report_failure(
                    FailureType.PERFORMANCE_DEGRADATION,
                    f"{system} 성능 저하",
                    [system],
                    {'health_score': self.system_health[system]}
                )
    
    def enable_safe_mode(self, reason: str):
        """안전 모드 활성화"""
        self.safe_mode_enabled = True
        
        print(f"🛡️ 안전 모드 활성화: {reason}")
        
        if self.monitor:
            self.monitor._send_alert(
                AlertLevel.CRITICAL,
                f"안전 모드 활성화: {reason}"
            )
    
    def disable_safe_mode(self):
        """안전 모드 비활성화"""
        self.safe_mode_enabled = False
        
        print(f"🟢 안전 모드 비활성화")
        
        if self.monitor:
            self.monitor._send_alert(
                AlertLevel.INFO,
                "안전 모드 비활성화"
            )
    
    def get_system_status(self) -> Dict:
        """시스템 상태 조회"""
        active_failure_count = len(self.active_failures)
        total_failure_count = len(self.failure_history)
        
        # 최근 스트레스 테스트 결과
        recent_stress_test = None
        if self.stress_test_results:
            recent_stress_test = self.stress_test_results[-1]
        
        return {
            'safe_mode_enabled': self.safe_mode_enabled,
            'liquidation_flag': self.liquidation_flag,
            'active_failures': active_failure_count,
            'total_failures': total_failure_count,
            'system_health': self.system_health.copy(),
            'recovery_active': self.recovery_active,
            'recent_stress_test': {
                'timestamp': recent_stress_test.test_timestamp if recent_stress_test else None,
                'passed': recent_stress_test.passed if recent_stress_test else None,
                'cost_multiplier': recent_stress_test.cost_multiplier if recent_stress_test else None
            } if recent_stress_test else None
        }
    
    def add_failure_callback(self, callback: Callable[[FailureEvent], None]):
        """장애 콜백 추가"""
        self.failure_callbacks.append(callback)
    
    def add_recovery_callback(self, callback: Callable[[FailureEvent], None]):
        """복구 콜백 추가"""
        self.recovery_callbacks.append(callback)
    
    def export_failure_log(self) -> pd.DataFrame:
        """장애 로그 내보내기"""
        log_data = []
        
        for failure in self.failure_history:
            log_data.append({
                'timestamp': failure.timestamp,
                'failure_type': failure.failure_type.value,
                'description': failure.description,
                'severity': failure.severity.value,
                'affected_systems': ', '.join(failure.affected_systems),
                'recovery_attempts': failure.recovery_attempts,
                'resolved': failure.resolved,
                'resolution_time': failure.resolution_time,
                'resolution_duration': (
                    (failure.resolution_time - failure.timestamp).total_seconds()
                    if failure.resolution_time else None
                )
            })
        
        return pd.DataFrame(log_data)

def main():
    """테스트 실행"""
    print("🚀 장애 대응 시스템 테스트")
    print("="*80)
    
    # 모니터링 시스템과 연동
    from realtime_monitoring_system import RealtimeMonitor, MonitoringConfig
    
    monitor = RealtimeMonitor(MonitoringConfig())
    monitor.start_monitoring(10000.0)
    
    # 장애 복구 시스템 초기화
    recovery_config = FailureRecoveryConfig(
        cost_multiplier_stress=2.5,
        max_retry_attempts=2,
        auto_reduce_threshold=0.03
    )
    
    recovery_system = FailureRecoverySystem(recovery_config, monitor)
    
    # 콜백 함수 등록
    def failure_handler(failure: FailureEvent):
        print(f"🔔 장애 처리: {failure.failure_type.value} - {failure.description}")
    
    def recovery_handler(failure: FailureEvent):
        print(f"🎉 복구 완료: {failure.description}")
    
    recovery_system.add_failure_callback(failure_handler)
    recovery_system.add_recovery_callback(recovery_handler)
    
    # 복구 시스템 시작
    recovery_system.start_recovery_system()
    
    print(f"\n📊 장애 시나리오 테스트:")
    
    # 장애 시나리오들
    scenarios = [
        {
            'type': FailureType.NETWORK_ERROR,
            'description': '네트워크 연결 불안정',
            'systems': ['data_feed']
        },
        {
            'type': FailureType.API_ERROR,
            'description': '거래소 API 오류',
            'systems': ['trading_engine', 'order_system']
        },
        {
            'type': FailureType.COST_SPIKE,
            'description': '거래 비용 급증',
            'systems': ['trading_engine']
        },
        {
            'type': FailureType.SYSTEM_ERROR,
            'description': '시스템 메모리 부족',
            'systems': ['trading_engine', 'risk_manager']
        }
    ]
    
    # 시나리오 실행
    for i, scenario in enumerate(scenarios):
        print(f"\n🎭 시나리오 {i+1}: {scenario['description']}")
        
        failure_id = recovery_system.report_failure(
            scenario['type'],
            scenario['description'],
            scenario['systems'],
            {'test_scenario': i+1}
        )
        
        # 복구 과정 관찰
        time.sleep(2.0)
        
        # 상태 확인
        status = recovery_system.get_system_status()
        print(f"   활성 장애: {status['active_failures']}개")
        print(f"   안전 모드: {status['safe_mode_enabled']}")
        print(f"   청산 플래그: {status['liquidation_flag']}")
        
        # 시스템 건강도 출력
        for system, health in status['system_health'].items():
            print(f"   {system}: {health*100:.1f}%")
    
    # 복구 과정 대기
    print(f"\n⏳ 복구 과정 관찰 (10초)...")
    time.sleep(10.0)
    
    # 최종 상태
    final_status = recovery_system.get_system_status()
    print(f"\n📊 최종 시스템 상태:")
    for key, value in final_status.items():
        if key != 'system_health':
            print(f"   {key}: {value}")
    
    # 스트레스 테스트 결과
    if recovery_system.stress_test_results:
        latest_test = recovery_system.stress_test_results[-1]
        print(f"\n🧪 최근 스트레스 테스트:")
        print(f"   비용 배수: {latest_test.cost_multiplier}x")
        print(f"   성능 영향: {latest_test.performance_impact*100:.1f}%")
        print(f"   결과: {'통과' if latest_test.passed else '실패'}")
        if latest_test.recommendations:
            print(f"   권장사항: {', '.join(latest_test.recommendations)}")
    
    # 장애 로그 내보내기
    failure_log = recovery_system.export_failure_log()
    print(f"\n📋 장애 로그: {len(failure_log)}개 이벤트")
    
    if not failure_log.empty:
        resolved_count = failure_log['resolved'].sum()
        avg_resolution_time = failure_log['resolution_duration'].mean()
        print(f"   해결된 장애: {resolved_count}/{len(failure_log)}개")
        if avg_resolution_time:
            print(f"   평균 해결 시간: {avg_resolution_time:.1f}초")
    
    # 시스템 정리
    recovery_system.stop_recovery_system()
    monitor.stop_monitoring()
    
    print(f"\n🎯 핵심 특징:")
    print(f"   • 다양한 장애 유형 자동 감지")
    print(f"   • 지능적 복구 액션 선택")
    print(f"   • 비용 2배 스트레스 테스트")
    print(f"   • 자동 포지션 축소/청산")
    print(f"   • 백업 시스템 자동 전환")
    print(f"   • 에스컬레이션 및 수동 개입")

if __name__ == "__main__":
    main()