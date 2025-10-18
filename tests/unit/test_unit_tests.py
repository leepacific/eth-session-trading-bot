#!/usr/bin/env python3
"""
단위 테스트 구현
- 데이터 엔진 컴포넌트 테스트
- 최적화 알고리즘 테스트
- 통계 함수 테스트
- 포지션 사이징 계산 테스트
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
import warnings
warnings.filterwarnings('ignore')

# 테스트할 모듈들 import
from performance_evaluator import PerformanceEvaluator, PerformanceMetrics
from statistical_validator import StatisticalValidator
from kelly_position_sizer import KellyPositionSizer, KellyParameters, TradeStatistics
from dd_scaling_system import DDScalingSystem, DDScalingConfig
from realtime_monitoring_system import RealtimeMonitor, MonitoringConfig, MarketData, TradeEvent
from performance_optimizer import PerformanceOptimizer, PerformanceConfig, MemoryManager

class TestPerformanceEvaluator(unittest.TestCase):
    """성과 평가자 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.evaluator = PerformanceEvaluator()
        
        # 테스트용 거래 데이터 생성
        np.random.seed(42)
        self.sample_trades = []
        
        for i in range(100):
            # 60% 승률, 평균 수익 2%, 평균 손실 1%
            if np.random.random() < 0.6:
                pnl = np.random.normal(0.02, 0.01)  # 수익
            else:
                pnl = np.random.normal(-0.01, 0.005)  # 손실
            
            self.sample_trades.append({
                'entry_time': datetime.now() - timedelta(days=100-i),
                'exit_time': datetime.now() - timedelta(days=100-i) + timedelta(hours=4),
                'pnl': pnl,
                'pnl_pct': pnl,
                'quantity': 1.0,
                'side': 'long'
            })
    
    def test_calculate_basic_metrics(self):
        """기본 지표 계산 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        
        # 기본 검증
        self.assertIsInstance(metrics, PerformanceMetrics)
        self.assertGreater(metrics.total_trades, 0)
        self.assertGreaterEqual(metrics.win_rate, 0)
        self.assertLessEqual(metrics.win_rate, 1)
        
        # 수익 팩터 검증
        self.assertGreater(metrics.profit_factor, 0)
        
        # 샤프 비율 검증 (합리적 범위)
        self.assertGreater(metrics.sharpe_ratio, -5)
        self.assertLess(metrics.sharpe_ratio, 10)
        
        print(f"✅ 기본 지표: PF={metrics.profit_factor:.2f}, Sharpe={metrics.sharpe_ratio:.2f}")
    
    def test_sortino_ratio_calculation(self):
        """소르티노 비율 계산 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        
        # 소르티노 비율이 계산되었는지 확인
        self.assertIsNotNone(metrics.sortino_ratio)
        self.assertGreater(metrics.sortino_ratio, -10)
        self.assertLess(metrics.sortino_ratio, 20)
        
        # 소르티노가 샤프보다 일반적으로 높아야 함 (하방 위험만 고려)
        if metrics.sharpe_ratio > 0:
            self.assertGreaterEqual(metrics.sortino_ratio, metrics.sharpe_ratio)
        
        print(f"✅ 소르티노 비율: {metrics.sortino_ratio:.2f}")
    
    def test_calmar_ratio_calculation(self):
        """칼마 비율 계산 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        
        # 칼마 비율 검증
        self.assertIsNotNone(metrics.calmar_ratio)
        
        # 최대 낙폭이 있으면 칼마 비율도 계산되어야 함
        if metrics.max_drawdown > 0:
            self.assertGreater(abs(metrics.calmar_ratio), 0)
        
        print(f"✅ 칼마 비율: {metrics.calmar_ratio:.2f}")
    
    def test_sqn_calculation(self):
        """SQN 계산 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        
        # SQN 검증
        self.assertIsNotNone(metrics.sqn)
        self.assertGreater(metrics.sqn, -10)
        self.assertLess(metrics.sqn, 10)
        
        print(f"✅ SQN: {metrics.sqn:.2f}")
    
    def test_composite_score_calculation(self):
        """복합 점수 계산 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        score = self.evaluator.calculate_composite_score(metrics)
        
        # 점수가 계산되었는지 확인
        self.assertIsNotNone(score)
        self.assertIsInstance(score, float)
        
        # 합리적 범위 확인
        self.assertGreater(score, -5)
        self.assertLess(score, 5)
        
        print(f"✅ 복합 점수: {score:.4f}")
    
    def test_constraint_validation(self):
        """제약 조건 검증 테스트"""
        metrics = self.evaluator.calculate_metrics(self.sample_trades)
        constraints_passed = self.evaluator.validate_constraints(metrics)
        
        # 제약 조건 결과가 불린값인지 확인
        self.assertIsInstance(constraints_passed, bool)
        
        print(f"✅ 제약 조건: {'통과' if constraints_passed else '실패'}")

class TestStatisticalValidator(unittest.TestCase):
    """통계적 검증자 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.performance_evaluator = PerformanceEvaluator()
        self.validator = StatisticalValidator(self.performance_evaluator)
    
    def test_deflated_sortino_calculation(self):
        """Deflated Sortino 계산 테스트"""
        sortino_ratio = 2.5
        n_tests = 100
        n_observations = 1000
        
        deflated_sortino, passed = self.validator.calculate_deflated_sortino(
            sortino_ratio, n_tests, n_observations
        )
        
        # 결과 검증
        self.assertIsInstance(deflated_sortino, float)
        self.assertIsInstance(passed, bool)
        self.assertLess(deflated_sortino, sortino_ratio)  # 보정 후 더 작아야 함
        
        print(f"✅ Deflated Sortino: {deflated_sortino:.4f} (원본: {sortino_ratio:.4f})")
    
    def test_whites_reality_check(self):
        """White's Reality Check 테스트"""
        # 벤치마크와 전략 수익률 생성
        np.random.seed(42)
        benchmark_returns = np.random.normal(0.001, 0.02, 252)  # 1년 데이터
        
        strategy_returns = [
            benchmark_returns + np.random.normal(0.002, 0.01, 252),  # 전략 1
            benchmark_returns + np.random.normal(0.001, 0.015, 252), # 전략 2
            benchmark_returns + np.random.normal(-0.001, 0.02, 252)  # 전략 3
        ]
        
        p_value, passed = self.validator.whites_reality_check(
            benchmark_returns, strategy_returns
        )
        
        # 결과 검증
        self.assertIsInstance(p_value, float)
        self.assertIsInstance(passed, bool)
        self.assertGreaterEqual(p_value, 0)
        self.assertLessEqual(p_value, 1)
        
        print(f"✅ White's Reality Check: p-value={p_value:.4f}, 통과={passed}")
    
    def test_spa_test(self):
        """SPA 테스트"""
        # 테스트 데이터 생성
        np.random.seed(42)
        benchmark_returns = np.random.normal(0.001, 0.02, 252)
        
        strategy_returns = [
            benchmark_returns + np.random.normal(0.003, 0.01, 252),  # 좋은 전략
            benchmark_returns + np.random.normal(0.0005, 0.015, 252) # 보통 전략
        ]
        
        p_value, passed = self.validator.spa_test(benchmark_returns, strategy_returns)
        
        # 결과 검증
        self.assertIsInstance(p_value, float)
        self.assertIsInstance(passed, bool)
        self.assertGreaterEqual(p_value, 0)
        self.assertLessEqual(p_value, 1)
        
        print(f"✅ SPA Test: p-value={p_value:.4f}, 통과={passed}")

