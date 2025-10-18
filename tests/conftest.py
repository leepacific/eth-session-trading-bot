"""
Pytest configuration and fixtures
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    np.random.seed(42)
    periods = 1000
    dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=periods, freq="15min")

    base_price = 2500.0
    returns = np.random.normal(0, 0.01, periods)
    prices = base_price * np.exp(np.cumsum(returns))

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": prices,
            "high": prices * (1 + np.abs(np.random.normal(0, 0.002, periods))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.002, periods))),
            "close": prices,
            "volume": np.random.lognormal(8, 1, periods),
        }
    )


@pytest.fixture
def sample_trades():
    """테스트용 샘플 거래"""
    np.random.seed(42)
    trades = []

    for i in range(100):
        if np.random.random() < 0.6:  # 60% 승률
            pnl_pct = np.random.normal(0.02, 0.01)
        else:
            pnl_pct = np.random.normal(-0.01, 0.005)

        trades.append(
            {
                "entry_time": datetime.now() - timedelta(days=100 - i),
                "exit_time": datetime.now() - timedelta(days=100 - i) + timedelta(hours=2),
                "pnl": pnl_pct * 10000,
                "pnl_pct": pnl_pct,
                "quantity": 1.0,
                "side": "long",
            }
        )

    return trades


@pytest.fixture
def sample_parameters():
    """테스트용 파라미터"""
    return {
        "target_r": 3.0,
        "stop_atr_mult": 0.1,
        "swing_len": 5,
        "rr_percentile": 0.25,
        "atr_len": 14,
        "session_strength": 1.5,
        "volume_filter": 1.2,
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # 경고 무시
    import warnings

    warnings.filterwarnings("ignore")

    # 랜덤 시드 고정
    np.random.seed(42)

    yield

    # 테스트 후 정리
    pass
