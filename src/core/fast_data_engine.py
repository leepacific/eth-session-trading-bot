#!/usr/bin/env python3
"""
고속 데이터 엔진
- Parquet columnar storage with float32 downcasting
- Pre-computed indicators cached as ndarray
- Event-driven backtesting with incremental state updates
- Numpy vectorization + Numba JIT compilation
"""

import os
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from numba import njit, prange
import psutil
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")

# Ray for parallel processing (Windows에서 지원되지 않음)
RAY_AVAILABLE = False

# Joblib as fallback
try:
    from joblib import Parallel, delayed

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("⚠️ Joblib not available, using single-threaded processing")


class FastDataEngine:
    def __init__(self, cache_dir: str = "data_cache"):
        """고속 데이터 엔진 초기화"""
        self.cache_dir = cache_dir
        self.setup_environment()
        self.setup_cache_directory()

        # 메모리 및 CPU 설정
        self.setup_resource_limits()

        # 캐시된 데이터
        self.cached_data = {}
        self.cached_indicators = {}

        print("🚀 고속 데이터 엔진 초기화 완료")
        print(f"   캐시 디렉토리: {self.cache_dir}")
        print(f"   CPU 코어: {self.max_workers}개")
        print(f"   메모리 제한: {self.max_memory_gb:.1f}GB")

    def setup_environment(self):
        """환경 설정 - MKL 스레딩 제어"""
        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["NUMEXPR_NUM_THREADS"] = "1"
        os.environ["OMP_NUM_THREADS"] = "1"

        # Ray는 Windows에서 지원되지 않으므로 joblib 사용
        print("✅ Joblib 병렬 처리 준비 완료")

    def setup_cache_directory(self):
        """캐시 디렉토리 설정"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            print(f"📁 캐시 디렉토리 생성: {self.cache_dir}")

    def setup_resource_limits(self):
        """리소스 제한 설정"""
        # CPU 제한 (물리 코어 기준)
        total_cpus = psutil.cpu_count(logical=False)
        self.max_workers = max(1, total_cpus)

        # 메모리 제한 (70%)
        total_memory = psutil.virtual_memory().total
        self.max_memory = int(total_memory * 0.7)
        self.max_memory_gb = self.max_memory / (1024**3)

        # 배치 크기 계산 (메모리 기반)
        estimated_memory_per_batch = 100 * 1024 * 1024  # 100MB per batch
        self.max_batch_size = max(1024, self.max_memory // estimated_memory_per_batch)

    def load_data(self, file_path: str, symbol: str = "ETHUSDT", timeframe: str = "15m") -> pd.DataFrame:
        """데이터 로드 및 Parquet 캐시"""
        cache_key = f"{symbol}_{timeframe}"
        parquet_path = os.path.join(self.cache_dir, f"{cache_key}.parquet")

        # 캐시된 Parquet 파일 확인
        if os.path.exists(parquet_path):
            print(f"📦 캐시된 데이터 로드: {parquet_path}")
            df = pd.read_parquet(parquet_path)
        else:
            print(f"📊 원본 데이터 로드 및 캐시 생성: {file_path}")
            df = pd.read_csv(file_path)

            # 데이터 타입 최적화
            df = self._optimize_dtypes(df)

            # Parquet으로 저장
            df.to_parquet(parquet_path, compression="snappy", index=False)
            print(f"💾 Parquet 캐시 저장: {parquet_path}")

        # 시간 컬럼 처리
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])

        # 정렬 및 인덱스 리셋
        df = df.sort_values("time").reset_index(drop=True)

        # 메모리 캐시
        self.cached_data[cache_key] = df

        print(f"✅ 데이터 로드 완료: {len(df):,}개 행")
        return df

    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 타입 최적화 - float32 다운캐스팅"""
        print("🔧 데이터 타입 최적화 중...")

        # OHLCV 컬럼을 float32로 변환
        float_columns = ["open", "high", "low", "close", "volume"]
        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(np.float32)

        # 메모리 사용량 출력
        memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024
        print(f"   메모리 사용량: {memory_usage:.1f}MB")

        return df

    def cache_indicators(self, df: pd.DataFrame, params: Dict) -> Dict[str, np.ndarray]:
        """지표 사전계산 및 ndarray 캐시"""
        print("⚡ 지표 사전계산 중...")

        # 기본 배열 추출
        high = df["high"].values.astype(np.float32)
        low = df["low"].values.astype(np.float32)
        close = df["close"].values.astype(np.float32)
        open_price = df["open"].values.astype(np.float32)
        volume = df["volume"].values.astype(np.float32)

        # 시간 정보
        time_values = df["time"].values
        hours = pd.to_datetime(time_values).hour.values.astype(np.int8)
        minutes = pd.to_datetime(time_values).minute.values.astype(np.int8)
        weekdays = pd.to_datetime(time_values).weekday.values.astype(np.int8)

        # Numba JIT 컴파일된 지표 계산
        indicators = {}

        # ATR 계산
        atr_len = params.get("atr_len", 41)
        indicators["atr"] = self._calculate_atr_numba(high, low, close, atr_len)

        # True Range
        indicators["tr"] = self._calculate_tr_numba(high, low, close)

        # 스윙 포인트
        swing_len = params.get("swing_len", 3)
        swing_highs, swing_lows = self._find_swing_points_numba(high, low, swing_len)
        indicators["swing_high"] = swing_highs
        indicators["swing_low"] = swing_lows

        # 세션 구분
        indicators["session"] = self._identify_sessions_numba(hours)

        # 바디 크기
        indicators["body"] = np.abs(close - open_price)
        indicators["body_pct"] = indicators["body"] / (high - low + 1e-8)

        # 디스플레이스먼트
        disp_mult = params.get("disp_mult", 1.31)
        indicators["displacement"] = self._calculate_displacement_numba(open_price, close, high, low, disp_mult)

        # 일중 변동성 (간소화된 버전)
        indicators["rr_percentile"] = self._calculate_rr_percentile_numba(indicators["tr"], params.get("rr_percentile", 0.13))

        # 시간 정보 저장
        indicators["hour"] = hours
        indicators["minute"] = minutes
        indicators["weekday"] = weekdays

        # 기본 가격 데이터
        indicators["open"] = open_price
        indicators["high"] = high
        indicators["low"] = low
        indicators["close"] = close
        indicators["volume"] = volume

        self.cached_indicators = indicators

        print(f"✅ {len(indicators)}개 지표 캐시 완료")
        return indicators

    @staticmethod
    @njit
    def _calculate_atr_numba(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        """Numba JIT ATR 계산"""
        n = len(high)
        tr = np.zeros(n, dtype=np.float32)
        atr = np.zeros(n, dtype=np.float32)

        # True Range 계산
        for i in range(1, n):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i - 1])
            tr3 = abs(low[i] - close[i - 1])
            tr[i] = max(tr1, max(tr2, tr3))

        # ATR 계산 (Simple Moving Average)
        for i in range(period, n):
            atr[i] = np.mean(tr[i - period + 1 : i + 1])

        return atr

    @staticmethod
    @njit
    def _calculate_tr_numba(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """Numba JIT True Range 계산"""
        n = len(high)
        tr = np.zeros(n, dtype=np.float32)

        for i in range(1, n):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i - 1])
            tr3 = abs(low[i] - close[i - 1])
            tr[i] = max(tr1, max(tr2, tr3))

        return tr

    @staticmethod
    @njit
    def _find_swing_points_numba(high: np.ndarray, low: np.ndarray, swing_len: int) -> Tuple[np.ndarray, np.ndarray]:
        """Numba JIT 스윙 포인트 찾기"""
        n = len(high)
        swing_highs = np.zeros(n, dtype=np.bool_)
        swing_lows = np.zeros(n, dtype=np.bool_)

        for i in range(swing_len, n - swing_len):
            # 스윙 하이 확인
            is_high = True
            for k in range(1, swing_len + 1):
                if high[i] <= high[i - k] or high[i] <= high[i + k]:
                    is_high = False
                    break
            swing_highs[i] = is_high

            # 스윙 로우 확인
            is_low = True
            for k in range(1, swing_len + 1):
                if low[i] >= low[i - k] or low[i] >= low[i + k]:
                    is_low = False
                    break
            swing_lows[i] = is_low

        return swing_highs, swing_lows

    @staticmethod
    @njit
    def _identify_sessions_numba(hours: np.ndarray) -> np.ndarray:
        """Numba JIT 세션 구분 (간소화)"""
        n = len(hours)
        sessions = np.zeros(n, dtype=np.int8)

        # 세션 코드: 0=other, 1=asia, 2=london, 3=ny, 4=london_ny
        for i in range(n):
            hour = hours[i]
            if 0 <= hour < 8:  # Asia
                sessions[i] = 1
            elif 8 <= hour < 13:  # London
                sessions[i] = 2
            elif 13 <= hour < 16:  # London-NY overlap
                sessions[i] = 4
            elif 16 <= hour < 21:  # NY
                sessions[i] = 3
            else:  # Other
                sessions[i] = 0

        return sessions

    @staticmethod
    @njit
    def _calculate_displacement_numba(
        open_price: np.ndarray, close: np.ndarray, high: np.ndarray, low: np.ndarray, disp_mult: float
    ) -> np.ndarray:
        """Numba JIT 디스플레이스먼트 계산"""
        n = len(open_price)
        displacement = np.zeros(n, dtype=np.bool_)

        # 바디와 레인지 크기
        body = np.abs(close - open_price)
        range_size = high - low

        # 10바 이동평균 계산
        window = 10
        for i in range(window, n):
            avg_body = np.mean(body[i - window : i])
            avg_range = np.mean(range_size[i - window : i])

            body_disp = body[i] >= (disp_mult * avg_body)
            range_disp = range_size[i] >= (disp_mult * avg_range)

            displacement[i] = body_disp or range_disp

        return displacement

    @staticmethod
    @njit
    def _calculate_rr_percentile_numba(tr: np.ndarray, threshold: float) -> np.ndarray:
        """Numba JIT RR Percentile 계산 (간소화)"""
        n = len(tr)
        rr_percentile = np.zeros(n, dtype=np.float32)

        # 20일 롤링 윈도우
        window = 20 * 96  # 20일 * 96개 15분봉

        for i in range(window, n):
            # 현재 TR과 과거 TR 비교
            current_tr = tr[i]
            past_trs = tr[i - window : i]

            # 퍼센타일 계산
            count_below = 0
            for j in range(len(past_trs)):
                if past_trs[j] < current_tr:
                    count_below += 1

            rr_percentile[i] = count_below / len(past_trs)

        return rr_percentile

    def get_cached_slice(self, start: int, end: int, indicators: List[str] = None) -> Dict[str, np.ndarray]:
        """캐시된 데이터 슬라이스 반환"""
        if not self.cached_indicators:
            raise ValueError("지표가 캐시되지 않았습니다. cache_indicators()를 먼저 실행하세요.")

        if indicators is None:
            indicators = list(self.cached_indicators.keys())

        sliced_data = {}
        for indicator in indicators:
            if indicator in self.cached_indicators:
                sliced_data[indicator] = self.cached_indicators[indicator][start:end]

        return sliced_data

    def update_incremental(self, new_bar: Dict) -> None:
        """증분 업데이트 (실시간 데이터용)"""
        # 새로운 바 데이터를 캐시에 추가
        for key, value in new_bar.items():
            if key in self.cached_indicators:
                # numpy array에 새 값 추가 (메모리 효율적이지 않음, 실제로는 circular buffer 사용)
                self.cached_indicators[key] = np.append(self.cached_indicators[key], value)

    def parallel_backtest(self, param_sets: List[Dict], strategy_func, n_jobs: int = None) -> List[Dict]:
        """병렬 백테스트 실행"""
        if n_jobs is None:
            n_jobs = self.max_workers

        print(f"🔄 병렬 백테스트 시작: {len(param_sets)}개 파라미터 세트, {n_jobs}개 프로세스")

        if RAY_AVAILABLE:
            return self._parallel_backtest_ray(param_sets, strategy_func)
        elif JOBLIB_AVAILABLE:
            return self._parallel_backtest_joblib(param_sets, strategy_func, n_jobs)
        else:
            # 단일 스레드 폴백
            return [strategy_func(params) for params in param_sets]

    def _parallel_backtest_ray(self, param_sets: List[Dict], strategy_func) -> List[Dict]:
        """Ray를 사용한 병렬 백테스트"""
        try:
            import ray

            @ray.remote
            def remote_backtest(params):
                return strategy_func(params)

            # Ray 작업 제출
            futures = [remote_backtest.remote(params) for params in param_sets]

            # 결과 수집
            results = ray.get(futures)
            return results
        except ImportError:
            # Ray가 없으면 단일 스레드로 폴백
            return [strategy_func(params) for params in param_sets]

    def _parallel_backtest_joblib(self, param_sets: List[Dict], strategy_func, n_jobs: int) -> List[Dict]:
        """Joblib을 사용한 병렬 백테스트"""
        results = Parallel(n_jobs=n_jobs, backend="multiprocessing")(delayed(strategy_func)(params) for params in param_sets)
        return results

    def get_memory_usage(self) -> Dict[str, float]:
        """메모리 사용량 조회"""
        memory_info = {}

        # 캐시된 데이터 메모리 사용량
        total_cache_memory = 0
        for key, data in self.cached_indicators.items():
            if isinstance(data, np.ndarray):
                memory_mb = data.nbytes / 1024 / 1024
                memory_info[f"cache_{key}"] = memory_mb
                total_cache_memory += memory_mb

        memory_info["total_cache_mb"] = total_cache_memory
        memory_info["system_available_mb"] = psutil.virtual_memory().available / 1024 / 1024
        memory_info["system_used_pct"] = psutil.virtual_memory().percent

        return memory_info

    def cleanup_cache(self):
        """캐시 정리"""
        self.cached_data.clear()
        self.cached_indicators.clear()

        # Ray 정리 불필요 (사용하지 않음)

        print("🧹 캐시 정리 완료")


def main():
    """테스트 실행"""
    engine = FastDataEngine()

    # 테스트 데이터 로드
    test_file = "data/ETHUSDT_15m_206319points_20251015_202539.csv"
    if os.path.exists(test_file):
        df = engine.load_data(test_file)

        # 테스트 파라미터
        test_params = {"atr_len": 41, "swing_len": 3, "disp_mult": 1.31, "rr_percentile": 0.13}

        # 지표 캐시
        indicators = engine.cache_indicators(df, test_params)

        # 메모리 사용량 확인
        memory_usage = engine.get_memory_usage()
        print(f"\n💾 메모리 사용량:")
        for key, value in memory_usage.items():
            print(f"   {key}: {value:.1f}MB")

        # 슬라이스 테스트
        slice_data = engine.get_cached_slice(1000, 2000, ["atr", "close", "displacement"])
        print(f"\n🔍 슬라이스 테스트: {len(slice_data)}개 지표, {len(slice_data['atr'])}개 데이터 포인트")

        engine.cleanup_cache()
    else:
        print(f"❌ 테스트 파일을 찾을 수 없습니다: {test_file}")


if __name__ == "__main__":
    main()
