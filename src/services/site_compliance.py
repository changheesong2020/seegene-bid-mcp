"""Service utilities that expose procurement site compliance guidance."""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime

from src.models.site_compliance import SiteComplianceDetails


def _build_entry(
    slug: str,
    country: str,
    site_name: str,
    base_urls: List[str],
    robots_notes: str,
    crawling_constraints: str,
    legal_notes: str,
    robots_txt_url: Optional[str] = None,
    last_reviewed: Optional[datetime] = None,
) -> SiteComplianceDetails:
    """Create a :class:`SiteComplianceDetails` object with shared defaults."""

    return SiteComplianceDetails(
        slug=slug,
        country=country,
        site_name=site_name,
        base_urls=base_urls,
        robots_txt_url=robots_txt_url,
        robots_notes=robots_notes.strip(),
        crawling_constraints=crawling_constraints.strip(),
        legal_notes=legal_notes.strip(),
        last_reviewed=last_reviewed or datetime.utcnow(),
    )


_SITE_COMPLIANCE_ENTRIES: Dict[str, SiteComplianceDetails] = {
    entry.slug: entry
    for entry in [
        _build_entry(
            slug="es-pcsp",
            country="Spain",
            site_name="Plataforma de Contratación del Sector Público",
            base_urls=["https://contrataciondelestado.es"],
            robots_txt_url="https://contrataciondelestado.es/robots.txt",
            robots_notes=(
                "공식 경로(https://contrataciondelestado.es/robots.txt)를 확인했으나 "
                "응답이 비어있거나 접근이 제한되는 사례가 보고되어 실제 내용 확보가 어려움."
            ),
            crawling_constraints=(
                "공개 입찰공고는 일반적으로 열람 가능하나, 문서 형식(PDF 등)이나 다운로드 링크가 "
                "특정 플로우를 거쳐야 하는 경우가 있음. 대량/자동 수집 전에는 Open Data/API 제공 "
                "여부를 우선 확인하고, 비상업적 이용 약관이나 인증 요구 사항을 검토하는 것이 안전함."
            ),
            legal_notes=(
                "정부/공공기관 공고는 대개 공개 대상이지만, 공고문에 포함된 도면·이미지 등은 별도 저작권이 "
                "존재할 수 있음. 데이터 이용 조건이나 오픈 데이터 라이선스를 반드시 확인해야 함."
            ),
        ),
        _build_entry(
            slug="fr-boamp",
            country="France",
            site_name="BOAMP / PLACE (Marchés publics)",
            base_urls=["https://www.boamp.fr", "https://www.marches-publics.gouv.fr"],
            robots_txt_url="https://www.boamp.fr/robots.txt",
            robots_notes=(
                "robots.txt 전문을 확인하려 했으나 일부 경로에서 접근이 제한되거나 리디렉션되어 내용 확인이 어려움."
            ),
            crawling_constraints=(
                "법적으로 공고 공개 의무가 있어 기본 정보 접근은 가능하나, PDF 사양서 등은 등록 사용자 또는 "
                "로그인이 필요한 경우가 있음. 페이지 구조가 복잡하고 동적 요소가 많아 크롤링 경로 탐색 비용이 높을 수 있음."
            ),
            legal_notes=(
                "프랑스 공공조달 정보는 공개 이용이 가능하지만, 사이트에서 명시한 이용 약관과 저작권 고지를 준수해야 함."
            ),
        ),
        _build_entry(
            slug="de-vergabestellen",
            country="Germany",
            site_name="Deutsches Vergabeportal / eVergabe 등",
            base_urls=[
                "https://www.deutsches-vergabeportal.de",
                "https://www.evergabe.de",
            ],
            robots_notes=(
                "각 포털의 robots.txt 존재 여부와 내용은 아직 확인되지 않았으며, 일부 포털은 API나 공고 발행 서비스를 제공하는 것으로 알려짐."
            ),
            crawling_constraints=(
                "공고 자체는 공개되지만, 많은 첨부 문서가 로그인 또는 유료 회원에게만 제공되는 경우가 있음. 연방/주별로 포털이 다수 존재해 "
                "각각 정책이 상이할 수 있으므로 사이트별 정책을 개별 확인해야 함."
            ),
            legal_notes=(
                "공공조달 정보는 공개 대상이지만, 문서 내 설계도나 상표 등은 별도의 저작권 보호를 받을 수 있어 재사용 시 출처 및 라이선스 확인이 필요함."
            ),
        ),
        _build_entry(
            slug="it-mepa",
            country="Italy",
            site_name="Acquisti in Rete della PA (MEPA)",
            base_urls=["https://www.acquistinretepa.it"],
            robots_txt_url="https://www.acquistinretepa.it/robots.txt",
            robots_notes=(
                "정부 포털 특성상 전면 차단 가능성은 낮지만, 세부 섹션별 허용/비허용 규칙이 존재할 수 있어 최신 robots.txt를 직접 확인해야 함."
            ),
            crawling_constraints=(
                "입찰·협상 공고는 공개되지만 세부 첨부(PDF, ZIP 등)는 로그인이나 자격이 필요한 경우가 많음. 대량 자동화 전에 공식 Open Data 채널이나 API 제공 여부를 확인하는 것이 권장됨."
            ),
            legal_notes=(
                "이탈리아 공공조달 정보는 일반적으로 공개 대상이나, 문서 내 도면·브랜드 로고 등은 개별 저작권이 있을 수 있음. 재배포 시 IODL 2.0 등 오픈데이터 라이선스나 사이트 약관을 확인해야 함."
            ),
        ),
        _build_entry(
            slug="uk-fts",
            country="United Kingdom",
            site_name="Contracts Finder / Find a Tender Service",
            base_urls=[
                "https://www.contractsfinder.service.gov.uk",
                "https://find-tender.service.gov.uk",
            ],
            robots_txt_url="https://find-tender.service.gov.uk/robots.txt",
            robots_notes=(
                "두 도메인 모두 robots.txt가 제공되며 기본 검색 페이지는 일반적으로 허용되지만, 특정 경로나 API 호출에는 제한 규칙이 존재할 수 있음."
            ),
            crawling_constraints=(
                "공공조달 공고는 공개 의무가 있으나, 자동화 트래픽은 정부 디지털서비스(GDS)의 이용 약관과 rate limit 정책을 준수해야 함. 일부 문서 링크가 공급자 시스템으로 연결되어 별도 인증이 필요한 경우가 있음."
            ),
            legal_notes=(
                "Crown Copyright 하에서 Open Government Licence v3.0 등의 재사용 조건을 준수해야 하며, 제3자 문서는 별도 저작권 또는 상업적 제한이 있을 수 있음."
            ),
        ),
        _build_entry(
            slug="nl-tenderned",
            country="Netherlands",
            site_name="TenderNed",
            base_urls=["https://www.tenderned.nl"],
            robots_txt_url="https://www.tenderned.nl/robots.txt",
            robots_notes=(
                "robots.txt에서 공개 영역은 허용하면서도 사용자 대시보드 등 민감 경로에 Disallow가 설정되어 있는 것으로 알려짐."
            ),
            crawling_constraints=(
                "공고 검색은 무료로 가능하지만 첨부 문서 다운로드나 질의응답 기능은 계정이 필요할 수 있음. 사이트가 React 기반 SPA 구조이므로 동적 로딩을 처리할 수 있는 크롤러 구성이 필요함."
            ),
            legal_notes=(
                "네덜란드 정부 공공데이터는 재사용이 가능하지만, Gebruiksvoorwaarden에 명시된 조건(출처 표시, 비침해 목적 등)을 준수해야 하며 첨부 문서의 설계도·이미지는 별도 저작권 보호 대상일 수 있음."
            ),
        ),
    ]
}


def list_site_compliance() -> List[SiteComplianceDetails]:
    """Return all stored site compliance entries sorted by country name."""

    return sorted(_SITE_COMPLIANCE_ENTRIES.values(), key=lambda entry: entry.country.lower())


def get_site_compliance(slug: str) -> Optional[SiteComplianceDetails]:
    """Return a single site compliance entry by its slug."""

    return _SITE_COMPLIANCE_ENTRIES.get(slug)
