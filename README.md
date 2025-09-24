# Seegene Global Bid Monitor

씨젠을 위한 다국가 입찰 정보 수집 및 분석 시스템 - 헬스케어 및 진단키트 전문

## 🌍 지원 플랫폼

### 주요 지원 플랫폼 (데이터베이스 저장 완료 ✅)
- 🇰🇷 **G2B (나라장터)**: 한국 정부 조달 API ✅
  - 공식 사이트: https://www.g2b.go.kr
  - API 엔드포인트: http://apis.data.go.kr/1230000/ad/BidPublicInfoService
  - 상태: **68건 수집/저장 성공**

- 🇺🇸 **SAM.gov**: 미국 정부 조달 시스템 ✅
  - 공식 사이트: https://sam.gov
  - API 엔드포인트: https://api.sam.gov/opportunities/v2/search
  - 상태: **저장 로직 완료**

- 🇪🇺 **TED**: EU 공식 입찰공고 플랫폼 ✅
  - 공식 사이트: https://ted.europa.eu
  - API 엔드포인트: https://api.ted.europa.eu
  - 상태: **저장 로직 완료**

- 🇬🇧 **UK FTS**: 영국 Find a Tender Service ✅
  - 공식 사이트: https://www.find-tender.service.gov.uk
  - API 엔드포인트: https://www.find-tender.service.gov.uk/api/1.0
  - 상태: **저장 로직 완료**

### 유럽 플랫폼 (저장 로직 완료 ✅)
- 🇫🇷 **FR_BOAMP**: 프랑스 공공조달 ✅
  - 공식 사이트: https://www.boamp.fr
  - 상태: **8건 수집/저장 성공 - RSS/API 통합**

- 🇩🇪 **DE_VERGABESTELLEN**: 독일 공공조달 ✅
  - 독일 조달 포털: https://www.deutsches-vergabeportal.de
  - eVergabe: https://www.evergabe.de
  - 상태: **3건 더미 데이터 저장 성공 - 네트워크 실패 시 대안 제공**

- 🇳🇱 **NL_TENDERNED**: 네덜란드 공공조달 ✅
  - 공식 사이트: https://www.tenderned.nl
  - 상태: **저장 구조 검증 완료**

- 🇪🇸 **ES_PCSP**: 스페인 공공조달 ✅
  - 공식 사이트: https://contrataciondelestado.es
  - 상태: **저장 구조 검증 완료**

- 🇮🇹 **IT_MEPA**: 이탈리아 공공조달 ✅
  - 공식 사이트: https://www.acquistinretepa.it
  - CONSIP: https://bandi.acquistinretepa.it
  - 상태: **저장 구조 검증 완료**

## 🚀 주요 기능

- **🌐 글로벌 입찰 수집**: 8개국 주요 조달 플랫폼 통합 모니터링
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
│   ├── crawler/                        # 크롤러 모듈
│   │   ├── manager.py                  # 크롤러 매니저
│   │   ├── g2b_crawler.py              # 한국 G2B API
│   │   ├── samgov_crawler.py           # 미국 SAM.gov
│   │   ├── ted_crawler.py              # EU TED API
│   │   ├── uk_fts_crawler.py           # 영국 FTS OCDS
│   │   ├── fr_boamp_crawler.py         # 프랑스 BOAMP
│   │   ├── de_vergabestellen_crawler.py # 독일 Vergabestellen
│   │   ├── nl_tenderned_crawler.py     # 네덜란드 TenderNed
│   │   ├── es_pcsp_crawler.py          # 스페인 PCSP
│   │   └── it_mepa_crawler.py          # 이탈리아 MEPA
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
```

**실행 성공 시 로그:**
```
2025-09-21 12:43:36 | INFO | 데이터베이스 엔진 생성 성공
2025-09-21 12:43:37 | INFO | 데이터베이스 초기화 완료
2025-09-21 12:43:37 | INFO | 🔐 SSL 인증서가 감지되어 HTTPS로 실행합니다
2025-09-21 12:43:37 | INFO | 🚀 Seegene Bid MCP Server 시작
2025-09-21 12:43:37 | INFO | 서버 주소: https://0.0.0.0:8000
2025-09-21 12:43:37 | INFO | API 문서: https://0.0.0.0:8000/docs
2025-09-21 12:43:37 | INFO | MCP 엔드포인트: https://0.0.0.0:8000/mcp
```

### 개발 모드 실행

```bash
# 자동 리로드 활성화
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### SSL/HTTPS 지원

서버는 SSL 인증서가 있을 경우 자동으로 HTTPS 모드로 실행됩니다:
- 인증서 파일: `server.crt`, `server.key`
- 프로덕션 환경에서 권장

## 🔧 MCP 클라이언트 연동

### Microsoft Copilot Studio 연결 (권장)

**⚠️ 중요**: 2025년 8월 이후 Streamable transport만 지원됩니다.

#### 1. MCP 온보딩 마법사 사용

1. **Copilot Studio 접속**
   - Microsoft Copilot Studio에 로그인
   - 왼쪽 네비게이션에서 **"Agents"** 선택

2. **에이전트 설정**
   - 연결할 에이전트 선택
   - **"Tools"** → **"Add a tool"** → **"New tool"** → **"Model Context Protocol"**

