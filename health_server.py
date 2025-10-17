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
        
        elif self.path == '/test-binance':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 바이낸스 연결 테스트 실행
            test_result = self.run_binance_test()
            
            self.wfile.write(json.dumps(test_result, indent=2).encode())
        
        elif self.path == '/test-tool':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # API 테스트 도구 페이지 반환
            test_tool_html = self.get_test_tool_page()
            self.wfile.write(test_tool_html.encode())
        
        elif self.path == '/debug':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 디버그 정보 반환
            debug_info = self.get_debug_info()
            self.wfile.write(json.dumps(debug_info, indent=2).encode())
        
        elif self.path == '/debug-binance':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 바이낸스 연결 상세 디버깅
            debug_result = self.run_binance_debug()
            self.wfile.write(json.dumps(debug_result, indent=2).encode())
        
        elif self.path == '/check-ip':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # IP 확인 (직접 vs 프록시)
            ip_check_result = self.check_outgoing_ip()
            self.wfile.write(json.dumps(ip_check_result, indent=2).encode())
        
        elif self.path == '/' or self.path == '':
            # 루트 경로 - 웰컴 페이지 반환
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            welcome_page = self.get_welcome_page()
            self.wfile.write(welcome_page.encode())
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                'error': 'Not Found',
                'message': f'The requested path {self.path} was not found',
                'available_endpoints': [
                    '/',
                    '/health',
                    '/status', 
                    '/parameters',
                    '/optimization',
                    '/test-binance',
                    '/test-tool'
                ],
                'timestamp': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(error_response, indent=2).encode())
    
    def get_test_tool_page(self):
        """API 테스트 도구 페이지 반환"""
        try:
            # web_test_tool.html 파일 읽기
            with open('web_test_tool.html', 'r', encoding='utf-8') as f:
                return f.read()
            
        except FileNotFoundError:
            # 파일이 없으면 간단한 테스트 페이지 반환
            return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧪 API 테스트 도구</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #2980b9; }
        .result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .success { background: #d5f4e6; border-left: 4px solid #27ae60; }
        .error { background: #fadbd8; border-left: 4px solid #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 API 테스트 도구</h1>
        <p>트레이딩 봇 API 상태 및 기능 테스트</p>
        
        <div style="margin: 20px 0;">
            <button class="btn" onclick="testEndpoint('/health')">헬스체크</button>
            <button class="btn" onclick="testEndpoint('/status')">상태 확인</button>
            <button class="btn" onclick="testEndpoint('/parameters')">파라미터</button>
            <button class="btn" onclick="testEndpoint('/optimization')">최적화 상태</button>
            <button class="btn" onclick="testEndpoint('/test-binance')">바이낸스 테스트</button>
        </div>
        
        <div id="results"></div>
    </div>
    
    <script>
        async function testEndpoint(endpoint) {
            const resultsDiv = document.getElementById('results');
            
            try {
                const response = await fetch(endpoint);
                const data = await response.json();
                
                const resultDiv = document.createElement('div');
                resultDiv.className = response.ok ? 'result success' : 'result error';
                resultDiv.innerHTML = `
                    <strong>${endpoint}</strong> (${response.status})<br>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
                
                resultsDiv.appendChild(resultDiv);
                
            } catch (error) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'result error';
                resultDiv.innerHTML = `
                    <strong>${endpoint}</strong> - 오류<br>
                    ${error.message}
                `;
                
                resultsDiv.appendChild(resultDiv);
            }
        }
    </script>
</body>
</html>
            """
    
    def get_debug_info(self):
        """디버그 정보 수집"""
        return {
            'timestamp': datetime.now().isoformat(),
            'server_info': {
                'port': os.getenv('PORT', '8080'),
                'railway_environment': os.getenv('RAILWAY_ENVIRONMENT', 'not_set')
            },
            'environment_variables': {
                'RAILWAY_ENVIRONMENT': os.getenv('RAILWAY_ENVIRONMENT'),
                'PORT': os.getenv('PORT'),
                'RAILWAY_PUBLIC_DOMAIN': os.getenv('RAILWAY_PUBLIC_DOMAIN'),
                'BINANCE_API_KEY': 'set' if os.getenv('BINANCE_API_KEY') else 'not_set',
                'BINANCE_PROXY_URL': os.getenv('BINANCE_PROXY_URL', 'not_set'),
                'USE_CLOUDFLARE_PROXY': os.getenv('USE_CLOUDFLARE_PROXY', 'not_set')
            },
            'available_endpoints': [
                '/',
                '/health',
                '/status',
                '/parameters', 
                '/optimization',
                '/test-binance',
                '/test-tool',
                '/debug'
            ],
            'railway_info': {
                'dashboard': 'https://railway.app/dashboard',
                'current_domain': os.getenv('RAILWAY_PUBLIC_DOMAIN', 'eth-trading-bot-production.up.railway.app')
            }
        }
    
    def run_binance_test(self):
        """바이낸스 연결 테스트 실행"""
        try:
            # Cloudflare 프록시 사용 여부 확인
            use_proxy = os.getenv('USE_CLOUDFLARE_PROXY', 'false').lower() == 'true'
            proxy_url = os.getenv('BINANCE_PROXY_URL')
            
            if use_proxy and proxy_url:
                print("🌐 Cloudflare 프록시를 통한 바이낸스 연결 테스트...")
                return self._test_binance_via_proxy(proxy_url)
            else:
                print("🔗 직접 바이낸스 연결 테스트...")
                return self._test_binance_direct()
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f'Binance test failed: {str(e)}',
                'status': 'failed'
            }
    
    def _test_binance_via_proxy(self, proxy_url):
        """프록시를 통한 바이낸스 테스트"""
        import requests
        import hmac
        import hashlib
        import time
        from urllib.parse import urlencode
        
        test_results = {}
        proxy_url = proxy_url.rstrip('/')
        
        try:
            # 1. 서버 시간 테스트
            response = requests.get(f"{proxy_url}/api/v3/time", timeout=15)
            test_results['server_time'] = response.status_code == 200
            
            # 2. 프록시 헤더 확인
            proxy_headers = {k: v for k, v in response.headers.items() if 'proxy' in k.lower()}
            test_results['proxy_headers'] = bool(proxy_headers)
            
            # 3. 계정 정보 테스트 (API 키 필요)
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            
            if api_key and secret_key:
                timestamp = int(time.time() * 1000)
                params = {'timestamp': timestamp}
                
                query_string = urlencode(params)
                signature = hmac.new(
                    secret_key.encode('utf-8'),
                    query_string.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                params['signature'] = signature
                headers = {'X-MBX-APIKEY': api_key}
                
                response = requests.get(
                    f"{proxy_url}/api/v3/account",
                    params=params,
                    headers=headers,
                    timeout=15
                )
                
                test_results['account_info'] = response.status_code == 200
            else:
                test_results['account_info'] = False
            
            # 4. IP 제한 테스트 (간접적)
            test_results['ip_restrictions'] = test_results['account_info']
            
            passed_tests = sum(test_results.values())
            total_tests = len(test_results)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'test_results': test_results,
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': passed_tests / total_tests * 100,
                'status': 'completed',
                'proxy_url': proxy_url,
                'proxy_headers': proxy_headers,
                'note': 'Using Cloudflare Workers proxy'
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f'Proxy test failed: {str(e)}',
                'status': 'failed',
                'proxy_url': proxy_url
            }
    
    def _test_binance_direct(self):
        """직접 바이낸스 테스트"""
        try:
            from binance_connection_test import BinanceConnectionTester
            
            tester = BinanceConnectionTester()
            
            # 기본 테스트만 실행 (주문 제외)
            test_results = {}
            
            # 1. 서버 시간 테스트
            test_results['server_time'] = tester.test_server_time()
            
            # 2. Cloudflare 통합 테스트
            test_results['cloudflare'] = tester.test_cloudflare_integration()
            
            # 3. IP 제한 테스트
            test_results['ip_restrictions'] = tester.test_ip_restrictions()
            
            # 4. 계정 정보 테스트
            test_results['account_info'] = tester.test_account_info()
            
            passed_tests = sum(test_results.values())
            total_tests = len(test_results)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'test_results': test_results,
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'success_rate': passed_tests / total_tests * 100,
                'status': 'completed',
                'note': 'Direct connection to Binance API'
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f'Direct test failed: {str(e)}',
                'status': 'failed'
            }
    
    def run_binance_debug(self):
        """바이낸스 연결 상세 디버깅"""
        try:
            import requests
            import hmac
            import hashlib
            import time
            from urllib.parse import urlencode
            
            debug_results = {
                'timestamp': datetime.now().isoformat(),
                'tests': {}
            }
            
            # 1. 기본 네트워크 연결 테스트
            network_tests = {}
            test_urls = [
                "https://api.binance.com/api/v3/ping",
                "https://api.binance.com/api/v3/time",
                "https://httpbin.org/ip"
            ]
            
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=10)
                    network_tests[url] = {
                        'status_code': response.status_code,
                        'success': response.status_code == 200,
                        'response_time': response.elapsed.total_seconds()
                    }
                    
                    if 'httpbin.org/ip' in url and response.status_code == 200:
                        ip_info = response.json()
                        network_tests[url]['current_ip'] = ip_info.get('origin', 'Unknown')
                        
                except Exception as e:
                    network_tests[url] = {'error': str(e), 'success': False}
            
            debug_results['tests']['network'] = network_tests
            
            # 2. API 키 검증
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            
            api_key_test = {
                'api_key_exists': bool(api_key),
                'secret_key_exists': bool(secret_key),
                'api_key_length': len(api_key) if api_key else 0,
                'secret_key_length': len(secret_key) if secret_key else 0,
                'api_key_format_ok': False,
                'secret_key_format_ok': False
            }
            
            if api_key:
                api_key_test['api_key_format_ok'] = len(api_key) == 64 and ' ' not in api_key
                api_key_test['api_key_preview'] = api_key[:8] + '...' if len(api_key) >= 8 else 'too_short'
            
            if secret_key:
                api_key_test['secret_key_format_ok'] = len(secret_key) == 64 and ' ' not in secret_key
                api_key_test['secret_key_preview'] = secret_key[:8] + '...' if len(secret_key) >= 8 else 'too_short'
            
            debug_results['tests']['api_keys'] = api_key_test
            
            # 3. 인증된 요청 테스트
            auth_test = {'success': False, 'error': 'No API keys'}
            
            if api_key and secret_key:
                try:
                    timestamp = int(time.time() * 1000)
                    params = {'timestamp': timestamp}
                    
                    query_string = urlencode(params)
                    signature = hmac.new(
                        secret_key.encode('utf-8'),
                        query_string.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    params['signature'] = signature
                    headers = {'X-MBX-APIKEY': api_key}
                    
                    response = requests.get(
                        "https://api.binance.com/api/v3/account",
                        params=params,
                        headers=headers,
                        timeout=15
                    )
                    
                    auth_test = {
                        'status_code': response.status_code,
                        'success': response.status_code == 200,
                        'timestamp_used': timestamp,
                        'signature_preview': signature[:16] + '...'
                    }
                    
                    if response.status_code == 200:
                        account_info = response.json()
                        auth_test['account_type'] = account_info.get('accountType', 'Unknown')
                        auth_test['can_trade'] = account_info.get('canTrade', False)
                        auth_test['permissions'] = account_info.get('permissions', [])
                    else:
                        try:
                            error_data = response.json()
                            auth_test['error_code'] = error_data.get('code', 'Unknown')
                            auth_test['error_message'] = error_data.get('msg', 'Unknown')
                        except:
                            auth_test['error_message'] = response.text[:200]
                    
                except Exception as e:
                    auth_test = {'success': False, 'error': str(e)}
            
            debug_results['tests']['authentication'] = auth_test
            
            # 4. 결과 요약
            network_success = sum(1 for test in network_tests.values() if test.get('success', False))
            network_total = len(network_tests)
            
            debug_results['summary'] = {
                'network_success_rate': f"{network_success}/{network_total}",
                'api_keys_configured': api_key_test['api_key_exists'] and api_key_test['secret_key_exists'],
                'api_keys_format_ok': api_key_test['api_key_format_ok'] and api_key_test['secret_key_format_ok'],
                'authentication_success': auth_test.get('success', False),
                'overall_status': 'success' if auth_test.get('success', False) else 'failed'
            }
            
            # 문제 해결 제안
            suggestions = []
            
            if not api_key_test['api_key_exists']:
                suggestions.append("BINANCE_API_KEY 환경변수를 설정하세요")
            
            if not api_key_test['secret_key_exists']:
                suggestions.append("BINANCE_SECRET_KEY 환경변수를 설정하세요")
            
            if not api_key_test['api_key_format_ok']:
                suggestions.append("API 키 형식을 확인하세요 (64자, 공백 없음)")
            
            if not api_key_test['secret_key_format_ok']:
                suggestions.append("Secret 키 형식을 확인하세요 (64자, 공백 없음)")
            
            if auth_test.get('error_code') == -2015:
                suggestions.append("바이낸스 API 관리에서 현재 IP를 허용 목록에 추가하세요")
            
            if auth_test.get('error_code') == -1022:
                suggestions.append("API 키와 Secret 키가 올바른 쌍인지 확인하세요")
            
            debug_results['suggestions'] = suggestions
            
            return debug_results
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f'Debug failed: {str(e)}',
                'status': 'failed'
            }
    
    def check_outgoing_ip(self):
        """송신 IP 확인 (직접 vs 프록시)"""
        import requests
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'direct_connection': {},
            'proxy_connection': {},
            'comparison': {}
        }
        
        # 1. 직접 연결로 IP 확인
        try:
            response = requests.get("https://httpbin.org/ip", timeout=10)
            if response.status_code == 200:
                ip_data = response.json()
                result['direct_connection'] = {
                    'success': True,
                    'ip': ip_data.get('origin', 'unknown'),
                    'response_time': response.elapsed.total_seconds()
                }
            else:
                result['direct_connection'] = {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
        except Exception as e:
            result['direct_connection'] = {
                'success': False,
                'error': str(e)
            }
        
        # 2. 프록시를 통한 IP 확인
        proxy_url = os.getenv('BINANCE_PROXY_URL')
        use_proxy = os.getenv('USE_CLOUDFLARE_PROXY', 'false').lower() == 'true'
        
        if use_proxy and proxy_url:
            try:
                # Cloudflare Tunnel을 통해 httpbin에 접근
                # 이를 위해 터널 설정에 httpbin 경로를 추가해야 함
                
                # 대신 바이낸스 API를 통해 간접적으로 확인
                response = requests.get(f"{proxy_url}/api/v3/time", timeout=10)
                if response.status_code == 200:
                    result['proxy_connection'] = {
                        'success': True,
                        'proxy_url': proxy_url,
                        'response_time': response.elapsed.total_seconds(),
                        'headers': dict(response.headers),
                        'note': 'Proxy connection successful, but IP not directly visible'
                    }
                else:
                    result['proxy_connection'] = {
                        'success': False,
                        'error': f'HTTP {response.status_code}',
                        'proxy_url': proxy_url
                    }
            except Exception as e:
                result['proxy_connection'] = {
                    'success': False,
                    'error': str(e),
                    'proxy_url': proxy_url
                }
        else:
            result['proxy_connection'] = {
                'success': False,
                'error': 'Proxy not configured',
                'use_proxy': use_proxy,
                'proxy_url': proxy_url
            }
        
        # 3. 비교 분석
        direct_ip = result['direct_connection'].get('ip', 'unknown')
        proxy_success = result['proxy_connection'].get('success', False)
        
        result['comparison'] = {
            'direct_ip': direct_ip,
            'proxy_configured': use_proxy,
            'proxy_working': proxy_success,
            'recommendation': self._get_ip_recommendation(direct_ip, proxy_success)
        }
        
        return result
    
    def _get_ip_recommendation(self, direct_ip, proxy_working):
        """IP 설정 권장사항"""
        if proxy_working:
            return {
                'status': 'use_proxy',
                'message': 'Cloudflare 프록시가 작동 중입니다. 바이낸스에서 Cloudflare IP 범위를 허용하세요.',
                'action': 'Add Cloudflare IP ranges to Binance whitelist'
            }
        else:
            return {
                'status': 'use_direct_ip',
                'message': f'프록시가 작동하지 않습니다. 바이낸스에서 직접 IP를 허용하세요: {direct_ip}',
                'action': f'Add {direct_ip} to Binance whitelist'
            }
    
    def get_welcome_page(self):
        """웰컴 페이지 HTML 생성"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 ETH Session Trading Bot API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 800px;
            width: 100%;
            text-align: center;
        }
        
        .header {
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2em;
            color: #7f8c8d;
        }
        
        .status {
            background: #d5f4e6;
            border: 2px solid #27ae60;
            border-radius: 10px;
            padding: 20px;
            margin: 30px 0;
        }
        
        .status h2 {
            color: #27ae60;
            margin-bottom: 10px;
        }
        
        .endpoints {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .endpoint {
            background: #f8f9fa;
            border: 2px solid #ecf0f1;
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.2s;
        }
        
        .endpoint:hover {
            transform: translateY(-5px);
            border-color: #3498db;
        }
        
        .endpoint h3 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .endpoint p {
            color: #7f8c8d;
            margin-bottom: 15px;
        }
        
        .endpoint a {
            display: inline-block;
            background: #3498db;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: 600;
            transition: background 0.2s;
        }
        
        .endpoint a:hover {
            background: #2980b9;
        }
        
        .info {
            background: #fef9e7;
            border: 2px solid #f39c12;
            border-radius: 10px;
            padding: 20px;
            margin: 30px 0;
        }
        
        .info h3 {
            color: #f39c12;
            margin-bottom: 10px;
        }
        
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
        }
        
        .timestamp {
            font-size: 0.9em;
            color: #95a5a6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ETH Session Trading Bot</h1>
            <p>고급 리스크 관리가 적용된 ETHUSDT 세션 스윕 리버설 트레이딩 봇</p>
        </div>
        
        <div class="status">
            <h2>✅ 시스템 정상 작동 중</h2>
            <p>자동 최적화 시스템이 매주 일요일 14:00 KST에 실행됩니다</p>
        </div>
        
        <div class="endpoints">
            <div class="endpoint">
                <h3>🏥 헬스체크</h3>
                <p>시스템 상태 확인</p>
                <a href="/health">확인하기</a>
            </div>
            
            <div class="endpoint">
                <h3>📊 상태 정보</h3>
                <p>봇 실행 상태 조회</p>
                <a href="/status">확인하기</a>
            </div>
            
            <div class="endpoint">
                <h3>⚙️ 파라미터</h3>
                <p>현재 최적 파라미터</p>
                <a href="/parameters">확인하기</a>
            </div>
            
            <div class="endpoint">
                <h3>🤖 최적화 상태</h3>
                <p>자동 최적화 정보</p>
                <a href="/optimization">확인하기</a>
            </div>
            
            <div class="endpoint">
                <h3>🔗 바이낸스 테스트</h3>
                <p>연결 및 IP 제한 테스트</p>
                <a href="/test-binance">테스트하기</a>
            </div>
            
            <div class="endpoint">
                <h3>🧪 API 테스트 도구</h3>
                <p>종합 테스트 도구</p>
                <a href="/test-tool">열기</a>
            </div>
            
            <div class="endpoint">
                <h3>🔧 디버그 정보</h3>
                <p>환경변수 및 설정 확인</p>
                <a href="/debug">확인하기</a>
            </div>
        </div>
        
        <div class="info">
            <h3>📋 주요 기능</h3>
            <ul style="text-align: left; max-width: 600px; margin: 0 auto;">
                <li><strong>세션 스윕 리버설</strong>: 아시아/런던/뉴욕 세션 분석</li>
                <li><strong>고급 리스크 관리</strong>: 포지션당 5% 리스크, 청산 확률 7%</li>
                <li><strong>자동 최적화</strong>: 매주 파라미터 자동 업데이트</li>
                <li><strong>실시간 모니터링</strong>: API 엔드포인트를 통한 상태 확인</li>
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>ETH Session Trading Bot API v1.0</strong></p>
            <p>Powered by Railway</p>
            <p class="timestamp">현재 시간: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
        </div>
    </div>
</body>
</html>
        """
    
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