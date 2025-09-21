# Seegene Global Bid Monitor

씨젠을 위한 다국가 입찰 정보 수집 및 분석 시스템 - 헬스케어 및 진단키트 전문

## 🌍 지원 플랫폼

### 현재 지원
- 🇰🇷 **G2B (나라장터)**: 한국 정부 조달 API
- 🇺🇸 **SAM.gov**: 미국 정부 조달 시스템
- 🇪🇺 **TED**: EU 공식 입찰공고 플랫폼
- 🇬🇧 **UK FTS**: 영국 Find a Tender Service

### 향후 확장 예정
- 🇫🇷 **BOAMP**: 프랑스 공공조달
- 🇪🇸 **PCSP**: 스페인 공공조달
- 🇩🇪 **bund.de**: 독일 연방조달

## 🚀 주요 기능

- **🌐 글로벌 입찰 수집**: 4개국 주요 조달 플랫폼 통합 모니터링
- **🏥 헬스케어 특화**: CPV 코드 기반 의료/진단 관련 입찰 자동 필터링
- **🤖 MCP 프로토콜 지원**: Claude, Cursor 등 AI 도구와 연동
- **🔄 실시간 동기화**: 자동 스케줄링 및 백그라운드 수집
- **📊 지능형 분석**: 관련성 점수, 다국어 키워드 매칭
- **🎯 스마트 필터링**: 헬스케어 관련성 임계값 조정 가능
- **💾 경량 데이터베이스**: SQLite 기반, 별도 DB 서버 불필요

## 📁 프로젝트 구조

```
seegene-bid-mcp/
├── src/
│   ├── main.py                 # FastAPI 서버 메인
│   ├── config.py              # 설정 관리
│   ├── database/              # SQLite DB 스키마
│   ├── models/                # 통합 데이터 모델
│   │   └── tender_notice.py   # TenderNotice 표준 스키마
│   ├── crawler/               # 크롤러 모듈
│   │   ├── manager.py         # 크롤러 매니저
│   │   ├── g2b_crawler.py     # 한국 G2B API
│   │   ├── samgov_crawler.py  # 미국 SAM.gov
│   │   ├── ted_crawler.py     # EU TED API
│   │   └── uk_fts_crawler.py  # 영국 FTS OCDS
│   └── utils/
│       ├── cpv_filter.py      # CPV 헬스케어 필터
│       └── logger.py          # 로깅 유틸
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
python -m venv venv # py -3 -m venv .venv
source .venv/Scripts/activate  # Windows: venv\Scripts\activate

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
# 서버 설정
HOST=127.0.0.1
PORT=8000
DEBUG=True

# 데이터베이스 (자동 설정됨)
DATABASE_URL=sqlite+aiosqlite:///./seegene_bids.db

# G2B API 키 (data.go.kr에서 발급)
G2B_API_KEY=your-g2b-api-key-from-data-go-kr

# 로그인 정보 (API 사용 시 선택사항)
G2B_USERNAME=your_g2b_username
G2B_PASSWORD=your_g2b_password
SAMGOV_USERNAME=your_samgov_username
SAMGOV_PASSWORD=your_samgov_password
SAMGOV_API_KEY=your_samgov_api_key

# 헬스케어 필터링 설정
URGENT_DEADLINE_DAYS=3
HIGH_VALUE_THRESHOLD_KRW=100000000
HIGH_VALUE_THRESHOLD_USD=1000000
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

### 전체 크롤링 실행

```bash
# 모든 플랫폼에서 헬스케어 관련 입찰 수집
curl -X POST "http://localhost:8000/crawl-all" -H "Content-Type: application/json"

# 특정 플랫폼만 실행
curl -X POST "http://localhost:8000/crawl-g2b" -H "Content-Type: application/json"
curl -X POST "http://localhost:8000/crawl-ted" -H "Content-Type: application/json"
curl -X POST "http://localhost:8000/crawl-uk-fts" -H "Content-Type: application/json"
```

### 검색 및 조회

```bash
# 최근 입찰 결과 조회
curl "http://localhost:8000/search?keyword=PCR&country=KR&limit=10"

# 헬스케어 관련 입찰만 조회
curl "http://localhost:8000/search?healthcare_only=true"
```

### 서버 상태 확인

```bash
# 건강상태 확인
curl http://localhost:8000/health

# API 문서 접속 (Swagger UI)
open http://localhost:8000/docs

# MCP 프로토콜 엔드포인트
curl http://localhost:8000/mcp
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

## 🏥 헬스케어 특화 기능

### CPV 코드 기반 필터링

시스템은 다음 CPV(Common Procurement Vocabulary) 코드를 기반으로 헬스케어 관련 입찰을 자동 식별합니다:

- **33100000**: 의료 장비 및 기기
- **33696000**: 진단 시약
- **85100000**: 보건 서비스
- **73140000**: 의학 연구

### 다국어 키워드 매칭

- **한국어**: 진단키트, PCR, 분자진단, 체외진단
- **영어**: diagnostic kit, PCR test, molecular diagnostic, IVD
- **프랑스어**: diagnostic, trousse de test, réactif
- **독일어**: diagnostik, testkit, reagenz
- **스페인어**: diagnóstico, kit de prueba, reactivo

### 관련성 점수 계산

각 입찰공고는 다음 기준으로 헬스케어 관련성 점수(0.0-1.0)를 받습니다:
- CPV 코드 매칭 (가중치 50%)
- 제목 키워드 매칭 (가중치 30%)
- 설명 키워드 매칭 (가중치 20%)

## 📦 다음 단계

1. **추가 플랫폼 확장**: 프랑스, 독일, 스페인 조달 플랫폼
2. **AI 기반 분석**: 입찰 성공 확률 예측
3. **알림 시스템**: 이메일/Slack 실시간 알림
4. **웹 대시보드**: 시각화된 관리 인터페이스
5. **모바일 앱**: 실시간 입찰 모니터링

## ⚡ 빠른 시작 체크리스트

- [x] 프로젝트 생성 완료
- [ ] `cd seegene-bid-mcp`
- [ ] `pip install -r requirements.txt`
- [ ] `.env` 파일 설정 (특히 G2B_API_KEY)
- [ ] `python run.py` 실행
- [ ] http://localhost:8000/health 접속 확인
- [ ] http://localhost:8000/docs에서 API 문서 확인
- [ ] 크롤링 테스트: `curl -X POST http://localhost:8000/crawl-all`
- [ ] Claude/Cursor MCP 설정 (선택사항)

## 📞 지원

- **문의**: chsong@seegene.com
- **문서**: 이 README 파일 참조

---

## 🎯 기술 스택

- **백엔드**: FastAPI + Python 3.8+
- **데이터베이스**: SQLite + SQLAlchemy (비동기)
- **크롤링**: aiohttp + Beautiful Soup + Selenium
- **스케줄링**: APScheduler
- **데이터 검증**: Pydantic
- **로깅**: Loguru
- **테스트**: pytest + httpx

## 📈 성능 특징

- **비동기 처리**: 동시 다국가 크롤링 지원
- **메모리 효율성**: SQLite 경량 데이터베이스
- **확장성**: 모듈화된 크롤러 아키텍처
- **신뢰성**: 오류 복구 및 재시도 로직
- **보안**: 환경변수 기반 설정 관리

---

**Made with ❤️ for Seegene Global Expansion**

*4개국 헬스케어 입찰 정보를 하나의 시스템으로!*
