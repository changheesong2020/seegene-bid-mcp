"""
CPV (Common Procurement Vocabulary) 헬스케어 관련 코드 필터링 유틸리티
Healthcare-related CPV code filtering for European tender classification
"""

from typing import List, Set, Dict, Optional
import re


class CPVHealthcareFilter:
    """CPV 코드를 이용한 헬스케어 관련 입찰 필터링"""

    # 의료/헬스케어 관련 CPV 코드 (8자리)
    HEALTHCARE_CPV_CODES = {
        # 의료 기기 및 장비
        "33100000": "의료 장비",
        "33110000": "의료용 영상 장비",
        "33111000": "X선 장비",
        "33112000": "자기공명영상(MRI) 장비",
        "33113000": "컴퓨터단층촬영(CT) 장비",
        "33114000": "초음파 장비",
        "33120000": "의료용 가구",
        "33130000": "의료용 소프트웨어",
        "33140000": "의료용 소모품",
        "33141000": "의료용 일회용품",
        "33150000": "수술용 기구",
        "33160000": "치과용 장비",
        "33170000": "수의학용 장비",
        "33180000": "보조 의료 제품",
        "33190000": "기타 의료 장비",

        # 실험실 장비 및 기기
        "38000000": "실험실, 광학 및 정밀 장비",
        "38100000": "항해, 기상, 수로 장비",
        "38200000": "측정 장비",
        "38300000": "실험실 장비",
        "38400000": "산업용 공정 제어 장비",
        "38500000": "광학 장비",
        "38600000": "사진 장비",
        "38700000": "정밀 장비",
        "38800000": "의료용 장비",
        "38900000": "기타 정밀 장비",

        # 진단 키트 및 시약
        "33696000": "진단 시약",
        "33651000": "의료용 화학 제품",
        "33652000": "약학용 화학 제품",
        "33690000": "의약품",
        "33691000": "혈액 제제",
        "33692000": "백신",
        "33693000": "항생제",
        "33694000": "진통제",
        "33695000": "마취제",
        "33696000": "진단용 시약",
        "33697000": "조영제",
        "33698000": "방사성 의약품",
        "33699000": "기타 의약품",

        # 보건 서비스
        "85100000": "보건 서비스",
        "85110000": "병원 서비스",
        "85111000": "응급 의료 서비스",
        "85112000": "전문 의료 서비스",
        "85120000": "의료 업무 서비스",
        "85121000": "공중 보건 서비스",
        "85130000": "치과 서비스",
        "85140000": "산과 서비스",
        "85150000": "간병 서비스",
        "85160000": "기타 의료 서비스",

        # IT 헬스케어 관련
        "72000000": "IT 서비스",
        "72200000": "소프트웨어 프로그래밍 및 컨설팅 서비스",
        "72500000": "컴퓨터 관련 서비스",
        "72600000": "컴퓨터 지원 서비스",

        # 연구개발 서비스
        "73000000": "연구개발 서비스",
        "73100000": "자연과학 연구개발 서비스",
        "73110000": "물리학 연구",
        "73120000": "화학 연구",
        "73130000": "생물학 연구",
        "73140000": "의학 연구",
        "73200000": "사회과학 연구개발 서비스",
        "73300000": "학제간 연구개발 서비스",
    }

    # 진단 키트 관련 특별 키워드
    DIAGNOSTIC_KEYWORDS = {
        'en': [
            'diagnostic', 'test kit', 'assay', 'reagent', 'pcr', 'rt-pcr',
            'elisa', 'immunoassay', 'lateral flow', 'point of care',
            'covid', 'coronavirus', 'influenza', 'respiratory',
            'molecular diagnostic', 'in vitro diagnostic', 'ivd',
            'pathogen detection', 'biomarker', 'screening'
        ],
        'ko': [
            '진단키트', '진단', '검사키트', '시약', 'PCR', 'RT-PCR',
            '면역분석', '측면유동', '현장진료', '코로나', '인플루엔자',
            '호흡기', '분자진단', '체외진단', '병원체검출', '스크리닝'
        ],
        'fr': [
            'diagnostic', 'trousse de test', 'réactif', 'pcr',
            'immunoessai', 'point de soins', 'covid', 'grippe'
        ],
        'de': [
            'diagnostik', 'testkit', 'reagenz', 'pcr',
            'immunoassay', 'point-of-care', 'covid', 'grippe'
        ],
        'es': [
            'diagnóstico', 'kit de prueba', 'reactivo', 'pcr',
            'inmunoensayo', 'punto de atención', 'covid', 'gripe'
        ]
    }

    def __init__(self):
        """CPV 필터 초기화"""
        self.healthcare_codes = set(self.HEALTHCARE_CPV_CODES.keys())
        self.diagnostic_keywords_flat = []
        for lang_keywords in self.DIAGNOSTIC_KEYWORDS.values():
            self.diagnostic_keywords_flat.extend([kw.lower() for kw in lang_keywords])

    def is_healthcare_cpv(self, cpv_code: str) -> bool:
        """CPV 코드가 헬스케어 관련인지 확인"""
        if not cpv_code:
            return False

        # CPV 코드 정규화 (공백, 하이픈 제거)
        clean_code = re.sub(r'[-\s]', '', cpv_code)

        # 8자리 코드로 맞춤
        if len(clean_code) >= 8:
            main_code = clean_code[:8]
            if main_code in self.healthcare_codes:
                return True

        # 상위 분류 확인 (예: 33000000 계열)
        if len(clean_code) >= 2:
            category = clean_code[:2] + "000000"
            if category in ["33000000", "38000000", "85000000", "73000000"]:
                return True

        return False

    def is_diagnostic_related(self, text: str, language: Optional[str] = None) -> bool:
        """텍스트가 진단 관련인지 확인"""
        if not text:
            return False

        text_lower = text.lower()

        # 특정 언어 키워드 확인
        if language and language in self.DIAGNOSTIC_KEYWORDS:
            keywords = [kw.lower() for kw in self.DIAGNOSTIC_KEYWORDS[language]]
            return any(keyword in text_lower for keyword in keywords)

        # 모든 언어 키워드 확인
        return any(keyword in text_lower for keyword in self.diagnostic_keywords_flat)

    def get_healthcare_relevance_score(self,
                                     cpv_codes: List[str] = None,
                                     title: str = "",
                                     description: str = "",
                                     language: Optional[str] = None) -> float:
        """헬스케어 관련성 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0

        # CPV 코드 점수 (가중치 0.5)
        if cpv_codes:
            cpv_matches = sum(1 for code in cpv_codes if self.is_healthcare_cpv(code))
            if cpv_matches > 0:
                score += 0.5 * min(cpv_matches / len(cpv_codes), 1.0)

        # 제목 키워드 점수 (가중치 0.3)
        if title and self.is_diagnostic_related(title, language):
            score += 0.3

        # 설명 키워드 점수 (가중치 0.2)
        if description and self.is_diagnostic_related(description, language):
            score += 0.2

        return min(score, 1.0)

    def is_healthcare_relevant(self,
                             cpv_codes: List[str] = None,
                             title: str = "",
                             description: str = "",
                             language: Optional[str] = None,
                             threshold: float = 0.3) -> bool:
        """헬스케어 관련성 여부 판단"""
        score = self.get_healthcare_relevance_score(cpv_codes, title, description, language)
        return score >= threshold

    def get_matched_keywords(self,
                           text: str,
                           language: Optional[str] = None) -> List[str]:
        """매칭된 키워드 반환"""
        if not text:
            return []

        text_lower = text.lower()
        matched = []

        # 특정 언어 키워드 확인
        if language and language in self.DIAGNOSTIC_KEYWORDS:
            keywords = self.DIAGNOSTIC_KEYWORDS[language]
        else:
            # 모든 언어 키워드 확인
            keywords = self.diagnostic_keywords_flat

        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        return matched

    def get_cpv_description(self, cpv_code: str) -> Optional[str]:
        """CPV 코드에 대한 설명 반환"""
        if not cpv_code:
            return None

        clean_code = re.sub(r'[-\s]', '', cpv_code)
        if len(clean_code) >= 8:
            main_code = clean_code[:8]
            return self.HEALTHCARE_CPV_CODES.get(main_code)

        return None

    def filter_healthcare_tenders(self, tenders: List[Dict], threshold: float = 0.3) -> List[Dict]:
        """입찰 목록에서 헬스케어 관련 입찰만 필터링"""
        filtered = []

        for tender in tenders:
            cpv_codes = tender.get('cpv_codes', [])
            title = tender.get('title', '')
            description = tender.get('description', '')
            language = tender.get('language')

            if self.is_healthcare_relevant(cpv_codes, title, description, language, threshold):
                # 매칭 정보 추가
                tender['healthcare_score'] = self.get_healthcare_relevance_score(
                    cpv_codes, title, description, language
                )
                tender['matched_keywords'] = self.get_matched_keywords(title + ' ' + description, language)
                filtered.append(tender)

        return filtered


# 전역 필터 인스턴스
cpv_filter = CPVHealthcareFilter()


def is_healthcare_cpv(cpv_code: str) -> bool:
    """CPV 코드가 헬스케어 관련인지 확인하는 편의 함수"""
    return cpv_filter.is_healthcare_cpv(cpv_code)


def is_diagnostic_related(text: str, language: Optional[str] = None) -> bool:
    """텍스트가 진단 관련인지 확인하는 편의 함수"""
    return cpv_filter.is_diagnostic_related(text, language)


def filter_healthcare_tenders(tenders: List[Dict], threshold: float = 0.3) -> List[Dict]:
    """헬스케어 관련 입찰만 필터링하는 편의 함수"""
    return cpv_filter.filter_healthcare_tenders(tenders, threshold)