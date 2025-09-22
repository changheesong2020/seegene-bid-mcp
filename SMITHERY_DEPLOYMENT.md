# Smithery.ai 배포 가이드

## 사전 준비사항

### 1. API 키 준비
- **G2B API 키**: [공공데이터포털](https://data.go.kr)에서 "나라장터 민간입찰공고서비스" API 신청
- **SAM.gov API 키**: [SAM.gov](https://sam.gov) 에서 발급 (선택사항)
- **TED API 키**: [EU Open Data Portal](https://data.europa.eu) 에서 발급 (선택사항)

### 2. GitHub 레포지토리 설정
- 프로젝트를 GitHub에 업로드
- public 또는 private 레포지토리 모두 가능
- `smithery.yaml` 파일이 루트에 있는지 확인

## 배포 방법

### 방법 1: Smithery CLI (권장)

```bash
# 1. Smithery CLI 설치
npm install -g @smithery/cli

# 2. Smithery 로그인
smithery login

# 3. 프로젝트 루트에서 배포
cd /path/to/seegene-bid-mcp
smithery deploy

# 4. 환경 변수 설정 (대화형)
# CLI가 필요한 환경 변수들을 물어볼 것입니다:
# - G2B_API_KEY
# - SAMGOV_API_KEY (선택사항)
# - TED_API_KEY (선택사항)
```

### 방법 2: Smithery 웹 인터페이스

1. [Smithery.ai](https://smithery.ai) 웹사이트 접속
2. "Publish Server" 클릭
3. GitHub 레포지토리 연결
4. `smithery.yaml` 설정 확인
5. 환경 변수 설정:
   ```
   G2B_API_KEY=your_g2b_api_key_here
   SAMGOV_API_KEY=your_samgov_api_key_here
   TED_API_KEY=your_ted_api_key_here
   HOST=0.0.0.0
   PORT=8000
   HEADLESS_MODE=True
   ```
6. "Deploy" 클릭

### 방법 3: Docker 컨테이너

```bash
# 1. Docker 이미지 빌드
docker build -t seegene-bid-mcp:latest .

# 2. 이미지 태그 설정
docker tag seegene-bid-mcp:latest your-registry/seegene-bid-mcp:latest

# 3. 레지스트리에 푸시
docker push your-registry/seegene-bid-mcp:latest

# 4. Smithery에서 Docker 배포
smithery deploy --docker your-registry/seegene-bid-mcp:latest
```

## 배포 후 확인사항

### 1. 헬스 체크
```bash
curl https://your-server.smithery.ai/health
```

예상 응답:
```json
{
    "status": "healthy",
    "timestamp": "2025-09-22T...",
    "database": "ok",
    "version": "2.0.0"
}
```

### 2. MCP 도구 확인
```bash
curl https://your-server.smithery.ai/mcp-status
```

### 3. API 문서 확인
- `https://your-server.smithery.ai/docs` - FastAPI 자동 생성 문서

## 환경 변수 상세 설명

### 필수 환경 변수
| 변수명 | 설명 | 예시 |
|--------|------|------|
| `G2B_API_KEY` | 한국 나라장터 API 키 | `abcd1234...` |

### 선택적 환경 변수
| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `SAMGOV_API_KEY` | 미국 SAM.gov API 키 | (없음) |
| `TED_API_KEY` | EU TED API 키 | (없음) |
| `HOST` | 서버 호스트 | `0.0.0.0` |
| `PORT` | 서버 포트 | `8000` |
| `DEBUG` | 디버그 모드 | `True` |
| `HEADLESS_MODE` | 헤드리스 크롤링 | `True` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |

## 문제 해결

### 자주 발생하는 문제들

1. **API 키 오류**
   - G2B API 키가 올바르게 설정되었는지 확인
   - 공공데이터포털에서 API 승인 상태 확인

2. **크롤링 실패**
   - `HEADLESS_MODE=True` 설정 확인
   - Chrome 브라우저 설치 상태 확인 (Docker에서는 자동 설치됨)

3. **데이터베이스 오류**
   - SQLite 파일 권한 확인
   - 디스크 공간 확인

4. **네트워크 연결 문제**
   - 방화벽 설정 확인
   - 외부 API 접근 권한 확인

### 로그 확인
```bash
# Smithery CLI로 로그 확인
smithery logs seegene-bid-mcp

# 또는 웹 인터페이스에서 로그 탭 확인
```

## 업데이트 방법

### 코드 업데이트
1. GitHub 레포지토리에 새 코드 푸시
2. Smithery가 자동으로 재배포 (Webhook 설정 시)
3. 또는 수동으로 `smithery deploy` 실행

### 환경 변수 업데이트
```bash
smithery config set G2B_API_KEY new_api_key_value
smithery restart seegene-bid-mcp
```

## 지원 및 문의

- **GitHub Issues**: [프로젝트 이슈 페이지]
- **Smithery 지원**: [Smithery.ai 지원 페이지]
- **이메일**: info@seegene.com

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능