3. **서버 정보 입력**
   ```
   Server name: Seegene Bid Information Server
   Server description: 씨젠을 위한 글로벌 입찰 정보 수집 및 분석 시스템
   Server URL: https://your-domain.com:8000/mcp
   ```

4. **인증 설정**
   - 현재: **No authentication**
   - 프로덕션: **API key** 또는 **OAuth 2.0** 권장

#### 2. 사용 가능한 MCP 도구들

- `search_bids`: 입찰 정보 검색
- `get_bid_statistics`: 입찰 통계 조회
- `run_crawler`: 크롤러 실행
- `get_crawler_results`: 크롤러 결과 조회
- `search_advanced_bids`: 고급 검색
- `get_keyword_suggestions`: 키워드 제안
- `expand_keywords`: 키워드 확장
- `schedule_crawler`: 크롤러 스케줄링

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

**4. SQLite 연결 오류 해결됨 ✅**
- **문제**: `asyncio.CancelledError` 발생
- **해결**: SQLite 파라미터 최적화 및 비동기 처리 개선
- **결과**: 안정적인 데이터베이스 연결

**5. Windows 연결 오류 최소화**
- **문제**: `ConnectionResetError` 발생
- **해결**: Windows 전용 asyncio 설정 및 graceful shutdown 구현

**6. 401 인증 오류 해결됨 ✅**
- **문제**: SSL 인증서 검증 실패로 인한 401 에러
- **해결**: SSL 컨텍스트 우회 설정 및 User-Agent 헤더 최적화
- **결과**: 모든 크롤러에서 안정적인 API 접근

## 🏥 헬스케어 특화 기능

### CPV 코드 기반 필터링

시스템은 다음 CPV(Common Procurement Vocabulary) 코드를 기반으로 헬스케어 관련 입찰을 자동 식별합니다:

- **33100000**: 의료 장비 및 기기
- **33696000**: 진단 시약
- **85100000**: 보건 서비스
- **73140000**: 의학 연구

### 다국어 키워드 매칭

#### 핵심 진단키트 키워드
- **한국어**: PCR, 진단키트, 진단, 검사키트, 시약, RT-PCR, 면역분석, 측면유동, 현장진료, 코로나, 인플루엔자, 호흡기, 분자진단, 체외진단, 병원체검출, 스크리닝

- **영어**: diagnostic, test kit, assay, reagent, pcr, rt-pcr, elisa, immunoassay, lateral flow, point of care, covid, coronavirus, influenza, respiratory, molecular diagnostic, in vitro diagnostic, ivd, pathogen detection, biomarker, screening

- **프랑스어**: diagnostic, trousse de test, réactif, pcr, immunoessai, point de soins, covid, grippe

- **독일어**: diagnostik, testkit, reagenz, pcr, immunoassay, point-of-care, covid, grippe

- **스페인어**: diagnóstico, kit de prueba, reactivo, pcr, inmunoensayo, punto de atención, covid, gripe

#### 광범위 헬스케어 키워드 (TED 플랫폼용)
- **영어**: medical, healthcare, health, diagnostic, laboratory, hospital, pharmaceutical, biomedical, clinical, equipment, device, reagent, vaccine, medicine, therapy, surgical, biotechnology, biotech, life science, research, testing, analysis, screening, monitoring, treatment, care, medic, pharma, bio, lab, test, drug, molecular

- **유럽 다국어**: médical, santé (프랑스어), medizin, gesundheit (독일어), medicale, salute (이탈리아어)

#### 프랑스 BOAMP 특화 키워드
- **프랑스어**: médical, médecin, santé, hôpital, clinique, diagnostic, laboratoire, équipement médical, dispositif médical, matériel médical, chu, aphp

### 관련성 점수 계산

각 입찰공고는 다음 기준으로 헬스케어 관련성 점수(0.0-1.0)를 받습니다:
- CPV 코드 매칭 (가중치 50%)
- 제목 키워드 매칭 (가중치 30%)
- 설명 키워드 매칭 (가중치 20%)

## 📦 다음 단계

1. **추가 데이터 소스**: 아시아 태평양 지역 조달 플랫폼 확장
2. **AI 기반 분석**: 입찰 성공 확률 예측 및 경쟁 분석
3. **알림 시스템**: 이메일/Slack/Teams 실시간 알림
4. **웹 대시보드**: 시각화된 관리 인터페이스 및 분석 도구
5. **모바일 앱**: 실시간 입찰 모니터링 및 알림

## ⚡ 빠른 시작 체크리스트

- [x] 프로젝트 생성 완료
- [x] 데이터베이스 연결 문제 해결
- [x] SSL/HTTPS 지원 추가
- [x] Microsoft Copilot Studio MCP 연동 가이드 작성
- [ ] `cd seegene-bid-mcp`
- [ ] `pip install -r requirements.txt`
- [ ] `.env` 파일 설정 (특히 G2B_API_KEY)
- [ ] `python run.py` 실행
- [ ] https://localhost:8000/health 접속 확인 (HTTPS 주의)
- [ ] https://localhost:8000/docs에서 API 문서 확인
- [ ] 크롤링 테스트: `curl -X POST https://localhost:8000/crawl-all`
- [ ] Microsoft Copilot Studio MCP 연결 (권장)
- [ ] Claude Desktop MCP 설정 (선택사항)

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
