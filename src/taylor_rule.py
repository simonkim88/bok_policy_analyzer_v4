# pyright: reportCallIssue=false, reportArgumentType=false, reportReturnType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""
Extended Taylor Rule for Korean Monetary Policy Analysis.

Models:
1. Standard Taylor Rule: i = r* + pi + alpha(pi - pi*) + beta(y)
2. Extended Taylor Rule: i = r* + pi + alpha(pi - pi*) + beta(y) + gamma*FSI
3. Augmented Taylor Rule: i = r* + pi + alpha(pi - pi*) + beta(y) + gamma*FSI + delta*ToneAdj

Where:
- FSI = Financial Stability Index (credit gap, FX deviation, yield spread)
- ToneAdj = Tone-based policy adjustment from NLP analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
import logging

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore", message="divide by zero", category=RuntimeWarning)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class TaylorRuleResult:
    """Taylor Rule calculation result."""

    df: pd.DataFrame
    latest_taylor_rate: float
    latest_base_rate: float
    gap: float
    model_type: str
    parameters: Dict[str, float]
    fsi_details: Optional[Dict[str, float]]
    tone_details: Optional[Dict[str, float]]


class ExtendedTaylorRule:
    """Extended Taylor Rule calculator with local CSV data support."""

    def __init__(
        self,
        alpha: float = 0.5,
        beta: float = 0.5,
        r_star: float = 2.0,
        pi_star: float = 2.0,
        gamma: float = 0.3,
        delta: float = 0.2,
        rho: float = 0.8,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.r_star = r_star
        self.pi_star = pi_star
        self.gamma = gamma
        self.delta = delta
        self.rho = rho
        self.data_dir = PROJECT_ROOT / "data"

    def _csv_path(self, relative_path: str) -> Path:
        csv_file = self.data_dir / relative_path
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        return csv_file

    def _parse_time(self, series: pd.Series, frequency: str) -> pd.Series:
        if frequency == "daily":
            return pd.to_datetime(series.astype(str), format="%Y%m%d", errors="coerce")
        if frequency == "monthly":
            parsed = pd.to_datetime(series.astype(str), format="%Y%m", errors="coerce")
            return parsed + pd.offsets.MonthEnd(0)
        if frequency == "quarterly":
            periods = pd.PeriodIndex(series.astype(str), freq="Q")
            return periods.to_timestamp(how="end").normalize()
        raise ValueError(f"Unsupported frequency: {frequency}")

    def _load_csv(self, csv_path: str, frequency: str, value_name: str = "Value") -> pd.DataFrame:
        """Load ECOS CSV to [Date, value_name] DataFrame."""
        path = self._csv_path(csv_path)
        df = pd.read_csv(path)
        if "TIME" not in df.columns or "DATA_VALUE" not in df.columns:
            raise ValueError(f"Invalid ECOS CSV format in {path}")

        out = df[["TIME", "DATA_VALUE"]].copy()
        out["Date"] = self._parse_time(out["TIME"], frequency)
        out[value_name] = pd.to_numeric(out["DATA_VALUE"], errors="coerce")
        out = out[["Date", value_name]].dropna().sort_values("Date")
        out = out.groupby("Date", as_index=False).last()
        return out

    def _to_monthly_last(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        out = df[["Date", value_col]].copy()
        out["Date"] = out["Date"].dt.to_period("M").dt.to_timestamp("M")
        out = out.groupby("Date", as_index=False).last()
        return out

    def _to_monthly_mean(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        out = df[["Date", value_col]].copy()
        out["Date"] = out["Date"].dt.to_period("M").dt.to_timestamp("M")
        out = out.groupby("Date", as_index=False)[value_col].mean()
        return out

    def _quarterly_to_monthly_ffill(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        out = df[["Date", value_col]].copy().sort_values("Date")
        out = out.set_index("Date").resample("ME").ffill().reset_index()
        return out

    def _normalize_tanh(self, series: pd.Series) -> pd.Series:
        sigma = series.std(ddof=0)
        if sigma is None or np.isnan(sigma) or sigma == 0:
            return pd.Series(0.0, index=series.index)
        return np.tanh(series / sigma)

    def _monthly_calendar(self, *frames: pd.DataFrame) -> pd.DataFrame:
        starts = [f["Date"].min() for f in frames if not f.empty]
        ends = [f["Date"].max() for f in frames if not f.empty]
        if not starts or not ends:
            raise ValueError("Cannot construct monthly calendar: missing input data")
        start_date = max(starts)
        end_date = min(ends)
        if pd.isna(start_date) or pd.isna(end_date) or start_date > end_date:
            raise ValueError("No overlapping period among required datasets")
        return pd.DataFrame({"Date": pd.date_range(start=start_date, end=end_date, freq="ME")})

    def _one_sided_hp_filter(
        self,
        series: pd.Series,
        lamb: float,
        ar_lags: int = 4,
        forecast_periods: int = 10,
    ) -> pd.Series:
        """Approximate one-sided HP filter via AR extension and expanding window."""
        values = pd.to_numeric(series, errors="coerce").astype(float).to_numpy()
        n = len(values)
        cycles = np.full(n, np.nan, dtype=float)

        for t in range(n):
            hist = values[: t + 1]
            hist = hist[np.isfinite(hist)]
            if len(hist) < 3:
                cycles[t] = 0.0
                continue

            effective_lags = min(ar_lags, len(hist) - 1)
            forecast = np.full(forecast_periods, hist[-1], dtype=float)

            if effective_lags >= 1 and len(hist) >= (effective_lags + 5):
                try:
                    ar_model = sm.tsa.AutoReg(hist, lags=effective_lags, old_names=False).fit()
                    forecast = np.asarray(
                        ar_model.predict(
                            start=len(hist),
                            end=len(hist) + forecast_periods - 1,
                            dynamic=False,
                        ),
                        dtype=float,
                    )
                except Exception:
                    forecast = np.full(forecast_periods, hist[-1], dtype=float)

            extended = np.concatenate([hist, forecast])
            cycle_ext, _ = sm.tsa.filters.hpfilter(extended, lamb=lamb)
            cycles[t] = float(cycle_ext[len(hist) - 1])

        return pd.Series(cycles, index=series.index)

    def _calculate_output_gap(self, gdp_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate output gap using HP filter on log GDP."""
        gdp = gdp_df[["Date", "GDP_Real"]].dropna().sort_values("Date").copy()
        gdp["ln_GDP"] = np.log(gdp["GDP_Real"])
        cycle = self._one_sided_hp_filter(gdp["ln_GDP"], lamb=1600.0)
        gdp["Output_Gap"] = (cycle * 100.0).astype(float)
        return gdp[["Date", "Output_Gap"]]

    def _calculate_inflation(self, cpi_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate YoY inflation from CPI index."""
        cpi = cpi_df[["Date", "CPI"]].dropna().sort_values("Date").copy()
        cpi["Inflation"] = cpi["CPI"].pct_change(12) * 100.0
        return cpi
    def _load_tone_data(self) -> pd.DataFrame:
        """Load tone index results and convert to monthly series."""
        path = self._csv_path("analysis/tone_index_results.csv")
        tone = pd.read_csv(path)
        required = {"meeting_date", "tone_index"}
        if not required.issubset(set(tone.columns)):
            raise ValueError("tone_index_results.csv missing required columns")

        tone["Date"] = pd.to_datetime(tone["meeting_date"], errors="coerce")
        tone["tone_index"] = pd.to_numeric(tone["tone_index"], errors="coerce")
        tone = tone[["Date", "tone_index"]].dropna().sort_values("Date")
        tone_monthly = self._to_monthly_mean(tone, "tone_index")
        return tone_monthly

    def _build_core_dataframe(self) -> pd.DataFrame:
        base_daily = self._load_csv("08_ecos/base_rate/base_rate.csv", "daily", "Base_Rate")
        cpi_monthly = self._load_csv("08_ecos/cpi/cpi_total.csv", "monthly", "CPI")
        gdp_quarterly = self._load_csv("08_ecos/gdp/gdp_real.csv", "quarterly", "GDP_Real")

        base_monthly = self._to_monthly_last(base_daily, "Base_Rate")
        inflation_df = self._calculate_inflation(cpi_monthly)
        output_gap_quarterly = self._calculate_output_gap(gdp_quarterly)
        output_gap_monthly = self._quarterly_to_monthly_ffill(output_gap_quarterly, "Output_Gap")

        calendar = self._monthly_calendar(base_monthly, inflation_df, output_gap_monthly)
        merged = calendar.copy()
        merged = merged.merge(base_monthly, on="Date", how="left")
        merged = merged.merge(inflation_df, on="Date", how="left")
        merged = merged.merge(output_gap_monthly, on="Date", how="left")

        merged = merged.sort_values("Date")
        merged[["Base_Rate", "CPI", "Inflation", "Output_Gap"]] = merged[
            ["Base_Rate", "CPI", "Inflation", "Output_Gap"]
        ].ffill()
        merged["Inflation_Gap"] = merged["Inflation"] - self.pi_star
        return merged.dropna(subset=["Base_Rate", "CPI", "Inflation", "Output_Gap"]).reset_index(drop=True)

    def _build_result(
        self,
        df: pd.DataFrame,
        model_type: str,
        fsi_details: Optional[Dict[str, float]] = None,
        tone_details: Optional[Dict[str, float]] = None,
    ) -> TaylorRuleResult:
        latest = df.iloc[-1]
        latest_taylor = float(latest["Taylor_Rate"])
        latest_base = float(latest["Base_Rate"])
        gap = latest_taylor - latest_base
        params = {
            "alpha": self.alpha,
            "beta": self.beta,
            "r_star": self.r_star,
            "pi_star": self.pi_star,
            "gamma": self.gamma,
            "delta": self.delta,
            "rho": self.rho,
        }
        return TaylorRuleResult(
            df=df,
            latest_taylor_rate=latest_taylor,
            latest_base_rate=latest_base,
            gap=gap,
            model_type=model_type,
            parameters=params,
            fsi_details=fsi_details,
            tone_details=tone_details,
        )

    def _calculate_fsi(self) -> pd.DataFrame:
        """Calculate Financial Stability Index and components."""
        credit_q = self._load_csv(
            "08_ecos/household_debt/household_credit.csv",
            "quarterly",
            "Household_Credit",
        )
        gdp_q = self._load_csv("08_ecos/gdp/gdp_real.csv", "quarterly", "GDP_Real")
        fx_d = self._load_csv("08_ecos/exchange_rates/usd_krw.csv", "daily", "USD_KRW")
        y3_d = self._load_csv("08_ecos/bond_yields/ktb_3y.csv", "daily", "KTB_3Y")
        y10_d = self._load_csv("08_ecos/bond_yields/ktb_10y.csv", "daily", "KTB_10Y")

        credit = credit_q.merge(gdp_q, on="Date", how="inner").dropna().copy()
        credit["Credit_to_GDP"] = (credit["Household_Credit"] / credit["GDP_Real"]) * 100.0
        credit["Credit_Gap"] = self._one_sided_hp_filter(credit["Credit_to_GDP"], lamb=400000.0)
        credit_m = self._quarterly_to_monthly_ffill(credit[["Date", "Credit_Gap"]], "Credit_Gap")

        fx = fx_d.copy().sort_values("Date")
        fx["FX_Return"] = np.log(fx["USD_KRW"]).diff()
        fx["FX_MA_200"] = fx["USD_KRW"].rolling(window=200, min_periods=60).mean()
        fx["FX_Deviation"] = ((fx["USD_KRW"] / fx["FX_MA_200"]) - 1.0) * 100.0
        fx["FX_Volatility"] = fx["FX_Return"].rolling(window=60, min_periods=20).std(ddof=0) * np.sqrt(252.0)
        fx_m = self._to_monthly_mean(fx[["Date", "FX_Deviation"]].dropna(), "FX_Deviation")
        fx_vol_m = self._to_monthly_mean(fx[["Date", "FX_Volatility"]].dropna(), "FX_Volatility")

        yields = y10_d.merge(y3_d, on="Date", how="inner").dropna().copy()
        yields["Yield_Spread"] = yields["KTB_10Y"] - yields["KTB_3Y"]
        yields["Spread_Risk"] = -yields["Yield_Spread"]
        spread_m = self._to_monthly_mean(yields[["Date", "Spread_Risk"]], "Spread_Risk")

        calendar = self._monthly_calendar(credit_m, fx_m, fx_vol_m, spread_m)
        fsi = calendar.copy()
        fsi = fsi.merge(credit_m, on="Date", how="left")
        fsi = fsi.merge(fx_m, on="Date", how="left")
        fsi = fsi.merge(fx_vol_m, on="Date", how="left")
        fsi = fsi.merge(spread_m, on="Date", how="left")

        fsi[["Credit_Gap", "FX_Deviation", "FX_Volatility", "Spread_Risk"]] = fsi[
            ["Credit_Gap", "FX_Deviation", "FX_Volatility", "Spread_Risk"]
        ].ffill()
        fsi = fsi.dropna(subset=["Credit_Gap", "FX_Deviation", "FX_Volatility", "Spread_Risk"]).reset_index(drop=True)

        fsi["Credit_Component"] = self._normalize_tanh(fsi["Credit_Gap"])
        fsi["FX_Component"] = self._normalize_tanh(fsi["FX_Deviation"])
        fsi["FX_Volatility_Component"] = self._normalize_tanh(fsi["FX_Volatility"])
        fsi["Spread_Component"] = self._normalize_tanh(fsi["Spread_Risk"])

        fsi["FSI"] = (
            0.35 * fsi["Credit_Component"]
            + 0.25 * fsi["FX_Component"]
            + 0.15 * fsi["FX_Volatility_Component"]
            + 0.25 * fsi["Spread_Component"]
        )
        return fsi
    def calculate_standard(self) -> TaylorRuleResult:
        """Standard Taylor Rule: i = r* + pi + alpha(pi-pi*) + beta(y)."""
        df = self._build_core_dataframe()
        df["Taylor_Rate"] = (
            self.r_star
            + df["Inflation"]
            + (self.alpha * df["Inflation_Gap"])
            + (self.beta * df["Output_Gap"])
        )

        ordered = df[
            [
                "Date",
                "Base_Rate",
                "CPI",
                "Inflation",
                "Output_Gap",
                "Inflation_Gap",
                "Taylor_Rate",
            ]
        ].copy()
        return self._build_result(ordered, "standard")

    def calculate_extended(self) -> TaylorRuleResult:
        """Extended Taylor Rule with financial stability term."""
        core = self._build_core_dataframe()
        fsi = self._calculate_fsi()

        df = core.merge(fsi, on="Date", how="left")
        df["FSI"] = df["FSI"].ffill()
        df = df.dropna(subset=["FSI"]).reset_index(drop=True)

        df["Taylor_Rate_Standard"] = (
            self.r_star
            + df["Inflation"]
            + (self.alpha * df["Inflation_Gap"])
            + (self.beta * df["Output_Gap"])
        )
        df["Taylor_Rate"] = df["Taylor_Rate_Standard"] + (self.gamma * df["FSI"])
        df["Taylor_Rate_Raw"] = df["Taylor_Rate"].copy()

        smoothed = df["Taylor_Rate"].to_numpy(dtype=float).copy()
        for t in range(1, len(smoothed)):
            smoothed[t] = (self.rho * smoothed[t - 1]) + ((1.0 - self.rho) * smoothed[t])
        df["Taylor_Rate"] = smoothed

        latest = df.iloc[-1]
        # Use last row with valid component data (components may be NaN in trailing months after ffill of FSI)
        comp_cols = ["Credit_Component", "FX_Component", "FX_Volatility_Component", "Spread_Component"]
        valid_comp = df.dropna(subset=comp_cols)
        comp_row = valid_comp.iloc[-1] if not valid_comp.empty else latest
        fsi_details = {
            "fsi_latest": float(latest["FSI"]),
            "credit_component_latest": float(comp_row["Credit_Component"]),
            "fx_component_latest": float(comp_row["FX_Component"]),
            "fx_volatility_component_latest": float(comp_row["FX_Volatility_Component"]),
            "spread_component_latest": float(comp_row["Spread_Component"]),
            "gamma": float(self.gamma),
        }

        ordered = df[
            [
                "Date",
                "Base_Rate",
                "CPI",
                "Inflation",
                "Output_Gap",
                "Inflation_Gap",
                "FSI",
                "Credit_Component",
                "FX_Component",
                "FX_Volatility_Component",
                "Spread_Component",
                "Taylor_Rate_Standard",
                "Taylor_Rate_Raw",
                "Taylor_Rate",
            ]
        ].copy()
        return self._build_result(ordered, "extended", fsi_details=fsi_details)

    def calculate_augmented(self) -> TaylorRuleResult:
        """Augmented Taylor Rule with FSI and NLP tone adjustment."""
        extended_result = self.calculate_extended()
        df = extended_result.df.copy()
        tone = self._load_tone_data()

        df = df.merge(tone, on="Date", how="left")
        df["tone_index"] = df["tone_index"].shift(1).ffill().fillna(0.0)
        df["Taylor_Residual"] = df["Base_Rate"] - df["Taylor_Rate_Standard"]

        sensitivity = 0.0
        r_squared = 0.0
        p_value = np.nan
        valid = df[["Taylor_Residual", "tone_index"]].dropna()
        if len(valid) > 10:
            X = sm.add_constant(valid["tone_index"])
            model = sm.OLS(valid["Taylor_Residual"], X).fit()
            sensitivity = float(model.params.get("tone_index", 0.0))
            sensitivity = float(np.clip(sensitivity, -2.0, 2.0))
            r_squared = float(model.rsquared)
            p_value = float(model.pvalues.get("tone_index", np.nan))

        df["Tone_Adjustment"] = df["tone_index"] * sensitivity
        df["Taylor_Rate_Raw"] = (
            df["Taylor_Rate_Standard"]
            + (self.gamma * df["FSI"])
            + (self.delta * df["Tone_Adjustment"])
        )

        smoothed = df["Taylor_Rate_Raw"].to_numpy(dtype=float).copy()
        for t in range(1, len(smoothed)):
            smoothed[t] = (self.rho * smoothed[t - 1]) + ((1.0 - self.rho) * smoothed[t])
        df["Taylor_Rate"] = smoothed

        latest = df.iloc[-1]
        tone_details = {
            "tone_latest": float(latest["tone_index"]),
            "tone_adjustment_latest": float(latest["Tone_Adjustment"]),
            "sensitivity": sensitivity,
            "sensitivity_method": "residual_regression",
            "r_squared": r_squared,
            "p_value": p_value,
            "delta": float(self.delta),
        }

        ordered = df[
            [
                "Date",
                "Base_Rate",
                "CPI",
                "Inflation",
                "Output_Gap",
                "Inflation_Gap",
                "FSI",
                "Credit_Component",
                "FX_Component",
                "FX_Volatility_Component",
                "Spread_Component",
                "tone_index",
                "Tone_Adjustment",
                "Taylor_Rate_Standard",
                "Taylor_Rate_Raw",
                "Taylor_Rate",
            ]
        ].copy()
        return self._build_result(
            ordered,
            "augmented",
            fsi_details=extended_result.fsi_details,
            tone_details=tone_details,
        )

    def calculate(self, model_type: str = "extended") -> TaylorRuleResult:
        """Main entry point for rule variants."""
        model = model_type.lower().strip()
        if model == "standard":
            return self.calculate_standard()
        if model == "extended":
            return self.calculate_extended()
        if model == "augmented":
            return self.calculate_augmented()
        raise ValueError(f"Unknown model_type: {model_type}")


def calculate_taylor_rule(
    alpha: float = 0.5,
    beta: float = 0.5,
    r_star: float = 2.0,
    pi_star: float = 2.0,
) -> pd.DataFrame:
    """Legacy wrapper kept for backward compatibility with existing views."""
    engine = ExtendedTaylorRule(alpha=alpha, beta=beta, r_star=r_star, pi_star=pi_star)
    result = engine.calculate_standard()
    return result.df[
        [
            "Date",
            "Base_Rate",
            "CPI",
            "Inflation",
            "Output_Gap",
            "Inflation_Gap",
            "Taylor_Rate",
        ]
    ].copy()


if __name__ == "__main__":
    demo = ExtendedTaylorRule()
    demo_standard = demo.calculate_standard().df
    print(demo_standard.tail(5).to_string(index=False))
