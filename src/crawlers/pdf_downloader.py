"""
한국은행 금융통화위원회 문서 PDF 다운로드 및 텍스트 추출

수집된 회의 목록(JSON)에서 PDF 파일을 다운로드하고,
pdfplumber를 사용하여 텍스트를 추출합니다.
"""

import json
import logging
import re
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import pdfplumber
import requests

try:
    import olefile
except ImportError:
    olefile = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

# 기존 경로 (하위 호환)
PDF_DIR = DATA_DIR / "pdfs"
TEXT_DIR = DATA_DIR / "texts"

# 신규 문서 타입별 경로
DECISION_PDF_DIR = DATA_DIR / "02_decision_statements" / "pdf"
DECISION_TEXT_DIR = DATA_DIR / "02_decision_statements" / "txt"
PRESS_PDF_DIR = DATA_DIR / "03_press_conferences" / "opening_remarks"
PRESS_TEXT_DIR = DATA_DIR / "03_press_conferences" / "opening_remarks" / "txt"
ISSUE_PDF_DIR = DATA_DIR / "05_policy_reports" / "pdf"
ISSUE_TEXT_DIR = DATA_DIR / "05_policy_reports" / "txt"


@dataclass
class DownloadResult:
    """다운로드 결과"""

    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None


class PDFDownloader:
    """PDF 다운로드 및 텍스트 추출기"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/pdf,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": "https://www.bok.or.kr/",
            }
        )
        self._ensure_output_dirs()

    def _ensure_output_dirs(self) -> None:
        """필요한 출력 디렉토리를 생성합니다."""
        for directory in [
            PDF_DIR,
            TEXT_DIR,
            DECISION_PDF_DIR,
            DECISION_TEXT_DIR,
            PRESS_PDF_DIR,
            PRESS_TEXT_DIR,
            ISSUE_PDF_DIR,
            ISSUE_TEXT_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_date_parts(meeting_date: str) -> Tuple[str, str, str]:
        """meeting_date(YYYY.MM.DD)에서 연/월/일을 추출합니다."""
        try:
            year, month, day = meeting_date.split(".")
            return year, month, day
        except (AttributeError, ValueError):
            return "unknown", "00", "00"

    def download_pdf(self, url: str, filename: str, output_dir: Optional[Path] = None) -> DownloadResult:
        """PDF 파일을 다운로드합니다."""
        if not url:
            return DownloadResult(success=False, error="URL이 비어있습니다")

        target_dir = output_dir or PDF_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{filename}.pdf"

        if file_path.exists() and file_path.stat().st_size > 0:
            logger.info(f"이미 존재: {file_path}")
            return DownloadResult(success=True, file_path=file_path)

        try:
            logger.info(f"다운로드 중: {file_path}")
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                logger.warning(f"예상치 못한 Content-Type: {content_type}")

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if file_path.stat().st_size < 1000:
                if file_path.exists():
                    file_path.unlink()
                return DownloadResult(success=False, error="파일이 너무 작음 (손상된 파일)")

            logger.info(f"다운로드 완료: {file_path} ({file_path.stat().st_size:,} bytes)")
            return DownloadResult(success=True, file_path=file_path)

        except requests.RequestException as e:
            logger.error(f"다운로드 실패 ({filename}): {e}")
            return DownloadResult(success=False, error=str(e))

    @staticmethod
    def _is_hwp_compound(path: Path) -> bool:
        try:
            return path.read_bytes()[:8] == bytes.fromhex("D0CF11E0A1B11AE1")
        except OSError:
            return False

    @staticmethod
    def _decode_hwp_section(section_data: bytes) -> str:
        payload = section_data
        try:
            payload = zlib.decompress(section_data, -15)
        except zlib.error:
            payload = section_data

        texts = []
        pos = 0
        size = len(payload)

        while pos + 4 <= size:
            header = int.from_bytes(payload[pos : pos + 4], "little")
            tag_id = header & 0x3FF
            rec_size = (header >> 20) & 0xFFF
            pos += 4

            if rec_size == 0xFFF:
                if pos + 4 > size:
                    break
                rec_size = int.from_bytes(payload[pos : pos + 4], "little")
                pos += 4

            if pos + rec_size > size:
                break

            record_data = payload[pos : pos + rec_size]
            pos += rec_size

            if tag_id != 67 or not record_data:
                continue

            text = record_data.decode("utf-16le", errors="ignore")
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()
            if cleaned:
                texts.append(cleaned)

        return "\n".join(texts)

    def _extract_hwp_text(self, file_path: Path) -> Optional[str]:
        if olefile is None:
            logger.warning("olefile 미설치로 HWP 추출을 건너뜁니다")
            return None

        if not self._is_hwp_compound(file_path):
            return None

        try:
            with olefile.OleFileIO(str(file_path)) as ole:
                section_streams = [
                    "/".join(entry)
                    for entry in ole.listdir(streams=True, storages=False)
                    if len(entry) == 2 and entry[0] == "BodyText" and entry[1].startswith("Section")
                ]

                section_streams.sort(key=lambda name: int(name.split("Section")[-1]))

                extracted_parts = []
                for stream_name in section_streams:
                    section_data = ole.openstream(stream_name).read()
                    section_text = self._decode_hwp_section(section_data)
                    if section_text:
                        extracted_parts.append(section_text)

                if not extracted_parts:
                    return None

                return "\n\n".join(extracted_parts)

        except Exception as exc:
            logger.error(f"HWP 텍스트 추출 실패 ({file_path.name}): {exc}")
            return None

    def extract_text_to_dir(self, pdf_path: Path, output_dir: Path, output_filename: str) -> Optional[Path]:
        """PDF 텍스트를 지정 디렉토리로 추출합니다."""
        if not pdf_path or not pdf_path.exists():
            logger.error(f"PDF 파일이 존재하지 않음: {pdf_path}")
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        text_path = output_dir / f"{output_filename}.txt"

        if text_path.exists() and text_path.stat().st_size > 0:
            logger.info(f"이미 추출됨: {text_path}")
            return text_path

        try:
            logger.info(f"텍스트 추출 중: {pdf_path.name}")
            all_text = []

            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        all_text.append(f"--- 페이지 {i} ---\n{text}")

            if not all_text:
                logger.warning(f"텍스트를 추출할 수 없음: {pdf_path.name}")
                return None

            full_text = "\n\n".join(all_text)
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            logger.info(f"텍스트 추출 완료: {text_path} ({len(full_text):,} chars)")
            return text_path

        except Exception as e:
            if "No /Root object" not in str(e):
                logger.error(f"텍스트 추출 실패 ({pdf_path.name}): {e}")
                return None

            logger.warning(f"PDF 파싱 실패, HWP fallback 시도: {pdf_path.name}")
            hwp_text = self._extract_hwp_text(pdf_path)
            if not hwp_text:
                logger.error(f"HWP fallback 추출 실패 ({pdf_path.name})")
                return None

            with open(text_path, "w", encoding="utf-8") as f:
                f.write(hwp_text)

            logger.info(f"HWP fallback 텍스트 추출 완료: {text_path} ({len(hwp_text):,} chars)")
            return text_path

    def extract_text(self, pdf_path: Path, output_filename: str) -> Optional[Path]:
        """기존 하위 호환용 텍스트 추출 메서드입니다."""
        return self.extract_text_to_dir(pdf_path, TEXT_DIR, output_filename)

    def process_minutes_file(self, json_path: Path, delay: float = 1.0) -> dict:
        """기존 의사록 JSON 처리 로직(하위 호환)."""
        with open(json_path, "r", encoding="utf-8") as f:
            minutes_list = json.load(f)

        stats = {"total": len(minutes_list), "downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0}

        for item in minutes_list:
            meeting_date = item.get("meeting_date", "unknown")
            year, month, day = self._extract_date_parts(meeting_date)
            filename = f"minutes_{year}_{month}_{day}"

            pdf_url = item.get("minutes_pdf_url")
            if not pdf_url:
                logger.info(f"PDF URL 없음: {meeting_date}")
                stats["skipped"] += 1
                continue

            result = self.download_pdf(pdf_url, filename, output_dir=PDF_DIR)
            if result.success:
                stats["downloaded"] += 1
                text_path = self.extract_text_to_dir(result.file_path, TEXT_DIR, filename)
                if text_path:
                    stats["extracted"] += 1
            else:
                stats["failed"] += 1

            time.sleep(delay)

        return stats

    def process_all_document_types(self, json_path: Path, delay: float = 1.0) -> dict:
        """단일 연도 JSON에서 모든 문서 타입을 다운로드/추출합니다."""
        with open(json_path, "r", encoding="utf-8") as f:
            minutes_list = json.load(f)

        stats = {
            "meetings": len(minutes_list),
            "minutes": {"downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0},
            "decision": {"downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0},
            "press": {"downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0},
            "issue": {"downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0},
        }

        for item in minutes_list:
            meeting_date = item.get("meeting_date", "unknown")
            year, month, day = self._extract_date_parts(meeting_date)

            document_jobs = [
                {
                    "key": "minutes",
                    "url": item.get("minutes_pdf_url"),
                    "filename": f"minutes_{year}_{month}_{day}",
                    "pdf_dir": PDF_DIR,
                    "txt_dir": TEXT_DIR,
                },
                {
                    "key": "decision",
                    "url": item.get("decision_url"),
                    "filename": f"decision_{year}_{month}",
                    "pdf_dir": DECISION_PDF_DIR,
                    "txt_dir": DECISION_TEXT_DIR,
                },
                {
                    "key": "press",
                    "url": item.get("press_url"),
                    "filename": f"opening_remarks_{year}_{month}",
                    "pdf_dir": PRESS_PDF_DIR,
                    "txt_dir": PRESS_TEXT_DIR,
                },
                {
                    "key": "issue",
                    "url": item.get("issue_url"),
                    "filename": f"issue_{year}_{month}",
                    "pdf_dir": ISSUE_PDF_DIR,
                    "txt_dir": ISSUE_TEXT_DIR,
                },
            ]

            for job in document_jobs:
                if not job["url"]:
                    stats[job["key"]]["skipped"] += 1
                    continue

                result = self.download_pdf(job["url"], job["filename"], output_dir=job["pdf_dir"])
                if result.success:
                    stats[job["key"]]["downloaded"] += 1
                    text_path = self.extract_text_to_dir(result.file_path, job["txt_dir"], job["filename"])
                    if text_path:
                        stats[job["key"]]["extracted"] += 1
                else:
                    stats[job["key"]]["failed"] += 1

                time.sleep(delay)

        return stats

    @staticmethod
    def _flatten_stats(document_stats: dict) -> dict:
        """문서 타입별 통계를 기존 포맷(total/downloaded/...)으로 변환합니다."""
        total_meetings = document_stats.get("meetings", 0)
        downloaded = 0
        extracted = 0
        skipped = 0
        failed = 0

        for doc_key in ["minutes", "decision", "press", "issue"]:
            if doc_key not in document_stats:
                continue
            downloaded += document_stats[doc_key].get("downloaded", 0)
            extracted += document_stats[doc_key].get("extracted", 0)
            skipped += document_stats[doc_key].get("skipped", 0)
            failed += document_stats[doc_key].get("failed", 0)

        return {
            "total": total_meetings,
            "downloaded": downloaded,
            "extracted": extracted,
            "skipped": skipped,
            "failed": failed,
        }

    def process_all_years(self, years: list = None, delay: float = 1.0, all_document_types: bool = False) -> dict:
        """여러 연도의 문서를 처리합니다."""
        if years is None:
            years = []
            for f in RAW_DIR.glob("minutes_*.json"):
                try:
                    years.append(int(f.stem.split("_")[1]))
                except (IndexError, ValueError):
                    continue
            years.sort()

        total_stats = {"total": 0, "downloaded": 0, "extracted": 0, "skipped": 0, "failed": 0}

        for year in years:
            json_path = RAW_DIR / f"minutes_{year}.json"
            if not json_path.exists():
                logger.warning(f"파일 없음: {json_path}")
                continue

            logger.info(f"\n{'=' * 50}")
            logger.info(f"{year}년 문서 처리 시작")
            logger.info("=" * 50)

            if all_document_types:
                yearly_doc_stats = self.process_all_document_types(json_path, delay=delay)
                yearly_stats = self._flatten_stats(yearly_doc_stats)
            else:
                yearly_stats = self.process_minutes_file(json_path, delay=delay)

            for key in total_stats:
                total_stats[key] += yearly_stats[key]

            logger.info(
                f"{year}년 완료: 다운로드 {yearly_stats['downloaded']}, "
                f"추출 {yearly_stats['extracted']}, 스킵 {yearly_stats['skipped']}, 실패 {yearly_stats['failed']}"
            )

        return total_stats


def main():
    """메인 실행 함수"""
    downloader = PDFDownloader()

    print("=" * 70)
    print("한국은행 금융통화위원회 문서 PDF 다운로드 및 텍스트 추출")
    print("(의사록 + 결정문 + 기자간담회 모두발언 + 정책 관련 보고서)")
    print("=" * 70)

    stats = downloader.process_all_years(delay=0.5, all_document_types=True)

    print("\n" + "=" * 70)
    print("처리 완료")
    print("=" * 70)
    print(f"총 회의: {stats['total']}개")
    print(f"다운로드: {stats['downloaded']}개")
    print(f"텍스트 추출: {stats['extracted']}개")
    print(f"스킵 (URL 없음): {stats['skipped']}개")
    print(f"실패: {stats['failed']}개")
    print(f"\n의사록 PDF 위치: {PDF_DIR}")
    print(f"의사록 텍스트 위치: {TEXT_DIR}")
    print(f"결정문 PDF 위치: {DECISION_PDF_DIR}")
    print(f"결정문 텍스트 위치: {DECISION_TEXT_DIR}")
    print(f"모두발언 PDF 위치: {PRESS_PDF_DIR}")
    print(f"모두발언 텍스트 위치: {PRESS_TEXT_DIR}")
    print(f"이슈리포트 PDF 위치: {ISSUE_PDF_DIR}")
    print(f"이슈리포트 텍스트 위치: {ISSUE_TEXT_DIR}")


if __name__ == "__main__":
    main()
