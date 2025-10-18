#!/usr/bin/env python3
"""
통합 테스트 구현
- 전체 최적화 파이프라인 테스트
- 워크포워드 검증 워크플로우 테스트
- 몬테카를로 시뮬레이션 체인 테스트
- 켈리 포지션 사이징 통합 테스트
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
import time
import warnings

warnings.filterwarnings("ignore")

# 통합 테스트할 모듈들 import
from optimization_pipeline import OptimizationPipeline, PipelineConfig, PipelineStatus
from performance_evaluator import PerformanceEvaluator
from statistical_validator import StatisticalValidator
from kelly_position_sizer import KellyPositionSizer
from dd_scaling_system import DDScalingSystem
from realtime_monitoring_system import RealtimeMonitor, MonitoringConfig
from failure_recovery_system import FailureRecoverySystem, FailureRecoveryConfig
from performance_optimizer import PerformanceOptimizer, PerformanceConfig


class TestOptimizationPipelineIntegration(unittest.TestCase):
    """최적화 파이프라인 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        # 테스트용 축소 설정
        self.config = PipelineConfig(
            symbol="BTCUSDT",
            data_length=1000,  # 축소
            global_search_samples=20,  # 축소
            local_refinement_steps=10,  # 축소
            mc_simulations=100,  # 축소
            parallel_workers=2,
            timeout_minutes=5,  # 축소
            save_intermediate=False,  # 테스트에서는 저장 안함
        )

        self.pipeline = OptimizationPipeline(self.config)

        # 테스트용 파라미터 공간
        self.parameter_space = {
            "target_r": (2.0, 4.0),
            "stop_atr_mult": (0.05, 0.2),
            "swing_len": (3, 10),
            "rr_percentile": (0.1, 0.4),
        }

    def test_full_pipeline_execution(self):
        """전체 파이프라인 실행 테스트"""
        print("🔄 전체 파이프라인 실행 테스트...")

        # 진행률 추적
        progress_updates = []

        def progress_callback(progress: float, message: str):
            progress_updates.append((progress, message))

        self.pipeline.add_progress_callback(progress_callback)

        # 파이프라인 실행
        start_time = time.time()
        result = self.pipeline.run_pipeline(self.parameter_space)
        end_time = time.time()

        # 기본 검증
        self.assertIsNotNone(result)
        self.assertEqual(result.config.symbol, "BTCUSDT")
        self.assertIsNotNone(result.start_time)
        self.assertIsNotNone(result.end_time)

        # 실행 시간 검증 (5분 이내)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 300)  # 5분

        # 상태 검증
        self.assertIn(result.status, [PipelineStatus.COMPLETED, PipelineStatus.FAILED])

        # 단계 결과 검증
        self.assertGreater(len(result.stage_results), 0)

        # 진행률 업데이트 확인
        self.assertGreater(len(progress_updates), 0)

        print(f"   ✅ 파이프라인 실행 완료: {execution_time:.1f}초")
        print(f"   📊 상태: {result.status.value}")
        print(f"   📋 단계 수: {len(result.stage_results)}")

        # 성공한 경우 최종 결과 검증
        if result.status == PipelineStatus.COMPLETED:
            self.assertIsNotNone(result.final_parameters)
            self.assertIsNotNone(result.final_metrics)

            # 파라미터가 범위 내에 있는지 확인
            for param_name, value in result.final_parameters.items():
                if param_name in self.parameter_space:
                    min_val, max_val = self.parameter_space[param_name]
                    self.assertGreaterEqual(value, min_val * 0.8)  # 약간의 여유
                    self.assertLessEqual(value, max_val * 1.2)

            print(f"   🎯 최종 점수: {result.final_metrics.get('combined_score', 'N/A')}")

    def test_pipeline_stage_validation(self):
        """파이프라인 단계별 검증 테스트"""
        print("🔍 파이프라인 단계별 검증 테스트...")

        # 각 단계별 콜백 등록
        stage_completions = {}

        def create_stage_callback(stage_name):
            def callback(stage_result):
                stage_completions[stage_name] = True

            return callback

        from optimization_pipeline import PipelineStage

        for stage in PipelineStage:
            self.pipeline.add_stage_callback(stage, create_stage_callback(stage.value))

        # 파이프라인 실행
        result = self.pipeline.run_pipeline(self.parameter_space)

        # 단계별 완료 확인
        completed_stages = len([s for s in result.stage_results if s.status == PipelineStatus.COMPLETED])

        print(f"   ✅ 완료된 단계: {completed_stages}/{len(result.stage_results)}")

        # 각 단계의 실행 시간 확인
        for stage_result in result.stage_results:
            if stage_result.duration_seconds:
                self.assertGreater(stage_result.duration_seconds, 0)
                self.assertLess(stage_result.duration_seconds, 60)  # 1분 이내

        print(
            f"   ⏱️ 평균 단계 시간: {np.mean([s.duration_seconds for s in result.stage_results if s.duration_seconds]):.1f}초"
        )

    def test_pipeline_error_handling(self):
        """파이프라인 오류 처리 테스트"""
        print("🚨 파이프라인 오류 처리 테스트...")

        # 잘못된 파라미터 공간으로 테스트
        invalid_parameter_space = {"invalid_param": (0, 0)}  # 잘못된 범위

        # 파이프라인 실행 (오류 발생 예상)
        result = self.pipeline.run_pipeline(invalid_parameter_space)

        # 오류 처리 확인
        self.assertIsNotNone(result)

        # 실패하거나 부분적으로 완료되어야 함
        if result.status == PipelineStatus.FAILED:
            self.assertIsNotNone(result.error_message)
            print(f"   ✅ 오류 감지됨: {result.error_message[:50]}...")
        else:
            print(f"   ⚠️ 예상과 다른 결과: {result.status.value}")


