"""
Teknofest balast + yay grid araması.

PC için: preset="fast" veya "medium"
Colab için: preset="full" (daha geniş arama, ~3–8 dk)
"""

from __future__ import annotations

import json
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import physics_engine as pe
from optimizer import METRIC_FUNCTIONS
from teknofest.preset import MAX_TOTAL_MASS_KG, create_teknofest_torpedo, default_sim_params
from teknofest.spring_feasibility import is_producible_spring
from teknofest.spring_limits import (
    LAUNCH_SPRING_COUNT,
    SPRING_MAX_COIL_DIAMETER_M,
    SPRING_MAX_FREE_LENGTH_M,
    SPRING_MAX_WIRE_DIAMETER_M,
)

# Her preset: grid dict + opsiyonel sabitler
_PRESETS: dict[str, dict[str, Any]] = {
  # ~96 deneme — Colab / PC smoke test
    "quick": {
        "grid": {
            "infill": (0.12, 0.18),
            "bm": (0.0, 0.10),
            "bp": (0.08, 0.14),
            "wire": (0.0015, 0.0020),
            "cd": (0.012, 0.016),
            "comp": (0.018, 0.024, 0.030),
        },
        "fixed": {"nc": 8.0, "fl": 0.050},
    },
    # ~160 deneme — PC dostu
    "fast": {
        "grid": {
            "infill": (0.12, 0.20),
            "bm": (0.0, 0.10),
            "bp": (0.08, 0.14),
            "wire": (0.0015, 0.0020),
            "cd": (0.012, 0.016),
            "comp": (0.015, 0.022, 0.028, 0.034),
        },
        "fixed": {"nc": 8.0, "fl": 0.050},
    },
    # ~650 deneme
    "medium": {
        "grid": {
            "infill": (0.12, 0.14, 0.16),
            "bm": (0.0, 0.05, 0.10, 0.15),
            "bp": (0.06, 0.10, 0.14),
            "wire": (0.0010, 0.0015, 0.0020),
            "cd": (0.010, 0.012, 0.014),
            "nc": (6, 8),
            "comp": (0.018, 0.024, 0.030, 0.036),
        },
        "fixed": {"fl": 0.060},
    },
    # Colab önerilen, üretilebilir sıkıştırma aralığı
    "full": {
        "grid": {
            "infill": (0.10, 0.12, 0.14, 0.16),
            "bm": (0.0, 0.05, 0.10, 0.15),
            "bp": (0.08, 0.14),
            "wire": (0.0012, 0.0015, 0.0018, 0.0020),
            "cd": (0.010, 0.012, 0.014, 0.016),
            "nc": (6, 7, 8),
            "fl": (0.050, 0.055, 0.060),
            "comp": (0.018, 0.024, 0.030, 0.036),
        },
        "fixed": {},
    },
}


def _apply(t, h, b, sp, p: dict, fixed: dict) -> None:
    h.infill = p["infill"]
    b.mass = p["bm"]
    b.position = min(p["bp"], h.length - 0.02)
    sp.wire_diameter = p["wire"]
    sp.coil_diameter = p["cd"]
    sp.active_coils = float(p.get("nc", fixed.get("nc", 8.0)))
    sp.free_length = p.get("fl", fixed.get("fl", 0.060))
    sp.compression = p["comp"]
    sp.clamp_to_limits(
        max_coil_diameter=SPRING_MAX_COIL_DIAMETER_M,
        max_free_length=SPRING_MAX_FREE_LENGTH_M,
        max_wire_diameter=SPRING_MAX_WIRE_DIAMETER_M,
    )


def count_combos(preset: str) -> int:
    g = _PRESETS[preset]["grid"]
    n = 1
    for v in g.values():
        n *= len(v)
    return n


