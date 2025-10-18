"""
ETHUSDT 세션 스윕 리버설 + 리퀴데이션 모멘텀 전략
15분봉 데이터 기반 백테스팅 시스템
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# 고급 리스크 관리 시스템 import
from advanced_risk_system import AdvancedRiskManager, RiskParameters


class ETHSessionStrategy:
    def __init__(self, data_file=None, initial_balance=100000):
        """전략 초기화"""
        self.data_file = data_file or "data/ETHUSDT_15m_206319points_20251015_202539.csv"
        self.initial_balance = initial_balance

        # 전략 파라미터 (워크포워드 테스트 통과 최적값 - 2025.10.17)
        self.params = {
            # 기본 설정 (워크포워드 검증됨)
            "swing_len": 3,  # 스윙 고저 인식 길이
            "rr_percentile": 0.1278554501836069,  # 변동성 필터
            "disp_mult": 1.3107139215624644,  # 디스플레이스먼트 배수
            "sweep_wick_mult": 0.6490576952390765,  # 스윕 꼬리 비율
            "atr_len": 41,  # ATR 계산 길이
            # 리스크 관리 (워크포워드 검증됨)
            "stop_atr_mult": 0.0549414233732278,  # 스톱 ATR 배수
            "time_stop_bars": 8,  # 시간 스톱
            "target_r": 2.862429365474845,  # 목표 R배수
            # 추가 최적화 파라미터 (워크포워드 검증됨)
            "funding_avoid_bars": 1,  # 펀딩 회피 바
            "min_volatility_rank": 0.3052228633363352,  # 최소 변동성 순위
            "session_strength": 1.9322268126535338,  # 세션 강도
            "volume_filter": 1.8994566274211397,  # 볼륨 필터
            "trend_filter_len": 13,  # 트렌드 필터 길이
            # 세션 시간 (UTC 기준, 15분봉에 맞춰 조정)
            "asia_start": 0,  # 00:00 UTC
            "asia_end": 8,  # 08:00 UTC
            "london_start": 8,  # 08:00 UTC
            "london_end": 16,  # 16:00 UTC
            "ny_start": 13,  # 13:00 UTC (런던과 겹침)
            "ny_end": 21,  # 21:00 UTC
            # 펀딩 시간 (UTC)
            "funding_hours": [0, 8, 16],  # 00:00, 08:00, 16:00 UTC
            "funding_avoid_bars": 1,  # 펀딩 전후 1바 (15분) 회피
        }

        self.df = None
        self.signals = None
        self.trades = []
        self.equity_curve = []

        # 고급 리스크 관리자 초기화
        # 계좌 잔고에 따른 동적 리스크 파라미터
        risk_params = RiskParameters(
            account_balance=initial_balance,
            min_notional_usdt=20.0,  # 바이낸스 최소 주문 금액
            # 나머지는 __post_init__에서 자동 조정됨
        )
        self.risk_manager = AdvancedRiskManager(risk_params)

        print("🚀 ETH 세션 전략 초기화 완료")
        print(f"   데이터 파일: {self.data_file}")
        print(f"   타임프레임: 15분봉")

    def load_data(self):
        """데이터 로드 및 전처리"""
        print("📊 데이터 로딩 중...")

        self.df = pd.read_csv(self.data_file)
        self.df["time"] = pd.to_datetime(self.df["time"])
        self.df = self.df.sort_values("time").reset_index(drop=True)

        # 기본 지표 계산
        self._calculate_indicators()

        print(f"   데이터 수: {len(self.df):,}개")
        print(f"   기간: {self.df['time'].iloc[0]} ~ {self.df['time'].iloc[-1]}")
        print(f"   총 {(self.df['time'].iloc[-1] - self.df['time'].iloc[0]).days}일")

    def _calculate_indicators(self):
        """기술적 지표 계산"""
        df = self.df

        # ATR 계산
        df["tr"] = np.maximum(
            df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1)))
        )
        df["atr"] = df["tr"].rolling(self.params["atr_len"]).mean()

        # 시간 정보 추출
        df["hour"] = df["time"].dt.hour
        df["minute"] = df["time"].dt.minute
        df["weekday"] = df["time"].dt.weekday  # 0=월요일

        # 세션 구분
        df["session"] = self._identify_sessions(df)

        # 스윙 고저점
        df["swing_high"], df["swing_low"] = self._find_swing_points(df)

        # 일중 변동성 (Realized Range Percentile)
        df["daily_tr"] = self._calculate_daily_tr(df)
        df["rr_percentile"] = self._calculate_rr_percentile(df)

        # 디스플레이스먼트
        df["displacement"] = self._calculate_displacement(df)

        # 바디 크기
        df["body"] = abs(df["close"] - df["open"])
        df["body_pct"] = df["body"] / (df["high"] - df["low"])

        print("✅ 지표 계산 완료")

    def _identify_sessions(self, df):
        """세션 구분"""
        sessions = []
        for _, row in df.iterrows():
            hour = row["hour"]
            if self.params["asia_start"] <= hour < self.params["asia_end"]:
                sessions.append("asia")
            elif self.params["london_start"] <= hour < self.params["london_end"]:
                if hour >= self.params["ny_start"]:
                    sessions.append("london_ny")  # 겹치는 시간
                else:
                    sessions.append("london")
            elif self.params["ny_start"] <= hour < self.params["ny_end"]:
                sessions.append("ny")
            else:
                sessions.append("other")
        return sessions

    def _find_swing_points(self, df):
        """스윙 고저점 찾기"""
        swing_len = self.params["swing_len"]
        n = len(df)

        swing_highs = [False] * n
        swing_lows = [False] * n

        for i in range(swing_len, n - swing_len):
            # 스윙 하이
            is_high = True
            for k in range(1, swing_len + 1):
                if df.iloc[i]["high"] <= df.iloc[i - k]["high"] or df.iloc[i]["high"] <= df.iloc[i + k]["high"]:
                    is_high = False
                    break
            swing_highs[i] = is_high

            # 스윙 로우
            is_low = True
            for k in range(1, swing_len + 1):
                if df.iloc[i]["low"] >= df.iloc[i - k]["low"] or df.iloc[i]["low"] >= df.iloc[i + k]["low"]:
                    is_low = False
                    break
            swing_lows[i] = is_low

        return swing_highs, swing_lows

    def _calculate_daily_tr(self, df):
        """일별 True Range 합계 (최적화된 버전)"""
        df_copy = df.copy()
        df_copy["date"] = df_copy["time"].dt.date

        # 각 날짜별로 누적 TR 계산
        result = []
        current_date = None
        daily_cumulative = 0

        for _, row in df_copy.iterrows():
            if row["date"] != current_date:
                # 새로운 날짜 시작
                current_date = row["date"]
                daily_cumulative = row["tr"]
            else:
                # 같은 날짜 내에서 누적
                daily_cumulative += row["tr"]

            result.append(daily_cumulative)

        return result

    def _calculate_rr_percentile(self, df):
        """Realized Range Percentile 계산 (최적화된 버전)"""
        df_copy = df.copy()
        df_copy["date"] = df_copy["time"].dt.date

        # 각 날짜별 최종 TR (일중 마지막 누적값)
        daily_final_tr = df_copy.groupby("date")["daily_tr"].last()

        # 20일 롤링 윈도우로 퍼센타일 계산
        percentiles = []
        lookback = 20

        daily_tr_values = daily_final_tr.values
        for i in range(len(daily_tr_values)):
            if i < lookback:
                percentiles.append(0.5)  # 초기값
            else:
                # 과거 20일 데이터와 비교
                past_values = daily_tr_values[i - lookback : i]
                current_value = daily_tr_values[i]
                percentile = (past_values < current_value).sum() / len(past_values)
                percentiles.append(percentile)

        # 날짜별 퍼센타일 매핑
        date_to_percentile = dict(zip(daily_final_tr.index, percentiles))

        # 각 행에 매핑
        result = []
        for _, row in df_copy.iterrows():
            result.append(date_to_percentile.get(row["date"], 0.5))

        return result

    def _calculate_displacement(self, df):
        """디스플레이스먼트 계산"""
        body = abs(df["close"] - df["open"])
        range_size = df["high"] - df["low"]

        # 평균 바디와 레인지
        avg_body = body.rolling(10).mean()
        avg_range = range_size.rolling(10).mean()

        # 디스플레이스먼트 조건
        body_disp = body >= (self.params["disp_mult"] * avg_body)
        range_disp = range_size >= (self.params["disp_mult"] * avg_range)

        return body_disp | range_disp

    def find_session_levels(self):
        """세션별 고저점 찾기"""
        df = self.df
        session_levels = {}

        # 날짜별로 그룹화
        df["date"] = df["time"].dt.date

        for date in df["date"].unique():
            day_data = df[df["date"] == date].copy()

            # 아시아 세션 고저점
            asia_data = day_data[day_data["session"] == "asia"]
            if len(asia_data) > 0:
                asia_high = asia_data["high"].max()
                asia_low = asia_data["low"].min()

                session_levels[date] = {"asia_high": asia_high, "asia_low": asia_low}

        return session_levels

    def detect_sweeps(self, session_levels):
        """스윕 패턴 감지"""
        df = self.df
        sweeps = []

        for i in range(len(df)):
            row = df.iloc[i]
            date = row["date"]

            if date not in session_levels:
                continue

            levels = session_levels[date]

            # 런던/NY 세션에서만 스윕 감지
            if row["session"] not in ["london", "ny", "london_ny"]:
                continue

            # 상승 스윕 (아시아 고점 돌파 후 복귀)
            if row["high"] > levels["asia_high"] and row["close"] < levels["asia_high"]:

                # 꼬리 비율 확인
                wick_size = row["high"] - max(row["open"], row["close"])
                total_range = row["high"] - row["low"]

                if total_range > 0:
                    wick_ratio = wick_size / total_range

                    if wick_ratio >= self.params["sweep_wick_mult"]:
                        sweeps.append(
                            {
                                "index": i,
                                "type": "bullish_sweep",
                                "sweep_level": levels["asia_high"],
                                "sweep_high": row["high"],
                                "wick_ratio": wick_ratio,
                                "time": row["time"],
                            }
                        )

            # 하락 스윕 (아시아 저점 하회 후 복귀)
            if row["low"] < levels["asia_low"] and row["close"] > levels["asia_low"]:

                # 꼬리 비율 확인
                wick_size = min(row["open"], row["close"]) - row["low"]
                total_range = row["high"] - row["low"]

                if total_range > 0:
                    wick_ratio = wick_size / total_range

                    if wick_ratio >= self.params["sweep_wick_mult"]:
                        sweeps.append(
                            {
                                "index": i,
                                "type": "bearish_sweep",
                                "sweep_level": levels["asia_low"],
                                "sweep_low": row["low"],
                                "wick_ratio": wick_ratio,
                                "time": row["time"],
                            }
                        )

        return sweeps

    def generate_signals(self):
        """트레이딩 신호 생성"""
        print("🔍 신호 생성 중...")

        # 세션 레벨 찾기
        session_levels = self.find_session_levels()

        # 스윕 감지
        sweeps = self.detect_sweeps(session_levels)

        signals = []
        df = self.df

        for sweep in sweeps:
            i = sweep["index"]

            # 다음 몇 개 바에서 디스플레이스먼트 확인
            for j in range(i + 1, min(i + 4, len(df))):  # 최대 3바 후까지
                next_row = df.iloc[j]

                # 레짐 필터 (변동성)
                if next_row["rr_percentile"] < self.params["rr_percentile"]:
                    continue

                # 펀딩 시간 회피
                if self._is_funding_time(next_row):
                    continue

                # 디스플레이스먼트 확인
                if not next_row["displacement"]:
                    continue

                # 신호 생성
                if sweep["type"] == "bullish_sweep":
                    # 상승 디스플레이스먼트 확인
                    if next_row["close"] > next_row["open"]:
                        # 스톱은 스윕 레벨 아래
                        stop_price = sweep["sweep_level"] - (self.params["stop_atr_mult"] * next_row["atr"])
                        risk = next_row["close"] - stop_price
                        target_price = next_row["close"] + (self.params["target_r"] * risk)

                        signals.append(
                            {
                                "index": j,
                                "type": "long",
                                "entry_price": next_row["close"],
                                "stop_price": stop_price,
                                "target_price": target_price,
                                "sweep_data": sweep,
                                "time": next_row["time"],
                                "atr": next_row["atr"],
                            }
                        )
                        break

                elif sweep["type"] == "bearish_sweep":
                    # 하락 디스플레이스먼트 확인
                    if next_row["close"] < next_row["open"]:
                        # 스톱은 스윕 레벨 위
                        stop_price = sweep["sweep_level"] + (self.params["stop_atr_mult"] * next_row["atr"])
                        risk = stop_price - next_row["close"]
                        target_price = next_row["close"] - (self.params["target_r"] * risk)

                        signals.append(
                            {
                                "index": j,
                                "type": "short",
                                "entry_price": next_row["close"],
                                "stop_price": stop_price,
                                "target_price": target_price,
                                "sweep_data": sweep,
                                "time": next_row["time"],
                                "atr": next_row["atr"],
                            }
                        )
                        break

        self.signals = signals
        print(f"✅ {len(signals)}개 신호 생성 완료")

        return signals

    def _is_funding_time(self, row):
        """펀딩 시간 확인"""
        hour = row["hour"]
        minute = row["minute"]

        for funding_hour in self.params["funding_hours"]:
            # 펀딩 시간 전후 15분 회피
            if (
                (funding_hour == hour and minute == 0)
                or (funding_hour - 1 == hour and minute == 45)
                or (funding_hour == hour and minute == 15)
            ):
                return True
        return False

    def backtest(self):
        """고급 리스크 관리가 적용된 백테스트 실행"""
        if not self.signals:
            print("❌ 신호가 없습니다. generate_signals()를 먼저 실행하세요.")
            return

        print("📈 고급 리스크 관리 백테스트 실행 중...")

        trades = []
        df = self.df
        equity_curve = [self.initial_balance]

        for i, signal in enumerate(self.signals):
            if i % 100 == 0 and i > 0:
                print(f"   진행률: {i}/{len(self.signals)} ({i/len(self.signals)*100:.1f}%)")

            # 현재 계좌 상태 확인
            account_status = self.risk_manager.get_account_status()
            # 최소 주문 금액의 2배 이상 있어야 거래 가능
            min_balance_required = self.risk_manager.params.min_notional_usdt * 2
            if account_status["balance"] < min_balance_required:
                print(
                    f"⚠️ 계좌 잔고 부족으로 거래 중단 (필요: ${min_balance_required}, 현재: ${account_status['balance']:.2f})"
                )
                break
            entry_idx = signal["index"]
            entry_price = signal["entry_price"]
            stop_price = signal["stop_price"]
            target_price = signal["target_price"]
            trade_type = signal["type"]
            atr = signal["atr"]

            # 최적 포지션 계산
            position_info = self.risk_manager.calculate_optimal_position(entry_price, stop_price, atr, trade_type)
            position_info = self.risk_manager.validate_position(position_info, entry_price, stop_price, trade_type)

            # 거래 추적
            trade = {
                "entry_time": signal["time"],
                "entry_price": entry_price,
                "entry_index": entry_idx,
                "type": trade_type,
                "stop_price": stop_price,
                "target_price": target_price,
                "position_size": position_info["position_size"],
                "leverage": position_info["leverage"],
                "required_margin": position_info["required_margin"],
                "liquidation_price": position_info["liquidation_price"],
                "exit_time": None,
                "exit_price": None,
                "exit_reason": None,
                "pnl": 0,
                "roe_pct": 0,
                "bars_held": 0,
                "max_favorable": 0,
                "max_adverse": 0,
            }

            # 다음 바부터 출구 찾기
            max_fav = 0
            max_adv = 0

            for j in range(entry_idx + 1, min(entry_idx + self.params["time_stop_bars"] + 1, len(df))):
                bar = df.iloc[j]

                if trade_type == "long":
                    # 유리한/불리한 움직임 추적
                    favorable = bar["high"] - entry_price
                    adverse = entry_price - bar["low"]

                    max_fav = max(max_fav, favorable)
                    max_adv = max(max_adv, adverse)

                    # 청산 확인 (우선순위 최고)
                    if bar["low"] <= position_info["liquidation_price"]:
                        pnl_result = self.risk_manager.calculate_pnl(
                            position_info, entry_price, position_info["liquidation_price"], trade_type
                        )
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": position_info["liquidation_price"],
                                "exit_reason": "liquidation",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

                    # 스톱 히트
                    if bar["low"] <= stop_price:
                        pnl_result = self.risk_manager.calculate_pnl(position_info, entry_price, stop_price, trade_type)
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": stop_price,
                                "exit_reason": "stop_loss",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

                    # 타겟 히트
                    if bar["high"] >= target_price:
                        pnl_result = self.risk_manager.calculate_pnl(position_info, entry_price, target_price, trade_type)
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": target_price,
                                "exit_reason": "target",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

                else:  # short
                    # 유리한/불리한 움직임 추적
                    favorable = entry_price - bar["low"]
                    adverse = bar["high"] - entry_price

                    max_fav = max(max_fav, favorable)
                    max_adv = max(max_adv, adverse)

                    # 청산 확인 (우선순위 최고)
                    if bar["high"] >= position_info["liquidation_price"]:
                        pnl_result = self.risk_manager.calculate_pnl(
                            position_info, entry_price, position_info["liquidation_price"], trade_type
                        )
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": position_info["liquidation_price"],
                                "exit_reason": "liquidation",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

                    # 스톱 히트
                    if bar["high"] >= stop_price:
                        pnl_result = self.risk_manager.calculate_pnl(position_info, entry_price, stop_price, trade_type)
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": stop_price,
                                "exit_reason": "stop_loss",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

                    # 타겟 히트
                    if bar["low"] <= target_price:
                        pnl_result = self.risk_manager.calculate_pnl(position_info, entry_price, target_price, trade_type)
                        trade.update(
                            {
                                "exit_time": bar["time"],
                                "exit_price": target_price,
                                "exit_reason": "target",
                                "bars_held": j - entry_idx,
                                "pnl": pnl_result["pnl_amount"],
                                "roe_pct": pnl_result["roe_pct"],
                            }
                        )
                        break

            # 시간 스톱 (루프가 끝까지 갔을 경우)
            if trade["exit_time"] is None:
                final_bar = df.iloc[min(entry_idx + self.params["time_stop_bars"], len(df) - 1)]
                exit_price = final_bar["close"]

                pnl_result = self.risk_manager.calculate_pnl(position_info, entry_price, exit_price, trade_type)

                trade.update(
                    {
                        "exit_time": final_bar["time"],
                        "exit_price": exit_price,
                        "exit_reason": "time_stop",
                        "bars_held": self.params["time_stop_bars"],
                        "pnl": pnl_result["pnl_amount"],
                        "roe_pct": pnl_result["roe_pct"],
                    }
                )

            trade["max_favorable"] = max_fav
            trade["max_adverse"] = max_adv

            # 계좌 잔고 업데이트
            self.risk_manager.update_account_balance(trade["pnl"])
            equity_curve.append(self.risk_manager.params.account_balance)

            trades.append(trade)

        self.trades = trades
        self.equity_curve = equity_curve

        final_balance = self.risk_manager.params.account_balance
        total_return = (final_balance - self.initial_balance) / self.initial_balance * 100

        print(f"✅ {len(trades)}개 거래 완료")
        print(f"💰 최종 계좌 잔고: ${final_balance:,.2f}")
        print(f"📈 총 수익률: {total_return:.2f}%")

        return trades

    def calculate_performance(self):
        """성과 분석"""
        if not self.trades:
            print("❌ 거래 데이터가 없습니다.")
            return None

        trades_df = pd.DataFrame(self.trades)

        # 기본 통계
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df["pnl"] > 0])
        losing_trades = len(trades_df[trades_df["pnl"] < 0])

        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

        # 수익률 통계
        total_pnl = trades_df["pnl"].sum()
        avg_win = trades_df[trades_df["pnl"] > 0]["pnl"].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df["pnl"] < 0]["pnl"].mean() if losing_trades > 0 else 0

        profit_factor = (
            abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 and avg_loss != 0 else float("inf")
        )

        # 최대 연속 손실
        consecutive_losses = 0
        max_consecutive_losses = 0

        for pnl in trades_df["pnl"]:
            if pnl < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0

        # 거래 기간 분석
        trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
        trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])

        start_date = trades_df["entry_time"].min()
        end_date = trades_df["exit_time"].max()
        total_days = (end_date - start_date).days

        performance = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_consecutive_losses": max_consecutive_losses,
            "avg_bars_held": trades_df["bars_held"].mean(),
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "trades_per_month": total_trades / (total_days / 30) if total_days > 0 else 0,
        }

        return performance, trades_df

    def print_performance_report(self):
        """성과 리포트 출력"""
        perf, trades_df = self.calculate_performance()

        if perf is None:
            return

        print("\n" + "=" * 80)
        print("📊 백테스트 성과 리포트")
        print("=" * 80)

        print(
            f"📅 기간: {perf['start_date'].strftime('%Y-%m-%d')} ~ {perf['end_date'].strftime('%Y-%m-%d')} ({perf['total_days']}일)"
        )
        print(f"📈 총 거래 수: {perf['total_trades']}개")
        print(f"🎯 승률: {perf['win_rate']:.1f}% ({perf['winning_trades']}승 {perf['losing_trades']}패)")

        print(f"\n💰 수익성:")
        print(f"   총 PnL: ${perf['total_pnl']:.2f}")
        print(f"   평균 승리: ${perf['avg_win']:.2f}")
        print(f"   평균 손실: ${perf['avg_loss']:.2f}")
        print(f"   Profit Factor: {perf['profit_factor']:.2f}")

        print(f"\n⏱️ 거래 특성:")
        print(f"   평균 보유 기간: {perf['avg_bars_held']:.1f}바 ({perf['avg_bars_held']*15:.0f}분)")
        print(f"   월 평균 거래: {perf['trades_per_month']:.1f}개")
        print(f"   최대 연속 손실: {perf['max_consecutive_losses']}회")

        # 거래 유형별 분석
        long_trades = trades_df[trades_df["type"] == "long"]
        short_trades = trades_df[trades_df["type"] == "short"]

        print(f"\n📊 거래 유형별:")
        if len(long_trades) > 0:
            long_win_rate = len(long_trades[long_trades["pnl"] > 0]) / len(long_trades) * 100
            print(f"   롱: {len(long_trades)}개, 승률 {long_win_rate:.1f}%, PnL ${long_trades['pnl'].sum():.2f}")

        if len(short_trades) > 0:
            short_win_rate = len(short_trades[short_trades["pnl"] > 0]) / len(short_trades) * 100
            print(f"   숏: {len(short_trades)}개, 승률 {short_win_rate:.1f}%, PnL ${short_trades['pnl'].sum():.2f}")

        # 종료 사유별 분석
        print(f"\n🚪 종료 사유별:")
        exit_reasons = trades_df["exit_reason"].value_counts()
        for reason, count in exit_reasons.items():
            pct = count / len(trades_df) * 100
            reason_pnl = trades_df[trades_df["exit_reason"] == reason]["pnl"].sum()
            print(f"   {reason}: {count}개 ({pct:.1f}%), PnL ${reason_pnl:.2f}")

    def run_full_backtest(self):
        """전체 백테스트 실행"""
        print("🚀 전체 백테스트 시작")
        print("=" * 80)

        # 1. 데이터 로드
        self.load_data()

        # 2. 신호 생성
        self.generate_signals()

        # 3. 백테스트 실행
        self.backtest()

        # 4. 성과 분석
        self.print_performance_report()

        return self.trades


def main():
    """메인 실행 함수"""
    strategy = ETHSessionStrategy()
    trades = strategy.run_full_backtest()

    if trades:
        print(f"\n✅ 백테스트 완료! {len(trades)}개 거래 분석됨")
    else:
        print("\n❌ 거래가 생성되지 않았습니다.")


if __name__ == "__main__":
    main()
