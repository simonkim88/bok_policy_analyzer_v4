"""ECOS 지표 일괄 다운로드 스크립트."""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import yaml

from src.data.ecos_api import EcosAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).parent / "ecos_indicators.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "08_ecos"
DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUT_DIR / "download_manifest.json"


class ECOSBulkDownloader:
    """YAML 설정 기반 ECOS 벌크 다운로더."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        request_delay: float = 1.0,
    ):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.manifest_path = manifest_path or DEFAULT_MANIFEST_PATH
        self.request_delay = request_delay

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

        api_key = os.environ.get("ECOS_API_KEY", "LZUNMUPZQ4FFUITEF1R7")
        self.ecos = EcosAPI(api_key=api_key)
        self.indicators = self._load_config()
        self.manifest = self._load_manifest()

    def _load_config(self) -> Dict[str, dict]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"YAML 설정 파일이 없습니다: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        indicators = config.get("indicators", {})
        if not indicators:
            raise ValueError(f"indicators 설정이 비어 있습니다: {self.config_path}")

        return indicators

    def _load_manifest(self) -> Dict[str, dict]:
        if not self.manifest_path.exists():
            return {"downloads": {}}

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"manifest 로딩 실패, 새로 생성합니다: {exc}")
            return {"downloads": {}}

    def _save_manifest(self) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize_range(period_type: str, start_date: str, end_date: Optional[str]) -> Tuple[str, str]:
        now = datetime.now()
        period = period_type.upper()

        if end_date is None:
            if period == "D":
                end_date = now.strftime("%Y%m%d")
            elif period == "M":
                end_date = now.strftime("%Y%m")
            elif period == "Q":
                end_date = f"{now.year}Q{((now.month - 1) // 3) + 1}"
            elif period == "A":
                end_date = now.strftime("%Y")
            else:
                end_date = now.strftime("%Y%m")

        if period == "D":
            start = start_date.replace("-", "")
            if len(start) == 6:
                start = f"{start}01"
            end = end_date.replace("-", "")
            if len(end) == 6:
                end = f"{end}01"
            return start, end

        if period == "M":
            return start_date.replace("-", "")[:6], end_date.replace("-", "")[:6]

        if period == "Q":
            start = start_date
            if "Q" not in start:
                start_raw = start.replace("-", "")[:6]
                month = int(start_raw[4:6]) if len(start_raw) >= 6 else 1
                start = f"{start_raw[:4]}Q{((month - 1) // 3) + 1}"

            end = end_date
            if "Q" not in end:
                end_raw = end.replace("-", "")[:6]
                month = int(end_raw[4:6]) if len(end_raw) >= 6 else now.month
                end = f"{end_raw[:4]}Q{((month - 1) // 3) + 1}"
            return start, end

        if period == "A":
            return start_date[:4], end_date[:4]

        return start_date.replace("-", ""), end_date.replace("-", "")

    @staticmethod
    def _is_recent(csv_path: Path, hours: int = 24) -> bool:
        if not csv_path.exists():
            return False
        modified = datetime.fromtimestamp(csv_path.stat().st_mtime)
        return datetime.now() - modified < timedelta(hours=hours)

    def _update_manifest(self, indicator_name: str, payload: dict) -> None:
        self.manifest.setdefault("downloads", {})[indicator_name] = payload
        self.manifest["updated_at"] = datetime.now().isoformat()
        self._save_manifest()

    def download_indicator(self, indicator_name: str, config: dict, start_date: str, end_date: Optional[str]) -> dict:
        category = config["category"]
        category_dir = self.output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        csv_path = category_dir / f"{indicator_name}.csv"
        if self._is_recent(csv_path):
            logger.info(f"[SKIP] 최신 파일 존재: {csv_path}")
            result = {"status": "skipped_recent", "path": str(csv_path), "rows": None}
            self._update_manifest(indicator_name, {**result, "timestamp": datetime.now().isoformat()})
            return result

        normalized_start, normalized_end = self._normalize_range(
            period_type=config["period_type"],
            start_date=start_date,
            end_date=end_date,
        )

        try:
            df = self.ecos.fetch_data(
                stat_code=config["stat_code"],
                period_type=config["period_type"],
                start_date=normalized_start,
                end_date=normalized_end,
                item_code1=config["item_code1"],
            )
        except Exception as exc:
            logger.error(f"[FAIL] {indicator_name} API 호출 실패: {exc}")
            result = {"status": "failed", "path": str(csv_path), "rows": None, "error": str(exc)}
            self._update_manifest(indicator_name, {**result, "timestamp": datetime.now().isoformat()})
            return result

        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            logger.warning(f"[FAIL] {indicator_name}: 수신 데이터 없음")
            result = {"status": "failed", "path": str(csv_path), "rows": 0, "error": "No data"}
            self._update_manifest(indicator_name, {**result, "timestamp": datetime.now().isoformat()})
            return result

        try:
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            rows = int(len(df))
            logger.info(f"[OK] {indicator_name}: {rows}건 저장 -> {csv_path}")
            result = {"status": "downloaded", "path": str(csv_path), "rows": rows}
            self._update_manifest(
                indicator_name,
                {
                    **result,
                    "timestamp": datetime.now().isoformat(),
                    "start_date": normalized_start,
                    "end_date": normalized_end,
                    "stat_code": config["stat_code"],
                    "item_code1": config["item_code1"],
                    "period_type": config["period_type"],
                    "category": category,
                },
            )
            return result
        except Exception as exc:
            logger.error(f"[FAIL] {indicator_name} CSV 저장 실패: {exc}")
            result = {"status": "failed", "path": str(csv_path), "rows": None, "error": str(exc)}
            self._update_manifest(indicator_name, {**result, "timestamp": datetime.now().isoformat()})
            return result

    def download_all(self, start_date: str = "2015-01", end_date: Optional[str] = None) -> dict:
        stats = {"total": len(self.indicators), "downloaded": 0, "skipped_recent": 0, "failed": 0}

        for idx, (indicator_name, config) in enumerate(self.indicators.items(), start=1):
            logger.info(f"[{idx}/{len(self.indicators)}] 처리 중: {indicator_name}")
            result = self.download_indicator(indicator_name, config, start_date=start_date, end_date=end_date)
            stats[result["status"]] += 1

            if idx < len(self.indicators) and result["status"] != "skipped_recent":
                time.sleep(self.request_delay)

        return stats


def main() -> None:
    downloader = ECOSBulkDownloader()
    stats = downloader.download_all(start_date="2015-01")

    print("=" * 60)
    print("ECOS Bulk Download Complete")
    print("=" * 60)
    print(f"Total indicators: {stats['total']}")
    print(f"Downloaded: {stats['downloaded']}")
    print(f"Skipped (recent): {stats['skipped_recent']}")
    print(f"Failed: {stats['failed']}")
    print(f"Output dir: {downloader.output_dir}")
    print(f"Manifest: {downloader.manifest_path}")


if __name__ == "__main__":
    main()