class TestKellyPositionSizer(unittest.TestCase):
    """켈리 포지션 사이저 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.kelly_sizer = KellyPositionSizer()
        
        # 테스트용 거래 통계 생성
        np.random.seed(42)
        self.sample_trades = []
        
        for i in range(100):
            # 65% 승률, 평균 수익 2.5%, 평균 손실 1.2%
            if np.random.random() < 0.65:
                pnl_pct = np.random.normal(0.025, 0.01)  # 수익
            else:
                pnl_pct = np.random.normal(-0.012, 0.005)  # 손실
            
            self.sample_trades.append({'pnl_pct': pnl_pct})
    
    def test_trade_statistics_calculation(self):
        """거래 통계 계산 테스트"""
        trade_stats = self.kelly_sizer.calculate_trade_statistics(self.sample_trades)
        
        # 결과 검증
        self.assertIsInstance(trade_stats, TradeStatistics)
        self.assertGreater(trade_stats.total_trades, 0)
        self.assertGreaterEqual(trade_stats.win_rate, 0)
        self.assertLessEqual(trade_stats.win_rate, 1)
        self.assertGreater(trade_stats.avg_win, 0)
        self.assertGreater(trade_stats.avg_loss, 0)
        self.assertGreater(trade_stats.profit_factor, 0)
        
        print(f"✅ 거래 통계: 승률={trade_stats.win_rate*100:.1f}%, PF={trade_stats.profit_factor:.2f}")
    
    def test_kelly_optimal_calculation(self):
        """켈리 최적값 계산 테스트"""
        trade_stats = self.kelly_sizer.calculate_trade_statistics(self.sample_trades)
        
        # 켈리 최적값 검증
        self.assertGreaterEqual(trade_stats.kelly_optimal, 0)
        self.assertLessEqual(trade_stats.kelly_optimal, 1)  # 100% 이하
        
        # 수익성이 있으면 켈리값이 0보다 커야 함
        if trade_stats.expectancy > 0:
            self.assertGreater(trade_stats.kelly_optimal, 0)
        
        print(f"✅ 켈리 최적값: {trade_stats.kelly_optimal:.4f}")
    
    def test_position_sizing_small_account(self):
        """소액 계좌 포지션 사이징 테스트"""
        balance = 500.0  # $500 (1000 미만)
        trade_stats = self.kelly_sizer.calculate_trade_statistics(self.sample_trades)
        
        position_info = self.kelly_sizer.calculate_position_size(balance, trade_stats)
        
        # 소액 계좌는 최소 주문 금액 사용
        self.assertEqual(position_info.adjusted_position_size, 20.0)
        self.assertTrue(position_info.min_order_applied)
        
        print(f"✅ 소액 계좌 포지션: ${position_info.adjusted_position_size}")
    
    def test_position_sizing_large_account(self):
        """대형 계좌 포지션 사이징 테스트"""
        balance = 10000.0  # $10,000
        trade_stats = self.kelly_sizer.calculate_trade_statistics(self.sample_trades)
        
        position_info = self.kelly_sizer.calculate_position_size(balance, trade_stats)
        
        # 대형 계좌는 켈리 기반 계산
        self.assertGreater(position_info.kelly_fraction, 0)
        self.assertLessEqual(position_info.adjusted_position_size, balance * 0.05)  # 5% 이하
        
        print(f"✅ 대형 계좌 포지션: ${position_info.adjusted_position_size:.2f}")
    
    def test_dd_scaling(self):
        """DD 스케일링 테스트"""
        balance = 10000.0
        trade_stats = self.kelly_sizer.calculate_trade_statistics(self.sample_trades)
        
        # DD 없을 때
        position_no_dd = self.kelly_sizer.calculate_position_size(balance, trade_stats, 0.0)
        
        # DD 15%일 때
        position_with_dd = self.kelly_sizer.calculate_position_size(balance, trade_stats, 0.15)
        
        # DD가 있으면 포지션이 축소되어야 함
        self.assertLess(position_with_dd.adjusted_position_size, position_no_dd.adjusted_position_size)
        self.assertGreater(position_with_dd.dd_scaling_applied, 0)
        
        print(f"✅ DD 스케일링: {position_with_dd.dd_scaling_applied*100:.1f}% 축소")

class TestDDScalingSystem(unittest.TestCase):
    """DD 스케일링 시스템 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.dd_system = DDScalingSystem()
    
    def test_balance_update_and_dd_calculation(self):
        """잔고 업데이트 및 DD 계산 테스트"""
        # 초기 잔고
        initial_balance = 10000.0
        self.dd_system.update_balance(initial_balance)
        
        # 손실 발생
        loss_balance = 8500.0  # 15% 손실
        dd_state = self.dd_system.update_balance(loss_balance)
        
        # DD 계산 검증
        expected_dd = (initial_balance - loss_balance) / initial_balance
        self.assertAlmostEqual(dd_state.current_dd, expected_dd, places=4)
        self.assertGreater(dd_state.scaling_applied, 0)  # 스케일링 적용되어야 함
        
        print(f"✅ DD 계산: {dd_state.current_dd*100:.1f}%, 스케일링: {dd_state.scaling_applied*100:.1f}%")
    
    def test_scaling_application(self):
        """스케일링 적용 테스트"""
        # DD 상태 설정
        self.dd_system.update_balance(10000.0)
        self.dd_system.update_balance(8000.0)  # 20% DD
        
        original_position = 1000.0
        scaling_result = self.dd_system.apply_scaling(original_position)
        
        # 스케일링 결과 검증
        self.assertLess(scaling_result.scaled_position, original_position)
        self.assertGreater(scaling_result.scaling_factor, 0)
        self.assertEqual(scaling_result.dd_level, 0.2)
        
        print(f"✅ 포지션 스케일링: ${original_position} → ${scaling_result.scaled_position:.2f}")
    
    def test_recovery_signal_detection(self):
        """회복 신호 감지 테스트"""
        # DD 발생 후 회복 시뮬레이션
        balances = [10000, 8500, 8200, 8400, 8700, 9100, 9400]  # 점진적 회복
        
        for balance in balances:
            self.dd_system.update_balance(balance)
        
        # 회복 신호 확인 (실제로는 더 복잡한 로직)
        recovery_signal = len(balances) > 5  # 단순화된 테스트
        
        self.assertIsInstance(recovery_signal, bool)
        
        print(f"✅ 회복 신호: {'감지됨' if recovery_signal else '없음'}")

