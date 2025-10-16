# 🌐 Cloudflare 단계별 설정 가이드

## 🎯 목표
도메인을 Cloudflare에 연결하여 고정 IP와 보안 기능 활용

## 📋 1단계: Cloudflare 계정 생성

### 1. 회원가입
1. https://dash.cloudflare.com/sign-up 접속
2. 이메일과 비밀번호 입력
3. 이메일 인증 완료

### 2. 도메인 추가
1. "Add a Site" 버튼 클릭
2. 구입한 도메인 입력 (예: `eth-trading-bot.com`)
3. "Add Site" 클릭

### 3. 플랜 선택
- **Free 플랜** 선택 (무료)
- "Continue" 클릭

## 📋 2단계: DNS 스캔 및 설정

### 1. DNS 레코드 스캔
- Cloudflare가 자동으로 기존 DNS 레코드 스캔
- "Continue" 클릭

### 2. 네임서버 정보 확인
Cloudflare가 제공하는 네임서버 2개 복사:
```
예시:
ns1.cloudflare.com
ns2.cloudflare.com
```

## 📋 3단계: 도메인 등록업체에서 네임서버 변경

### Namecheap에서 네임서버 변경:
1. Namecheap 대시보드 로그인
2. "Domain List" → 도메인 선택
3. "Manage" 클릭
4. "Nameservers" 섹션에서 "Custom DNS" 선택
5. Cloudflare 네임서버 2개 입력
6. "Save" 클릭

### ⏰ 대기 시간
- DNS 전파: 최대 24시간 (보통 1-2시간)
- Cloudflare에서 "Active" 상태 확인될 때까지 대기

## 📋 4단계: Cloudflare API 토큰 생성

### 1. API 토큰 페이지 접속
1. Cloudflare 대시보드 우상단 프로필 클릭
2. "My Profile" 선택
3. "API Tokens" 탭 클릭

### 2. 커스텀 토큰 생성
1. "Create Token" 클릭
2. "Custom token" → "Get started" 클릭

### 3. 토큰 권한 설정
```
Token name: Railway Trading Bot
Permissions:
- Zone:Zone:Read
- Zone:DNS:Edit
- Zone:Zone Settings:Edit

Zone Resources:
- Include: Specific zone: your-domain.com

Client IP Address Filtering: (비워둠)
TTL: (기본값)
```

### 4. 토큰 생성 및 복사
1. "Continue to summary" 클릭
2. "Create Token" 클릭
3. **생성된 토큰을 안전한 곳에 저장** (다시 볼 수 없음)

## 📋 5단계: Zone ID 확인

### Zone ID 찾기:
1. Cloudflare 대시보드에서 도메인 선택
2. 우측 사이드바에서 "Zone ID" 복사
3. 안전한 곳에 저장

## 📋 6단계: DNS 레코드 설정

### 1. DNS 관리 페이지
1. Cloudflare 대시보드에서 도메인 선택
2. "DNS" → "Records" 탭

### 2. A 레코드 추가 (임시)
```
Type: A
Name: api
IPv4 address: 192.0.2.1 (임시 IP)
Proxy status: Proxied (주황색 구름)
TTL: Auto
```

## 📋 7단계: SSL/TLS 설정

### 1. SSL/TLS 설정
1. "SSL/TLS" 탭 클릭
2. "Overview" → Encryption mode를 **"Full (strict)"** 선택

### 2. Edge Certificates
1. "Edge Certificates" 탭
2. "Always Use HTTPS" → **On**
3. "Automatic HTTPS Rewrites" → **On**

## ✅ 완료 확인

### 확인 사항:
- [ ] 도메인이 Cloudflare에서 "Active" 상태
- [ ] API 토큰 생성 완료
- [ ] Zone ID 확인 완료
- [ ] DNS 레코드 추가 완료
- [ ] SSL 설정 완료

### 다음 단계:
Railway 환경변수 설정으로 이동