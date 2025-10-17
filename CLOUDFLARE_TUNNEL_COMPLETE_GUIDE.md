# 🌐 Cloudflare Workers 바이낸스 프록시 완전 설정 가이드

## 📋 개요

Railway의 동적 IP 문제를 해결하기 위해 Cloudflare Workers를 프록시로 사용하여 안정적인 바이낸스 API 접근을 구현합니다.

## 🎯 장점

- ✅ **고정 IP**: Cloudflare의 안정적인 IP 범위 사용
- ✅ **무료**: Cloudflare Workers 무료 플랜 (월 100,000 요청)
- ✅ **빠른 속도**: 글로벌 CDN을 통한 최적화된 라우팅
- ✅ **안정성**: Railway IP 변경에 영향받지 않음
- ✅ **보안**: HTTPS 암호화 및 CORS 지원

## 🛠️ 단계별 설정

### 1단계: Cloudflare Workers 배포

1. **Cloudflare 대시보드 접속**
   ```
   https://dash.cloudflare.com
   ```

2. **Workers & Pages 메뉴 클릭**
   - 좌측 메뉴에서 `Workers & Pages` 선택

3. **새 Worker 생성**
   - `Create application` 버튼 클릭
   - `Create Worker` 선택
   - Worker 이름 입력: `binance-api-proxy`
   - `Deploy` 클릭

4. **Worker 코드 편집**
   - `Edit code` 버튼 클릭
   - 기존 코드를 모두 삭제
   - `binance_proxy_worker.js` 파일의 내용을 복사하여 붙여넣기
   - `Save and Deploy` 클릭

5. **Worker URL 확인**
   - 배포 완료 후 Worker URL 복사
   - 예: `https://binance-api-proxy.your-account.workers.dev`

### 2단계: Railway 환경변수 설정

Worker URL을 확인한 후 다음 명령어들을 실행:

```bash
# Cloudflare 프록시 설정
railway variables --set "BINANCE_PROXY_URL=https://binance-api-proxy.your-account.workers.dev"
railway variables --set "USE_CLOUDFLARE_PROXY=true"
railway variables --set "PROXY_TIMEOUT=30"
railway variables --set "PROXY_RETRIES=3"

# Railway 재배포
railway up --detach
```

### 3단계: 바이낸스 API IP 제한 설정

1. **바이낸스 API 관리 접속**
   ```
   https://www.binance.com/en/my/settings/api-management
   ```

2. **기존 IP 제한 제거**
   - 기존에 설정된 Railway IP (`208.77.246.29`) 삭제

3. **Cloudflare IP 범위 추가**
   
   바이낸스 API 관리에서 다음 IP 범위들을 허용 목록에 추가:
   
   ```
   173.245.48.0/20
   103.21.244.0/22
   103.22.200.0/22
   103.31.4.0/22
   141.101.64.0/18
   108.162.192.0/18
   190.93.240.0/20
   188.114.96.0/20
   197.234.240.0/22
   198.41.128.0/17
   162.158.0.0/15
   104.16.0.0/13
   104.24.0.0/14
   172.64.0.0/13
   131.0.72.0/22
   ```

   **주의**: 바이낸스는 IP 범위(CIDR) 형식을 지원하지 않을 수 있습니다. 
   그 경우 개별 IP 주소로 변환하거나 IP 제한을 사용하지 않는 것을 고려하세요.

### 4단계: 연결 테스트

1. **Railway API 테스트**
   ```
   https://eth-trading-bot-production.up.railway.app/test-binance
   ```

2. **프록시 상태 확인**
   ```
   https://eth-trading-bot-production.up.railway.app/debug-binance
   ```

3. **로컬 테스트** (선택사항)
   ```bash
   python binance_proxy_client.py
   ```

## 🧪 테스트 결과 해석

### 성공적인 프록시 연결
```json
{
  "status": "completed",
  "proxy_url": "https://binance-api-proxy.your-account.workers.dev",
  "proxy_headers": {
    "X-Proxy-By": "Cloudflare-Workers",
    "X-Proxy-Timestamp": "2025-10-17T08:00:00.000Z"
  },
  "test_results": {
    "server_time": true,
    "proxy_headers": true,
    "account_info": true,
    "ip_restrictions": true
  },
  "success_rate": 100.0
}
```

### 문제 발생 시 확인사항

1. **Worker 배포 확인**
   - Cloudflare Workers 대시보드에서 배포 상태 확인
   - Worker URL 직접 접속 테스트

2. **환경변수 확인**
   ```bash
   railway variables | findstr PROXY
   ```

3. **바이낸스 IP 제한 확인**
   - API 키 설정에서 IP 제한 상태 확인
   - Cloudflare IP 범위가 올바르게 추가되었는지 확인

## 🔧 고급 설정

### Worker 커스텀 도메인 (선택사항)

1. **Cloudflare에서 도메인 관리**
   - `Workers & Pages` → `binance-api-proxy` → `Settings` → `Triggers`
   - `Custom Domains` → `Add Custom Domain`
   - 예: `binance-proxy.yourdomain.com`

2. **Railway 환경변수 업데이트**
   ```bash
   railway variables --set "BINANCE_PROXY_URL=https://binance-proxy.yourdomain.com"
   ```

### 프록시 로깅 및 모니터링

Worker에서 로그 확인:
1. Cloudflare Workers 대시보드
2. `binance-api-proxy` 선택
3. `Logs` 탭에서 실시간 로그 확인

## 📊 성능 및 제한사항

### Cloudflare Workers 무료 플랜 제한
- **요청 수**: 월 100,000 요청
- **CPU 시간**: 요청당 10ms
- **메모리**: 128MB

### 예상 사용량
- **백테스트**: 요청 수 적음 (시간당 < 100 요청)
- **실시간 거래**: 요청 수 많음 (시간당 1,000+ 요청)

월 100,000 요청은 대부분의 트레이딩 봇에 충분합니다.

## 🚨 문제 해결

### 일반적인 오류들

1. **"Worker not found" 오류**
   - Worker URL 확인
   - Worker 배포 상태 확인

2. **CORS 오류**
   - Worker 코드에서 CORS 헤더 설정 확인
   - 브라우저 개발자 도구에서 네트워크 탭 확인

3. **바이낸스 IP 제한 오류**
   - Cloudflare IP 범위 설정 확인
   - 바이낸스 API 키 권한 확인

4. **타임아웃 오류**
   - `PROXY_TIMEOUT` 환경변수 증가 (기본 30초)
   - Worker 코드에서 타임아웃 설정 확인

### 디버깅 도구

1. **Railway 로그**
   ```bash
   railway logs --tail 50
   ```

2. **Cloudflare Workers 로그**
   - Workers 대시보드 → Logs 탭

3. **네트워크 테스트**
   ```bash
   curl -I https://binance-api-proxy.your-account.workers.dev/api/v3/time
   ```

## 🎉 완료!

이제 Railway에서 Cloudflare Workers를 통해 안정적으로 바이낸스 API에 접근할 수 있습니다:

- ✅ Railway IP 변경에 영향받지 않음
- ✅ Cloudflare의 안정적인 IP 범위 사용
- ✅ 글로벌 CDN을 통한 빠른 접속
- ✅ 무료로 사용 가능

정기적으로 연결 상태를 모니터링하고, 필요시 Worker 코드를 업데이트하세요!