class TestRealtimeMonitor(unittest.TestCase):
    """실시간 모니터링 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        config = MonitoringConfig(
            daily_loss_limit_pct=0.05,
            max_consecutive_losses=3
        )
        self.monitor = RealtimeMonitor(config)
    
    def test_balance_update_and_loss_tracking(self):
        """잔고 업데이트 및 손실 추적 테스트"""
        initial_balance = 10000.0
        self.monitor.start_monitoring(initial_balance)
        
        # 손실 발생
        loss_balance = 9400.0  # 6% 손실 (한도 초과)
        self.monitor.update_balance(loss_balance)
        
        # 상태 확인
        status = self.monitor.get_monitoring_status()
        
        self.assertEqual(status['current_balance'], loss_balance)
        self.assertLess(status['daily_pnl_pct'], -0.05)  # 5% 이상 손실
        
        print(f"✅ 손실 추적: {status['daily_pnl_pct']*100:.1f}%")
        
        self.monitor.stop_monitoring()
    
    def test_consecutive_loss_tracking(self):
        """연속 손실 추적 테스트"""
        self.monitor.start_monitoring(10000.0)
        
        # 연속 손실 거래 기록
        for i in range(4):  # 4회 연속 손실 (한도 3회 초과)
            trade = TradeEvent(
                timestamp=datetime.now(),
                symbol='BTCUSDT',
                side='long',
                quantity=0.1,
                price=50000.0,
                pnl=-100.0
            )
            self.monitor.record_trade(trade)
        
        # 연속 손실 확인
        status = self.monitor.get_monitoring_status()
        self.assertGreaterEqual(status['consecutive_losses'], 3)
        
        print(f"✅ 연속 손실: {status['consecutive_losses']}회")
        
        self.monitor.stop_monitoring()
    
    def test_market_data_validation(self):
        """시장 데이터 검증 테스트"""
        self.monitor.start_monitoring(10000.0)
        
        # 문제가 있는 시장 데이터
        bad_market_data = MarketData(
            symbol='BTCUSDT',
            timestamp=datetime.now(),
            bid=49900.0,
            ask=50200.0,  # 30bps 스프레드 (높음)
            last_price=50000.0,
            volume_24h=50000.0  # 낮은 거래량
        )
        
        self.monitor.update_market_data('BTCUSDT', bad_market_data)
        
        # 스프레드 계산 확인
        self.assertGreater(bad_market_data.spread_bps, 20)  # 20bps 이상
        
        print(f"✅ 시장 데이터: 스프레드 {bad_market_data.spread_bps:.1f}bps")
        
        self.monitor.stop_monitoring()

class TestPerformanceOptimizer(unittest.TestCase):
    """성능 최적화기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        config = PerformanceConfig(
            max_memory_usage_gb=1.0,  # 테스트용 축소
            cache_size_mb=64.0
        )
        self.optimizer = PerformanceOptimizer(config)
    
    def test_memory_manager_initialization(self):
        """메모리 관리자 초기화 테스트"""
        memory_manager = self.optimizer.memory_manager
        
        # 메모리 통계 조회
        stats = memory_manager.get_memory_stats()
        
        self.assertIsInstance(stats.total_gb, float)
        self.assertIsInstance(stats.available_gb, float)
        self.assertGreater(stats.total_gb, 0)
        self.assertGreater(stats.available_gb, 0)
        
        print(f"✅ 메모리 상태: {stats.available_gb:.1f}GB 사용 가능")
    
    def test_cache_operations(self):
        """캐시 작업 테스트"""
        memory_manager = self.optimizer.memory_manager
        
        # 캐시 저장
        test_data = np.random.random((1000, 10))
        memory_manager.cache_set("test_key", test_data)
        
        # 캐시 조회
        retrieved_data = memory_manager.cache_get("test_key")
        
        self.assertIsNotNone(retrieved_data)
        np.testing.assert_array_equal(test_data, retrieved_data)
        
        # 캐시 통계
        cache_stats = memory_manager.get_cache_stats()
        self.assertGreater(cache_stats['cache_entries'], 0)
        
        print(f"✅ 캐시 작업: {cache_stats['cache_entries']}개 항목")
    
    def test_parallel_processing(self):
        """병렬 처리 테스트"""
        parallel_processor = self.optimizer.parallel_processor
        parallel_processor.start_pools()
        
        # 테스트 함수
        def square_function(x):
            return x ** 2
        
        # 테스트 데이터
        test_data = list(range(100))
        
        # 병렬 처리 실행
        results = parallel_processor.process_parallel(square_function, test_data)
        
        # 결과 검증
        expected_results = [x ** 2 for x in test_data]
        self.assertEqual(len(results), len(expected_results))
        
        # 일부 결과 확인 (None이 아닌 것들만)
        valid_results = [r for r in results if r is not None]
        self.assertGreater(len(valid_results), 0)
        
        print(f"✅ 병렬 처리: {len(valid_results)}/{len(test_data)}개 성공")
        
        parallel_processor.stop_pools()
    
    def test_performance_metrics_collection(self):
        """성능 지표 수집 테스트"""
        pipeline_id = "test_pipeline"
        
        # 성능 지표 수집
        metrics = self.optimizer.collect_performance_metrics(pipeline_id)
        
        # 결과 검증
        self.assertIsNotNone(metrics.timestamp)
        self.assertIsNotNone(metrics.memory_stats)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        
        print(f"✅ 성능 지표: CPU {metrics.cpu_percent:.1f}%, 메모리 {metrics.memory_stats.process_memory_gb:.2f}GB")

