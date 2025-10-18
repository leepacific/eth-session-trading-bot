#!/usr/bin/env python3
"""
기존 Railway Trading Bot에 최적화된 파라미터 업데이트
Binance와 연결된 기존 봇의 파라미터를 업데이트
"""

import json
import requests
import os
from datetime import datetime

def update_railway_parameters():
    """기존 Railway Trading Bot에 최적화된 파라미터 전송"""
    
    # 실제 Railway Trading Bot URL (여기에 실제 URL 입력)
    railway_url = os.getenv('RAILWAY_TRADING_BOT_URL', 'https://your-trading-bot.railway.app')
    
    if railway_url == 'https://your-trading-bot.railway.app':
        print("❌ 실제 Railway Trading Bot URL을 설정해주세요")
        print("방법 1: export RAILWAY_TRADING_BOT_URL=https://your-actual-bot.railway.app")
        print("방법 2: 이 스크립트의 railway_url 변수를 직접 수정")
        return False
    
    try:
        # 현재 최적화된 파라미터 로드
        with open('config/current_parameters.json', 'r') as f:
            params_data = json.load(f)
        
        print("📊 현재 최적화된 파라미터:")
        for param, value in params_data['parameters'].items():
            print(f"   {param}: {value:.4f}")
        
        # 기존 Trading Bot의 API 엔드포인트 (실제 엔드포인트에 맞게 수정 필요)
        # 일반적인 엔드포인트들:
        # - /api/config/update
        # - /api/parameters/update  
        # - /config/trading-parameters
        # - /update-strategy-params
        
        update_url = f"{railway_url}/api/config/update"  # 실제 엔드포인트로 변경 필요
        
        # 기존 봇의 파라미터 형식에 맞게 변환
        trading_params = {
            'strategy_config': {
                'target_reward_ratio': params_data['parameters']['target_r'],
                'stop_loss_atr_multiplier': params_data['parameters']['stop_atr_mult'],
                'swing_length': int(params_data['parameters']['swing_len']),
                'risk_reward_percentile': params_data['parameters']['rr_percentile'],
                'atr_length': int(params_data['parameters']['atr_len']),
                'session_strength_multiplier': params_data['parameters']['session_strength'],
                'volume_filter_threshold': params_data['parameters']['volume_filter']
            },
            'metadata': {
                'optimization_timestamp': params_data['timestamp'],
                'optimization_source': 'weekly_auto_optimization',
                'optimization_score': params_data.get('score', 0),
                'update_timestamp': datetime.now().isoformat()
            }
        }
        
        print(f"\n🚀 Railway에 파라미터 업데이트 중...")
        print(f"URL: {update_url}")
        
        # API 호출
        response = requests.post(
            update_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 파라미터 업데이트 성공!")
            print(f"응답: {result}")
            
            # 상태 확인
            status_url = f"{railway_url}/status"
            status_response = requests.get(status_url, timeout=10)
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"\n📊 Trading Bot 상태:")
                print(f"   활성화: {status.get('is_active', False)}")
                print(f"   마지막 업데이트: {status.get('last_update', 'N/A')}")
                print(f"   총 거래: {status.get('total_trades', 0)}")
                print(f"   현재 잔고: ${status.get('current_balance', 0):.2f}")
            
            return True
            
        else:
            print(f"❌ 업데이트 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except FileNotFoundError:
        print("❌ config/current_parameters.json 파일을 찾을 수 없습니다")
        print("먼저 최적화를 실행해주세요: python run_optimization.py")
        return False
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Railway 앱에 연결할 수 없습니다: {railway_url}")
        print("URL이 올바른지 확인하고 앱이 실행 중인지 확인해주세요")
        return False
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def check_railway_status(railway_url):
    """Railway 앱 상태 확인"""
    try:
        health_url = f"{railway_url}/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Railway 앱 상태: {health.get('status', 'unknown')}")
            print(f"   타임스탬프: {health.get('timestamp', 'N/A')}")
            print(f"   봇 활성화: {health.get('bot_active', False)}")
            return True
        else:
            print(f"⚠️ 상태 확인 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 상태 확인 오류: {e}")
        return False

def main():
    """메인 실행"""
    print("🚀 Railway 파라미터 업데이트")
    print("="*40)
    
    railway_url = os.getenv('RAILWAY_APP_URL', 'https://your-app.railway.app')
    
    # 1. Railway 앱 상태 확인
    print("1️⃣ Railway 앱 상태 확인...")
    if not check_railway_status(railway_url):
        print("Railway 앱이 실행되지 않거나 접근할 수 없습니다")
        return 1
    
    # 2. 파라미터 업데이트
    print("\n2️⃣ 파라미터 업데이트...")
    if update_railway_parameters():
        print("\n🎉 모든 작업 완료!")
        print("Trading Bot이 새로운 파라미터로 실행 중입니다.")
        return 0
    else:
        print("\n❌ 파라미터 업데이트 실패")
        return 1

if __name__ == "__main__":
    exit(main())