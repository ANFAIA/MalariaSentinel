"""D14: Mobility conservation — OD matrix rows sum to 1.0 (row-stochastic)."""
from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

import numpy as np

from scorers.base import Scorer, ScorerResult


def _read_csr(path: Path) -> tuple[int, int, int, np.ndarray, np.ndarray, np.ndarray]:
    with open(path, "rb") as f:
        n_rows = struct.unpack("i", f.read(4))[0]
        n_cols = struct.unpack("i", f.read(4))[0]
        nnz = struct.unpack("i", f.read(4))[0]
        row_ptr = np.frombuffer(f.read(4 * (n_rows + 1)), dtype=np.int32)
        col_idx = np.frombuffer(f.read(4 * nnz), dtype=np.int32)
        values = np.frombuffer(f.read(4 * nnz), dtype=np.float32)
    return n_rows, n_cols, nnz, row_ptr, col_idx, values


def _row_sums(row_ptr: np.ndarray, values: np.ndarray) -> np.ndarray:
    n_rows = len(row_ptr) - 1
    sums = np.zeros(n_rows, dtype=np.float64)
    for i in range(n_rows):
        start, end = row_ptr[i], row_ptr[i + 1]
        sums[i] = float(values[start:end].sum())
    return sums


class MobilityConservationScorer(Scorer):
    @property
    def name(self) -> str:
        return "D14_mobility_conservation"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        csr_files = list(run_dir.glob("*.csr"))
        if not csr_files:
            for parent in [run_dir.parent, run_dir.parent / "hosts"]:
                csr_files = list(parent.glob("*.csr"))
                if csr_files:
                    break

        if not csr_files:
            return ScorerResult(
                score=0.0,
                value=0.0,
                target="row sums ~ 1.0",
                diagnostics={"error": "no .csr files found"},
                passed=False,
            )

        results = []
        for csr in sorted(csr_files):
            try:
                n_rows, n_cols, nnz, row_ptr, col_idx, values = _read_csr(csr)
                sums = _row_sums(row_ptr, values)

                deviations = np.abs(sums - 1.0)
                mean_dev = float(deviations.mean())
                max_dev = float(deviations.max())
                n_valid_rows = int((np.abs(sums - 1.0) < 0.01).sum())
                fraction_valid = n_valid_rows / max(n_rows, 1)

                results.append({
                    "file": csr.name,
                    "n_rows": n_rows,
                    "nnz": nnz,
                    "mean_deviation": round(mean_dev, 6),
                    "max_deviation": round(max_dev, 6),
                    "fraction_rows_sum_to_one": round(fraction_valid, 4),
                })
            except Exception as e:
                results.append({"file": csr.name, "error": str(e)})

        fractions = [r.get("fraction_rows_sum_to_one", 0.0) for r in results if "error" not in r]
        if fractions:
            min_fraction = min(fractions)
            if min_fraction >= 0.99:
                raw = 1.0
            else:
                raw = math.exp(-((min_fraction - 0.99) / 0.10) ** 2)
        else:
            raw = 0.0

        return ScorerResult(
            score=round(raw, 4),
            value=round(min(fractions) if fractions else 0.0, 4),
            target="row sums ~ 1.0 (all files)",
            diagnostics={"files_checked": results},
            passed=raw >= 0.70,
        )
