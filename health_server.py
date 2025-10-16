"""
Railway 배포를 위한 헬스체크 서버
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
import os
from datetime import datetime

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'eth-session-trading-bot',
                'version': '1.0.0'
            }
            
            self.wfile.write(json.dumps(health_data).encode())
        
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status_data = {
                'bot_status': 'running',
                'last_update': datetime.now().isoformat(),
                'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development')
            }
            
            self.wfile.write(json.dumps(status_data).encode())
        
        elif self.path == '/parameters':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 현재 최적 파라미터 반환
            current_params = self.get_current_parameters()
            
            self.wfile.write(json.dumps(current_params, indent=2).encode())
        
        elif self.path == '/optimization':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 최적화 상태 및 히스토리 반환
            optimization_info = self.get_optimization_info()
            
            self.wfile.write(json.dumps(optimization_info, indent=2).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def get_current_parameters(self):
        """현재 최적 파라미터 조회"""
        try:
            from eth_session_strategy import ETHSessionStrategy
            strategy = ETHSessionStrategy()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'source': 'current_strategy',
                'parameters': {
                    'swing_len': strategy.params.get('swing_len', 5),
                    'rr_percentile': strategy.params.get('rr_percentile', 0.2956456168878421),
                    'disp_mult': strategy.params.get('disp_mult', 1.1007752243798252),
                    'sweep_wick_mult': strategy.params.get('sweep_wick_mult', 0.5391008387578328),
                    'atr_len': strategy.params.get('atr_len', 32),
                    'stop_atr_mult': strategy.params.get('stop_atr_mult', 0.07468310011731281),
                    'target_r': strategy.params.get('target_r', 3.0721376531107074),
                    'time_stop_bars': strategy.params.get('time_stop_bars', 1),
                    'funding_avoid_bars': strategy.params.get('funding_avoid_bars', 1),
                    'min_volatility_rank': strategy.params.get('min_volatility_rank', 0.41615733983481445),
                    'session_strength': strategy.params.get('session_strength', 1.6815393680831972),
                    'volume_filter': strategy.params.get('volume_filter', 1.2163453246372455),
                    'trend_filter_len': strategy.params.get('trend_filter_len', 32)
                },
                'optimization_status': 'active',
                'next_optimization': 'Every Sunday 14:00 KST'
            }
        except Exception as e:
            return {
                'error': f'Failed to load parameters: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_optimization_info(self):
        """최적화 정보 조회"""
        try:
            import glob
            import os
            
            # 최근 최적화 결과 파일 찾기
            result_files = glob.glob('optimization_result_*.json')
            result_files.sort(reverse=True)  # 최신 순
            
            optimization_info = {
                'timestamp': datetime.now().isoformat(),
                'schedule': 'Every Sunday 14:00 KST',
                'status': 'scheduled',
                'last_optimization': None,
                'next_optimization': None,
                'recent_results': []
            }
            
            # 다음 실행 시간 계산
            from datetime import datetime, timedelta
            import pytz
            
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            
            # 다음 일요일 14:00 계산
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour >= 14:
                days_until_sunday = 7
            
            next_sunday = now + timedelta(days=days_until_sunday)
            next_optimization = next_sunday.replace(hour=14, minute=0, second=0, microsecond=0)
            
            optimization_info['next_optimization'] = next_optimization.isoformat()
            
            # 최근 결과 파일들 읽기 (최대 5개)
            for result_file in result_files[:5]:
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                        optimization_info['recent_results'].append({
                            'file': result_file,
                            'timestamp': result_data.get('timestamp'),
                            'duration_minutes': result_data.get('duration_minutes'),
                            'best_score': result_data.get('stage_results', {}).get('stage3', {}).get('best_score')
                        })
                        
                        if optimization_info['last_optimization'] is None:
                            optimization_info['last_optimization'] = result_data.get('end_time')
                            optimization_info['status'] = 'completed'
                except:
                    continue
            
            return optimization_info
            
        except Exception as e:
            return {
                'error': f'Failed to load optimization info: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def log_message(self, format, *args):
        # 로그 출력 억제
        pass

def start_health_server():
    """헬스체크 서버 시작"""
    port = int(os.getenv('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"🏥 헬스체크 서버 시작: http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    start_health_server()