#!/usr/bin/env python3
"""
성능 및 검증 테스트 구현
- 최적화 속도 벤치마크 테스트
- 메모리 사용량 프로파일링 테스트
- 히스토리컬 백테스트 비교 테스트
- 리스크 관리 검증 테스트
"""

import unittest
import time
import psutil
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import gc
import threading
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# 성능 테스트할 모듈들 import
from optimization_pipeline import OptimizationPipeline, PipelineConfig
from performance_evaluator import PerformanceEvaluator
from statistical_validator import StatisticalValidator
from kelly_position_sizer import KellyPositionSizer
from performance_optimizer import PerformanceOptimizer, PerformanceConfig
from realtime_monitoring_system import RealtimeMonitor, MonitoringConfig

class TestOptimizationSpeedBenchmark(unittest.TestCase):
    """최적화 속도 벤치마크 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 다양한 크기의 테스트 설정
        self.benchmark_configs = {
            'small': PipelineConfig(
                data_length=1000,
                global_search_samples=20,
                local_refinement_steps=10,
                mc_simulations=100,
                parallel_workers=2
            ),
            'medium': PipelineConfig(
                data_length=5000,
                global_search_samples=50,
                local_refinement_steps=20,
                mc_simulations=500,
                parallel_workers=4
            ),
            'large': PipelineConfig(
                data_length=10000,
                global_search_samples=100,
                local_refinement_steps=40,
                mc_simulations=1000,
                parallel_workers=4
            )
        }
        
        self.parameter_space = {
            'target_r': (2.0, 4.0),
            'stop_atr_mult': (0.05, 0.2),
            'swing_len': (3, 10),
            'rr_percentile': (0.1, 0.4)
        }
    
    def test_small_scale_optimization_speed(self):
        """소규모 최적화 속도 테스트"""
        print("⚡ 소규모 최적화 속도 벤치마크...")
        
        config = self.benchmark_configs['small']
        pipeline = OptimizationPipeline(config)
        
        # 속도 측정
        start_time = time.time()
        result = pipeline.run_pipeline(self.parameter_space)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 성능 기준 (소규모: 30초 이내)
        target_time = 30.0
        
        print(f"   ⏱️ 실행 시간: {execution_time:.1f}초 (목표: {target_time}초)")
        print(f"   📊 데이터 크기: {config.data_length:,}개")
        print(f"   🔍 탐색 샘플: {config.global_search_samples}개")
        
        # 성능 검증
        self.assertLess(execution_time, target_time * 1.5)  # 50% 여유
        
        # 처리 속도 계산 (샘플/초)
        processing_speed = config.global_search_samples / execution_time
        print(f"   🚀 처리 속도: {processing_speed:.1f} 샘플/초")
        
        # 최소 처리 속도 검증
        self.assertGreater(processing_speed, 0.5)  # 최소 0.5 샘플/초
    
    def test_medium_scale_optimization_speed(self):
        """중규모 최적화 속도 테스트"""
        print("⚡ 중규모 최적화 속도 벤치마크...")
        
        config = self.benchmark_configs['medium']
        pipeline = OptimizationPipeline(config)
        
        # 속도 측정
        start_time = time.time()
        result = pipeline.run_pipeline(self.parameter_space)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 성능 기준 (중규모: 2분 이내)
        target_time = 120.0
        
        print(f"   ⏱️ 실행 시간: {execution_time:.1f}초 (목표: {target_time}초)")
        print(f"   📊 데이터 크기: {config.data_length:,}개")
        print(f"   🔍 탐색 샘플: {config.global_search_samples}개")
        
        # 성능 검증 (더 관대한 기준)
        self.assertLess(execution_time, target_time * 2.0)  # 100% 여유
        
        # 처리 속도 계산
        processing_speed = config.global_search_samples / execution_time
        print(f"   🚀 처리 속도: {processing_speed:.1f} 샘플/초")
    
    def test_parallel_processing_efficiency(self):
        """병렬 처리 효율성 테스트"""
        print("🔄 병렬 처리 효율성 테스트...")
        
        # 단일 스레드 vs 멀티 스레드 비교
        base_config = self.benchmark_configs['small']
        
        # 단일 스레드 설정
        single_config = PipelineConfig(
            data_length=base_config.data_length,
            global_search_samples=base_config.global_search_samples,
            local_refinement_steps=base_config.local_refinement_steps,
            mc_simulations=base_config.mc_simulations,
            parallel_workers=1
        )
        
        # 멀티 스레드 설정
        multi_config = PipelineConfig(
            data_length=base_config.data_length,
            global_search_samples=base_config.global_search_samples,
            local_refinement_steps=base_config.local_refinement_steps,
            mc_simulations=base_config.mc_simulations,
            parallel_workers=4
        )
        
        # 단일 스레드 실행
        single_pipeline = OptimizationPipeline(single_config)
        start_time = time.time()
        single_result = single_pipeline.run_pipeline(self.parameter_space)
        single_time = time.time() - start_time
        
        # 멀티 스레드 실행
        multi_pipeline = OptimizationPipeline(multi_config)
        start_time = time.time()
        multi_result = multi_pipeline.run_pipeline(self.parameter_space)
        multi_time = time.time() - start_time
        
        # 효율성 계산
        speedup = single_time / multi_time if multi_time > 0 else 1.0
        efficiency = speedup / multi_config.parallel_workers
        
        print(f"   🔧 단일 스레드: {single_time:.1f}초")
        print(f"   ⚡ 멀티 스레드: {multi_time:.1f}초 ({multi_config.parallel_workers}개 워커)")
        print(f"   📈 속도 향상: {speedup:.2f}x")
        print(f"   📊 효율성: {efficiency*100:.1f}%")
        
        # 병렬 처리가 도움이 되어야 함 (최소 20% 향상)
        self.assertGreater(speedup, 1.2)
        
        # 효율성이 너무 낮지 않아야 함 (최소 30%)
        self.assertGreater(efficiency, 0.3)
    
    def test_scalability_analysis(self):
        """확장성 분석 테스트"""
        print("📈 확장성 분석 테스트...")
        
        # 다양한 데이터 크기에서 성능 측정
        data_sizes = [500, 1000, 2000, 5000]
        performance_results = []
        
        for data_size in data_sizes:
            config = PipelineConfig(
                data_length=data_size,
                global_search_samples=20,  # 고정
                local_refinement_steps=10,  # 고정
                mc_simulations=100,  # 고정
                parallel_workers=2
            )
            
            pipeline = OptimizationPipeline(config)
            
            # 실행 시간 측정
            start_time = time.time()
            result = pipeline.run_pipeline(self.parameter_space)
            execution_time = time.time() - start_time
            
            # 데이터 포인트당 처리 시간
            time_per_datapoint = execution_time / data_size
            
            performance_results.append({
                'data_size': data_size,
                'execution_time': execution_time,
                'time_per_datapoint': time_per_datapoint
            })
            
            print(f"   📊 데이터 크기 {data_size:,}: {execution_time:.1f}초 "
                  f"({time_per_datapoint*1000:.2f}ms/포인트)")
        
        # 확장성 분석
        # 시간 복잡도가 선형에 가까워야 함
        if len(performance_results) >= 2:
            first_result = performance_results[0]
            last_result = performance_results[-1]
            
            size_ratio = last_result['data_size'] / first_result['data_size']
            time_ratio = last_result['execution_time'] / first_result['execution_time']
            
            complexity_factor = time_ratio / size_ratio
            
            print(f"   📈 크기 비율: {size_ratio:.1f}x")
            print(f"   ⏱️ 시간 비율: {time_ratio:.1f}x")
            print(f"   🔍 복잡도 계수: {complexity_factor:.2f}")
            
            # 복잡도가 너무 높지 않아야 함 (3배 이하)
            self.assertLess(complexity_factor, 3.0)

class TestMemoryUsageProfiling(unittest.TestCase):
    """메모리 사용량 프로파일링 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.performance_optimizer = PerformanceOptimizer(
            PerformanceConfig(max_memory_usage_gb=2.0)
        )
        self.performance_optimizer.start_optimization()
    
    def tearDown(self):
        """테스트 정리"""
        self.performance_optimizer.stop_optimization()
    
    def test_memory_usage_during_optimization(self):
        """최적화 중 메모리 사용량 테스트"""
        print("🧠 최적화 중 메모리 사용량 프로파일링...")
        
        # 초기 메모리 상태
        initial_memory = psutil.virtual_memory()
        process = psutil.Process()
        initial_process_memory = process.memory_info().rss / (1024**3)  # GB
        
        print(f"   📊 초기 시스템 메모리: {initial_memory.available/(1024**3):.1f}GB 사용 가능")
        print(f"   🔍 초기 프로세스 메모리: {initial_process_memory:.2f}GB")
        
        # 메모리 사용량 추적
        memory_samples = []
        
        def memory_monitor():
            for _ in range(20):  # 20초간 모니터링
                current_memory = psutil.virtual_memory()
                current_process_memory = process.memory_info().rss / (1024**3)
                
                memory_samples.append({
                    'timestamp': time.time(),
                    'system_available_gb': current_memory.available / (1024**3),
                    'process_memory_gb': current_process_memory,
                    'system_usage_pct': current_memory.percent
                })
                
                time.sleep(1)
        
        # 메모리 모니터링 스레드 시작
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()
        
        # 최적화 실행
        config = PipelineConfig(
            data_length=5000,
            global_search_samples=30,
            mc_simulations=200,
            parallel_workers=2
        )
        
        pipeline = OptimizationPipeline(config)
        parameter_space = {
            'target_r': (2.0, 4.0),
            'stop_atr_mult': (0.05, 0.2)
        }
        
        result = pipeline.run_pipeline(parameter_space)
        
        # 모니터링 완료 대기
        monitor_thread.join(timeout=25)
        
        # 메모리 사용량 분석
        if memory_samples:
            max_process_memory = max(sample['process_memory_gb'] for sample in memory_samples)
            avg_process_memory = np.mean([sample['process_memory_gb'] for sample in memory_samples])
            memory_growth = max_process_memory - initial_process_memory
            
            print(f"   📈 최대 프로세스 메모리: {max_process_memory:.2f}GB")
            print(f"   📊 평균 프로세스 메모리: {avg_process_memory:.2f}GB")
            print(f"   📏 메모리 증가량: {memory_growth:.2f}GB")
            
            # 메모리 사용량 검증
            self.assertLess(max_process_memory, 4.0)  # 4GB 이하
            self.assertLess(memory_growth, 2.0)       # 증가량 2GB 이하
            
            # 메모리 누수 체크 (마지막 10% 샘플의 평균이 처음 10%보다 크게 높지 않아야 함)
            if len(memory_samples) >= 10:
                early_samples = memory_samples[:len(memory_samples)//10]
                late_samples = memory_samples[-len(memory_samples)//10:]
                
                early_avg = np.mean([s['process_memory_gb'] for s in early_samples])
                late_avg = np.mean([s['process_memory_gb'] for s in late_samples])
                
                memory_leak_ratio = late_avg / early_avg if early_avg > 0 else 1.0
                
                print(f"   🔍 메모리 누수 비율: {memory_leak_ratio:.2f}")
                
                # 메모리 누수가 심하지 않아야 함 (50% 이하 증가)
                self.assertLess(memory_leak_ratio, 1.5)
    
    def test_cache_memory_management(self):
        """캐시 메모리 관리 테스트"""
        print("💾 캐시 메모리 관리 테스트...")
        
        memory_manager = self.performance_optimizer.memory_manager
        
        # 초기 캐시 상태
        initial_cache_stats = memory_manager.get_cache_stats()
        print(f"   📊 초기 캐시: {initial_cache_stats['cache_entries']}개 항목")
        
        # 대량 데이터 캐시
        large_data_items = []
        
        for i in range(50):
            # 큰 데이터 생성 (각각 ~10MB)
            large_data = np.random.random((1000, 1000))
            cache_key = f"large_data_{i}"
            
            memory_manager.cache_set(cache_key, large_data)
            large_data_items.append(cache_key)
            
            # 캐시 상태 확인
            cache_stats = memory_manager.get_cache_stats()
            
            if i % 10 == 0:
                print(f"   📈 {i+1}개 항목 후: {cache_stats['cache_size_mb']:.1f}MB")
        
        # 최종 캐시 상태
        final_cache_stats = memory_manager.get_cache_stats()
        
        print(f"   📊 최종 캐시: {final_cache_stats['cache_entries']}개 항목")
        print(f"   💾 최종 크기: {final_cache_stats['cache_size_mb']:.1f}MB")
        
        # 캐시 크기 제한 검증
        max_cache_size = self.performance_optimizer.config.cache_size_mb
        self.assertLessEqual(final_cache_stats['cache_size_mb'], max_cache_size * 1.2)  # 20% 여유
        
        # 캐시 정리 테스트
        memory_manager.cleanup_memory()
        
        after_cleanup_stats = memory_manager.get_cache_stats()
        print(f"   🧹 정리 후: {after_cleanup_stats['cache_entries']}개 항목, "
              f"{after_cleanup_stats['cache_size_mb']:.1f}MB")
        
        # 정리 후 크기가 줄어들어야 함
        self.assertLessEqual(after_cleanup_stats['cache_size_mb'], 
                           final_cache_stats['cache_size_mb'])
    
    def test_garbage_collection_efficiency(self):
        """가비지 컬렉션 효율성 테스트"""
        print("🗑️ 가비지 컬렉션 효율성 테스트...")
        
        # 초기 메모리 상태
        gc.collect()  # 초기 정리
        initial_objects = len(gc.get_objects())
        
        # 대량 객체 생성
        temp_objects = []
        
        for i in range(1000):
            # 다양한 크기의 객체 생성
            obj = {
                'data': np.random.random(100),
                'metadata': {'id': i, 'timestamp': datetime.now()},
                'nested': [np.random.random(10) for _ in range(10)]
            }
            temp_objects.append(obj)
        
        after_creation_objects = len(gc.get_objects())
        
        # 객체 참조 해제
        temp_objects.clear()
        del temp_objects
        
        # 가비지 컬렉션 실행
        collected_count = gc.collect()
        
        after_gc_objects = len(gc.get_objects())
        
        print(f"   📊 초기 객체 수: {initial_objects:,}")
        print(f"   📈 생성 후 객체 수: {after_creation_objects:,}")
        print(f"   🗑️ 수집된 객체 수: {collected_count:,}")
        print(f"   📉 정리 후 객체 수: {after_gc_objects:,}")
        
        # 가비지 컬렉션 효율성 검증
        objects_created = after_creation_objects - initial_objects
        objects_remaining = after_gc_objects - initial_objects
        
        cleanup_efficiency = 1 - (objects_remaining / objects_created) if objects_created > 0 else 1
        
        print(f"   📊 정리 효율성: {cleanup_efficiency*100:.1f}%")
        
        # 최소 50% 이상 정리되어야 함
        self.assertGreater(cleanup_efficiency, 0.5)

class TestHistoricalBacktestComparison(unittest.TestCase):
    """히스토리컬 백테스트 비교 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.performance_evaluator = PerformanceEvaluator()
        
        # 테스트용 히스토리컬 데이터 생성
        np.random.seed(42)
        self.historical_data = self._generate_historical_data()
        
        # 알려진 좋은 파라미터 (기준점)
        self.benchmark_parameters = {
            'target_r': 3.0,
            'stop_atr_mult': 0.1,
            'swing_len': 5,
            'rr_percentile': 0.25
        }
    
    def _generate_historical_data(self) -> pd.DataFrame:
        """히스토리컬 데이터 생성"""
        # 3년간의 시간별 데이터
        dates = pd.date_range(start='2021-01-01', end='2023-12-31', freq='1H')
        
        # 현실적인 가격 움직임 시뮬레이션
        returns = np.random.normal(0, 0.002, len(dates))  # 0.2% 시간당 변동성
        
        # 트렌드와 변동성 체제 추가
        trend_changes = np.random.choice([0, 1], size=len(dates), p=[0.99, 0.01])
        volatility_regime = np.random.choice([0.5, 1.0, 2.0], size=len(dates), p=[0.7, 0.2, 0.1])
        
        returns = returns * volatility_regime
        
        # 가격 계산
        prices = 50000 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.001, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.001, len(dates)))),
            'close': prices,
            'volume': np.random.uniform(100, 1000, len(dates))
        })
    
    def test_parameter_sensitivity_analysis(self):
        """파라미터 민감도 분석 테스트"""
        print("🎛️ 파라미터 민감도 분석 테스트...")
        
        # 기준 파라미터로 백테스트
        baseline_trades = self._simulate_backtest(self.benchmark_parameters)
        baseline_metrics = self.performance_evaluator.calculate_metrics(baseline_trades)
        baseline_score = self.performance_evaluator.calculate_composite_score(baseline_metrics)
        
        print(f"   📊 기준 점수: {baseline_score:.4f}")
        print(f"   📈 기준 PF: {baseline_metrics.profit_factor:.2f}")
        
        # 각 파라미터별 민감도 테스트
        sensitivity_results = {}
        
        for param_name, base_value in self.benchmark_parameters.items():
            param_scores = []
            
            # 파라미터 값 변화 (-20%, -10%, 0%, +10%, +20%)
            variations = [-0.2, -0.1, 0.0, 0.1, 0.2]
            
            for variation in variations:
                test_params = self.benchmark_parameters.copy()
                
                if isinstance(base_value, (int, float)):
                    test_params[param_name] = base_value * (1 + variation)
                
                # 백테스트 실행
                test_trades = self._simulate_backtest(test_params)
                test_metrics = self.performance_evaluator.calculate_metrics(test_trades)
                test_score = self.performance_evaluator.calculate_composite_score(test_metrics)
                
                param_scores.append(test_score)
            
            # 민감도 계산 (점수 변화의 표준편차)
            sensitivity = np.std(param_scores)
            sensitivity_results[param_name] = {
                'sensitivity': sensitivity,
                'scores': param_scores,
                'variations': variations
            }
            
            print(f"   🎛️ {param_name} 민감도: {sensitivity:.4f}")
        
        # 가장 민감한 파라미터 식별
        most_sensitive = max(sensitivity_results.keys(), 
                           key=lambda k: sensitivity_results[k]['sensitivity'])
        
        print(f"   🔍 가장 민감한 파라미터: {most_sensitive}")
        
        # 민감도가 합리적 범위에 있는지 확인
        for param_name, result in sensitivity_results.items():
            self.assertGreater(result['sensitivity'], 0.001)  # 최소 민감도
            self.assertLess(result['sensitivity'], 1.0)       # 최대 민감도
    
    def test_regime_performance_consistency(self):
        """레짐별 성능 일관성 테스트"""
        print("📊 레짐별 성능 일관성 테스트...")
        
        # 데이터를 변동성 레짐별로 분할
        returns = self.historical_data['close'].pct_change().dropna()
        
        # 롤링 변동성 계산 (30일 윈도우)
        rolling_vol = returns.rolling(30*24).std()  # 30일 * 24시간
        
        # 변동성 레짐 분류
        vol_quantiles = rolling_vol.quantile([0.33, 0.67])
        
        low_vol_mask = rolling_vol <= vol_quantiles.iloc[0]
        high_vol_mask = rolling_vol >= vol_quantiles.iloc[1]
        medium_vol_mask = ~(low_vol_mask | high_vol_mask)
        
        regimes = {
            'low_volatility': self.historical_data[low_vol_mask],
            'medium_volatility': self.historical_data[medium_vol_mask],
            'high_volatility': self.historical_data[high_vol_mask]
        }
        
        regime_results = {}
        
        for regime_name, regime_data in regimes.items():
            if len(regime_data) < 100:  # 최소 데이터 요구량
                continue
            
            # 레짐별 백테스트
            regime_trades = self._simulate_backtest_on_data(
                self.benchmark_parameters, regime_data
            )
            
            if regime_trades:
                regime_metrics = self.performance_evaluator.calculate_metrics(regime_trades)
                regime_score = self.performance_evaluator.calculate_composite_score(regime_metrics)
                
                regime_results[regime_name] = {
                    'score': regime_score,
                    'profit_factor': regime_metrics.profit_factor,
                    'win_rate': regime_metrics.win_rate,
                    'trade_count': len(regime_trades)
                }
                
                print(f"   📊 {regime_name}: 점수={regime_score:.4f}, "
                      f"PF={regime_metrics.profit_factor:.2f}, "
                      f"거래수={len(regime_trades)}")
        
        # 레짐 간 성능 일관성 검증
        if len(regime_results) >= 2:
            scores = [result['score'] for result in regime_results.values()]
            score_std = np.std(scores)
            score_mean = np.mean(scores)
            
            consistency_ratio = 1 - (score_std / abs(score_mean)) if score_mean != 0 else 0
            
            print(f"   📈 레짐 간 일관성: {consistency_ratio*100:.1f}%")
            
            # 최소 일관성 요구 (50% 이상)
            self.assertGreater(consistency_ratio, 0.5)
    
    def test_out_of_sample_degradation(self):
        """표본 외 성능 저하 테스트"""
        print("📉 표본 외 성능 저하 테스트...")
        
        # 데이터를 훈련/테스트로 분할 (70%/30%)
        split_point = int(len(self.historical_data) * 0.7)
        
        train_data = self.historical_data[:split_point]
        test_data = self.historical_data[split_point:]
        
        # 훈련 데이터에서 백테스트
        train_trades = self._simulate_backtest_on_data(self.benchmark_parameters, train_data)
        train_metrics = self.performance_evaluator.calculate_metrics(train_trades)
        train_score = self.performance_evaluator.calculate_composite_score(train_metrics)
        
        # 테스트 데이터에서 백테스트
        test_trades = self._simulate_backtest_on_data(self.benchmark_parameters, test_data)
        test_metrics = self.performance_evaluator.calculate_metrics(test_trades)
        test_score = self.performance_evaluator.calculate_composite_score(test_metrics)
        
        # 성능 저하 계산
        performance_degradation = (train_score - test_score) / abs(train_score) if train_score != 0 else 0
        
        print(f"   📊 훈련 점수: {train_score:.4f}")
        print(f"   📉 테스트 점수: {test_score:.4f}")
        print(f"   📈 성능 저하: {performance_degradation*100:.1f}%")
        
        # 성능 저하가 너무 크지 않아야 함 (50% 이하)
        self.assertLess(performance_degradation, 0.5)
        
        # 테스트 성능이 최소 기준을 만족해야 함
        self.assertGreater(test_score, -1.0)  # 최소 점수
    
    def _simulate_backtest(self, parameters: Dict) -> List[Dict]:
        """파라미터로 백테스트 시뮬레이션"""
        return self._simulate_backtest_on_data(parameters, self.historical_data)
    
    def _simulate_backtest_on_data(self, parameters: Dict, data: pd.DataFrame) -> List[Dict]:
        """특정 데이터에서 백테스트 시뮬레이션"""
        trades = []
        
        # 간단한 백테스트 시뮬레이션
        for i in range(100, len(data) - 100, 50):  # 50바마다 거래 기회
            
            # 파라미터 기반 거래 신호 생성 (단순화)
            target_r = parameters.get('target_r', 3.0)
            stop_atr_mult = parameters.get('stop_atr_mult', 0.1)
            
            # 가상의 거래 결과 생성
            if np.random.random() < 0.6:  # 60% 승률
                pnl_pct = np.random.normal(0.02, 0.01)  # 평균 2% 수익
            else:
                pnl_pct = np.random.normal(-0.01, 0.005)  # 평균 1% 손실
            
            # 파라미터 영향 반영
            pnl_pct *= (target_r / 3.0)  # target_r 영향
            pnl_pct *= (1 - stop_atr_mult * 5)  # stop_atr_mult 영향
            
            trades.append({
                'entry_time': data.iloc[i]['timestamp'],
                'exit_time': data.iloc[i+10]['timestamp'],
                'pnl': pnl_pct * 10000,  # $10,000 기준
                'pnl_pct': pnl_pct,
                'quantity': 1.0,
                'side': 'long'
            })
        
        return trades

class TestRiskManagementValidation(unittest.TestCase):
    """리스크 관리 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.kelly_sizer = KellyPositionSizer()
        self.monitor = RealtimeMonitor(MonitoringConfig(
            daily_loss_limit_pct=0.05,
            max_consecutive_losses=5
        ))
        
        # 테스트용 거래 데이터
        np.random.seed(42)
        self.test_trades = self._generate_test_trades()
    
    def _generate_test_trades(self) -> List[Dict]:
        """테스트용 거래 데이터 생성"""
        trades = []
        
        for i in range(200):
            # 다양한 시나리오 포함
            if i < 50:
                # 초기: 좋은 성과
                win_prob = 0.7
                avg_win = 0.025
                avg_loss = 0.012
            elif i < 100:
                # 중간: 보통 성과
                win_prob = 0.6
                avg_win = 0.02
                avg_loss = 0.015
            elif i < 150:
                # 후반: 나쁜 성과 (DD 발생)
                win_prob = 0.4
                avg_win = 0.015
                avg_loss = 0.02
            else:
                # 회복: 다시 좋은 성과
                win_prob = 0.65
                avg_win = 0.022
                avg_loss = 0.013
            
            if np.random.random() < win_prob:
                pnl_pct = np.random.normal(avg_win, avg_win * 0.3)
            else:
                pnl_pct = np.random.normal(-avg_loss, avg_loss * 0.3)
            
            trades.append({
                'timestamp': datetime.now() - timedelta(days=200-i),
                'pnl_pct': pnl_pct,
                'win': pnl_pct > 0
            })
        
        return trades
    
    def test_position_sizing_risk_limits(self):
        """포지션 사이징 리스크 한도 테스트"""
        print("⚖️ 포지션 사이징 리스크 한도 테스트...")
        
        # 다양한 계좌 크기에서 리스크 한도 검증
        test_balances = [500, 1000, 5000, 10000, 25000, 50000]
        
        for balance in test_balances:
            recommendation = self.kelly_sizer.get_position_recommendation(
                balance, self.test_trades, current_dd=0.0
            )
            
            # 리스크 비율 계산
            risk_ratio = recommendation['risk_amount'] / balance
            
            print(f"   💰 잔고 ${balance:,}: 포지션 ${recommendation['position_size']:.2f}, "
                  f"리스크 {risk_ratio*100:.1f}%")
            
            # 리스크 한도 검증 (최대 5%)
            self.assertLessEqual(risk_ratio, 0.05)
            
            # 최소 주문 금액 검증
            self.assertGreaterEqual(recommendation['position_size'], 20.0)
            
            # 포지션이 계좌 크기를 초과하지 않음
            self.assertLessEqual(recommendation['position_size'], balance)
    
    def test_drawdown_scaling_effectiveness(self):
        """드로우다운 스케일링 효과성 테스트"""
        print("📉 드로우다운 스케일링 효과성 테스트...")
        
        balance = 10000.0
        dd_levels = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        
        position_sizes = []
        
        for dd_level in dd_levels:
            recommendation = self.kelly_sizer.get_position_recommendation(
                balance, self.test_trades, current_dd=dd_level
            )
            
            position_sizes.append(recommendation['position_size'])
            
            print(f"   📊 DD {dd_level*100:3.0f}%: 포지션 ${recommendation['position_size']:6.2f}")
        
        # DD가 증가할수록 포지션이 감소해야 함
        for i in range(1, len(position_sizes)):
            self.assertLessEqual(position_sizes[i], position_sizes[i-1] * 1.01)  # 1% 오차 허용
        
        # 최대 DD에서도 최소 포지션은 유지
        self.assertGreaterEqual(position_sizes[-1], 20.0)  # 최소 주문 금액
        
        # 스케일링 효과 계산
        max_scaling = (position_sizes[0] - position_sizes[-1]) / position_sizes[0]
        print(f"   📈 최대 스케일링: {max_scaling*100:.1f}%")
        
        # 적절한 스케일링이 적용되어야 함 (20% 이상)
        self.assertGreater(max_scaling, 0.2)
    
    def test_consecutive_loss_protection(self):
        """연속 손실 보호 테스트"""
        print("🛡️ 연속 손실 보호 테스트...")
        
        self.monitor.start_monitoring(10000.0)
        
        # 연속 손실 시뮬레이션
        consecutive_losses = 0
        max_consecutive = 0
        
        for i, trade in enumerate(self.test_trades):
            if not trade['win']:
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0
            
            # 거래 기록
            from realtime_monitoring_system import TradeEvent
            
            trade_event = TradeEvent(
                timestamp=trade['timestamp'],
                symbol='BTCUSDT',
                side='long',
                quantity=0.1,
                price=50000.0,
                pnl=trade['pnl_pct'] * 10000
            )
            
            self.monitor.record_trade(trade_event)
            
            # 상태 확인
            status = self.monitor.get_monitoring_status()
            
            # 연속 손실 한도 확인
            if status['consecutive_losses'] >= 5:  # 설정된 한도
                print(f"   🚨 연속 손실 한도 도달: {status['consecutive_losses']}회")
                break
        
        print(f"   📊 최대 연속 손실: {max_consecutive}회")
        print(f"   🛡️ 모니터링 상태: {self.monitor.trading_state.value}")
        
        # 연속 손실 보호가 작동해야 함
        final_status = self.monitor.get_monitoring_status()
        if max_consecutive >= 5:
            self.assertNotEqual(final_status['trading_state'], 'active')
        
        self.monitor.stop_monitoring()
    
    def test_daily_loss_limit_enforcement(self):
        """일일 손실 한도 시행 테스트"""
        print("📅 일일 손실 한도 시행 테스트...")
        
        initial_balance = 10000.0
        daily_loss_limit = 0.05  # 5%
        
        self.monitor.start_monitoring(initial_balance)
        
        # 큰 손실 시뮬레이션
        cumulative_loss = 0.0
        
        for i in range(20):
            # 각각 1% 손실
            loss_amount = initial_balance * 0.01
            cumulative_loss += loss_amount
            
            new_balance = initial_balance - cumulative_loss
            self.monitor.update_balance(new_balance)
            
            status = self.monitor.get_monitoring_status()
            daily_loss_pct = abs(status['daily_pnl_pct'])
            
            print(f"   📉 손실 {i+1}: {daily_loss_pct*100:.1f}% "
                  f"(상태: {status['trading_state']})")
            
            # 손실 한도 도달 시 거래 중지 확인
            if daily_loss_pct >= daily_loss_limit:
                self.assertEqual(status['trading_state'], 'stopped')
                print(f"   🛑 일일 손실 한도 도달로 거래 중지")
                break
        
        self.monitor.stop_monitoring()
    
    def test_risk_metrics_calculation_accuracy(self):
        """리스크 지표 계산 정확성 테스트"""
        print("📊 리스크 지표 계산 정확성 테스트...")
        
        # 알려진 결과를 가진 테스트 데이터
        known_trades = [
            {'pnl_pct': 0.02, 'win': True},   # 2% 수익
            {'pnl_pct': -0.01, 'win': False}, # 1% 손실
            {'pnl_pct': 0.03, 'win': True},   # 3% 수익
            {'pnl_pct': -0.015, 'win': False}, # 1.5% 손실
            {'pnl_pct': 0.025, 'win': True},  # 2.5% 수익
        ]
        
        # 예상 결과 계산
        expected_win_rate = 3/5  # 60%
        expected_avg_win = (0.02 + 0.03 + 0.025) / 3  # 2.5%
        expected_avg_loss = (0.01 + 0.015) / 2  # 1.25%
        expected_profit_factor = (0.02 + 0.03 + 0.025) / (0.01 + 0.015)  # 3.0
        
        # 켈리 계산
        trade_stats = self.kelly_sizer.calculate_trade_statistics(known_trades)
        
        print(f"   📊 계산된 승률: {trade_stats.win_rate:.3f} (예상: {expected_win_rate:.3f})")
        print(f"   📈 계산된 평균 수익: {trade_stats.avg_win:.4f} (예상: {expected_avg_win:.4f})")
        print(f"   📉 계산된 평균 손실: {trade_stats.avg_loss:.4f} (예상: {expected_avg_loss:.4f})")
        print(f"   💰 계산된 PF: {trade_stats.profit_factor:.2f} (예상: {expected_profit_factor:.2f})")
        
        # 정확성 검증 (1% 오차 허용)
        self.assertAlmostEqual(trade_stats.win_rate, expected_win_rate, delta=0.01)
        self.assertAlmostEqual(trade_stats.avg_win, expected_avg_win, delta=0.001)
        self.assertAlmostEqual(trade_stats.avg_loss, expected_avg_loss, delta=0.001)
        self.assertAlmostEqual(trade_stats.profit_factor, expected_profit_factor, delta=0.1)

class TestPerformanceValidationSuite:
    """성능 및 검증 테스트 스위트"""
    
    def __init__(self):
        """테스트 스위트 초기화"""
        self.test_classes = [
            TestOptimizationSpeedBenchmark,
            TestMemoryUsageProfiling,
            TestHistoricalBacktestComparison,
            TestRiskManagementValidation
        ]
    
    def run_all_performance_tests(self):
        """모든 성능 테스트 실행"""
        print("⚡ 성능 및 검증 테스트 실행 시작")
        print("="*80)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for test_class in self.test_classes:
            print(f"\n📋 {test_class.__name__} 실행:")
            print("-" * 60)
            
            # 테스트 스위트 생성 및 실행
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
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
            
            # 실패 상세 정보
            if result.failures or result.errors:
                print(f"   ❌ 문제 발생:")
                for test, traceback in result.failures + result.errors:
                    error_lines = traceback.strip().split('\n')
                    error_msg = error_lines[-1] if error_lines else "Unknown error"
                    print(f"      - {test}: {error_msg}")
        
        # 전체 결과 요약
        print(f"\n📊 성능 테스트 전체 결과:")
        print("="*80)
        print(f"   총 테스트: {total_tests}개")
        print(f"   통과: {passed_tests}개 ({passed_tests/total_tests*100:.1f}%)")
        print(f"   실패: {failed_tests}개 ({failed_tests/total_tests*100:.1f}%)")
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        if success_rate >= 0.9:
            print(f"   🎉 성능 품질: 우수 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.8:
            print(f"   ✅ 성능 품질: 양호 ({success_rate*100:.1f}%)")
        elif success_rate >= 0.7:
            print(f"   ⚠️ 성능 품질: 보통 ({success_rate*100:.1f}%)")
        else:
            print(f"   ❌ 성능 품질: 개선 필요 ({success_rate*100:.1f}%)")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate
        }

def main():
    """메인 실행 함수"""
    print("🚀 성능 및 검증 테스트 시스템 실행")
    print("="*80)
    
    # 성능 테스트 스위트 실행
    test_suite = TestPerformanceValidationSuite()
    results = test_suite.run_all_performance_tests()
    
    print(f"\n🎯 핵심 특징:")
    print(f"   • 최적화 속도 벤치마크 및 확장성 분석")
    print(f"   • 메모리 사용량 프로파일링 및 누수 감지")
    print(f"   • 히스토리컬 백테스트 비교 및 민감도 분석")
    print(f"   • 리스크 관리 시스템 검증")
    print(f"   • 성능 저하 및 레짐 일관성 테스트")
    print(f"   • 실시간 모니터링 효과성 검증")
    
    return results

if __name__ == "__main__":
    main()