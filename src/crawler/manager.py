"""
Crawler Manager
크롤러 관리 및 스케줄링
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.crawler.g2b_crawler import G2BCrawler
from src.crawler.samgov_crawler import SAMGovCrawler
from src.config import settings, crawler_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrawlerManager:
    """크롤러 관리자"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.crawlers = {
            "G2B": G2BCrawler(),
            "SAM.gov": SAMGovCrawler()
        }
        self.is_running = False
        self.last_run_results = {}

    async def start_scheduler(self):
        """스케줄러 시작"""
        try:
            if not self.is_running:
                # 기본 스케줄 설정
                await self._setup_default_schedules()

                self.scheduler.start()
                self.is_running = True
                logger.info("크롤러 스케줄러 시작됨")

        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {e}")

    async def stop_scheduler(self):
        """스케줄러 중지"""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("크롤러 스케줄러 중지됨")

        except Exception as e:
            logger.error(f"스케줄러 중지 실패: {e}")

    async def _setup_default_schedules(self):
        """기본 스케줄 설정"""
        # G2B - 매일 오전 9시, 오후 6시
        self.scheduler.add_job(
            self._run_g2b_crawler,
            CronTrigger(hour=9, minute=0),
            id="g2b_morning",
            name="G2B Morning Crawl"
        )

        self.scheduler.add_job(
            self._run_g2b_crawler,
            CronTrigger(hour=18, minute=0),
            id="g2b_evening",
            name="G2B Evening Crawl"
        )

        # SAM.gov - 매일 오전 10시, 오후 7시 (시차 고려)
        self.scheduler.add_job(
            self._run_samgov_crawler,
            CronTrigger(hour=10, minute=0),
            id="samgov_morning",
            name="SAM.gov Morning Crawl"
        )

        self.scheduler.add_job(
            self._run_samgov_crawler,
            CronTrigger(hour=19, minute=0),
            id="samgov_evening",
            name="SAM.gov Evening Crawl"
        )

        logger.info("기본 크롤링 스케줄 설정 완료")

    async def _run_g2b_crawler(self):
        """G2B 크롤러 실행"""
        try:
            logger.info("예약된 G2B 크롤링 시작")
            result = await self.run_crawler("G2B")
            self.last_run_results["G2B"] = {
                **result,
                "scheduled_run": True,
                "run_time": datetime.now().isoformat()
            }
            logger.info(f"G2B 크롤링 완료: {result}")

        except Exception as e:
            logger.error(f"예약된 G2B 크롤링 실패: {e}")

    async def _run_samgov_crawler(self):
        """SAM.gov 크롤러 실행"""
        try:
            logger.info("예약된 SAM.gov 크롤링 시작")
            result = await self.run_crawler("SAM.gov")
            self.last_run_results["SAM.gov"] = {
                **result,
                "scheduled_run": True,
                "run_time": datetime.now().isoformat()
            }
            logger.info(f"SAM.gov 크롤링 완료: {result}")

        except Exception as e:
            logger.error(f"예약된 SAM.gov 크롤링 실패: {e}")

    async def run_crawler(self, site_name: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """특정 크롤러 실행"""
        if site_name not in self.crawlers:
            return {
                "success": False,
                "error": f"알 수 없는 사이트: {site_name}",
                "site": site_name
            }

        crawler = self.crawlers[site_name]

        try:
            # 기본 키워드 사용
            if not keywords:
                keywords = (
                    crawler_config.SEEGENE_KEYWORDS['korean']
                    if site_name == "G2B"
                    else crawler_config.SEEGENE_KEYWORDS['english']
                )

            # 크롤러 실행
            result = await crawler.run_crawler(keywords)

            # 결과 기록
            self.last_run_results[site_name] = {
                **result,
                "manual_run": True,
                "run_time": datetime.now().isoformat()
            }

            return result

        except Exception as e:
            logger.error(f"{site_name} 크롤러 실행 실패: {e}")
            return {
                "success": False,
                "site": site_name,
                "error": str(e),
                "total_found": 0
            }

    async def run_all_crawlers(self, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """모든 크롤러 실행"""
        results = {}

        for site_name in self.crawlers.keys():
            logger.info(f"{site_name} 크롤러 실행 중...")
            result = await self.run_crawler(site_name, keywords)
            results[site_name] = result

            # 크롤러 간 간격
            await asyncio.sleep(5)

        total_found = sum(r.get('total_found', 0) for r in results.values())
        success_count = sum(1 for r in results.values() if r.get('success', False))

        return {
            "success": success_count > 0,
            "total_crawlers": len(self.crawlers),
            "successful_crawlers": success_count,
            "total_found": total_found,
            "results": results,
            "run_time": datetime.now().isoformat()
        }

    def get_crawler_status(self) -> Dict[str, Any]:
        """크롤러 상태 조회"""
        status = {
            "scheduler_running": self.is_running,
            "crawlers": {}
        }

        for site_name, crawler in self.crawlers.items():
            # 로그인 정보 확인
            has_credentials = False
            if site_name == "G2B":
                has_credentials = bool(settings.G2B_USERNAME and settings.G2B_PASSWORD)
            elif site_name == "SAM.gov":
                has_credentials = bool(settings.SAMGOV_USERNAME and settings.SAMGOV_PASSWORD)

            # 마지막 실행 결과
            last_result = self.last_run_results.get(site_name, {})

            status["crawlers"][site_name] = {
                "has_credentials": has_credentials,
                "can_make_requests": True,  # WebDriver 기반이므로 항상 가능
                "status": "configured" if has_credentials else "partial",
                "last_run": last_result.get("run_time"),
                "last_success": last_result.get("success", False),
                "last_found": last_result.get("total_found", 0)
            }

        return status

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """예약된 작업 목록"""
        jobs = []

        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })

        return jobs

    async def add_custom_schedule(self, site_name: str, cron_expression: str, job_id: str = None) -> bool:
        """사용자 정의 스케줄 추가"""
        try:
            if site_name not in self.crawlers:
                return False

            if not job_id:
                job_id = f"{site_name}_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 크론 표현식 파싱
            parts = cron_expression.split()
            if len(parts) != 5:
                return False

            minute, hour, day, month, day_of_week = parts

            # 실행 함수 선택
            func = self._run_g2b_crawler if site_name == "G2B" else self._run_samgov_crawler

            # 작업 추가
            self.scheduler.add_job(
                func,
                CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id=job_id,
                name=f"{site_name} Custom Schedule"
            )

            logger.info(f"사용자 정의 스케줄 추가: {job_id}")
            return True

        except Exception as e:
            logger.error(f"사용자 정의 스케줄 추가 실패: {e}")
            return False

    def remove_scheduled_job(self, job_id: str) -> bool:
        """예약된 작업 제거"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"예약된 작업 제거: {job_id}")
            return True
        except Exception as e:
            logger.error(f"작업 제거 실패: {e}")
            return False


# 전역 크롤러 매니저 인스턴스
crawler_manager = CrawlerManager()