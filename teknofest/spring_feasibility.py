"""Manufacturability checks for compression spring geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from torpedo_model import LaunchSpring

# Yay endeksi C = D/d (sıkıştırma yayı için tipik 4–10)
SPRING_INDEX_MIN = 4.0
SPRING_INDEX_MAX = 10.0

# Serbest boyun en fazla bu oranı kadar sıkıştır (üretim + güvenlik payı)
MAX_COMPRESSION_RATIO = 0.45

# Katı yükseklikten en az bu kadar pay (sıkıştırılmış boy / tel çapı)
MIN_SOLID_MARGIN_COILS = 1.15

# 4 yay toplam / tek yay üst kuvvet (bench launcher için)
MAX_TOTAL_FORCE_N = 520.0
MAX_FORCE_PER_SPRING_N = 150.0

# Wahl kayması — music/spring çeliği için muhafazakâr tavan (Pa)
MAX_SHEAR_STRESS_MPA = 650.0
MAX_SHEAR_STRESS_PA = MAX_SHEAR_STRESS_MPA * 1e6

# Burkulma: serbest boy / orta çap
MAX_FREE_LENGTH_TO_COIL_RATIO = 4.5

# Simülasyonda yaydan gelen Δv üst sınırı (tek başına fırlatma)
MAX_LAUNCH_DELTA_V_M_S = 9.0


@dataclass(frozen=True)
class SpringFeasibility:
    ok: bool
    reason: str = ""


def _wahl_factor(coil_index: float) -> float:
    if coil_index <= 0:
        return 1.0
    return (4.0 * coil_index - 1.0) / (4.0 * coil_index - 2.0) + 0.615 / coil_index


def shear_stress_pa(force_n: float, wire_d_m: float, coil_d_m: float) -> float:
    """Max kayma gerilmesi (Wahl), tek yay kuvveti F."""
    d, D = wire_d_m, coil_d_m
    if d <= 0 or D <= 0 or force_n <= 0:
        return 0.0
    c = D / d
    kw = _wahl_factor(c)
    return kw * 8.0 * force_n * D / (math.pi * d ** 3)


def check_spring_feasibility(spring: "LaunchSpring", *, total_mass_kg: float | None = None) -> SpringFeasibility:
    d = spring.wire_diameter
    D = spring.coil_diameter
    if d <= 0 or D <= 0:
        return SpringFeasibility(False, "tel veya bobin çapı geçersiz")

    index = D / d
    if index < SPRING_INDEX_MIN:
        return SpringFeasibility(False, f"yay endeksi D/d={index:.1f} < {SPRING_INDEX_MIN}")
    if index > SPRING_INDEX_MAX:
        return SpringFeasibility(False, f"yay endeksi D/d={index:.1f} > {SPRING_INDEX_MAX}")

    fl = spring.free_length
    if fl > 0 and spring.effective_compression / fl > MAX_COMPRESSION_RATIO + 1e-9:
        ratio = spring.effective_compression / fl
        return SpringFeasibility(
            False,
            f"sıkıştırma oranı %{ratio * 100:.0f} > %{MAX_COMPRESSION_RATIO * 100:.0f}",
        )

    solid = d * max(spring.active_coils, 1.0)
    compressed_height = fl - spring.effective_compression
    if compressed_height < solid * MIN_SOLID_MARGIN_COILS:
        return SpringFeasibility(False, "katı yüksekliğe çok yakın (tel dolması)")

    if fl / D > MAX_FREE_LENGTH_TO_COIL_RATIO:
        return SpringFeasibility(
            False,
            f"ince/uzun yay L/D={fl / D:.1f} > {MAX_FREE_LENGTH_TO_COIL_RATIO}",
        )

    f1 = spring.launch_force_single
    ft = spring.launch_force
    if f1 > MAX_FORCE_PER_SPRING_N + 1e-6:
        return SpringFeasibility(
            False,
            f"tek yay kuvveti {f1:.0f} N > {MAX_FORCE_PER_SPRING_N:.0f} N",
        )
    if ft > MAX_TOTAL_FORCE_N + 1e-6:
        return SpringFeasibility(
            False,
            f"toplam kuvvet {ft:.0f} N > {MAX_TOTAL_FORCE_N:.0f} N",
        )

    tau = shear_stress_pa(f1, d, D)
    if tau > MAX_SHEAR_STRESS_PA:
        return SpringFeasibility(
            False,
            f"kayma gerilmesi {tau / 1e6:.0f} MPa > {MAX_SHEAR_STRESS_MPA:.0f} MPa",
        )

    if total_mass_kg is not None and total_mass_kg > 0:
        dv = spring.launch_velocity_boost(total_mass_kg)
        if dv > MAX_LAUNCH_DELTA_V_M_S:
            return SpringFeasibility(
                False,
                f"Δv={dv:.1f} m/s > {MAX_LAUNCH_DELTA_V_M_S} m/s",
            )

    return SpringFeasibility(True)


def is_producible_spring(spring: "LaunchSpring", *, total_mass_kg: float | None = None) -> bool:
    return check_spring_feasibility(spring, total_mass_kg=total_mass_kg).ok
