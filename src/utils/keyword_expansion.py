"""
Keyword Expansion System
키워드 확장 및 검색어 개선 시스템
"""

import re
from typing import List, Dict, Set, Any
from dataclasses import dataclass
from src.models.advanced_filters import KeywordExpansion, KeywordSuggestion
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExpandedKeyword:
    """확장된 키워드"""
    keyword: str
    source: str  # synonym, related, translation, abbreviation
    relevance: float
    weight: float = 1.0


class KeywordExpansionEngine:
    """키워드 확장 엔진"""

    def __init__(self):
        self.synonym_dict = self._load_synonyms()
        self.related_terms = self._load_related_terms()
        self.translations = self._load_translations()
        self.abbreviations = self._load_abbreviations()

    def _load_synonyms(self) -> Dict[str, List[str]]:
        """동의어 사전 로드"""
        return {
            # 한국어 동의어
            'PCR': ['중합효소연쇄반응', 'polymerase chain reaction', 'RT-PCR'],
            '진단키트': ['진단 키트', '진단 도구', '검사키트', '검사 키트'],
            '분자진단': ['분자 진단', 'molecular diagnosis', 'molecular diagnostic'],
            '체외진단': ['체외 진단', 'IVD', 'in vitro diagnostic'],
            '코로나': ['COVID', 'COVID-19', '신종코로나바이러스', 'SARS-CoV-2'],
            '인플루엔자': ['독감', 'influenza', 'flu'],
            '호흡기감염': ['호흡기 감염', 'respiratory infection'],
            '병원체검사': ['병원체 검사', 'pathogen test'],

            # 영어 동의어
            'diagnostic kit': ['diagnostic tool', 'test kit', 'assay kit'],
            'molecular diagnostic': ['molecular diagnosis', 'molecular test'],
            'in vitro diagnostic': ['IVD', 'laboratory diagnostic'],
            'point of care': ['POC', 'point-of-care', 'bedside test'],
            'respiratory pathogen': ['respiratory infection', 'lung infection'],
            'COVID test': ['COVID-19 test', 'coronavirus test', 'SARS-CoV-2 test'],
            'influenza test': ['flu test', 'influenza diagnostic'],
            'rapid test': ['quick test', 'fast test', 'instant test'],
            'antigen test': ['antigen detection', 'antigen assay'],
            'antibody test': ['serology test', 'serological test'],
        }

    def _load_related_terms(self) -> Dict[str, List[str]]:
        """관련 용어 사전 로드"""
        return {
            # 의료기기 관련
            'PCR': ['qPCR', 'real-time PCR', '정량PCR', 'RT-qPCR', 'nested PCR'],
            '진단키트': ['래피드테스트', '항원검사', '항체검사', '면역크로마토그래피'],
            '분자진단': ['LAMP', 'NASBA', 'TMA', 'SDA', 'RPA'],
            '체외진단': ['임상화학', '면역검사', '혈액학', '미생물학'],

            # 질병 관련
            '코로나': ['팬데믹', '감염병', '바이러스', '변이'],
            '인플루엔자': ['조류독감', '신종플루', 'H1N1', 'H5N1'],
            '호흡기감염': ['폐렴', '기관지염', '상기도감염', '하기도감염'],

            # 영어 관련 용어
            'diagnostic kit': ['biosensor', 'microarray', 'ELISA', 'immunoassay'],
            'molecular diagnostic': ['NGS', 'sequencing', 'genotyping', 'mutation detection'],
            'point of care': ['portable device', 'handheld device', 'mobile testing'],
            'COVID test': ['pandemic', 'outbreak', 'epidemic', 'variant'],
            'respiratory pathogen': ['pneumonia', 'bronchitis', 'COPD', 'asthma']
        }

    def _load_translations(self) -> Dict[str, List[str]]:
        """다국어 번역 사전 로드"""
        return {
            # 한국어 → 영어
            'PCR': ['PCR', 'polymerase chain reaction'],
            '진단키트': ['diagnostic kit', 'test kit'],
            '분자진단': ['molecular diagnostic', 'molecular diagnosis'],
            '체외진단': ['in vitro diagnostic', 'IVD'],
            '코로나': ['corona', 'COVID', 'coronavirus'],
            '인플루엔자': ['influenza', 'flu'],
            '호흡기감염': ['respiratory infection'],
            '병원체검사': ['pathogen test', 'pathogen detection'],

            # 영어 → 한국어
            'diagnostic kit': ['진단키트', '진단 키트'],
            'molecular diagnostic': ['분자진단', '분자 진단'],
            'in vitro diagnostic': ['체외진단', '체외 진단'],
            'point of care': ['현장진료', 'POC'],
            'COVID test': ['코로나검사', '코로나 검사'],
            'influenza test': ['인플루엔자검사', '독감검사'],
            'respiratory pathogen': ['호흡기병원체', '호흡기 병원체'],

            # 중국어 (간체)
            'diagnostic kit': ['诊断试剂盒', '检测试剂盒'],
            'PCR': ['聚合酶链反应', 'PCR检测'],
            'COVID test': ['新冠检测', '新冠病毒检测'],
        }

    def _load_abbreviations(self) -> Dict[str, List[str]]:
        """약어 사전 로드"""
        return {
            # 축약형 → 전체형
            'PCR': ['polymerase chain reaction', '중합효소연쇄반응'],
            'RT-PCR': ['reverse transcription PCR', '역전사 PCR'],
            'qPCR': ['quantitative PCR', '정량 PCR'],
            'IVD': ['in vitro diagnostic', '체외진단'],
            'POC': ['point of care', '현장진료'],
            'ELISA': ['enzyme-linked immunosorbent assay', '효소면역측정법'],
            'NGS': ['next generation sequencing', '차세대염기서열분석'],
            'LAMP': ['loop-mediated isothermal amplification', 'LAMP 증폭'],
            'COPD': ['chronic obstructive pulmonary disease', '만성폐쇄성폐질환'],

            # 전체형 → 축약형
            'polymerase chain reaction': ['PCR'],
            'in vitro diagnostic': ['IVD'],
            'point of care': ['POC'],
            'enzyme-linked immunosorbent assay': ['ELISA'],
            'next generation sequencing': ['NGS'],
            'chronic obstructive pulmonary disease': ['COPD'],
        }

    def expand_keywords(
        self,
        keywords: List[str],
        expansion_config: KeywordExpansion
    ) -> List[ExpandedKeyword]:
        """키워드 확장"""
        expanded = []
        seen = set()

        for keyword in keywords:
            # 원본 키워드 추가
            if keyword.lower() not in seen:
                expanded.append(ExpandedKeyword(
                    keyword=keyword,
                    source="original",
                    relevance=1.0,
                    weight=1.0
                ))
                seen.add(keyword.lower())

            # 동의어 확장
            if expansion_config.enable_synonyms:
                synonyms = self._get_synonyms(keyword)
                for synonym in synonyms[:expansion_config.max_expansions_per_keyword]:
                    if synonym.lower() not in seen:
                        expanded.append(ExpandedKeyword(
                            keyword=synonym,
                            source="synonym",
                            relevance=0.9,
                            weight=0.9
                        ))
                        seen.add(synonym.lower())

            # 관련 용어 확장
            if expansion_config.enable_related_terms:
                related = self._get_related_terms(keyword)
                for term in related[:expansion_config.max_expansions_per_keyword]:
                    if term.lower() not in seen:
                        expanded.append(ExpandedKeyword(
                            keyword=term,
                            source="related",
                            relevance=0.8,
                            weight=0.8
                        ))
                        seen.add(term.lower())

            # 번역 확장
            if expansion_config.enable_translations:
                translations = self._get_translations(keyword)
                for translation in translations[:expansion_config.max_expansions_per_keyword]:
                    if translation.lower() not in seen:
                        expanded.append(ExpandedKeyword(
                            keyword=translation,
                            source="translation",
                            relevance=0.95,
                            weight=0.95
                        ))
                        seen.add(translation.lower())

            # 약어 확장
            if expansion_config.enable_abbreviations:
                abbreviations = self._get_abbreviations(keyword)
                for abbr in abbreviations[:expansion_config.max_expansions_per_keyword]:
                    if abbr.lower() not in seen:
                        expanded.append(ExpandedKeyword(
                            keyword=abbr,
                            source="abbreviation",
                            relevance=0.85,
                            weight=0.85
                        ))
                        seen.add(abbr.lower())

        logger.info(f"키워드 확장: {len(keywords)} → {len(expanded)}")
        return expanded

    def _get_synonyms(self, keyword: str) -> List[str]:
        """동의어 검색"""
        synonyms = []
        keyword_lower = keyword.lower()

        for key, values in self.synonym_dict.items():
            if key.lower() == keyword_lower or keyword_lower in [v.lower() for v in values]:
                synonyms.extend([key] + values)

        # 중복 제거 및 원본 키워드 제외
        synonyms = [s for s in set(synonyms) if s.lower() != keyword_lower]
        return synonyms

    def _get_related_terms(self, keyword: str) -> List[str]:
        """관련 용어 검색"""
        related = []
        keyword_lower = keyword.lower()

        for key, values in self.related_terms.items():
            if key.lower() == keyword_lower:
                related.extend(values)

        return related

    def _get_translations(self, keyword: str) -> List[str]:
        """번역 검색"""
        translations = []
        keyword_lower = keyword.lower()

        for key, values in self.translations.items():
            if key.lower() == keyword_lower:
                translations.extend(values)

        return translations

    def _get_abbreviations(self, keyword: str) -> List[str]:
        """약어 검색"""
        abbreviations = []
        keyword_lower = keyword.lower()

        for key, values in self.abbreviations.items():
            if key.lower() == keyword_lower:
                abbreviations.extend(values)

        return abbreviations

    def get_keyword_suggestions(
        self,
        keywords: List[str],
        max_suggestions: int = 20
    ) -> List[KeywordSuggestion]:
        """키워드 제안"""
        suggestions = []
        seen = set([k.lower() for k in keywords])

        for keyword in keywords:
            # 동의어 제안
            for synonym in self._get_synonyms(keyword):
                if synonym.lower() not in seen:
                    suggestions.append(KeywordSuggestion(
                        keyword=synonym,
                        frequency=100,  # 가상 빈도
                        relevance=0.9,
                        source="synonym"
                    ))
                    seen.add(synonym.lower())

            # 관련 용어 제안
            for related in self._get_related_terms(keyword):
                if related.lower() not in seen:
                    suggestions.append(KeywordSuggestion(
                        keyword=related,
                        frequency=80,
                        relevance=0.8,
                        source="related"
                    ))
                    seen.add(related.lower())

            # 번역 제안
            for translation in self._get_translations(keyword):
                if translation.lower() not in seen:
                    suggestions.append(KeywordSuggestion(
                        keyword=translation,
                        frequency=90,
                        relevance=0.95,
                        source="translation"
                    ))
                    seen.add(translation.lower())

            # 약어 제안
            for abbr in self._get_abbreviations(keyword):
                if abbr.lower() not in seen:
                    suggestions.append(KeywordSuggestion(
                        keyword=abbr,
                        frequency=70,
                        relevance=0.85,
                        source="abbreviation"
                    ))
                    seen.add(abbr.lower())

        # 관련도 순으로 정렬
        suggestions.sort(key=lambda x: x.relevance, reverse=True)
        return suggestions[:max_suggestions]

    def calculate_enhanced_relevance(
        self,
        text: str,
        expanded_keywords: List[ExpandedKeyword]
    ) -> float:
        """향상된 관련성 점수 계산"""
        text_lower = text.lower()
        total_score = 0.0
        matched_keywords = []

        for expanded_keyword in expanded_keywords:
            keyword_lower = expanded_keyword.keyword.lower()

            # 키워드 매칭 확인
            if keyword_lower in text_lower:
                # 가중치 적용 점수
                score = expanded_keyword.relevance * expanded_keyword.weight

                # 정확한 단어 매칭에 보너스 점수
                if re.search(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
                    score *= 1.2

                # 제목에 있으면 추가 점수
                if 'title' in text.lower() and keyword_lower in text.lower():
                    score *= 1.5

                total_score += score
                matched_keywords.append(expanded_keyword.keyword)

        # 최대 점수 제한
        final_score = min(total_score, 10.0)

        logger.debug(f"관련성 점수: {final_score:.2f}, 매칭 키워드: {matched_keywords}")
        return final_score


# 전역 키워드 확장 엔진 인스턴스
keyword_engine = KeywordExpansionEngine()