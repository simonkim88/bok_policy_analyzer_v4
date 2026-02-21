# pyright: basic, reportArgumentType=false, reportCallIssue=false, reportAttributeAccessIssue=false, reportReturnType=false
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import os

import pandas as pd
import requests

from src.config import get_config


class EcosDataLoader:
    """Unified ECOS data loader with local CSV priority."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or get_config()
        self.ecos_config = self.config.get("ecos", {})
        self.indicators = self.ecos_config.get("indicators", {})
        self.base_url = self.ecos_config.get("base_url", "https://ecos.bok.or.kr/api/StatisticSearch")
        api_key_env = self.ecos_config.get("api_key_env", "ECOS_API_KEY")
        self.api_key = os.environ.get(api_key_env, "")
        self.project_root = Path(__file__).resolve().parent.parent.parent

    def get_base_rate(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("base_rate", start_date, end_date)

    def get_cpi(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("cpi", start_date, end_date)

    def get_gdp(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("gdp", start_date, end_date)

    def get_household_credit(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("household_credit", start_date, end_date)

    def get_ktb_3y(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("ktb_3y", start_date, end_date)

    def get_ktb_10y(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("ktb_10y", start_date, end_date)

    def get_usd_krw(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("usd_krw", start_date, end_date)

    def get_kospi(self, start_date=None, end_date=None) -> pd.DataFrame:
        return self._get_indicator("kospi", start_date, end_date)

    def _get_indicator(self, indicator_name: str, start_date=None, end_date=None) -> pd.DataFrame:
        indicator = self.indicators.get(indicator_name, {})
        csv_path = indicator.get("csv_path")
        frequency = indicator.get("frequency", "D")

        csv_df = pd.DataFrame()
        if csv_path:
            csv_df = self._load_from_csv(csv_path, frequency)
            if not csv_df.empty and not self._is_csv_stale(csv_df, frequency, end_date):
                return self._filter_date_range(csv_df, start_date, end_date)

        api_df = self._load_from_api(
            stat_code=indicator.get("stat_code", ""),
            item_code=indicator.get("item_code", "?"),
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )

        if api_df.empty:
            return self._filter_date_range(csv_df, start_date, end_date)

        return self._filter_date_range(api_df, start_date, end_date)

    def _is_csv_stale(self, df: pd.DataFrame, frequency: str, end_date=None) -> bool:
        if df.empty:
            return True

        latest_date = pd.to_datetime(df["Date"]).max().normalize()

        if end_date is not None:
            target = pd.to_datetime(end_date).normalize()
            return latest_date < target

        today = pd.Timestamp.today().normalize()
        threshold_days = {"D": 10, "M": 40, "Q": 130}.get(frequency, 10)
        return (today - latest_date) > pd.Timedelta(days=threshold_days)

    def _load_from_csv(self, csv_path, frequency) -> pd.DataFrame:
        """Parse ECOS CSV format into normalized DataFrame [Date, Value]."""
        path = Path(csv_path)
        if not path.is_absolute():
            path = (self.project_root / path).resolve()

        if not path.exists():
            return pd.DataFrame(columns=["Date", "Value"])

        try:
            df = pd.read_csv(path, usecols=["TIME", "DATA_VALUE"], encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, usecols=["TIME", "DATA_VALUE"], encoding="cp949")
        except Exception:
            return pd.DataFrame(columns=["Date", "Value"])

        if df.empty:
            return pd.DataFrame(columns=["Date", "Value"])

        df["Date"] = df["TIME"].astype(str).apply(lambda x: self._parse_time(x, frequency))
        df["Value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
        df = df.dropna(subset=["Date", "Value"])
        df = df[["Date", "Value"]].sort_values("Date").reset_index(drop=True)

        return df

    def _load_from_api(self, stat_code, item_code, frequency, start_date, end_date) -> pd.DataFrame:
        """Fallback fetch from ECOS API."""
        if not self.api_key or not stat_code:
            return pd.DataFrame(columns=["Date", "Value"])

        api_start = self._to_ecos_date(start_date, frequency, is_start=True)
        api_end = self._to_ecos_date(end_date, frequency, is_start=False)

        url = (
            f"{self.base_url}/{self.api_key}/json/kr/1/10000/"
            f"{stat_code}/{frequency}/{api_start}/{api_end}/{item_code}/?/"
        )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("StatisticSearch", {}).get("row", [])
            if not rows:
                return pd.DataFrame(columns=["Date", "Value"])

            df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]]
            df["Date"] = df["TIME"].astype(str).apply(lambda x: self._parse_time(x, frequency))
            df["Value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
            df = df.dropna(subset=["Date", "Value"])
            return df[["Date", "Value"]].sort_values("Date").reset_index(drop=True)
        except Exception:
            return pd.DataFrame(columns=["Date", "Value"])

    def get_rate_history(self) -> Dict[str, Tuple[float, str]]:
        """Derive rate history from base-rate CSV and meeting dates."""
        base_rate_df = self.get_base_rate()
        if base_rate_df.empty:
            return {}

        tone_path = Path(self.config.get("paths", {}).get("analysis", self.project_root / "data" / "analysis"))
        if tone_path.is_dir():
            tone_path = tone_path / "tone_index_results.csv"

        if not tone_path.exists():
            return {}

        tone_df = pd.read_csv(tone_path)
        if "meeting_date_str" not in tone_df.columns:
            return {}

        tone_df = tone_df.dropna(subset=["meeting_date_str"]).copy()
        tone_df["meeting_date"] = pd.to_datetime(
            tone_df["meeting_date_str"].astype(str).str.replace("_", "-"),
            errors="coerce",
        )
        tone_df = tone_df.dropna(subset=["meeting_date"]).sort_values("meeting_date")

        base_rate_df = base_rate_df.sort_values("Date").reset_index(drop=True)
        rate_history: Dict[str, Tuple[float, str]] = {}

        prev_rate = None
        for _, row in tone_df.iterrows():
            meeting_date = row["meeting_date"]
            meeting_key = row["meeting_date_str"]

            valid_rates = base_rate_df.loc[base_rate_df["Date"] <= meeting_date, "Value"]
            if valid_rates.empty:
                continue

            current_rate = float(valid_rates.iloc[-1])
            if prev_rate is None:
                action = "hold"
            elif current_rate > prev_rate:
                action = "hike"
            elif current_rate < prev_rate:
                action = "cut"
            else:
                action = "hold"

            rate_history[meeting_key] = (current_rate, action)
            prev_rate = current_rate

        return rate_history

    def _filter_date_range(self, df: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
        if df.empty:
            return df

        filtered = df.copy()
        if start_date is not None:
            filtered = filtered[filtered["Date"] >= pd.to_datetime(start_date)]
        if end_date is not None:
            filtered = filtered[filtered["Date"] <= pd.to_datetime(end_date)]

        return filtered.reset_index(drop=True)

    def _to_ecos_date(self, value, frequency: str, is_start: bool) -> str:
        if value is None:
            dt = datetime.now()
            if is_start:
                dt = dt - timedelta(days=3650)
            return self._format_ecos_date(dt, frequency)

        if isinstance(value, str):
            value = value.strip()
            if frequency == "Q" and "Q" in value:
                return value.upper()
            if value.isdigit():
                if frequency == "D" and len(value) >= 8:
                    return value[:8]
                if frequency == "M" and len(value) >= 6:
                    return value[:6]
                if frequency == "Q" and len(value) >= 6:
                    dt = pd.to_datetime(value[:6], format="%Y%m", errors="coerce")
                    if pd.notna(dt):
                        return f"{dt.year}Q{((dt.month - 1) // 3) + 1}"

        dt = pd.to_datetime(value, errors="coerce")
        if pd.isna(dt):
            dt = datetime.now()
        return self._format_ecos_date(dt.to_pydatetime(), frequency)

    def _format_ecos_date(self, dt: datetime, frequency: str) -> str:
        if frequency == "D":
            return dt.strftime("%Y%m%d")
        if frequency == "M":
            return dt.strftime("%Y%m")
        if frequency == "Q":
            quarter = ((dt.month - 1) // 3) + 1
            return f"{dt.year}Q{quarter}"
        return dt.strftime("%Y%m%d")

    def _parse_time(self, value: str, frequency: str) -> pd.Timestamp:
        value = value.strip()
        if frequency == "D":
            return pd.to_datetime(value, format="%Y%m%d", errors="coerce")
        if frequency == "M":
            return pd.to_datetime(value + "01", format="%Y%m%d", errors="coerce")
        if frequency == "Q":
            if "Q" in value:
                year = int(value[:4])
                quarter = int(value[-1])
                month = quarter * 3
                day = 31 if month in (3, 12) else 30
                return pd.Timestamp(year=year, month=month, day=day)
            parsed = pd.to_datetime(value, errors="coerce")
            if pd.isna(parsed):
                return pd.NaT
            quarter = ((parsed.month - 1) // 3) + 1
            month = quarter * 3
            day = 31 if month in (3, 12) else 30
            return pd.Timestamp(year=parsed.year, month=month, day=day)
        return pd.to_datetime(value, errors="coerce")
