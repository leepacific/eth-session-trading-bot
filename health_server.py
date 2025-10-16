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
        
        else:
            self.send_response(404)
            self.end_headers()
    
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