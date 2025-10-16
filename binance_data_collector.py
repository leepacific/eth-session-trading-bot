"""
바이낸스 API를 통한 ETHUSDT.P 15분봉 데이터 수집기
목표: 100,000개 데이터 포인트 수집
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import hashlib
import hmac
from urllib.parse import urlencode

# 환경 변수 로드
load_dotenv()

class BinanceDataCollector:
    def __init__(self):
        """바이낸스 데이터 수집기 초기화"""
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # API 엔드포인트 설정
        if self.testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        # 데이터 수집 설정
        self.symbol = os.getenv('DATA_SYMBOL', 'ETHUSDT')
        self.interval = os.getenv('DATA_INTERVAL', '15m')
        self.target_points = int(os.getenv('DATA_POINTS_TARGET', '500000'))
        self.points_per_request = int(os.getenv('DATA_POINTS_PER_REQUEST', '1000'))
        
        # 요청 제한 (바이낸스 API 제한 준수)
        self.request_delay = 0.1  # 100ms 딜레이
        self.max_retries = 3
        
        print(f"🚀 바이낸스 데이터 수집기 초기화")
        print(f"   심볼: {self.symbol}")
        print(f"   간격: {self.interval}")
        print(f"   목표 데이터: {self.target_points:,}개")
        print(f"   배치 크기: {self.points_per_request}개")
        print(f"   예상 요청 수: {self.target_points // self.points_per_request}회")
        print(f"   테스트넷: {self.testnet}")
    
    def get_klines(self, symbol, interval, limit=1000, start_time=None, end_time=None):
        """K라인 데이터 가져오기"""
        endpoint = "/fapi/v1/klines"
        url = self.base_url + endpoint
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = int(start_time)
        if end_time:
            params['endTime'] = int(end_time)
        
        headers = {}
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    print(f"   ⚠️ Rate limit 도달, {wait_time}초 대기...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"   ❌ API 오류: {response.status_code} - {response.text}")
                    if attempt == self.max_retries - 1:
                        return None
                    time.sleep(1)
                    
            except Exception as e:
                print(f"   ❌ 요청 오류: {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)
        
        return None
    
    def collect_historical_data(self):
        """과거 데이터 수집"""
        print(f"\n📊 {self.symbol} {self.interval} 데이터 수집 시작")
        print("=" * 80)
        
        all_data = []
        total_requests = self.target_points // self.points_per_request
        
        # 현재 시간부터 과거로 거슬러 올라가며 수집
        end_time = int(datetime.now().timestamp() * 1000)
        
        for batch_num in range(total_requests):
            print(f"📥 배치 {batch_num + 1}/{total_requests} 수집 중...", end=" ")
            
            # API 요청
            klines = self.get_klines(
                symbol=self.symbol,
                interval=self.interval,
                limit=self.points_per_request,
                end_time=end_time
            )
            
            if klines is None:
                print("❌ 실패")
                break
            
            if len(klines) == 0:
                print("❌ 데이터 없음")
                break
            
            # 데이터 처리
            batch_data = []
            for kline in klines:
                batch_data.append({
                    'timestamp': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': kline[6],
                    'quote_volume': float(kline[7]),
                    'trades': int(kline[8]),
                    'taker_buy_base': float(kline[9]),
                    'taker_buy_quote': float(kline[10])
                })
            
            # 시간순 정렬 (과거부터)
            batch_data.sort(key=lambda x: x['timestamp'])
            all_data.extend(batch_data)
            
            # 다음 배치를 위한 end_time 업데이트
            end_time = batch_data[0]['timestamp'] - 1
            
            print(f"✅ {len(klines)}개 수집 (총 {len(all_data):,}개)")
            
            # 진행률 표시
            progress = (batch_num + 1) / total_requests * 100
            print(f"   진행률: {progress:.1f}% | 수집된 데이터: {len(all_data):,}/{self.target_points:,}")
            
            # API 제한 준수
            time.sleep(self.request_delay)
            
            # 목표 달성 확인
            if len(all_data) >= self.target_points:
                print(f"🎯 목표 달성! {len(all_data):,}개 데이터 수집 완료")
                break
        
        return all_data
    
    def process_and_save_data(self, raw_data):
        """데이터 처리 및 저장"""
        if not raw_data:
            print("❌ 저장할 데이터가 없습니다.")
            return None
        
        print(f"\n🔄 데이터 처리 중...")
        
        # DataFrame 생성
        df = pd.DataFrame(raw_data)
        
        # 시간 변환
        df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # 시간순 정렬
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 중복 제거
        initial_count = len(df)
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
        final_count = len(df)
        
        if initial_count != final_count:
            print(f"   중복 제거: {initial_count - final_count}개 제거됨")
        
        # 데이터 검증
        print(f"📋 데이터 검증:")
        print(f"   총 데이터 수: {len(df):,}개")
        print(f"   시작 시간: {df['time'].iloc[0]}")
        print(f"   종료 시간: {df['time'].iloc[-1]}")
        print(f"   기간: {(df['time'].iloc[-1] - df['time'].iloc[0]).days}일")
        
        # 가격 범위 확인
        print(f"   가격 범위: ${df['low'].min():.2f} ~ ${df['high'].max():.2f}")
        print(f"   평균 거래량: {df['volume'].mean():,.2f}")
        
        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/{self.symbol}_{self.interval}_{len(df)}points_{timestamp}.csv"
        
        # data 폴더 생성
        os.makedirs('data', exist_ok=True)
        
        # CSV 저장 (트레이딩에 필요한 컬럼만)
        trading_df = df[['time', 'open', 'high', 'low', 'close', 'volume']].copy()
        trading_df.to_csv(filename, index=False)
        
        print(f"💾 데이터 저장 완료: {filename}")
        
        # 상세 데이터도 별도 저장
        detailed_filename = f"data/{self.symbol}_{self.interval}_detailed_{len(df)}points_{timestamp}.csv"
        df.to_csv(detailed_filename, index=False)
        print(f"💾 상세 데이터 저장: {detailed_filename}")
        
        return filename, trading_df
    
    def run_collection(self):
        """전체 데이터 수집 프로세스 실행"""
        start_time = time.time()
        
        try:
            # 데이터 수집
            raw_data = self.collect_historical_data()
            
            if not raw_data:
                print("❌ 데이터 수집 실패")
                return None
            
            # 데이터 처리 및 저장
            result = self.process_and_save_data(raw_data)
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            print(f"\n🎉 데이터 수집 완료!")
            print(f"   실행 시간: {execution_time:.1f}초")
            print(f"   수집 속도: {len(raw_data)/execution_time:.1f} 포인트/초")
            
            return result
            
        except KeyboardInterrupt:
            print("\n⚠️ 사용자에 의해 중단되었습니다.")
            return None
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """메인 실행 함수"""
    print("🎯 바이낸스 ETHUSDT.P 15분봉 데이터 수집기")
    print("=" * 80)
    
    # API 키 확인
    if not os.getenv('BINANCE_API_KEY'):
        print("⚠️ 경고: BINANCE_API_KEY가 설정되지 않았습니다.")
        print("   공개 데이터만 수집 가능합니다.")
        
        choice = input("계속 진행하시겠습니까? (y/n): ")
        if choice.lower() != 'y':
            print("프로그램을 종료합니다.")
            return
    
    # 데이터 수집기 실행
    collector = BinanceDataCollector()
    result = collector.run_collection()
    
    if result:
        filename, df = result
        print(f"\n✅ 성공적으로 완료되었습니다!")
        print(f"   파일: {filename}")
        print(f"   데이터 수: {len(df):,}개")
        
        # 간단한 통계 표시
        print(f"\n📊 데이터 미리보기:")
        print(df.head().to_string(index=False))
        
    else:
        print("\n❌ 데이터 수집에 실패했습니다.")

if __name__ == "__main__":
    main()