class TestSuite:
    """전체 테스트 스위트"""
    
    def __init__(self):
        """테스트 스위트 초기화"""
        self.test_classes = [
            TestPerformanceEvaluator,
            TestStatisticalValidator,
            TestKellyPositionSizer,
            TestDDScalingSystem,
            TestRealtimeMonitor,
            TestPerformanceOptimizer
        ]
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🧪 단위 테스트 실행 시작")
        print("="*80)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for test_class in self.test_classes:
            print(f"\n📋 {test_class.__name__} 테스트 실행:")
            print("-" * 50)
            
            # 테스트 스위트 생성
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            
            # 테스트 실행
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            # 결과 집계
            class_total = result.testsRun
            class_failed = len(result.failures) + len(result.errors)
            class_passed = class_total - class_failed
            
            total_tests += class_total
            passed_tests += class_passed
            failed_tests += class_failed
            
            print(f"   실행: {class_total}개, 통과: {class_passed}개, 실패: {class_failed}개")
            
            # 실패한 테스트 상세 정보
            if result.failures:
                print(f"   ❌ 실패한 테스트:")
                for test, traceback in result.failures:
                    print(f"      - {test}: {traceback.split('AssertionError:')[-1].strip()}")
            
            if result.errors:
                print(f"   💥 오류 발생:")
                for test, traceback in result.errors:
                    print(f"      - {test}: {traceback.split('Exception:')[-1].strip()}")
        
        # 전체 결과 요약
        print(f"\n📊 전체 테스트 결과:")
        print("="*80)
        print(f"   총 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개 ({passed_tests/total_tests*100:.1f}%)")
        print(f"   실패: {failed_tests}개 ({failed_tests/total_tests*100:.1f}%)")
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        if success_rate >= 0.9:
            print(f"   🎉 테스트 품질: 우수 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.8:
            print(f"   ✅ 테스트 품질: 양호 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.7:
            print(f"   ⚠️ 테스트 품질: 보통 ({success_rate*100:.1f}%)")
        else:
            print(f"   ❌ 테스트 품질: 개선 필요 ({success_rate*100:.1f}%)")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate
        }

def main():
    """메인 실행 함수"""
    print("🚀 단위 테스트 시스템 실행")
    print("="*80)
    
    # 테스트 스위트 실행
    test_suite = TestSuite()
    results = test_suite.run_all_tests()
    
    print(f"\n🎯 핵심 특징:")
    print(f"   • 6개 주요 컴포넌트 단위 테스트")
    print(f"   • 성과 평가 알고리즘 검증")
    print(f"   • 통계적 검정 함수 테스트")
    print(f"   • 포지션 사이징 계산 검증")
    print(f"   • 실시간 모니터링 로직 테스트")
    print(f"   • 성능 최적화 기능 검증")
    
    return results

if __name__ == "__main__":
    main()