# FR_BOAMP 크롤러 서버 에러 해결 방법

## 문제 상황
- 엔드포인트: `http://20.243.193.245:8000/crawl/FR_BOAMP`
- 에러: 500 Internal Server Error (실제로는 Pydantic 검증 오류)
- 원인: `site` 필드 누락으로 인한 응답 모델 검증 실패

## 에러 메시지
```json
{
  "detail": "1 validation error for CrawlerExecutionResponse\nresult.site\n  Field required [type=missing, input_value={'success': True, 'total_...2232', 'total_found': 0}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/2.11/v/missing"
}
```

## 원인 분석
FR_BOAMP 크롤러는 `source` 필드를 반환하지만, API 응답 모델은 `site` 필드를 기대합니다.

## 해결 방법
`src/crawler/manager.py` 파일의 244-252줄을 다음과 같이 수정:

### 수정 전
```python
if site_name in ["FR_BOAMP", "DE_VERGABESTELLEN", "IT_MEPA", "ES_PCSP", "NL_TENDERNED"]:
    logger.info(f"📡 {site_name} crawl() 메서드 호출")
    result = await crawler.crawl(keywords)
    # 새 크롤러의 결과 필드명을 기존 형식으로 변환
    if "total_collected" in result:
        result["total_found"] = result["total_collected"]
    logger.info(f"✅ {site_name} crawl() 완료: {result.get('total_found', 0)}건")
```

### 수정 후
```python
if site_name in ["FR_BOAMP", "DE_VERGABESTELLEN", "IT_MEPA", "ES_PCSP", "NL_TENDERNED"]:
    logger.info(f"📡 {site_name} crawl() 메서드 호출")
    result = await crawler.crawl(keywords)
    # 새 크롤러의 결과 필드명을 기존 형식으로 변환
    if "total_collected" in result:
        result["total_found"] = result["total_collected"]
    if "source" in result:
        result["site"] = result["source"]
    logger.info(f"✅ {site_name} crawl() 완료: {result.get('total_found', 0)}건")
```

## 추가된 라인
```python
if "source" in result:
    result["site"] = result["source"]
```

## 테스트 결과
로컬에서 수정 후 테스트:
- ✅ `site: FR_BOAMP` 필드 정상 설정
- ✅ `total_found: 16` 정상 반환
- ✅ 16건의 프랑스 공공조달 공고 수집 성공

## 기타 정보
- 올바른 엔드포인트: `/crawl/FR_BOAMP` (❌ `/crawl/BOAMP` 아님)
- 크롤러는 BOAMP OpenDataSoft API를 통해 정상 작동
- 의료기기 관련 키워드 검색 정상 작동