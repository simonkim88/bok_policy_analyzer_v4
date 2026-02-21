"""
Enhanced Backtesting Framework.

Tests Taylor Rule variants against historical BOK decisions.
Calculates: accuracy, RMSE, directional accuracy, Granger causality.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests

from src.taylor_rule import ExtendedTaylorRule

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TaylorRuleBacktester:
    def __init__(self, model_type="extended"):
        self.model_type = model_type
        self.engine = ExtendedTaylorRule()
        self.data_dir = PROJECT_ROOT / "data"

    def _load_meeting_dates(self):
        tone_path = self.data_dir / "analysis/tone_index_results.csv"
        tone = pd.read_csv(tone_path)
        tone["Date"] = pd.to_datetime(tone["meeting_date"], errors="coerce")
        tone = pd.DataFrame(tone[["Date", "meeting_date_str"]])
        tone = tone[tone["Date"].notna()]
        tone = tone.set_index("Date").sort_index().reset_index()
        tone = tone.drop_duplicates(subset=["Date"]).reset_index(drop=True)
        return tone

    def _calc_direction(self, series):
        diff = series.diff().fillna(0.0)
        return pd.Series(np.sign(diff), index=series.index)

    def run_backtest(self, start_date="2015-01-01"):
        model_df = self.engine.calculate(self.model_type).df.copy()
        model_df = model_df.set_index("Date").sort_index().reset_index()

        meetings = self._load_meeting_dates()
        meetings = meetings[meetings["Date"] >= pd.to_datetime(start_date)].copy()
        if meetings.empty:
            return pd.DataFrame()

        meetings = meetings.set_index("Date").sort_index().reset_index()
        merged = pd.merge_asof(
            meetings,
            model_df,
            on="Date",
            direction="backward",
        )

        merged["Taylor_Gap"] = merged["Taylor_Rate"] - merged["Base_Rate"]
        merged["Taylor_Recommended_Rate"] = merged["Taylor_Rate"]
        merged["Actual_Direction"] = self._calc_direction(merged["Base_Rate"])

        prev_actual = merged["Base_Rate"].shift(1).fillna(merged["Base_Rate"])
        merged["Expected_Direction"] = np.sign(merged["Taylor_Recommended_Rate"] - prev_actual)
        merged["Direction_Match"] = merged["Expected_Direction"] == merged["Actual_Direction"]

        merged["Squared_Error"] = (merged["Taylor_Rate"] - merged["Base_Rate"]) ** 2
        merged["Abs_Error"] = (merged["Taylor_Rate"] - merged["Base_Rate"]).abs()

        return merged[
            [
                "Date",
                "meeting_date_str",
                "Base_Rate",
                "Taylor_Rate",
                "Taylor_Gap",
                "Expected_Direction",
                "Actual_Direction",
                "Direction_Match",
                "Abs_Error",
                "Squared_Error",
            ]
        ].copy()

    def calculate_metrics(self, results):
        if results.empty:
            return {
                "observations": 0,
                "directional_accuracy": 0.0,
                "rmse": 0.0,
                "mae": 0.0,
                "r_squared": 0.0,
                "hit_ratio_by_year": {},
                "granger_pvalue_lag2": np.nan,
            }

        y_true = results["Base_Rate"].astype(float)
        y_pred = results["Taylor_Rate"].astype(float)

        rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
        mae = float(np.mean(np.abs(y_pred - y_true)))

        ss_res = float(np.sum((y_true - y_pred) ** 2))
        ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        directional_accuracy = float(results["Direction_Match"].mean())

        by_year = results.copy()
        by_year["Year"] = by_year["Date"].dt.year
        hit_ratio = by_year.groupby("Year")["Direction_Match"].mean().to_dict()
        hit_ratio = {str(k): float(v) for k, v in hit_ratio.items()}

        granger_pvalue = np.nan
        try:
            gc_input = results[["Base_Rate", "Taylor_Rate"]].dropna()
            if len(gc_input) >= 12:
                gc_res = grangercausalitytests(gc_input, maxlag=2, verbose=False)
                granger_pvalue = float(gc_res[2][0]["ssr_ftest"][1])
        except Exception:
            granger_pvalue = np.nan

        return {
            "observations": int(len(results)),
            "directional_accuracy": directional_accuracy,
            "rmse": rmse,
            "mae": mae,
            "r_squared": float(r_squared),
            "hit_ratio_by_year": hit_ratio,
            "granger_pvalue_lag2": granger_pvalue,
        }

    def compare_models(self, start_date="2015-01-01"):
        rows = []
        for model_type in ["standard", "extended", "augmented"]:
            tester = TaylorRuleBacktester(model_type=model_type)
            result = tester.run_backtest(start_date=start_date)
            metrics = tester.calculate_metrics(result)
            rows.append(
                {
                    "model_type": model_type,
                    "observations": metrics["observations"],
                    "directional_accuracy": metrics["directional_accuracy"],
                    "rmse": metrics["rmse"],
                    "mae": metrics["mae"],
                    "r_squared": metrics["r_squared"],
                    "granger_pvalue_lag2": metrics["granger_pvalue_lag2"],
                }
            )

        return pd.DataFrame(rows).sort_values(by="rmse").reset_index(drop=True)


class Backtester(TaylorRuleBacktester):
    """Backward-compatible alias for existing imports."""


if __name__ == "__main__":
    backtester = TaylorRuleBacktester(model_type="extended")
    out = backtester.run_backtest(start_date="2018-01-01")
    print(backtester.calculate_metrics(out))
