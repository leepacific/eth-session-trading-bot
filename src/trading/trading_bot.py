"""
ETH 세션 스윕 전략 실시간 거래 봇
Railway 배포용 메인 파일
"""

import asyncio
import logging
import os
import time
import warnings
from datetime import datetime, timedelta

import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException

warnings.filterwarnings("ignore")

# .env 파일 로드
from dotenv import load_dotenv

load_dotenv()

from advanced_risk_system import AdvancedRiskManager, RiskParameters

# 로컬 모듈 import
from eth_session_strategy import ETHSessionStrategy

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("trading_bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class LiveTradingBot:
    def __init__(self):
        """실시간 거래 봇 초기화"""

        # 환경 변수에서 API 키 로드
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

        if not self.api_key or not self.secret_key:
            raise ValueError("바이낸스 API 키가 설정되지 않았습니다!")

        # 바이낸스 클라이언트 초기화
        if self.testnet:
            self.client = Client(self.api_key, self.secret_key, testnet=True)
            logger.info("🧪 테스트넷 모드로 연결됨")
        else:
            self.client = Client(self.api_key, self.secret_key)
            logger.info("🔴 실제 거래 모드로 연결됨")

        # 거래 설정
        self.symbol = "ETHUSDT"
        self.interval = "15m"
        self.lookback_periods = 1000  # 분석용 데이터 개수

        # 전략 및 리스크 관리자 초기화
        self.strategy = None
        self.risk_manager = None
        self.active_positions = {}

        # 거래 상태
        self.is_trading = True
        self.last_signal_time = None

        logger.info("🚀 실시간 거래 봇 초기화 완료")

    async def initialize_strategy(self):
        """전략 초기화"""
        try:
            # 계좌 잔고 확인
            account_info = self.client.futures_account()
            balance = float(account_info["totalWalletBalance"])

            logger.info(f"💰 현재 계좌 잔고: ${balance:,.2f}")

            # 리스크 관리자 초기화
            risk_params = RiskParameters(
                account_balance=balance,
                max_account_risk_per_trade=0.05,  # 5%
                liquidation_probability=0.07,  # 7%
                max_leverage=125,
            )
            self.risk_manager = AdvancedRiskManager(risk_params)

            # 전략 초기화 (백테스트용이 아닌 실시간용)
            self.strategy = ETHSessionStrategy()

            logger.info("✅ 전략 및 리스크 관리자 초기화 완료")

        except Exception as e:
            logger.error(f"❌ 전략 초기화 실패: {e}")
            raise

    async def get_market_data(self):
        """시장 데이터 수집"""
        try:
            # 15분봉 데이터 수집
            klines = self.client.futures_klines(symbol=self.symbol, interval=self.interval, limit=self.lookback_periods)

            # DataFrame 변환
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_volume",
                    "trades",
                    "taker_buy_base",
                    "taker_buy_quote",
                    "ignore",
                ],
            )

            # 데이터 타입 변환
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            df["time"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df[["time", "open", "high", "low", "close", "volume"]].copy()

            return df

        except Exception as e:
            logger.error(f"❌ 시장 데이터 수집 실패: {e}")
            return None

    async def analyze_market(self, df):
        """시장 분석 및 신호 생성"""
        try:
            # 전략에 데이터 설정
            self.strategy.df = df
            self.strategy._calculate_indicators()

            # 최근 신호만 확인 (마지막 몇 개 바)
            recent_signals = []

            # 세션 레벨 찾기
            session_levels = self.strategy.find_session_levels()

            # 최근 스윕 감지
            recent_sweeps = self.strategy.detect_sweeps(session_levels)

            # 최근 10개 바에서만 신호 확인
            current_time = datetime.now()
            for sweep in recent_sweeps[-5:]:  # 최근 5개만
                sweep_time = pd.to_datetime(sweep["time"])

                # 15분 이내의 신호만 처리
                if (current_time - sweep_time).total_seconds() < 900:  # 15분

                    # 신호 생성 로직 (간소화)
                    i = sweep["index"]
                    if i + 3 < len(df):
                        for j in range(i + 1, min(i + 4, len(df))):
                            next_row = df.iloc[j]

                            # 기본 필터링
                            if next_row["rr_percentile"] < self.strategy.params["rr_percentile"]:
                                continue

                            if not next_row["displacement"]:
                                continue

                            # 신호 생성
                            if sweep["type"] == "bullish_sweep" and next_row["close"] > next_row["open"]:
                                stop_price = sweep["sweep_level"] - (self.strategy.params["stop_atr_mult"] * next_row["atr"])
                                risk = next_row["close"] - stop_price
                                target_price = next_row["close"] + (self.strategy.params["target_r"] * risk)

                                recent_signals.append(
                                    {
                                        "type": "long",
                                        "entry_price": next_row["close"],
                                        "stop_price": stop_price,
                                        "target_price": target_price,
                                        "atr": next_row["atr"],
                                        "time": next_row["time"],
                                        "confidence": self._calculate_signal_confidence(sweep, next_row),
                                    }
                                )
                                break

                            elif sweep["type"] == "bearish_sweep" and next_row["close"] < next_row["open"]:
                                stop_price = sweep["sweep_level"] + (self.strategy.params["stop_atr_mult"] * next_row["atr"])
                                risk = stop_price - next_row["close"]
                                target_price = next_row["close"] - (self.strategy.params["target_r"] * risk)

                                recent_signals.append(
                                    {
                                        "type": "short",
                                        "entry_price": next_row["close"],
                                        "stop_price": stop_price,
                                        "target_price": target_price,
                                        "atr": next_row["atr"],
                                        "time": next_row["time"],
                                        "confidence": self._calculate_signal_confidence(sweep, next_row),
                                    }
                                )
                                break

            return recent_signals

        except Exception as e:
            logger.error(f"❌ 시장 분석 실패: {e}")
            return []

    def _calculate_signal_confidence(self, sweep, bar):
        """신호 신뢰도 계산"""
        confidence = 0.5  # 기본값

        # 스윕 품질
        if sweep.get("wick_ratio", 0) > 0.7:
            confidence += 0.2

        # 볼륨
        if bar.get("volume", 0) > bar.get("avg_volume", 0) * 1.5:
            confidence += 0.1

        # 시간대 (고변동성 시간)
        hour = pd.to_datetime(bar["time"]).hour
        if hour in [8, 9, 13, 14, 15, 16]:  # UTC
            confidence += 0.1

        return min(confidence, 1.0)

    async def execute_trade(self, signal):
        """거래 실행"""
        try:
            # 포지션 계산
            position_info = self.risk_manager.calculate_optimal_position(
                signal["entry_price"], signal["stop_price"], signal["atr"], signal["type"]
            )

            position_info = self.risk_manager.validate_position(
                position_info, signal["entry_price"], signal["stop_price"], signal["type"]
            )

            # 레버리지 설정
            self.client.futures_change_leverage(symbol=self.symbol, leverage=int(position_info["leverage"]))

            # 주문 실행
            side = "BUY" if signal["type"] == "long" else "SELL"
            quantity = round(position_info["position_size"], 4)

            # 시장가 주문
            order = self.client.futures_create_order(symbol=self.symbol, side=side, type="MARKET", quantity=quantity)

            logger.info(f"✅ 주문 실행: {side} {quantity} {self.symbol} @ {signal['entry_price']}")
            logger.info(f"   레버리지: {position_info['leverage']}x")
            logger.info(f"   스톱: {signal['stop_price']:.2f}")
            logger.info(f"   타겟: {signal['target_price']:.2f}")

            # 스톱로스 주문
            stop_side = "SELL" if signal["type"] == "long" else "BUY"
            stop_order = self.client.futures_create_order(
                symbol=self.symbol, side=stop_side, type="STOP_MARKET", quantity=quantity, stopPrice=signal["stop_price"]
            )

            # 활성 포지션에 추가
            self.active_positions[order["orderId"]] = {
                "signal": signal,
                "position_info": position_info,
                "entry_order": order,
                "stop_order": stop_order,
                "entry_time": datetime.now(),
            }

            return True

        except BinanceAPIException as e:
            logger.error(f"❌ 바이낸스 API 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 거래 실행 실패: {e}")
            return False

    async def monitor_positions(self):
        """포지션 모니터링"""
        try:
            if not self.active_positions:
                return

            # 현재 포지션 확인
            positions = self.client.futures_position_information(symbol=self.symbol)
            current_price = float(self.client.futures_symbol_ticker(symbol=self.symbol)["price"])

            for pos_id, pos_data in list(self.active_positions.items()):
                signal = pos_data["signal"]
                entry_time = pos_data["entry_time"]

                # 시간 기반 종료 (1시간)
                if (datetime.now() - entry_time).total_seconds() > 3600:
                    await self.close_position(pos_id, "시간 만료")

                # 타겟 도달 확인
                if signal["type"] == "long" and current_price >= signal["target_price"]:
                    await self.close_position(pos_id, "타겟 도달")
                elif signal["type"] == "short" and current_price <= signal["target_price"]:
                    await self.close_position(pos_id, "타겟 도달")

        except Exception as e:
            logger.error(f"❌ 포지션 모니터링 실패: {e}")

    async def close_position(self, pos_id, reason):
        """포지션 종료"""
        try:
            if pos_id not in self.active_positions:
                return

            pos_data = self.active_positions[pos_id]
            signal = pos_data["signal"]

            # 반대 주문 실행
            side = "SELL" if signal["type"] == "long" else "BUY"
            quantity = pos_data["position_info"]["position_size"]

            close_order = self.client.futures_create_order(symbol=self.symbol, side=side, type="MARKET", quantity=quantity)

            logger.info(f"✅ 포지션 종료: {reason} - {side} {quantity} {self.symbol}")

            # 스톱 주문 취소
            try:
                self.client.futures_cancel_order(symbol=self.symbol, orderId=pos_data["stop_order"]["orderId"])
            except Exception as e:
                logger.warning(f"Stop order cancellation failed: {e}")

            # 활성 포지션에서 제거
            del self.active_positions[pos_id]

        except Exception as e:
            logger.error(f"❌ 포지션 종료 실패: {e}")

    async def run(self):
        """메인 실행 루프"""
        logger.info("🚀 실시간 거래 봇 시작")

        # 전략 초기화
        await self.initialize_strategy()

        while self.is_trading:
            try:
                # 시장 데이터 수집
                df = await self.get_market_data()
                if df is None:
                    await asyncio.sleep(60)
                    continue

                # 시장 분석
                signals = await self.analyze_market(df)

                # 신호 처리
                for signal in signals:
                    if signal["confidence"] > 0.7:  # 높은 신뢰도만
                        logger.info(f"🎯 신호 감지: {signal['type']} @ {signal['entry_price']:.2f}")
                        await self.execute_trade(signal)

                # 포지션 모니터링
                await self.monitor_positions()

                # 15분 대기 (다음 캔들까지)
                await asyncio.sleep(900)  # 15분

            except KeyboardInterrupt:
                logger.info("⚠️ 사용자에 의해 중단됨")
                self.is_trading = False
                break
            except Exception as e:
                logger.error(f"❌ 메인 루프 오류: {e}")
                await asyncio.sleep(60)

        logger.info("🛑 거래 봇 종료")


async def main():
    """메인 함수"""
    bot = LiveTradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
