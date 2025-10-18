#!/usr/bin/env python3
"""
실시간 모니터링 시스템 구현
- 일중 손실한도 및 연속손실 n회 자동 정지
- 유동성 필터 (스프레드·체결량)
- 실시간 지연 < 바 주기 20% 모니터링
"""

import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


class TradingState(Enum):
    """거래 상태"""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    EMERGENCY = "emergency"


class AlertLevel(Enum):
    """알림 레벨"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class MonitoringConfig:
    """모니터링 설정"""

    # 손실 한도 설정
    daily_loss_limit_pct: float = 0.05  # 일일 손실 한도 5%
    max_consecutive_losses: int = 5  # 최대 연속 손실 횟수

    # 유동성 필터 설정
    max_spread_bps: float = 10.0  # 최대 스프레드 10bps
    min_volume_threshold: float = 100000.0  # 최소 거래량 $100k
    liquidity_check_interval: float = 30.0  # 유동성 체크 간격 (초)

    # 지연 모니터링 설정
    bar_period_seconds: float = 900.0  # 바 주기 (15분 = 900초)
    max_delay_ratio: float = 0.20  # 최대 지연 비율 20%
    latency_check_interval: float = 10.0  # 지연 체크 간격 (초)

    # 알림 설정
    alert_cooldown_seconds: float = 300.0  # 알림 쿨다운 5분
    emergency_stop_enabled: bool = True  # 긴급 정지 활성화


@dataclass
class MarketData:
    """시장 데이터"""

    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last_price: float
    volume_24h: float
    spread_bps: float = field(init=False)

    def __post_init__(self):
        """스프레드 계산"""
        if self.bid > 0 and self.ask > 0:
            self.spread_bps = (self.ask - self.bid) / ((self.ask + self.bid) / 2) * 10000
        else:
            self.spread_bps = float("inf")


@dataclass
class TradeEvent:
    """거래 이벤트"""

    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    pnl: float
    is_loss: bool = field(init=False)

    def __post_init__(self):
        """손실 여부 판단"""
        self.is_loss = self.pnl < 0


@dataclass
class Alert:
    """알림"""

    timestamp: datetime
    level: AlertLevel
    message: str
    data: Dict = field(default_factory=dict)


class RealtimeMonitor:
    def __init__(self, config: MonitoringConfig = None):
        """실시간 모니터링 시스템 초기화"""
        self.config = config or MonitoringConfig()

        # 상태 관리
        self.trading_state = TradingState.ACTIVE
        self.start_time = datetime.now()
        self.daily_start_balance = 0.0
        self.current_balance = 0.0

        # 거래 추적
        self.trades_today: List[TradeEvent] = []
        self.consecutive_losses = 0
        self.last_trade_time: Optional[datetime] = None

        # 시장 데이터 추적
        self.latest_market_data: Dict[str, MarketData] = {}
        self.data_timestamps: Dict[str, datetime] = {}

        # 알림 시스템
        self.alerts: List[Alert] = []
        self.last_alert_time: Dict[str, datetime] = {}

        # 모니터링 스레드
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 콜백 함수들
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.state_change_callbacks: List[Callable[[TradingState], None]] = []

        print("🔍 실시간 모니터링 시스템 초기화")
        print(f"   일일 손실 한도: {self.config.daily_loss_limit_pct*100}%")
        print(f"   최대 연속 손실: {self.config.max_consecutive_losses}회")
        print(f"   최대 스프레드: {self.config.max_spread_bps}bps")
        print(f"   최대 지연: {self.config.max_delay_ratio*100}%")

    def start_monitoring(self, initial_balance: float):
        """모니터링 시작"""
        self.daily_start_balance = initial_balance
        self.current_balance = initial_balance
        self.start_time = datetime.now()
        self.monitoring_active = True

        # 모니터링 스레드 시작
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        self._send_alert(AlertLevel.INFO, "모니터링 시작", {"initial_balance": initial_balance, "start_time": self.start_time})

        print(f"🚀 모니터링 시작: ${initial_balance:,.2f}")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        self._send_alert(
            AlertLevel.INFO, "모니터링 중지", {"stop_time": datetime.now(), "final_balance": self.current_balance}
        )

        print("⏹️ 모니터링 중지")

    def update_balance(self, new_balance: float):
        """잔고 업데이트"""
        self.current_balance = new_balance

        # 일일 손실 체크
        daily_pnl = new_balance - self.daily_start_balance
        daily_pnl_pct = daily_pnl / self.daily_start_balance

        if daily_pnl_pct <= -self.config.daily_loss_limit_pct:
            self._trigger_daily_loss_limit(daily_pnl_pct)

    def record_trade(self, trade: TradeEvent):
        """거래 기록"""
        self.trades_today.append(trade)
        self.last_trade_time = trade.timestamp

        # 연속 손실 추적
        if trade.is_loss:
            self.consecutive_losses += 1
            print(f"📉 손실 거래: {self.consecutive_losses}회 연속")

            # 연속 손실 한도 체크
            if self.consecutive_losses >= self.config.max_consecutive_losses:
                self._trigger_consecutive_loss_limit()
        else:
            self.consecutive_losses = 0  # 수익 거래시 리셋

        # 잔고 업데이트
        self.update_balance(self.current_balance + trade.pnl)

        print(f"📊 거래 기록: {trade.side} {trade.quantity} @ {trade.price}, PnL: {trade.pnl:.2f}")

    def update_market_data(self, symbol: str, market_data: MarketData):
        """시장 데이터 업데이트"""
        self.latest_market_data[symbol] = market_data
        self.data_timestamps[symbol] = market_data.timestamp

        # 유동성 체크
        self._check_liquidity(symbol, market_data)

        # 지연 체크
        self._check_latency(symbol, market_data.timestamp)

    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                # 주기적 체크들
                self._periodic_checks()

                # 체크 간격
                time.sleep(min(self.config.liquidity_check_interval, self.config.latency_check_interval))

            except Exception as e:
                self._send_alert(AlertLevel.CRITICAL, f"모니터링 오류: {str(e)}")
                time.sleep(1.0)

    def _periodic_checks(self):
        """주기적 체크"""
        current_time = datetime.now()

        # 유동성 체크
        for symbol in self.latest_market_data:
            market_data = self.latest_market_data[symbol]
            self._check_liquidity(symbol, market_data)

        # 데이터 지연 체크
        for symbol in self.data_timestamps:
            self._check_latency(symbol, self.data_timestamps[symbol])

        # 거래 활동 체크
        self._check_trading_activity()

    def _check_liquidity(self, symbol: str, market_data: MarketData):
        """유동성 체크"""
        issues = []

        # 스프레드 체크
        if market_data.spread_bps > self.config.max_spread_bps:
            issues.append(f"높은 스프레드: {market_data.spread_bps:.1f}bps")

        # 거래량 체크
        if market_data.volume_24h < self.config.min_volume_threshold:
            issues.append(f"낮은 거래량: ${market_data.volume_24h:,.0f}")

        if issues:
            alert_key = f"liquidity_{symbol}"
            if self._can_send_alert(alert_key):
                self._send_alert(
                    AlertLevel.WARNING,
                    f"{symbol} 유동성 문제",
                    {
                        "symbol": symbol,
                        "issues": issues,
                        "spread_bps": market_data.spread_bps,
                        "volume_24h": market_data.volume_24h,
                    },
                )
                self.last_alert_time[alert_key] = datetime.now()

    def _check_latency(self, symbol: str, data_timestamp: datetime):
        """지연 체크"""
        current_time = datetime.now()
        latency = (current_time - data_timestamp).total_seconds()
        max_allowed_delay = self.config.bar_period_seconds * self.config.max_delay_ratio

        if latency > max_allowed_delay:
            alert_key = f"latency_{symbol}"
            if self._can_send_alert(alert_key):
                self._send_alert(
                    AlertLevel.WARNING,
                    f"{symbol} 데이터 지연",
                    {
                        "symbol": symbol,
                        "latency_seconds": latency,
                        "max_allowed": max_allowed_delay,
                        "delay_ratio": latency / self.config.bar_period_seconds,
                    },
                )
                self.last_alert_time[alert_key] = datetime.now()

    def _check_trading_activity(self):
        """거래 활동 체크"""
        if not self.last_trade_time:
            return

        # 마지막 거래 이후 시간
        time_since_last_trade = (datetime.now() - self.last_trade_time).total_seconds()

        # 30분 이상 거래 없음
        if time_since_last_trade > 1800:  # 30분
            alert_key = "no_trading_activity"
            if self._can_send_alert(alert_key):
                self._send_alert(
                    AlertLevel.INFO,
                    "거래 활동 없음",
                    {"minutes_since_last_trade": time_since_last_trade / 60, "last_trade_time": self.last_trade_time},
                )
                self.last_alert_time[alert_key] = datetime.now()

    def _trigger_daily_loss_limit(self, loss_pct: float):
        """일일 손실 한도 도달"""
        self._change_trading_state(TradingState.STOPPED)

        self._send_alert(
            AlertLevel.CRITICAL,
            "일일 손실 한도 도달",
            {
                "loss_pct": loss_pct,
                "limit_pct": -self.config.daily_loss_limit_pct,
                "current_balance": self.current_balance,
                "start_balance": self.daily_start_balance,
            },
        )

        print(f"🛑 일일 손실 한도 도달: {loss_pct*100:.1f}%")

    def _trigger_consecutive_loss_limit(self):
        """연속 손실 한도 도달"""
        self._change_trading_state(TradingState.PAUSED)

        self._send_alert(
            AlertLevel.CRITICAL,
            "연속 손실 한도 도달",
            {"consecutive_losses": self.consecutive_losses, "limit": self.config.max_consecutive_losses},
        )

        print(f"⏸️ 연속 손실 한도 도달: {self.consecutive_losses}회")

    def _change_trading_state(self, new_state: TradingState):
        """거래 상태 변경"""
        old_state = self.trading_state
        self.trading_state = new_state

        print(f"🔄 거래 상태 변경: {old_state.value} → {new_state.value}")

        # 콜백 호출
        for callback in self.state_change_callbacks:
            try:
                callback(new_state)
            except Exception as e:
                print(f"상태 변경 콜백 오류: {e}")

    def _send_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """알림 전송"""
        alert = Alert(timestamp=datetime.now(), level=level, message=message, data=data or {})

        self.alerts.append(alert)

        # 콘솔 출력
        level_icons = {AlertLevel.INFO: "ℹ️", AlertLevel.WARNING: "⚠️", AlertLevel.CRITICAL: "🚨", AlertLevel.EMERGENCY: "🆘"}

        icon = level_icons.get(level, "📢")
        print(f"{icon} [{level.value.upper()}] {message}")

        # 콜백 호출
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"알림 콜백 오류: {e}")

    def _can_send_alert(self, alert_key: str) -> bool:
        """알림 전송 가능 여부 (쿨다운 체크)"""
        if alert_key not in self.last_alert_time:
            return True

        time_since_last = (datetime.now() - self.last_alert_time[alert_key]).total_seconds()
        return time_since_last >= self.config.alert_cooldown_seconds

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """알림 콜백 추가"""
        self.alert_callbacks.append(callback)

    def add_state_change_callback(self, callback: Callable[[TradingState], None]):
        """상태 변경 콜백 추가"""
        self.state_change_callbacks.append(callback)

    def emergency_stop(self, reason: str):
        """긴급 정지"""
        if not self.config.emergency_stop_enabled:
            return

        self._change_trading_state(TradingState.EMERGENCY)

        self._send_alert(AlertLevel.EMERGENCY, f"긴급 정지: {reason}", {"reason": reason})

        print(f"🆘 긴급 정지: {reason}")

    def resume_trading(self):
        """거래 재개"""
        if self.trading_state in [TradingState.PAUSED]:
            self._change_trading_state(TradingState.ACTIVE)
            self.consecutive_losses = 0  # 연속 손실 리셋

            self._send_alert(AlertLevel.INFO, "거래 재개")
            print("▶️ 거래 재개")
        else:
            print(f"❌ 현재 상태({self.trading_state.value})에서는 재개할 수 없습니다")

    def get_monitoring_status(self) -> Dict:
        """모니터링 상태 조회"""
        current_time = datetime.now()
        uptime = (current_time - self.start_time).total_seconds()

        daily_pnl = self.current_balance - self.daily_start_balance
        daily_pnl_pct = daily_pnl / self.daily_start_balance if self.daily_start_balance > 0 else 0

        return {
            "trading_state": self.trading_state.value,
            "uptime_seconds": uptime,
            "current_balance": self.current_balance,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "trades_today": len(self.trades_today),
            "consecutive_losses": self.consecutive_losses,
            "total_alerts": len(self.alerts),
            "monitoring_active": self.monitoring_active,
        }

    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """최근 알림 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp >= cutoff_time]

    def export_monitoring_log(self) -> pd.DataFrame:
        """모니터링 로그 내보내기"""
        log_data = []

        # 거래 로그
        for trade in self.trades_today:
            log_data.append(
                {
                    "timestamp": trade.timestamp,
                    "type": "trade",
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "pnl": trade.pnl,
                    "is_loss": trade.is_loss,
                }
            )

        # 알림 로그
        for alert in self.alerts:
            log_data.append(
                {
                    "timestamp": alert.timestamp,
                    "type": "alert",
                    "level": alert.level.value,
                    "message": alert.message,
                    "data": str(alert.data),
                }
            )

        return pd.DataFrame(log_data).sort_values("timestamp")


