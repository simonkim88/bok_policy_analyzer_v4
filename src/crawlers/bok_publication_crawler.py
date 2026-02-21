"""
Unified Bank of Korea publication crawler.

This crawler reads publication definitions from bok_publications.yaml,
collects article lists from the BOK AJAX endpoint, finds PDF links on detail pages,
downloads PDFs, and extracts text with pdfplumber through PDFDownloader.
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

from src.crawlers.pdf_downloader import PDFDownloader


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ArticleItem:
    title: str
    date: str
    url: str
    ntt_id: str
    department: str = ""


class BOKPublicationCrawler:
    BASE_URL = "https://www.bok.or.kr"
    LIST_CONT_URL = "https://www.bok.or.kr/portal/singl/newsData/listCont.do"

    def __init__(self, config_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent.parent
        default_config = Path(__file__).with_name("bok_publications.yaml")
        self.config_path = Path(config_path) if config_path else default_config

        self.config = self._load_config(self.config_path)
        self.publications = self.config.get("publications", {})

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.bok.or.kr/",
            }
        )
        self.pdf_downloader = PDFDownloader()

    @staticmethod
    def _load_config(config_path: Path) -> Dict:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    @staticmethod
    def _sanitize_filename(name: str, max_length: int = 120) -> str:
        cleaned = re.sub(r"[\\/:*?\"<>|]", "_", name)
        cleaned = re.sub(r"\s+", "_", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned).strip("_.")
        cleaned = re.sub(r"[^0-9a-zA-Z_\-]", "", cleaned)
        return cleaned[:max_length] if cleaned else "untitled"

    @staticmethod
    def _extract_date_parts(text: str) -> Dict[str, str]:
        date_patterns = [
            r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",
            r"(\d{4})[.\-/](\d{1,2})",
            r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일",
            r"(\d{4})\s*년\s*(\d{1,2})\s*월",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            groups = match.groups()
            year = groups[0]
            month = groups[1].zfill(2)
            day = groups[2].zfill(2) if len(groups) > 2 and groups[2] else ""
            return {"year": year, "month": month, "day": day}
        return {"year": "unknown", "month": "00", "day": ""}

    def _make_full_url(self, href: str) -> str:
        if not href:
            return ""
        return urljoin(self.BASE_URL, href)

    @staticmethod
    def _extract_ntt_id_from_url(url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        ntt_id_values = query.get("nttId", [])
        return ntt_id_values[0] if ntt_id_values else ""

    def fetch_article_list(self, menu_no: str, page_index: int = 1, page_unit: int = 10) -> str:
        params = {"menuNo": menu_no, "pageIndex": page_index, "pageUnit": page_unit}
        try:
            logger.info("Request list menuNo=%s page=%s", menu_no, page_index)
            response = self.session.get(self.LIST_CONT_URL, params=params, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as exc:
            logger.error("List fetch failed menuNo=%s page=%s: %s", menu_no, page_index, exc)
            return ""

    def parse_article_list(self, html: str) -> List[ArticleItem]:
        if not html.strip():
            return []

        soup = BeautifulSoup(html, "html.parser")
        items: List[ArticleItem] = []
        seen_urls: Set[str] = set()

        links = soup.select('a[href*="view.do"], a[href*="nttId"]')
        for link in links:
            href = link.get("href", "").strip()
            if not href:
                continue

            full_url = self._make_full_url(href)
            ntt_id = self._extract_ntt_id_from_url(full_url)
            if not ntt_id or full_url in seen_urls:
                continue

            title = link.get_text(" ", strip=True)
            if not title:
                continue

            parent = link.find_parent(["li", "tr", "div", "td", "article"])
            context_text = parent.get_text(" ", strip=True) if parent else ""
            date_match = re.search(r"\d{4}[.\-/]\d{1,2}([.\-/]\d{1,2})?", context_text)
            date_text = date_match.group() if date_match else ""

            dept_text = ""
            if parent:
                dept_node = parent.select_one(
                    ".department, .dept, .author, .writer, .name, .from, .subject, .info"
                )
                if dept_node:
                    dept_text = dept_node.get_text(" ", strip=True)

            items.append(
                ArticleItem(
                    title=title,
                    date=date_text,
                    url=full_url,
                    ntt_id=ntt_id,
                    department=dept_text,
                )
            )
            seen_urls.add(full_url)

        return items

    def _extract_pdf_urls_from_node(self, node) -> List[str]:
        urls: List[str] = []
        href = (node.get("href") or "").strip()
        onclick = (node.get("onclick") or "").strip()

        if href:
            if "pdfjs/viewer.html" in href and "file=" in href:
                file_param = parse_qs(urlparse(href).query).get("file", [""])[0]
                decoded_file = unquote(file_param)
                if decoded_file:
                    urls.append(self._make_full_url(decoded_file))
            elif "fileDown.do" in href:
                urls.append(self._make_full_url(href))
            elif "/fileSrc/" in href and ".pdf" in href.lower():
                urls.append(self._make_full_url(href))
            elif href.lower().endswith(".pdf"):
                urls.append(self._make_full_url(href))

            js_match = re.search(r"fn_fileDownLoad\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", href)
            if js_match:
                atch_file_id, file_sn = js_match.groups()
                generated = f"/portal/singl/newsData/fileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                urls.append(self._make_full_url(generated))

        if onclick:
            js_match = re.search(r"fn_fileDownLoad\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", onclick)
            if js_match:
                atch_file_id, file_sn = js_match.groups()
                generated = f"/portal/singl/newsData/fileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}"
                urls.append(self._make_full_url(generated))

        return urls

    def fetch_article_detail(self, url: str) -> List[str]:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
        except requests.RequestException as exc:
            logger.error("Detail fetch failed %s: %s", url, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        pdf_candidates: List[str] = []

        anchors = soup.select("a[href], a[onclick]")
        for anchor in anchors:
            pdf_candidates.extend(self._extract_pdf_urls_from_node(anchor))

        unique_urls: List[str] = []
        seen: Set[str] = set()
        for candidate in pdf_candidates:
            if not candidate:
                continue
            normalized = candidate.replace("&amp;", "&")
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_urls.append(normalized)

        return unique_urls

    def _build_output_dirs(self, pub_config: Dict) -> Dict[str, Path]:
        output_dir = str(pub_config.get("output_dir", "")).strip("/")
        sub_dir = str(pub_config.get("sub_dir", "")).strip("/")

        base = self.project_root / "data" / output_dir
        if sub_dir:
            base = base / sub_dir
        pdf_dir = base / "pdf"
        txt_dir = base / "txt"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        txt_dir.mkdir(parents=True, exist_ok=True)
        return {"base": base, "pdf": pdf_dir, "txt": txt_dir}

    def _build_filename(self, pub_key: str, article: ArticleItem, suffix: str = "") -> str:
        date_parts = self._extract_date_parts(article.date or article.title)
        year = date_parts["year"]
        month = date_parts["month"]
        day = date_parts["day"]

        if day:
            base = f"{pub_key}_{year}_{month}_{day}"
        else:
            base = f"{pub_key}_{year}_{month}"

        if suffix:
            base = f"{base}_{suffix}"

        return self._sanitize_filename(base)

    def _find_available_filename(self, base_name: str, pdf_dir: Path) -> str:
        candidate = base_name
        index = 2
        while (pdf_dir / f"{candidate}.pdf").exists() and (pdf_dir / f"{candidate}.pdf").stat().st_size > 0:
            candidate = f"{base_name}_{index}"
            index += 1
        return candidate

    def crawl_publication(
        self,
        pub_key: str,
        pub_config: Dict,
        max_pages: int = 5,
        delay: float = 1.0,
    ) -> Dict:
        menu_no = str(pub_config.get("menu_no", "")).strip()
        publication_name = pub_config.get("name", pub_key)
        dirs = self._build_output_dirs(pub_config)

        stats = {
            "publication": publication_name,
            "menu_no": menu_no,
            "pages_crawled": 0,
            "articles_found": 0,
            "articles_processed": 0,
            "pdf_links_found": 0,
            "downloaded": 0,
            "text_extracted": 0,
            "skipped_existing": 0,
            "failed": 0,
        }

        if not menu_no:
            logger.warning("Skip %s: menu_no is empty", pub_key)
            return stats

        logger.info("Start publication=%s (%s)", pub_key, publication_name)
        processed_ntt_ids: Set[str] = set()

        for page_index in range(1, max_pages + 1):
            html = self.fetch_article_list(menu_no=menu_no, page_index=page_index, page_unit=10)
            if not html:
                time.sleep(delay)
                continue

            articles = self.parse_article_list(html)
            if not articles:
                logger.info("No articles for %s at page=%s, stop pagination", pub_key, page_index)
                break

            stats["pages_crawled"] += 1
            stats["articles_found"] += len(articles)
            logger.info("%s page=%s article_count=%s", pub_key, page_index, len(articles))

            for article in articles:
                if article.ntt_id in processed_ntt_ids:
                    continue
                processed_ntt_ids.add(article.ntt_id)
                stats["articles_processed"] += 1

                pdf_urls = self.fetch_article_detail(article.url)
                stats["pdf_links_found"] += len(pdf_urls)
                if not pdf_urls:
                    logger.info("No PDF links: %s (%s)", article.title, article.url)
                    time.sleep(delay)
                    continue

                for idx, pdf_url in enumerate(pdf_urls, 1):
                    base_name = self._build_filename(pub_key, article)
                    if len(pdf_urls) > 1:
                        base_name = f"{base_name}_{idx}"
                    filename = self._find_available_filename(base_name, dirs["pdf"])

                    existing_pdf = dirs["pdf"] / f"{filename}.pdf"
                    if existing_pdf.exists() and existing_pdf.stat().st_size > 0:
                        stats["skipped_existing"] += 1
                        pdf_path = existing_pdf
                    else:
                        result = self.pdf_downloader.download_pdf(pdf_url, filename, output_dir=dirs["pdf"])
                        if not result.success or not result.file_path:
                            stats["failed"] += 1
                            continue
                        stats["downloaded"] += 1
                        pdf_path = result.file_path

                    txt_path = self.pdf_downloader.extract_text_to_dir(pdf_path, dirs["txt"], filename)
                    if txt_path:
                        stats["text_extracted"] += 1

                    time.sleep(delay)

                time.sleep(delay)

            time.sleep(delay)

        logger.info(
            "Done %s: pages=%s articles=%s pdf_links=%s downloaded=%s extracted=%s skipped=%s failed=%s",
            pub_key,
            stats["pages_crawled"],
            stats["articles_found"],
            stats["pdf_links_found"],
            stats["downloaded"],
            stats["text_extracted"],
            stats["skipped_existing"],
            stats["failed"],
        )
        return stats

    def crawl_all(
        self,
        max_pages_per_pub: int = 5,
        delay: float = 1.0,
        publication_keys: Optional[List[str]] = None,
    ) -> Dict:
        all_stats: Dict[str, Dict] = {}
        totals = {
            "publications": 0,
            "pages_crawled": 0,
            "articles_found": 0,
            "articles_processed": 0,
            "pdf_links_found": 0,
            "downloaded": 0,
            "text_extracted": 0,
            "skipped_existing": 0,
            "failed": 0,
        }

        keys = publication_keys or list(self.publications.keys())
        for pub_key in keys:
            pub_config = self.publications.get(pub_key)
            if not pub_config:
                logger.warning("Unknown publication key: %s", pub_key)
                continue

            stats = self.crawl_publication(
                pub_key=pub_key,
                pub_config=pub_config,
                max_pages=max_pages_per_pub,
                delay=delay,
            )
            all_stats[pub_key] = stats
            totals["publications"] += 1
            for metric in [
                "pages_crawled",
                "articles_found",
                "articles_processed",
                "pdf_links_found",
                "downloaded",
                "text_extracted",
                "skipped_existing",
                "failed",
            ]:
                totals[metric] += stats.get(metric, 0)

        return {"totals": totals, "publications": all_stats}


def _log_summary_table(result: Dict) -> None:
    headers = [
        "publication",
        "pages",
        "articles",
        "processed",
        "pdf_links",
        "downloaded",
        "extracted",
        "skipped",
        "failed",
    ]
    logger.info("\n%s", "-" * 120)
    logger.info("%-26s %6s %8s %10s %9s %10s %10s %8s %8s", *headers)
    logger.info("%s", "-" * 120)

    for pub_key, stats in result.get("publications", {}).items():
        logger.info(
            "%-26s %6d %8d %10d %9d %10d %10d %8d %8d",
            pub_key,
            stats.get("pages_crawled", 0),
            stats.get("articles_found", 0),
            stats.get("articles_processed", 0),
            stats.get("pdf_links_found", 0),
            stats.get("downloaded", 0),
            stats.get("text_extracted", 0),
            stats.get("skipped_existing", 0),
            stats.get("failed", 0),
        )

    logger.info("%s", "-" * 120)
    totals = result.get("totals", {})
    logger.info(
        "%-26s %6d %8d %10d %9d %10d %10d %8d %8d",
        "TOTAL",
        totals.get("pages_crawled", 0),
        totals.get("articles_found", 0),
        totals.get("articles_processed", 0),
        totals.get("pdf_links_found", 0),
        totals.get("downloaded", 0),
        totals.get("text_extracted", 0),
        totals.get("skipped_existing", 0),
        totals.get("failed", 0),
    )
    logger.info("%s", "-" * 120)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified BOK publication crawler")
    parser.add_argument("--publications", nargs="*", help="Specific publication keys to crawl")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--config-path", type=str, default=None)
    args = parser.parse_args()

    crawler = BOKPublicationCrawler(config_path=Path(args.config_path) if args.config_path else None)
    results = crawler.crawl_all(
        max_pages_per_pub=args.max_pages,
        delay=args.delay,
        publication_keys=args.publications,
    )
    _log_summary_table(results)


if __name__ == "__main__":
    main()