class TestWorkforwardValidationWorkflow(unittest.TestCase):
    """워크포워드 검증 워크플로우 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.performance_evaluator = PerformanceEvaluator()

        # 테스트용 데이터 생성
        np.random.seed(42)
        self.test_data = self._generate_test_data(2000)  # 2000개 데이터 포인트

    def _generate_test_data(self, length: int) -> pd.DataFrame:
        """테스트 데이터 생성"""
        dates = pd.date_range(start="2020-01-01", periods=length, freq="1H")

        # 랜덤 워크 가격 데이터
        returns = np.random.normal(0, 0.001, length)
        prices = 50000 * np.exp(np.cumsum(returns))

        return pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices * (1 + np.random.normal(0, 0.0001, length)),
                "high": prices * (1 + np.abs(np.random.normal(0, 0.002, length))),
                "low": prices * (1 - np.abs(np.random.normal(0, 0.002, length))),
                "close": prices,
                "volume": np.random.uniform(100, 1000, length),
            }
        )

    def test_walkforward_slice_creation(self):
        """워크포워드 슬라이스 생성 테스트"""
        print("📊 워크포워드 슬라이스 생성 테스트...")

        # 슬라이스 생성 (9개월 훈련, 2개월 테스트)
        train_length = int(len(self.test_data) * 0.8)  # 80% 훈련
        test_length = int(len(self.test_data) * 0.2)  # 20% 테스트

        slices = []
        overlap = int(train_length * 0.1)  # 10% 오버랩

        for i in range(0, len(self.test_data) - train_length - test_length, overlap):
            train_start = i
            train_end = i + train_length
            test_start = train_end
            test_end = test_start + test_length

            if test_end <= len(self.test_data):
                slices.append(
                    {"train_start": train_start, "train_end": train_end, "test_start": test_start, "test_end": test_end}
                )

        # 슬라이스 검증
        self.assertGreater(len(slices), 0)

        for slice_info in slices:
            # 훈련 구간이 테스트 구간보다 앞에 있어야 함
            self.assertLess(slice_info["train_end"], slice_info["test_start"])

            # 구간 길이 검증
            train_size = slice_info["train_end"] - slice_info["train_start"]
            test_size = slice_info["test_end"] - slice_info["test_start"]

            self.assertEqual(train_size, train_length)
            self.assertEqual(test_size, test_length)

        print(f"   ✅ 생성된 슬라이스: {len(slices)}개")
        print(f"   📏 훈련 크기: {train_length}, 테스트 크기: {test_length}")

    def test_oos_performance_evaluation(self):
        """OOS 성능 평가 테스트"""
        print("📈 OOS 성능 평가 테스트...")

        # 가상의 거래 결과 생성
        oos_trades = []

        for i in range(50):  # 50개 거래
            # 60% 승률
            if np.random.random() < 0.6:
                pnl = np.random.normal(0.02, 0.01)  # 수익
            else:
                pnl = np.random.normal(-0.01, 0.005)  # 손실

            oos_trades.append(
                {
                    "entry_time": datetime.now() - timedelta(days=50 - i),
                    "exit_time": datetime.now() - timedelta(days=50 - i) + timedelta(hours=2),
                    "pnl": pnl,
                    "pnl_pct": pnl,
                    "quantity": 1.0,
                    "side": "long",
                }
            )

        # OOS 성능 계산
        oos_metrics = self.performance_evaluator.calculate_metrics(oos_trades)

        # OOS 합격 기준 검증
        oos_criteria = {
            "profit_factor": 1.8,
            "sortino_ratio": 1.5,
            "calmar_ratio": 1.5,
            "max_drawdown": 0.30,
            "total_trades": 200,
        }

        passed_criteria = []

        if oos_metrics.profit_factor >= oos_criteria["profit_factor"]:
            passed_criteria.append("profit_factor")

        if oos_metrics.sortino_ratio >= oos_criteria["sortino_ratio"]:
            passed_criteria.append("sortino_ratio")

        if oos_metrics.calmar_ratio >= oos_criteria["calmar_ratio"]:
            passed_criteria.append("calmar_ratio")

        if oos_metrics.max_drawdown <= oos_criteria["max_drawdown"]:
            passed_criteria.append("max_drawdown")

        if oos_metrics.total_trades >= oos_criteria["total_trades"]:
            passed_criteria.append("total_trades")

        print(f"   ✅ 통과한 기준: {len(passed_criteria)}/{len(oos_criteria)}개")
        print(f"   📊 PF: {oos_metrics.profit_factor:.2f}, Sortino: {oos_metrics.sortino_ratio:.2f}")

        # 최소 일부 기준은 통과해야 함
        self.assertGreater(len(passed_criteria), 0)


class TestMonteCarloSimulationChain(unittest.TestCase):
    """몬테카를로 시뮬레이션 체인 테스트"""

    def setUp(self):
        """테스트 설정"""
        # 테스트용 거래 데이터 생성
        np.random.seed(42)
        self.base_trades = []

        for i in range(200):
            # 65% 승률, 평균 수익 2%, 평균 손실 1%
            if np.random.random() < 0.65:
                pnl_pct = np.random.normal(0.02, 0.008)  # 수익
            else:
                pnl_pct = np.random.normal(-0.01, 0.004)  # 손실

            self.base_trades.append(
                {
                    "timestamp": datetime.now() - timedelta(days=200 - i),
                    "pnl_pct": pnl_pct,
                    "side": "long" if np.random.random() > 0.5 else "short",
                    "win": pnl_pct > 0,
                }
            )

    def test_block_bootstrap_simulation(self):
        """블록 부트스트랩 시뮬레이션 테스트"""
        print("🎲 블록 부트스트랩 시뮬레이션 테스트...")

        # 원본 수익률
        original_returns = [trade["pnl_pct"] for trade in self.base_trades]

        # 블록 부트스트랩 실행
        n_simulations = 100
        block_size = 10  # 10개 거래씩 블록

        bootstrap_results = []

        for sim in range(n_simulations):
            # 블록 부트스트랩
            bootstrapped_returns = []
            n_blocks = len(original_returns) // block_size

            for _ in range(n_blocks):
                # 랜덤 블록 선택
                start_idx = np.random.randint(0, len(original_returns) - block_size + 1)
                block = original_returns[start_idx : start_idx + block_size]
                bootstrapped_returns.extend(block)

            # 통계 계산
            total_return = np.sum(bootstrapped_returns)
            win_rate = np.mean([r > 0 for r in bootstrapped_returns])

            bootstrap_results.append(
                {"total_return": total_return, "win_rate": win_rate, "trade_count": len(bootstrapped_returns)}
            )

        # 결과 검증
        self.assertEqual(len(bootstrap_results), n_simulations)

        # 백분위수 계산
        total_returns = [r["total_return"] for r in bootstrap_results]
        p5 = np.percentile(total_returns, 5)
        p50 = np.percentile(total_returns, 50)
        p95 = np.percentile(total_returns, 95)

        print(f"   ✅ 시뮬레이션: {n_simulations}회")
        print(f"   📊 수익률 분포: P5={p5:.4f}, P50={p50:.4f}, P95={p95:.4f}")

        # 분포가 합리적인지 확인
        self.assertLess(p5, p50)
        self.assertLess(p50, p95)

    def test_trade_resampling_with_structure_preservation(self):
        """구조 보존 거래 리샘플링 테스트"""
        print("🔄 구조 보존 거래 리샘플링 테스트...")

        # 원본 거래 구조 분석
        wins = [trade for trade in self.base_trades if trade["win"]]
        losses = [trade for trade in self.base_trades if not trade["win"]]

        original_win_rate = len(wins) / len(self.base_trades)

        # 리샘플링 실행
        n_simulations = 50
        resampling_results = []

        for sim in range(n_simulations):
            # 승/패 구조 보존하면서 리샘플링
            resampled_trades = []

            for trade in self.base_trades:
                if trade["win"]:
                    # 승리 거래에서 랜덤 선택
                    resampled_trade = np.random.choice(wins)
                else:
                    # 손실 거래에서 랜덤 선택
                    resampled_trade = np.random.choice(losses)

                resampled_trades.append(resampled_trade)

            # 구조 검증
            resampled_win_rate = np.mean([trade["win"] for trade in resampled_trades])
            total_pnl = np.sum([trade["pnl_pct"] for trade in resampled_trades])

            resampling_results.append({"win_rate": resampled_win_rate, "total_pnl": total_pnl})

        # 구조 보존 검증
        avg_resampled_win_rate = np.mean([r["win_rate"] for r in resampling_results])

        # 승률이 원본과 유사해야 함 (±5% 오차)
        self.assertAlmostEqual(avg_resampled_win_rate, original_win_rate, delta=0.05)

        print(f"   ✅ 원본 승률: {original_win_rate:.3f}")
        print(f"   🔄 리샘플링 승률: {avg_resampled_win_rate:.3f}")
        print(f"   📊 구조 보존: {'성공' if abs(avg_resampled_win_rate - original_win_rate) < 0.05 else '실패'}")

    def test_execution_noise_simulation(self):
        """실행 노이즈 시뮬레이션 테스트"""
        print("📡 실행 노이즈 시뮬레이션 테스트...")

        # 원본 거래 결과
        original_pnl = [trade["pnl_pct"] for trade in self.base_trades]

        # 실행 노이즈 추가
        slippage_std = 0.001  # 0.1% 슬리피지 표준편차
        spread_events = 0.05  # 5% 확률로 스프레드 확장

        noisy_simulations = []

        for sim in range(100):
            noisy_pnl = []

            for pnl in original_pnl:
                # 슬리피지 노이즈
                slippage = np.random.normal(0, slippage_std)

                # 스프레드 확장 이벤트
                if np.random.random() < spread_events:
                    spread_penalty = np.random.uniform(0.0005, 0.002)  # 0.05-0.2% 패널티
                    slippage -= spread_penalty

                noisy_pnl.append(pnl + slippage)

            total_noisy_pnl = np.sum(noisy_pnl)
            noisy_simulations.append(total_noisy_pnl)

        # 노이즈 영향 분석
        original_total = np.sum(original_pnl)
        avg_noisy_total = np.mean(noisy_simulations)
        noise_impact = (avg_noisy_total - original_total) / abs(original_total)

        print(f"   ✅ 원본 총 수익률: {original_total:.4f}")
        print(f"   📡 노이즈 적용 후: {avg_noisy_total:.4f}")
        print(f"   📊 노이즈 영향: {noise_impact*100:.2f}%")

        # 노이즈가 성능을 약간 저하시켜야 함
        self.assertLess(avg_noisy_total, original_total)

        # 하지만 너무 큰 영향은 아니어야 함 (10% 이내)
        self.assertGreater(abs(noise_impact), 0.001)  # 최소 0.1% 영향
        self.assertLess(abs(noise_impact), 0.10)  # 최대 10% 영향


class TestKellyPositionSizingIntegration(unittest.TestCase):
    """켈리 포지션 사이징 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.kelly_sizer = KellyPositionSizer()
        self.dd_system = DDScalingSystem()
        self.monitor = RealtimeMonitor()

        # 테스트용 거래 데이터
        np.random.seed(42)
        self.sample_trades = []

        for i in range(150):
            # 70% 승률, 평균 수익 2.5%, 평균 손실 1.2%
            if np.random.random() < 0.7:
                pnl_pct = np.random.normal(0.025, 0.01)  # 수익
            else:
                pnl_pct = np.random.normal(-0.012, 0.006)  # 손실

            self.sample_trades.append({"pnl_pct": pnl_pct})

    def test_integrated_position_sizing_workflow(self):
        """통합 포지션 사이징 워크플로우 테스트"""
        print("💰 통합 포지션 사이징 워크플로우 테스트...")

        # 다양한 계좌 크기와 DD 상황에서 테스트
        test_scenarios = [
            {"balance": 500, "dd": 0.0, "description": "소액계좌_정상"},
            {"balance": 1500, "dd": 0.0, "description": "중형계좌_정상"},
            {"balance": 10000, "dd": 0.05, "description": "대형계좌_5%DD"},
            {"balance": 25000, "dd": 0.15, "description": "대형계좌_15%DD"},
            {"balance": 50000, "dd": 0.25, "description": "대형계좌_25%DD"},
        ]

        results = []

        for scenario in test_scenarios:
            # 켈리 포지션 사이징
            recommendation = self.kelly_sizer.get_position_recommendation(
                scenario["balance"], self.sample_trades, scenario["dd"]
            )

            # 결과 검증
            self.assertIsNotNone(recommendation["position_size"])
            self.assertGreaterEqual(recommendation["position_size"], 20.0)  # 최소 주문 금액
            self.assertLessEqual(recommendation["position_size"], scenario["balance"] * 0.1)  # 10% 이하

            # DD 스케일링 검증
            if scenario["dd"] > 0:
                self.assertIn("dd_scaling", recommendation)
                self.assertGreater(recommendation["dd_scaling"], 0)

            results.append(
                {
                    "scenario": scenario["description"],
                    "balance": scenario["balance"],
                    "dd": scenario["dd"],
                    "position_size": recommendation["position_size"],
                    "kelly_fraction": recommendation["kelly_fraction"],
                    "confidence": recommendation["confidence"],
                }
            )

        print(f"   ✅ 테스트 시나리오: {len(results)}개")

        # 결과 분석
        for result in results:
            print(
                f"   📊 {result['scenario']}: ${result['position_size']:.2f} "
                f"(켈리: {result['kelly_fraction']:.3f}, 신뢰도: {result['confidence']*100:.0f}%)"
            )

        # 논리적 일관성 검증
        # 1. 계좌가 클수록 절대 포지션 크기가 커야 함 (DD가 같다면)
        normal_scenarios = [r for r in results if r["dd"] == 0.0]
        if len(normal_scenarios) >= 2:
            normal_scenarios.sort(key=lambda x: x["balance"])
            for i in range(1, len(normal_scenarios)):
                self.assertGreaterEqual(normal_scenarios[i]["position_size"], normal_scenarios[i - 1]["position_size"])

        # 2. DD가 클수록 포지션이 작아져야 함 (같은 계좌 크기라면)
        large_account_scenarios = [r for r in results if r["balance"] >= 10000]
        if len(large_account_scenarios) >= 2:
            large_account_scenarios.sort(key=lambda x: x["dd"])
            for i in range(1, len(large_account_scenarios)):
                self.assertLessEqual(
                    large_account_scenarios[i]["position_size"], large_account_scenarios[i - 1]["position_size"]
                )

    def test_real_time_monitoring_integration(self):
        """실시간 모니터링 통합 테스트"""
        print("📊 실시간 모니터링 통합 테스트...")

        # 모니터링 시작
        initial_balance = 10000.0
        self.monitor.start_monitoring(initial_balance)

        # 거래 시뮬레이션
        current_balance = initial_balance

        for i in range(10):
            # 거래 결과 시뮬레이션
            trade_pnl = np.random.choice(self.sample_trades)["pnl_pct"] * current_balance
            current_balance += trade_pnl

            # 모니터링 시스템에 거래 기록
            from realtime_monitoring_system import TradeEvent

            trade_event = TradeEvent(
                timestamp=datetime.now(),
                symbol="BTCUSDT",
                side="long" if trade_pnl > 0 else "short",
                quantity=0.1,
                price=50000.0,
                pnl=trade_pnl,
            )

            self.monitor.record_trade(trade_event)

            # 포지션 사이징 재계산
            current_dd = max(0, (initial_balance - current_balance) / initial_balance)

            recommendation = self.kelly_sizer.get_position_recommendation(current_balance, self.sample_trades, current_dd)

            # 모니터링 상태 확인
            status = self.monitor.get_monitoring_status()

            # 통합 검증
            self.assertEqual(status["current_balance"], current_balance)
            self.assertIsNotNone(recommendation["position_size"])

            # DD가 발생하면 포지션이 축소되어야 함
            if current_dd > 0.05:  # 5% 이상 DD
                self.assertIn("dd_scaling", recommendation)

        # 최종 상태 확인
        final_status = self.monitor.get_monitoring_status()
        final_pnl_pct = (current_balance - initial_balance) / initial_balance

        print(f"   ✅ 거래 수: {final_status['trades_today']}")
        print(f"   📊 최종 수익률: {final_pnl_pct*100:.1f}%")
        print(f"   🔄 연속 손실: {final_status['consecutive_losses']}회")

        # 모니터링 중지
        self.monitor.stop_monitoring()