def main():
    """테스트 실행"""
    print("🚀 실시간 모니터링 시스템 테스트")
    print("=" * 80)

    # 모니터링 시스템 초기화
    config = MonitoringConfig(
        daily_loss_limit_pct=0.03,  # 3% 손실 한도
        max_consecutive_losses=3,  # 3회 연속 손실
        max_spread_bps=15.0,  # 15bps 스프레드
        min_volume_threshold=50000,  # $50k 최소 거래량
    )

    monitor = RealtimeMonitor(config)

    # 콜백 함수 등록
    def alert_handler(alert: Alert):
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            print(f"🔔 중요 알림 처리: {alert.message}")

    def state_change_handler(new_state: TradingState):
        print(f"📊 상태 변경 처리: {new_state.value}")

    monitor.add_alert_callback(alert_handler)
    monitor.add_state_change_callback(state_change_handler)

    # 모니터링 시작
    initial_balance = 10000.0
    monitor.start_monitoring(initial_balance)

    print(f"\n📊 시뮬레이션 시작:")
    print(f"   초기 잔고: ${initial_balance:,}")

    # 시뮬레이션 시나리오
    scenarios = [
        # 정상 거래
        {"type": "trade", "pnl": 150, "side": "buy"},
        {"type": "trade", "pnl": -80, "side": "sell"},
        {"type": "trade", "pnl": 200, "side": "buy"},
        # 연속 손실 시나리오
        {"type": "trade", "pnl": -120, "side": "sell"},
        {"type": "trade", "pnl": -90, "side": "buy"},
        {"type": "trade", "pnl": -110, "side": "sell"},  # 3회 연속 손실
        # 시장 데이터 문제
        {"type": "market_data", "spread": 20.0, "volume": 30000},  # 높은 스프레드, 낮은 거래량
        # 큰 손실 (일일 한도 근접)
        {"type": "trade", "pnl": -250, "side": "sell"},
    ]

    current_balance = initial_balance

    for i, scenario in enumerate(scenarios):
        print(f"\n📅 시나리오 {i+1}: {scenario}")

        if scenario["type"] == "trade":
            # 거래 이벤트
            trade = TradeEvent(
                timestamp=datetime.now(),
                symbol="BTCUSDT",
                side=scenario["side"],
                quantity=0.1,
                price=50000.0,
                pnl=scenario["pnl"],
            )

            monitor.record_trade(trade)
            current_balance += scenario["pnl"]

        elif scenario["type"] == "market_data":
            # 시장 데이터 업데이트
            market_data = MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                bid=49990.0,
                ask=50000.0 + scenario["spread"],
                last_price=50000.0,
                volume_24h=scenario["volume"],
            )

            monitor.update_market_data("BTCUSDT", market_data)

        # 상태 확인
        status = monitor.get_monitoring_status()
        print(f"   현재 상태: {status['trading_state']}")
        print(f"   잔고: ${status['current_balance']:,.2f}")
        print(f"   일일 PnL: {status['daily_pnl_pct']*100:.1f}%")
        print(f"   연속 손실: {status['consecutive_losses']}회")

        # 잠시 대기
        time.sleep(0.5)

        # 거래 중지 상태면 재개 시도
        if monitor.trading_state == TradingState.PAUSED and i == len(scenarios) - 2:
            print("   🔄 거래 재개 시도...")
            monitor.resume_trading()

    # 최종 상태
    print(f"\n📊 최종 모니터링 상태:")
    final_status = monitor.get_monitoring_status()
    for key, value in final_status.items():
        print(f"   {key}: {value}")

    # 최근 알림 조회
    recent_alerts = monitor.get_recent_alerts(1)  # 최근 1시간
    print(f"\n🔔 최근 알림 ({len(recent_alerts)}개):")
    for alert in recent_alerts[-5:]:  # 최근 5개만
        print(f"   [{alert.level.value}] {alert.message}")

    # 모니터링 로그 내보내기
    log_df = monitor.export_monitoring_log()
    print(f"\n📋 모니터링 로그: {len(log_df)}개 이벤트")

    # 모니터링 중지
    monitor.stop_monitoring()

    print(f"\n🎯 핵심 특징:")
    print(f"   • 일일 손실 한도 자동 감지 및 정지")
    print(f"   • 연속 손실 추적 및 일시 정지")
    print(f"   • 실시간 유동성 모니터링")
    print(f"   • 데이터 지연 감지")
    print(f"   • 다단계 알림 시스템")
    print(f"   • 긴급 정지 기능")


if __name__ == "__main__":
    main()
