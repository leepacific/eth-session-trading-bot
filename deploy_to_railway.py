#!/usr/bin/env python3
"""
통합 최적화 시스템 Railway 배포 스크립트
"""

import os
import json
import subprocess
import requests
import time
from datetime import datetime

class OptimizationSystemDeployer:
    def __init__(self):
        self.railway_token = os.getenv('RAILWAY_TOKEN')
        self.project_id = os.getenv('RAILWAY_PROJECT_ID')
        
    def check_prerequisites(self):
        """배포 전 필수 조건 확인"""
        print("🔍 배포 전 확인사항 점검...")
        
        checks = []
        
        # 1. Railway CLI 확인
        try:
            result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                checks.append(("✅", f"Railway CLI: {result.stdout.strip()}"))
            else:
                checks.append(("❌", "Railway CLI 설치 필요"))
        except FileNotFoundError:
            checks.append(("❌", "Railway CLI 설치 필요: npm install -g @railway/cli"))
        
        # 2. 필수 파일 확인
        required_files = [
            'main.py',
            'run_optimization.py', 
            'run_full_backtest.py',
            'requirements.txt',
            'railway.json'
        ]
        
        for file in required_files:
            if os.path.exists(file):
                checks.append(("✅", f"파일 존재: {file}"))
            else:
                checks.append(("❌", f"파일 누락: {file}"))
        
        # 3. 데이터 파일 확인
        data_files = [
            'data/ETHUSDT_15m_206319points_20251015_202539.csv'
        ]
        
        for file in data_files:
            if os.path.exists(file):
                checks.append(("✅", f"데이터 파일: {file}"))
            else:
                checks.append(("⚠️", f"데이터 파일 누락: {file} (배포 후 생성됨)"))
        
        # 4. 환경변수 확인
        env_vars = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY']
        for var in env_vars:
            if os.getenv(var):
                checks.append(("✅", f"환경변수: {var}"))
            else:
                checks.append(("⚠️", f"환경변수 누락: {var} (Railway에서 설정 필요)"))
        
        # 결과 출력
        for status, message in checks:
            print(f"  {status} {message}")
        
        # 실패 항목이 있는지 확인
        failed = [check for check in checks if check[0] == "❌"]
        if failed:
            print(f"\n❌ {len(failed)}개 필수 조건 미충족")
            return False
        
        print(f"\n✅ 배포 준비 완료")
        return True
    
    def deploy_to_railway(self):
        """Railway에 배포"""
        print("\n🚀 Railway 배포 시작...")
        
        try:
            # 1. 로그인 확인
            result = subprocess.run(['railway', 'whoami'], capture_output=True, text=True)
            if result.returncode != 0:
                print("Railway 로그인 필요...")
                login_result = subprocess.run(['railway', 'login'])
                if login_result.returncode != 0:
                    print("❌ Railway 로그인 실패")
                    return False
            
            # 2. 프로젝트 연결 또는 생성
            if self.project_id:
                print(f"기존 프로젝트 연결: {self.project_id}")
                result = subprocess.run(['railway', 'link', self.project_id], capture_output=True, text=True)
            else:
                print("새 프로젝트 생성...")
                result = subprocess.run(['railway', 'login'], capture_output=True, text=True)
            
            # 3. 환경변수 설정
            self.setup_environment_variables()
            
            # 4. 배포 실행
            print("📦 배포 실행 중...")
            result = subprocess.run(['railway', 'up', '--detach'], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 배포 성공!")
                print(result.stdout)
                return True
            else:
                print(f"❌ 배포 실패: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 배포 중 오류: {e}")
            return False
    
    def setup_environment_variables(self):
        """Railway 환경변수 설정"""
        print("🔧 환경변수 설정...")
        
        # 기본 환경변수
        env_vars = {
            'PORT': '8000',
            'RAILWAY_ENVIRONMENT': 'production',
            'ENABLE_SCHEDULER': 'true',
            'OPTIMIZATION_TIMEZONE': 'Asia/Seoul',
            'RESOURCE_LIMIT_CPU': '0.8',
            'RESOURCE_LIMIT_MEMORY': '0.8',
            'LOG_LEVEL': 'INFO',
            'DATA_SYMBOL': 'ETHUSDT',
            'DATA_INTERVAL': '15m'
        }
        
        # 현재 파라미터가 있으면 포함
        try:
            if os.path.exists('config/current_parameters.json'):
                with open('config/current_parameters.json', 'r') as f:
                    params_data = json.load(f)
                env_vars['CURRENT_PARAMETERS'] = json.dumps(params_data['parameters'])
                env_vars['LAST_OPTIMIZATION'] = params_data['timestamp']
        except Exception as e:
            print(f"⚠️ 파라미터 로드 실패: {e}")
        
        # 환경변수 설정
        for key, value in env_vars.items():
            try:
                result = subprocess.run(
                    ['railway', 'variables', 'set', f'{key}={value}'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    print(f"  ✅ {key}")
                else:
                    print(f"  ⚠️ {key}: {result.stderr.strip()}")
            except Exception as e:
                print(f"  ❌ {key}: {e}")
    
    def verify_deployment(self):
        """배포 검증"""
        print("\n🔍 배포 검증 중...")
        
        # Railway URL 가져오기
        try:
            result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
            if result.returncode == 0:
                # URL 추출
                lines = result.stdout.split('\n')
                railway_url = None
                for line in lines:
                    if 'https://' in line and 'railway.app' in line:
                        railway_url = line.strip().split()[-1]
                        break
                
                if railway_url:
                    print(f"🌐 Railway URL: {railway_url}")
                    
                    # 헬스체크
                    print("⏳ 서비스 시작 대기 중...")
                    time.sleep(30)
                    
                    try:
                        response = requests.get(f"{railway_url}/health", timeout=30)
                        if response.status_code == 200:
                            print("✅ 헬스체크 성공")
                            health_data = response.json()
                            print(f"  상태: {health_data.get('status')}")
                            print(f"  타임스탬프: {health_data.get('timestamp')}")
                            return railway_url
                        else:
                            print(f"⚠️ 헬스체크 실패: {response.status_code}")
                    except Exception as e:
                        print(f"⚠️ 헬스체크 오류: {e}")
                        print("서비스가 아직 시작 중일 수 있습니다.")
                        return railway_url
                
        except Exception as e:
            print(f"❌ 상태 확인 실패: {e}")
        
        return None
    
    def test_api_endpoints(self, railway_url):
        """API 엔드포인트 테스트"""
        print("\n🧪 API 엔드포인트 테스트...")
        
        endpoints = [
            ('GET', '/', '기본 정보'),
            ('GET', '/health', '헬스체크'),
            ('GET', '/status', '시스템 상태'),
            ('GET', '/api/parameters', '현재 파라미터')
        ]
        
        for method, path, description in endpoints:
            try:
                url = f"{railway_url}{path}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"  ✅ {description}: {path}")
                else:
                    print(f"  ⚠️ {description}: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {description}: {e}")

def main():
    """메인 실행"""
    print("🚀 통합 최적화 시스템 Railway 배포")
    print("="*60)
    
    deployer = OptimizationSystemDeployer()
    
    # 1. 사전 확인
    if not deployer.check_prerequisites():
        print("\n❌ 배포 전 확인사항을 먼저 해결해주세요.")
        return 1
    
    # 2. 배포 실행
    if not deployer.deploy_to_railway():
        print("\n❌ 배포 실패")
        return 1
    
    # 3. 배포 검증
    railway_url = deployer.verify_deployment()
    
    if railway_url:
        # 4. API 테스트
        deployer.test_api_endpoints(railway_url)
        
        print(f"\n🎉 배포 완료!")
        print(f"🌐 URL: {railway_url}")
        print(f"📊 대시보드: https://railway.app/dashboard")
        print(f"📋 다음 최적화: 매주 일요일 14:00 KST")
        
        return 0
    else:
        print("\n⚠️ 배포는 완료되었지만 검증에 실패했습니다.")
        print("Railway 대시보드에서 수동으로 확인해주세요.")
        return 1

if __name__ == "__main__":
    exit(main())