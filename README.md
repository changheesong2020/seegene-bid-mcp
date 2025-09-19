# Seegene Bid Information MCP Server

씨젠을 위한 글로벌 입찰 정보 수집 및 분석 시스템 (SQLite 경량 버전)

## 🚀 주요 기능

- **🌐 다중 플랫폼 크롤링**: 나라장터, SAM.gov 등
- **🤖 MCP 프로토콜 지원**: Claude, Cursor 등 AI 도구와 연동
- **🔐 스마트 로그인 관리**: 세션 유지, 자동 재로그인
- **⚡ 실시간 알림**: 긴급/고액 입찰 자동 감지
- **📊 고도화된 분석**: 관련성 점수, 키워드 매칭
- **💾 SQLite 경량 DB**: 별도 DB 서버 불필요, 즉시 실행 가능

## 📁 프로젝트 구조

```
seegene-bid-mcp/
├── src/
│   ├── main.py                 # MCP 서버 메인
│   ├── config.py              # 설정 관리
│   ├── database/              # DB 스키마
│   ├── models/                # 데이터 모델
│   └── utils/                 # 유틸리티
├── requirements.txt           # Python 의존성
├── run.py                     # 실행 스크립트
├── seegene_bids.db           # SQLite 데이터베이스 (자동 생성)
└── .env.example             # 환경변수 템플릿
```

## 🛠️ 설치 및 설정

### 1. 환경 준비

```bash
# 프로젝트 이동
cd seegene-bid-mcp

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
# 환경변수 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

**필수 설정 항목:**
```env
# 로그인 정보 (선택사항)
G2B_USERNAME=your_g2b_username
G2B_PASSWORD=your_g2b_password
SAMGOV_USERNAME=your_samgov_username
SAMGOV_PASSWORD=your_samgov_password

# 데이터베이스 (자동 설정됨)
DATABASE_URL=sqlite+aiosqlite:///./seegene_bids.db
```

## 🚀 실행 방법

### 빠른 실행

```bash
# 추천: 실행 스크립트 사용
python run.py

# 또는 직접 실행
python -m src.main
```

### 개발 모드 실행

```bash
# 자동 리로드 활성화
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 MCP 클라이언트 연동

### Claude Desktop 설정

`~/.claude/config.json` 파일에 추가:

```json
{
  "mcpServers": {
    "seegene-bid": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/path/to/seegene-bid-mcp"
    }
  }
}
```

## 📚 API 사용법

### 기본 검색

```python
# AI 어시스턴트에게 요청
"씨젠 관련 진단키트 입찰정보를 검색해줘"
```

### 서버 상태 확인

```bash
# 건강상태 확인
curl http://localhost:8000/health

# API 문서 접속
open http://localhost:8000/docs
```

## 💾 데이터베이스 관리

### SQLite 데이터베이스

- **파일 위치**: `seegene_bids.db` (프로젝트 루트)
- **자동 생성**: 첫 실행 시 자동으로 생성됨
- **백업**: 단순히 파일 복사로 백업 가능

### 데이터 확인

```bash
# SQLite 명령줄 도구
sqlite3 seegene_bids.db
```

```sql
-- 입찰 정보 조회
SELECT title, organization, source_site, created_at 
FROM bid_information 
ORDER BY created_at DESC 
LIMIT 10;
```

## 🐛 문제 해결

### 일반적인 문제들

**1. 의존성 오류**
```bash
# 의존성 재설치
pip install -r requirements.txt
```

**2. 데이터베이스 오류**
```bash
# 데이터베이스 파일 삭제 후 재생성
rm seegene_bids.db
python run.py
```

**3. 포트 충돌**
```bash
# 다른 포트 사용
PORT=8001 python run.py
```

## 📦 다음 단계

1. **크롤링 모듈 추가**: 실제 크롤링 기능 구현
2. **알림 시스템**: 이메일/Slack 알림
3. **고급 필터링**: 더 정교한 검색 기능
4. **웹 대시보드**: 관리용 웹 인터페이스

## ⚡ 빠른 시작 체크리스트

- [x] 프로젝트 생성
- [ ] `cd seegene-bid-mcp`
- [ ] `pip install -r requirements.txt`
- [ ] `python run.py` 실행
- [ ] http://localhost:8000/health 접속 확인
- [ ] Claude/Cursor MCP 설정

## 📞 지원

- **문의**: chsong@seegene.com
- **문서**: 이 README 파일 참조

---

**Made with ❤️ for Seegene**

*SQLite 경량 버전으로 더욱 간편하게 시작하세요!*
