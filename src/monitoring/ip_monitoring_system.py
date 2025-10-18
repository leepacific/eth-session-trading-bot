
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
