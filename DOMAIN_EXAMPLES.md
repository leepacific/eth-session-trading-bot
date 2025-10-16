# 🌐 도메인 설정 구체적 예시

## 📋 실제 도메인별 설정 예시

### 예시 1: eth-trading-bot.com 구입한 경우

#### 구입한 도메인:
```
eth-trading-bot.com
```

#### Railway 환경변수 설정:
```
CUSTOM_DOMAIN=api.eth-trading-bot.com
```

#### 최종 접속 주소:
```
https://api.eth-trading-bot.com/health
https://api.eth-trading-bot.com/status
```

---

### 예시 2: crypto-session-bot.com 구입한 경우

#### 구입한 도메인:
```
crypto-session-bot.com
```

#### Railway 환경변수 설정:
```
CUSTOM_DOMAIN=api.crypto-session-bot.com
```

#### 최종 접속 주소:
```
https://api.crypto-session-bot.com/health
https://api.crypto-session-bot.com/status
```

---

### 예시 3: trading-api-pro.com 구입한 경우

#### 구입한 도메인:
```
trading-api-pro.com
```

#### Railway 환경변수 설정:
```
CUSTOM_DOMAIN=api.trading-api-pro.com
```

#### 최종 접속 주소:
```
https://api.trading-api-pro.com/health
https://api.trading-api-pro.com/status
```

---

## 🔧 서브도메인 선택 가이드

### 추천 서브도메인들:
- `api.your-domain.com` ⭐⭐⭐⭐⭐ (가장 추천)
- `bot.your-domain.com` ⭐⭐⭐⭐
- `trading.your-domain.com` ⭐⭐⭐
- `app.your-domain.com` ⭐⭐⭐

### 왜 서브도메인을 사용하나요?
1. **구분**: API와 웹사이트 분리
2. **확장성**: 나중에 다른 서비스 추가 가능
3. **보안**: 각 서비스별 독립적 관리
4. **전문성**: 더 전문적으로 보임

---

## 📋 단계별 설정 과정

### 1단계: 도메인 구입
- Namecheap에서 `your-chosen-domain.com` 구입

### 2단계: 서브도메인 결정
- `api.your-chosen-domain.com` 선택

### 3단계: Railway 환경변수 설정
```
CUSTOM_DOMAIN=api.your-chosen-domain.com
```

### 4단계: Cloudflare DNS 설정
```
Type: CNAME
Name: api
Target: your-railway-app.railway.app
```

### 5단계: 최종 테스트
- `https://api.your-chosen-domain.com/health` 접속

---

## ⚠️ 주의사항

### ❌ 잘못된 설정:
```
CUSTOM_DOMAIN=your-domain.com          # 서브도메인 없음
CUSTOM_DOMAIN=https://api.your-domain.com  # https:// 포함하면 안됨
CUSTOM_DOMAIN=api.your-domain.com/     # 마지막 / 포함하면 안됨
```

### ✅ 올바른 설정:
```
CUSTOM_DOMAIN=api.your-domain.com      # 정확한 형식
```

---

## 🎯 요약

**구입한 도메인이 `example.com`이라면:**
- Railway 환경변수: `CUSTOM_DOMAIN=api.example.com`
- 최종 주소: `https://api.example.com`

**이해하셨나요?** 구입하신 도메인 앞에 `api.`를 붙이면 됩니다! 🚀