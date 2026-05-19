#!/usr/bin/env python3
"""
Teknofest — ≤500 g toplam kütle, maksimum hız için optimizasyon.

Çalıştır:
    python -m teknofest.optimize_speed
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import physics_engine as pe
from optimizer import Constraint, ConstraintOp, DesignVariable, ObjectiveGoal, run_optimization
from teknofest.preset import (
    MAX_TOTAL_MASS_KG,
    create_teknofest_torpedo,
    default_sim_params,
    speed_optimization_setup,
)


def _fmt_m(val: float) -> str:
    if val < 0.01:
        return f"{val * 1000:.2f} mm"
    return f"{val * 100:.2f} cm"


def main() -> None:
    print("OpenTorpedo — Hız optimizasyonu (max 500 g)\n")

    torpedo, _geom = create_teknofest_torpedo(with_spring=True)
    sim = default_sim_params()
    dvar_specs, con_specs = speed_optimization_setup(torpedo)

    m0 = pe.total_mass(torpedo)
    print(f"Başlangıç kütlesi: {m0 * 1000:.1f} g (limit {MAX_TOTAL_MASS_KG * 1000:.0f} g)\n")

    dvars = [
        DesignVariable(
            component_index=s.get("component_index", 0),
            attribute=s["attribute"],
            lower=s["lower"],
            upper=s["upper"],
            label=s["label"],
            scope=s.get("scope", "component"),
        )
        for s in dvar_specs
    ]
    cons = [
        Constraint(
            metric=c["metric"],
            op=ConstraintOp.LEQ if c["op"] == "<=" else ConstraintOp.GEQ,
            limit=c["limit"],
            label=c.get("label", ""),
        )
        for c in con_specs
    ]

    def progress(it: int, val: float) -> None:
        if it % 5 == 0:
            print(f"  iter {it:3d}  max speed = {val:.3f} m/s")

    print("Optimizasyon çalışıyor (hedef: Max Speed)…\n")
    result = run_optimization(
        copy.deepcopy(torpedo),
        sim,
        "Max Speed (m/s)",
        ObjectiveGoal.MAXIMIZE,
        dvars,
        cons,
        callback=progress,
        maxiter=25,
        maxfun=60,
    )

    torpedo, _ = create_teknofest_torpedo(with_spring=True)
    for s in dvar_specs:
        label = s["label"]
        if label not in result.final_params:
            continue
        val = result.final_params[label]
        if s.get("scope") == "sim_params":
            sim[s["attribute"]] = val
        else:
            setattr(torpedo.components[s["component_index"]], s["attribute"], val)

    spring = torpedo.launch_spring
    ballast = next(c for c in torpedo.components if c.__class__.__name__ == "BallastMass")
    hull = torpedo.cad_hull

    m = pe.total_mass(torpedo)
    cog = pe.center_of_gravity(torpedo) * 100

    print("\n" + "=" * 56)
    print("SONUÇ" if result.success else f"UYARI: {result.message}")
    print("=" * 56)
    print(f"Hız (max)     : {result.initial_value:.3f} → {result.final_value:.3f} m/s")
    print(f"Toplam kütle  : {m * 1000:.1f} g")
    print(f"CoG (burundan): {cog:.2f} cm")

    if hull:
        print(f"Doluluk       : {hull.infill * 100:.1f} %")
        print(f"Gövde kütlesi : {hull.hull_mass * 1000:.1f} g")
    print(f"Balast        : {ballast.mass * 1000:.1f} g @ {ballast.position * 100:.1f} cm")

    if spring:
        print("\nYay:")
        print(f"  Tel çapı    : {_fmt_m(spring.wire_diameter)} (sabit)")
        print(f"  Orta çap    : {_fmt_m(spring.coil_diameter)}")
        print(f"  Sarım       : {spring.active_coils:.1f}")
        print(f"  Serbest boy : {_fmt_m(spring.free_length)}")
        print(f"  Sıkıştırma  : {_fmt_m(spring.effective_compression)}")
        print(f"  Δv (yay)    : {spring.launch_velocity_boost(m):.2f} m/s")


if __name__ == "__main__":
    main()