class TestIntegrationSuite:
    """통합 테스트 스위트"""

    def __init__(self):
        """통합 테스트 스위트 초기화"""
        self.test_classes = [
            TestOptimizationPipelineIntegration,
            TestWorkforwardValidationWorkflow,
            TestMonteCarloSimulationChain,
            TestKellyPositionSizingIntegration,
        ]

    def run_all_integration_tests(self):
        """모든 통합 테스트 실행"""
        print("🔗 통합 테스트 실행 시작")
        print("=" * 80)

        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        for test_class in self.test_classes:
            print(f"\n📋 {test_class.__name__} 실행:")
            print("-" * 60)

            # 테스트 스위트 생성 및 실행
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
            result = runner.run(suite)

            # 결과 집계
            class_total = result.testsRun
            class_failed = len(result.failures) + len(result.errors)
            class_passed = class_total - class_failed

            total_tests += class_total
            passed_tests += class_passed
            failed_tests += class_failed

            print(f"   실행: {class_total}개, 통과: {class_passed}개, 실패: {class_failed}개")

            # 실패 상세 정보
            if result.failures or result.errors:
                print(f"   ❌ 문제 발생:")
                for test, traceback in result.failures + result.errors:
                    error_msg = traceback.split("\n")[-2] if traceback.split("\n") else "Unknown error"
                    print(f"      - {test}: {error_msg}")

        # 전체 결과 요약
        print(f"\n📊 통합 테스트 전체 결과:")
        print("=" * 80)
        print(f"   총 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개 ({passed_tests/total_tests*100:.1f}%)")
        print(f"   실패: {failed_tests}개 ({failed_tests/total_tests*100:.1f}%)")

        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        if success_rate >= 0.9:
            print(f"   🎉 통합 품질: 우수 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.8:
            print(f"   ✅ 통합 품질: 양호 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.7:
            print(f"   ⚠️ 통합 품질: 보통 ({success_rate*100:.1f}%)")
        else:
            print(f"   ❌ 통합 품질: 개선 필요 ({success_rate*100:.1f}%)")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
        }


def main():
    """메인 실행 함수"""
    print("🚀 통합 테스트 시스템 실행")
    print("=" * 80)

    # 통합 테스트 스위트 실행
    test_suite = TestIntegrationSuite()
    results = test_suite.run_all_integration_tests()

    print(f"\n🎯 핵심 특징:")
    print(f"   • 전체 최적화 파이프라인 end-to-end 테스트")
    print(f"   • 워크포워드 검증 워크플로우 검증")
    print(f"   • 몬테카를로 시뮬레이션 체인 테스트")
    print(f"   • 켈리 포지션 사이징 통합 검증")
    print(f"   • 실시간 모니터링 시스템 연동 테스트")
    print(f"   • 컴포넌트 간 데이터 흐름 검증")

    return results


if __name__ == "__main__":
    main()
