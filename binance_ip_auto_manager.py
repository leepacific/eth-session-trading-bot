#!/usr/bin/env python3
"""
바이낸스 API IP 자동 관리 시스템
Railway IP 변경 시 자동으로 바이낸스 허용 목록 업데이트
"""

import requests
import json
import os
import time
from datetime import datetime

class BinanceIPManager:
    def __init__(self):
        self.current_ip = None
        self.last_known_ip = None
        
    def get_current_railway_ip(self):
        """현재 Railway IP 확인"""
        try:
            # Railway에서 실행 중인 경우 Railway API를 통해 IP 확인
            response = requests.get("https://httpbin.org/ip", timeout=10)
            if response.status_code == 200:
                ip_data = response.json()
                return ip_data.get('origin', '').strip()
        except:
            pass
        
        # 대체 IP 확인 서비스들
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://ipapi.co/json/",
            "https://api.myip.com"
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                data = response.json()
                ip = data.get('ip') or data.get('origin')
                if ip:
                    return ip.strip()
            except:
                continue
        
        return None
    
    def check_ip_change(self):
        """IP 변경 확인"""
        self.current_ip = self.get_current_railway_ip()
        
        if not self.current_ip:
            return {'status': 'error', 'message': 'IP를 확인할 수 없습니다'}
        
        # 이전 IP와 비교
        ip_changed = self.last_known_ip and self.last_known_ip != self.current_ip
        
        result = {
            'status': 'success',
            'current_ip': self.current_ip,
            'previous_ip': self.last_known_ip,
            'ip_changed': ip_changed,
            'timestamp': datetime.now().isoformat()
        }
        
        if ip_changed:
            print(f"🚨 IP 변경 감지!")
            print(f"   이전: {self.last_known_ip}")
            print(f"   현재: {self.current_ip}")
        
        self.last_known_ip = self.current_ip
        return result
    
    def create_binance_ip_update_guide(self, ip):
        """바이낸스 IP 업데이트 가이드 생성"""
        
        guide = f"""
🔐 바이낸스 API IP 업데이트 가이드

현재 Railway IP: {ip}
업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 수동 업데이트 단계:

1. 바이낸스 API 관리 접속
   https://www.binance.com/en/my/settings/api-management

2. API 키 편집
   - 기존 API 키 옆의 'Edit' 버튼 클릭
   - 보안 인증 완료 (SMS, 이메일, Google Authenticator)

3. IP 제한 업데이트
   - 'IP Access Restrictions' 섹션에서
   - 기존 IP 삭제 (있는 경우)
   - 새 IP 추가: {ip}
   - 'Confirm' 버튼 클릭

4. 권한 설정 확인
   ✅ Enable Reading
   ✅ Enable Spot & Margin Trading
   ❌ Enable Withdrawals (보안상 비활성화)

5. 연결 테스트
   https://eth-trading-bot-production.up.railway.app/test-binance

⚠️ 중요: IP 업데이트 후 5-10분 정도 기다린 후 테스트하세요.
"""
        
        return guide

def create_ip_monitoring_system():
    """IP 모니터링 시스템 생성"""
    
    monitoring_code = '''
import schedule
import time
from binance_ip_auto_manager import BinanceIPManager

def monitor_ip_changes():
    """IP 변경 모니터링"""
    manager = BinanceIPManager()
    
    result = manager.check_ip_change()
    
    if result['status'] == 'success':
        if result['ip_changed']:
            # IP 변경 감지 시 알림
            print("🚨 Railway IP 변경 감지!")
            print(f"새 IP: {result['current_ip']}")
            
            # 업데이트 가이드 생성
            guide = manager.create_binance_ip_update_guide(result['current_ip'])
            
            # 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"binance_ip_update_guide_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(guide)
            
            print(f"📄 업데이트 가이드 저장: {filename}")
            
            # 여기에 이메일/슬랙 알림 코드 추가 가능
            # send_notification(result['current_ip'])
        
        else:
            print(f"✅ IP 안정: {result['current_ip']}")
    
    else:
        print(f"❌ IP 확인 실패: {result['message']}")

# 스케줄 설정
schedule.every(30).minutes.do(monitor_ip_changes)  # 30분마다 확인
schedule.every().hour.do(monitor_ip_changes)       # 매시간 확인

print("🔍 IP 모니터링 시작...")
print("30분마다 Railway IP 변경을 확인합니다.")

while True:
    schedule.run_pending()
    time.sleep(60)  # 1분마다 스케줄 확인
'''
    
    return monitoring_code

def main():
    """메인 실행"""
    print("🔐 바이낸스 IP 자동 관리 시스템")
    print("=" * 80)
    
    manager = BinanceIPManager()
    
    # 현재 IP 확인
    result = manager.check_ip_change()
    
    if result['status'] == 'success':
        current_ip = result['current_ip']
        print(f"🌐 현재 Railway IP: {current_ip}")
        
        # 바이낸스 업데이트 가이드 생성
        guide = manager.create_binance_ip_update_guide(current_ip)
        
        # 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        guide_filename = f"binance_ip_update_guide_{timestamp}.txt"
        
        with open(guide_filename, 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print(f"📄 업데이트 가이드 저장: {guide_filename}")
        
        # 모니터링 시스템 코드 생성
        monitoring_code = create_ip_monitoring_system()
        
        with open('ip_monitoring_system.py', 'w', encoding='utf-8') as f:
            f.write(monitoring_code)
        
        print(f"📄 모니터링 시스템 저장: ip_monitoring_system.py")
        
        # 즉시 사용 가능한 IP 출력
        print(f"\n🎯 바이낸스에 추가할 IP:")
        print("=" * 40)
        print(f"{current_ip}")
        print("=" * 40)
        
        print(f"\n💡 사용 방법:")
        print("1. 위 IP를 바이낸스 API 관리에서 허용 목록에 추가")
        print("2. python ip_monitoring_system.py 실행하여 지속적 모니터링")
        print("3. IP 변경 시 자동으로 새 가이드 파일 생성")
        
    else:
        print(f"❌ IP 확인 실패: {result['message']}")

if __name__ == "__main__":
    main()