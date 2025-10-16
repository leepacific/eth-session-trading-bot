# 🔗 최종 연결 및 테스트 가이드

## 🎯 목표
Cloudflare와 Railway 연결을 완료하고 커스텀 도메인으로 접속 확인

## 📋 1단계: Railway 공개 도메인 확인

### Railway 도메인 찾기:
1. Railway 대시보드 → 프로젝트 → 서비스
2. "Settings" 탭 → "Domains" 섹션
3. 자동 생성된 도메인 복사 (예: `eth-trading-bot-production.up.railway.app`)

### 환경변수 업데이트:
Railway Variables에 추가:
```
RAILWAY_PUBLIC_DOMAIN=eth-trading-bot-production.up.railway.app
```

## 📋 2단계: Cloudflare DNS 레코드 업데이트

### 1. Cloudflare 대시보드 접속
1. https://dash.cloudflare.com 로그인
2. 도메인 선택
3. "DNS" → "Records" 탭

### 2. CNAME 레코드 수정
기존 A 레코드를 삭제하고 CNAME 레코드 생성:
```
Type: CNAME
Name: api
Target: your-app-name.up.railway.app
Proxy status: Proxied (주황색 구름 ✅)
TTL: Auto
```

### 3. 저장 및 대기
- "Save" 클릭
- DNS 전파 대기 (5-10분)

## 📋 3단계: Railway 커스텀 도메인 추가

### 1. Railway에서 커스텀 도메인 설정
1. Railway 대시보드 → 프로젝트 → 서비스
2. "Settings" → "Domains"
3. "Custom Domain" 클릭
4. 도메인 입력: `api.your-domain.com`
5. "Add Domain" 클릭

### 2. SSL 인증서 확인
- Railway가 자동으로 SSL 인증서 발급
- "Domains" 섹션에서 녹색 체크마크 확인

## 📋 4단계: 자동 설정 스크립트 실행

### Railway에서 자동 설정 실행:
배포 후 자동으로 실행되지만, 수동 실행도 가능:

```python
# Railway 컨테이너 내에서 실행
python setup_cloudflare.py
```

### 예상 출력:
```
🚀 Cloudflare + Railway 자동 설정 시작
🔍 필수 요구사항 확인 중...
✅ 모든 필수 환경변수가 설정되었습니다.
🌐 DNS 설정 중...
✅ DNS 설정 완료
🔍 설정 검증 중...
✅ 도메인 접근 성공: https://api.your-domain.com
```

## 📋 5단계: 최종 테스트

### 1. 헬스체크 테스트
브라우저 또는 curl로 테스트:
```bash
curl https://api.your-domain.com/health
```

예상 응답:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T12:00:00Z",
  "service": "eth-session-trading-bot",
  "version": "1.0.0"
}
```

### 2. 상태 확인 테스트
```bash
curl https://api.your-domain.com/status
```

예상 응답:
```json
{
  "bot_status": "running",
  "last_update": "2025-10-15T12:00:00Z",
  "environment": "production"
}
```

### 3. SSL 인증서 확인
브라우저에서 `https://api.your-domain.com` 접속:
- 🔒 자물쇠 아이콘 확인
- 인증서 정보에서 Cloudflare 발급 확인

## 📋 6단계: 성능 및 보안 확인

### 1. 속도 테스트
```bash
curl -w "@curl-format.txt" -o /dev/null -s https://api.your-domain.com/health
```

### 2. 보안 헤더 확인
```bash
curl -I https://api.your-domain.com/health
```

예상 헤더:
```
HTTP/2 200
server: cloudflare
cf-ray: xxxxx-ICN
```

### 3. DDoS 보호 테스트
- 여러 번 빠르게 요청하여 Rate limiting 확인
- Cloudflare가 자동으로 보호 적용

## 🎉 완료 확인

### ✅ 성공 체크리스트:
- [ ] 커스텀 도메인으로 접속 가능
- [ ] HTTPS 자동 적용
- [ ] 헬스체크 엔드포인트 정상 응답
- [ ] SSL 인증서 유효
- [ ] Cloudflare 프록시 활성화
- [ ] 트레이딩 봇 정상 작동

### 🎯 최종 결과:
```
🌐 메인 도메인: https://api.your-domain.com
🏥 헬스체크: https://api.your-domain.com/health
📊 상태 확인: https://api.your-domain.com/status
🔒 보안: SSL/TLS + DDoS 보호
⚡ 성능: Cloudflare CDN
🌍 가용성: 99.9% 업타임
```

## 🚨 문제 해결

### 일반적인 문제들:

#### 1. "DNS_PROBE_FINISHED_NXDOMAIN" 오류
- DNS 전파 대기 (최대 24시간)
- 네임서버 설정 재확인

#### 2. "SSL_ERROR_BAD_CERT_DOMAIN" 오류
- Railway 커스텀 도메인 설정 확인
- SSL 인증서 발급 대기

#### 3. "502 Bad Gateway" 오류
- Railway 앱 상태 확인
- 환경변수 설정 재확인

#### 4. Cloudflare API 오류
- API 토큰 권한 재확인
- Zone ID 정확성 확인

### 도움말:
- Railway 로그: `railway logs`
- Cloudflare 지원: https://support.cloudflare.com
- 프로젝트 Issues: GitHub 저장소