def run_grid_search(
    preset: str = "fast",
    *,
    root: Path | str | None = None,
    out_path: Path | str | None = None,
    progress_every: int = 50,
) -> dict:
    """
  Grid araması çalıştırır, sonuç dict döner ve JSON yazar.

  preset: quick | fast | medium | full
  """
    if preset not in _PRESETS:
        raise ValueError(f"Bilinmeyen preset: {preset!r}. Seçenekler: {list(_PRESETS)}")

    root = Path(root or _ROOT)
    out_path = Path(out_path or root / "configs" / "teknofest_optimized.json")
    cfg = _PRESETS[preset]
    grid = cfg["grid"]
    fixed = cfg.get("fixed", {})

    sim = default_sim_params()
    torpedo, _ = create_teknofest_torpedo(with_spring=True)
    h = torpedo.cad_hull
    b = next(c for c in torpedo.components if c.__class__.__name__ == "BallastMass")
    sp = torpedo.launch_spring
    assert h and sp

    keys = list(grid.keys())
    combos = list(product(*(grid[k] for k in keys)))
    n_total = len(combos)

    print(
        f"Preset={preset} | {n_total} kombinasyon | "
        f"{LAUNCH_SPRING_COUNT}× paralel yay | üretilebilir yay filtresi | "
        f"tel ≤2 mm | kütle ≤{MAX_TOTAL_MASS_KG*1000:.0f} g",
        flush=True,
    )

    t0 = time.time()
    best: dict = {"speed": -1.0}
    n_ok = 0

    for i, vals in enumerate(combos, 1):
        p = dict(zip(keys, vals))
        _apply(torpedo, h, b, sp, p, fixed)
        m = pe.total_mass(torpedo)
        if m > MAX_TOTAL_MASS_KG:
            continue
        if not is_producible_spring(sp, total_mass_kg=m):
            continue
        spd = METRIC_FUNCTIONS["Max Speed (m/s)"](torpedo, sim)
        n_ok += 1
        if spd > best["speed"]:
            best = {"speed": spd, **p}

        if progress_every and i % progress_every == 0:
            elapsed = time.time() - t0
            print(f"  … {i}/{n_total} ({100*i/n_total:.0f}%) — {elapsed:.0f}s", flush=True)

    _apply(torpedo, h, b, sp, best, fixed)
    m = pe.total_mass(torpedo)
    cog = pe.center_of_gravity(torpedo) * 100

    out = {
        "method": f"grid_{preset}",
        "preset": preset,
        "evaluations": n_total,
        "valid_evaluations": n_ok,
        "elapsed_s": round(time.time() - t0, 1),
        "max_speed_m_s": round(best["speed"], 3),
        "total_mass_g": round(m * 1000, 1),
        "cog_cm": round(cog, 2),
        "hull": {
            "infill_percent": round(h.infill * 100, 1),
            "mass_g": round(h.hull_mass * 1000, 1),
        },
        "ballast": {
            "mass_g": round(b.mass * 1000, 1),
            "position_cm": round(b.position * 100, 1),
        },
        "spring": {
            "parallel_count": int(sp.count),
            "wire_diameter_mm": round(sp.wire_diameter * 1000, 2),
            "coil_diameter_mm": round(sp.coil_diameter * 1000, 1),
            "active_coils": int(round(sp.active_coils)),
            "free_length_mm": round(sp.free_length * 1000, 1),
            "compression_mm": round(sp.effective_compression * 1000, 1),
            "k_total_N_per_m": round(sp.spring_constant, 1),
            "k_per_spring_N_per_m": round(sp.spring_constant_single, 1),
            "force_total_N": round(sp.launch_force, 1),
            "force_per_spring_N": round(sp.launch_force_single, 1),
            "spring_mass_total_g": round(sp.mass * 1000, 2),
            "delta_v_m_s": round(sp.launch_velocity_boost(m), 3),
            "accel_m_s2": round(sp.launch_acceleration(m), 1),
            "spring_index_D_over_d": round(sp.coil_diameter / sp.wire_diameter, 2),
            "compression_ratio_percent": round(
                100.0 * sp.effective_compression / sp.free_length if sp.free_length else 0, 1
            ),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False), flush=True)
    print(f"\nKayıt: {out_path}", flush=True)
    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Teknofest grid araması")
    p.add_argument(
        "--preset",
        default="fast",
        choices=list(_PRESETS),
        help="quick (~96), fast (~160), medium (~1900), full (~6900, Colab)",
    )
    p.add_argument("--root", default=None, help="Proje kök dizini")
    p.add_argument("--progress", type=int, default=50)
    args = p.parse_args()
    run_grid_search(args.preset, root=args.root, progress_every=args.progress)


if __name__ == "__main__":
    main()
