#!/usr/bin/env python3
"""
실제 거래 시스템 데모
- 가격 확인
- 계좌 잔고 확인  
- 주문 실행 과정
- 포지션 관리
"""

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime
from urllib.parse import urlencode

class LiveTradingDemo:
    def __init__(self):
        """실제 거래 시스템 초기화"""
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = "https://fapi.binance.com"
        self.symbol = "ETHUSDT"
        
        print("🚀 실제 거래 시스템 데모")
        print("=" * 80)
        print(f"📊 거래 심볼: {self.symbol}")
        print(f"🔗 API 엔드포인트: {self.base_url}")
        print(f"🔑 API 키 상태: {'✅ 설정됨' if self.api_key else '❌ 미설정'}")
    
    def _generate_signature(self, params):
        """API 서명 생성"""
        query_string = urlencode(params)
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, endpoint, method='GET', params=None, signed=False):
        """API 요청 실행"""
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            signature = self._generate_signature(params)
            params['signature'] = signature
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_current_price(self):
        """1. 현재 가격 확인"""
        print(f"\n💰 1. 현재 가격 확인")
        print("-" * 40)
        
        # 현재 가격 조회
        result = self._make_request('/fapi/v1/ticker/price', params={'symbol': self.symbol})
        
        if result['success']:
            price = float(result['data']['price'])
            print(f"✅ {self.symbol} 현재 가격: ${price:,.2f}")
            
            # 24시간 변동률도 확인
            stats_result = self._make_request('/fapi/v1/ticker/24hr', params={'symbol': self.symbol})
            if stats_result['success']:
                stats = stats_result['data']
                change_percent = float(stats['priceChangePercent'])
                volume = float(stats['volume'])
                
                print(f"📈 24시간 변동률: {change_percent:+.2f}%")
                print(f"📊 24시간 거래량: {volume:,.0f} ETH")
            
            return price
        else:
            print(f"❌ 가격 조회 실패: {result.get('error', 'Unknown error')}")
            return None
    
    def check_account_balance(self):
        """2. 계좌 잔고 확인"""
        print(f"\n💳 2. 계좌 잔고 확인")
        print("-" * 40)
        
        result = self._make_request('/fapi/v2/account', signed=True)
        
        if result['success']:
            account_data = result['data']
            
            # 총 잔고
            total_balance = float(account_data['totalWalletBalance'])
            available_balance = float(account_data['availableBalance'])
            
            print(f"💰 총 잔고: ${total_balance:,.2f} USDT")
            print(f"💵 사용 가능: ${available_balance:,.2f} USDT")
            
            # 현재 포지션들
            positions = account_data.get('positions', [])
            active_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            print(f"📊 활성 포지션: {len(active_positions)}개")
            
            for pos in active_positions:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                pnl = float(pos['unrealizedPnl'])
                
                side = "LONG" if size > 0 else "SHORT"
                print(f"   {symbol}: {side} {abs(size):.4f}, 진입가: ${entry_price:.2f}, PnL: ${pnl:+.2f}")
            
            return {
                'total_balance': total_balance,
                'available_balance': available_balance,
                'active_positions': len(active_positions)
            }
        else:
            print(f"❌ 계좌 정보 조회 실패")
            return None
    
    def demonstrate_order_types(self, current_price):
        """3. 주문 유형 설명"""
        print(f"\n📋 3. 주문 유형 및 파라미터")
        print("-" * 40)
        
        print("🎯 지원하는 주문 유형:")
        print("   • MARKET: 시장가 주문 (즉시 체결)")
        print("   • LIMIT: 지정가 주문 (특정 가격에서 체결)")
        print("   • STOP: 스탑 주문 (손절/익절)")
        print("   • STOP_MARKET: 스탑 시장가")
        print("   • TAKE_PROFIT: 이익실현 주문")
        
        print(f"\n📊 주문 파라미터 예시 (현재가: ${current_price:.2f}):")
        
        # 롱 포지션 예시
        long_entry = current_price * 0.999  # 현재가보다 0.1% 낮게
        long_stop = current_price * 0.985   # 1.5% 손절
        long_target = current_price * 1.045  # 4.5% 익절
        
        print(f"🟢 롱 포지션 예시:")
        print(f"   진입: ${long_entry:.2f} (LIMIT)")
        print(f"   손절: ${long_stop:.2f} (STOP_MARKET)")
        print(f"   익절: ${long_target:.2f} (TAKE_PROFIT)")
        
        # 숏 포지션 예시
        short_entry = current_price * 1.001  # 현재가보다 0.1% 높게
        short_stop = current_price * 1.015   # 1.5% 손절
        short_target = current_price * 0.955  # 4.5% 익절
        
        print(f"🔴 숏 포지션 예시:")
        print(f"   진입: ${short_entry:.2f} (LIMIT)")
        print(f"   손절: ${short_stop:.2f} (STOP_MARKET)")
        print(f"   익절: ${short_target:.2f} (TAKE_PROFIT)")
        
        return {
            'long_entry': long_entry,
            'long_stop': long_stop,
            'long_target': long_target,
            'short_entry': short_entry,
            'short_stop': short_stop,
            'short_target': short_target
        }
    
    def calculate_position_size(self, account_balance, entry_price, stop_price, risk_percent=0.05):
        """4. 포지션 사이즈 계산"""
        print(f"\n🧮 4. 포지션 사이즈 계산")
        print("-" * 40)
        
        # 리스크 금액 계산
        risk_amount = account_balance * risk_percent
        
        # 가격 리스크 계산
        price_risk = abs(entry_price - stop_price) / entry_price
        
        # 포지션 가치 계산
        position_value = risk_amount / price_risk
        
        # 포지션 사이즈 계산
        position_size = position_value / entry_price
        
        # 최소 주문 금액 확인 (20 USDT)
        min_notional = 20.0
        if position_value < min_notional:
            print(f"⚠️ 최소 주문 금액 조정: ${position_value:.2f} → ${min_notional:.2f}")
            position_value = min_notional
            position_size = position_value / entry_price
            actual_risk = position_value * price_risk
            print(f"   실제 리스크: ${actual_risk:.2f} ({actual_risk/account_balance*100:.1f}%)")
        
        # 레버리지 계산 (125배 최대)
        leverage = min(position_value / (account_balance * 0.1), 125)  # 계좌의 10%를 증거금으로 사용
        
        print(f"💰 계좌 잔고: ${account_balance:.2f}")
        print(f"🎯 리스크 비율: {risk_percent*100}%")
        print(f"💸 리스크 금액: ${risk_amount:.2f}")
        print(f"📊 가격 리스크: {price_risk*100:.2f}%")
        print(f"💎 포지션 가치: ${position_value:.2f}")
        print(f"⚖️ 포지션 사이즈: {position_size:.4f} ETH")
        print(f"🔢 레버리지: {leverage:.1f}x")
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'leverage': leverage,
            'risk_amount': risk_amount
        }
    
    def show_order_execution_process(self, order_params):
        """5. 주문 실행 과정 시뮬레이션"""
        print(f"\n🚀 5. 주문 실행 과정")
        print("-" * 40)
        
        print("📝 주문 실행 단계:")
        print("   1️⃣ 시장 분석 및 신호 생성")
        print("   2️⃣ 리스크 관리 및 포지션 사이즈 계산")
        print("   3️⃣ 주문 파라미터 설정")
        print("   4️⃣ 주문 전송")
        print("   5️⃣ 체결 확인")
        print("   6️⃣ 손절/익절 주문 설정")
        print("   7️⃣ 포지션 모니터링")
        
        print(f"\n📋 실제 주문 파라미터:")
        print(f"   심볼: {self.symbol}")
        print(f"   방향: BUY (LONG)")
        print(f"   타입: LIMIT")
        print(f"   수량: {order_params['position_size']:.4f} ETH")
        print(f"   가격: ${order_params['entry_price']:.2f}")
        print(f"   포지션사이드: LONG")
        print(f"   시간조건: GTC (Good Till Cancel)")
        
        # 실제 주문 JSON 예시
        order_json = {
            "symbol": self.symbol,
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{order_params['position_size']:.4f}",
            "price": f"{order_params['entry_price']:.2f}",
            "positionSide": "LONG"
        }
        
        print(f"\n💻 실제 API 호출:")
        print(f"POST {self.base_url}/fapi/v1/order")
        print(json.dumps(order_json, indent=2))
    
    def run_complete_demo(self):
        """전체 데모 실행"""
        print(f"\n🎬 실제 거래 시스템 완전 데모")
        print("=" * 80)
        
        # 1. 현재 가격 확인
        current_price = self.check_current_price()
        if not current_price:
            return
        
        # 2. 계좌 잔고 확인
        account_info = self.check_account_balance()
        if not account_info:
            return
        
        # 3. 주문 유형 설명
        order_examples = self.demonstrate_order_types(current_price)
        
        # 4. 포지션 사이즈 계산 (롱 예시)
        position_calc = self.calculate_position_size(
            account_info['available_balance'],
            order_examples['long_entry'],
            order_examples['long_stop']
        )
        
        # 5. 주문 실행 과정
        order_params = {
            'position_size': position_calc['position_size'],
            'entry_price': order_examples['long_entry']
        }
        self.show_order_execution_process(order_params)
        
        # 요약
        print(f"\n" + "=" * 80)
        print(f"📊 데모 요약")
        print("=" * 80)
        print(f"✅ 가격 확인: ${current_price:.2f}")
        print(f"✅ 계좌 잔고: ${account_info['total_balance']:.2f}")
        print(f"✅ 포지션 계산: {position_calc['position_size']:.4f} ETH")
        print(f"✅ 레버리지: {position_calc['leverage']:.1f}x")
        print(f"✅ 리스크 관리: ${position_calc['risk_amount']:.2f}")
        
        print(f"\n🎯 실제 거래 준비 완료!")
        print(f"   Railway Static IP: 208.77.246.15")
        print(f"   바이낸스 연결: ✅ 정상")
        print(f"   동적 리스크 관리: ✅ 활성화")

if __name__ == "__main__":
    demo = LiveTradingDemo()
    demo.run_complete_demo()