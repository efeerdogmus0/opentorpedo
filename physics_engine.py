"""
physics_engine.py — Enhanced hydrodynamics calculations for torpedoes.

Includes:
  - ITTC-1957 friction line with Hoerner form factor
  - Fin lift & induced drag (thin-plate / Barrowman)
  - Body slender-body lift
  - Pitch damping torque
  - Directional added mass (Lamb k-factors)
  - Proper moment-of-inertia per component with parallel-axis theorem
  - Centre of pressure estimation
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from torpedo_model import Torpedo, NoseCone, BodyTube, Fin, Motor

# ═══════════════════════════════════════════════════════════════════════════
# Physical constants
# ═══════════════════════════════════════════════════════════════════════════
RHO_WATER: float = 1000.0          # kg/m³ (fresh water)
G: float = 9.81                     # m/s²
NU_WATER: float = 1.0e-6           # m²/s kinematic viscosity @ 20 °C
CD_BASE: float = 0.30              # fallback drag coefficient
OSWALD_EFFICIENCY: float = 0.85    # span efficiency for induced drag


# ═══════════════════════════════════════════════════════════════════════════
# Aggregate properties
# ═══════════════════════════════════════════════════════════════════════════

def total_mass(torpedo: "Torpedo", t: float = 0.0) -> float:
    """Sum of all component masses (time-aware for Motor burn)."""
    return torpedo.mass_at(t)


def total_volume(torpedo: "Torpedo") -> float:
    """Sum displaced volumes (BallastMass & Motor = 0)."""
    return sum(c.volume for c in torpedo.components)


def total_wetted_area(torpedo: "Torpedo") -> float:
    return torpedo.total_wetted_area


# ═══════════════════════════════════════════════════════════════════════════
# Centres
# ═══════════════════════════════════════════════════════════════════════════

def center_of_gravity(torpedo: "Torpedo", t: float = 0.0) -> float:
    """Mass-weighted centroid (m from nose tip).  Time-aware for Motor."""
    from torpedo_model import Motor
    m_total = 0.0
    moment = 0.0
    for c in torpedo.components:
        if isinstance(c, Motor):
            m_c = c.mass_at(t)
        else:
            m_c = c.mass
        m_total += m_c
        moment += m_c * c.centroid_x
    return moment / m_total if m_total > 0 else 0.0


def center_of_buoyancy(torpedo: "Torpedo") -> float:
    """Volume-weighted centroid (m from nose tip)."""
    v_total = total_volume(torpedo)
    if v_total == 0:
        return 0.0
    return sum(c.volume * c.centroid_x for c in torpedo.components) / v_total


# ═══════════════════════════════════════════════════════════════════════════
# Reference area
# ═══════════════════════════════════════════════════════════════════════════

def frontal_area(torpedo: "Torpedo") -> float:
    """Cross-sectional reference area π r²."""
    r = torpedo.max_diameter / 2.0
    return math.pi * r ** 2


# ═══════════════════════════════════════════════════════════════════════════
# Reynolds-dependent friction drag  (ITTC-1957 + Hoerner form factor)
# ═══════════════════════════════════════════════════════════════════════════

def reynolds_number(speed: float, length: float, nu: float = NU_WATER) -> float:
    """Re = V · L / ν."""
    return speed * length / nu if nu > 0 else 0.0


def friction_coefficient(re: float) -> float:
    """ITTC-1957 friction line: Cf = 0.075 / (log10(Re) - 2)²."""
    if re < 1e3:
        return 0.0
    log_re = math.log10(re)
    denom = (log_re - 2.0) ** 2
    return 0.075 / denom if denom > 0 else 0.0


def form_factor(diameter: float, length: float) -> float:
    """Hoerner body form factor: k = 1 + 1.5·(d/L)^1.5 + 7·(d/L)^3."""
    if length <= 0:
        return 1.0
    dl = diameter / length
    return 1.0 + 1.5 * dl ** 1.5 + 7.0 * dl ** 3


def drag_coefficient(torpedo: "Torpedo", speed: float) -> float:
    """Total Cd referenced to frontal area.

    Cd = Cd_friction + Cd_pressure_base
    Cd_friction = (1 + k) · Cf · S_wet / A_ref
    Cd_pressure  ≈ 0.029 · (d/L)^0.5 / sqrt(Cd_friction)   [Hoerner stern drag]
    but we use a simpler constant base-drag term for stability.
    """
    L = torpedo.total_length
    d = torpedo.max_diameter
    a_ref = frontal_area(torpedo)
    s_wet = total_wetted_area(torpedo)

    if speed < 1e-6 or L < 1e-6 or a_ref < 1e-12:
        return CD_BASE

    re = reynolds_number(speed, L)
    cf = friction_coefficient(re)
    k = form_factor(d, L)

    cd_friction = (1.0 + k) * cf * s_wet / a_ref

    # Base drag (blunt stern approximation)
    cd_base = 0.029 * (d / L) ** 0.5 / max(cd_friction ** 0.5, 1e-6)
    cd_base = min(cd_base, 0.15)  # cap it

    return cd_friction + cd_base


# ═══════════════════════════════════════════════════════════════════════════
# Fin lift & induced drag
# ═══════════════════════════════════════════════════════════════════════════

def fin_lift_coefficient(fins: "Fin", alpha: float) -> float:
    """Lift coefficient for N fins using thin-plate / Barrowman theory.

    CL = N · (2π · AR / (AR + 2)) · α
    α in radians, referenced to total fin planform area.
    """
    ar = fins.aspect_ratio
    if ar <= 0:
        return 0.0
    n = fins.count
    cl_alpha = 2.0 * math.pi * ar / (ar + 2.0)
    return n * cl_alpha * alpha


def fin_induced_drag_coefficient(cl: float, fins: "Fin") -> float:
    """Induced drag: CDi = CL² / (π · e · AR)."""
    ar = fins.aspect_ratio
    if ar <= 0:
        return 0.0
    return cl ** 2 / (math.pi * OSWALD_EFFICIENCY * ar)


def fin_forces(fins: "Fin", alpha: float, speed: float,
               rho: float = RHO_WATER):
    """Return (lift_force, induced_drag_force) from fins.

    Forces referenced to fin planform area.
    """
    if speed < 1e-6:
        return 0.0, 0.0
    q = 0.5 * rho * speed ** 2
    s_fin = fins.plan_area
    cl = fin_lift_coefficient(fins, alpha)
    cdi = fin_induced_drag_coefficient(cl, fins)
    lift = cl * q * s_fin
    drag_i = cdi * q * s_fin
    return lift, drag_i


# ═══════════════════════════════════════════════════════════════════════════
# Body (slender-body) lift
# ═══════════════════════════════════════════════════════════════════════════

def body_lift_force(torpedo: "Torpedo", alpha: float, speed: float,
                    rho: float = RHO_WATER) -> float:
    """Slender-body crossflow lift: F = 2·sin(α)·cos(α) · q · A_ref."""
    if speed < 1e-6:
        return 0.0
    q = 0.5 * rho * speed ** 2
    a_ref = frontal_area(torpedo)
    return 2.0 * math.sin(alpha) * math.cos(alpha) * q * a_ref


# ═══════════════════════════════════════════════════════════════════════════
# Basic forces
# ═══════════════════════════════════════════════════════════════════════════

def drag_force(rho: float, speed: float, cd: float, area: float) -> float:
    """F_drag = 0.5 · ρ · v² · Cd · A."""
    return 0.5 * rho * speed ** 2 * cd * area


def buoyancy_force(volume: float, rho: float = RHO_WATER, g: float = G) -> float:
    return volume * rho * g


def gravity_force(mass: float, g: float = G) -> float:
    return mass * g


# ═══════════════════════════════════════════════════════════════════════════
# Moment of inertia  (proper per-component + parallel-axis)
# ═══════════════════════════════════════════════════════════════════════════

def _moi_nose(nose: "NoseCone", cg: float) -> float:
    """MOI of a half-ellipsoid about its own centroid + parallel-axis to cg."""
    m = nose.mass
    r = nose.radius
    L = nose.length
    # MOI of solid half-ellipsoid about its centroid (longitudinal axis approx)
    # I_cm ≈ m · (L²/5 + r²/4) / 2  (approximate)
    i_cm = m * (L ** 2 / 5.0 + r ** 2 / 4.0) / 2.0
    d = nose.centroid_x - cg
    return i_cm + m * d ** 2


def _moi_body(body: "BodyTube", cg: float) -> float:
    """MOI of a cylindrical shell about cg (pitch axis)."""
    m = body.mass
    r = body.radius
    L = body.length
    # Thin-walled cylinder about centre: I = m·(3r² + L²) / 12
    i_cm = m * (3.0 * r ** 2 + L ** 2) / 12.0
    d = body.centroid_x - cg
    return i_cm + m * d ** 2


def _moi_point(mass: float, centroid: float, cg: float) -> float:
    """Point mass MOI about cg."""
    d = centroid - cg
    return mass * d ** 2


def _moi_cad_hull(hull: "CadHull", cg: float) -> float:
    """Pitch MOI of CAD hull approximated as a solid cylinder."""
    m = hull.mass
    r = hull.diameter / 2.0
    L = hull.length
    i_cm = m * (3.0 * r ** 2 + L ** 2) / 12.0
    d = hull.centroid_x - cg
    return i_cm + m * d ** 2


def moment_of_inertia(torpedo: "Torpedo", t: float = 0.0) -> float:
    """Total pitch-axis MOI about the current CoG (parallel-axis theorem)."""
    from torpedo_model import NoseCone, BodyTube, CadHull, Fin, Motor, BallastMass, LaunchSpring
    cg = center_of_gravity(torpedo, t)
    moi = 0.0
    for c in torpedo.components:
        if isinstance(c, NoseCone):
            moi += _moi_nose(c, cg)
        elif isinstance(c, BodyTube):
            moi += _moi_body(c, cg)
        elif isinstance(c, CadHull):
            moi += _moi_cad_hull(c, cg)
        elif isinstance(c, Fin):
            moi += _moi_point(c.mass, c.centroid_x, cg)
        elif isinstance(c, Motor):
            moi += _moi_point(c.mass_at(t), c.centroid_x, cg)
        elif isinstance(c, BallastMass):
            moi += _moi_point(c.mass, c.centroid_x, cg)
        elif isinstance(c, LaunchSpring):
            moi += _moi_point(c.mass, c.centroid_x, cg)
    return max(moi, 1e-12)


# ═══════════════════════════════════════════════════════════════════════════
# Centre of pressure  (Barrowman method)
# ═══════════════════════════════════════════════════════════════════════════

def center_of_pressure(torpedo: "Torpedo", alpha: float = 0.01) -> float:
    """Approximate CP using Barrowman-like normal forces per component.

    The CP is the force-weighted average of each component's CP.
    For small α we compute dCN/dα contributions.
    """
    from torpedo_model import NoseCone, Fin
    a_ref = frontal_area(torpedo)
    if a_ref < 1e-12:
        return 0.0

    cn_list = []  # (CN_alpha, x_cp) pairs

    for c in torpedo.components:
        if isinstance(c, NoseCone):
            # Nose: CN_α = 2 (per reference area), CP at 2/3 of length from tip
            cn_a = 2.0
            x_cp = c.position + 2.0 * c.length / 3.0
            cn_list.append((cn_a, x_cp))
        elif isinstance(c, Fin):
            ar = c.aspect_ratio
            if ar > 0:
                cn_a = c.count * 2.0 * math.pi * ar / (ar + 2.0) * c.plan_area / a_ref
                x_cp = c.cp_x
                cn_list.append((cn_a, x_cp))

    total_cn = sum(cn for cn, _ in cn_list)
    if total_cn < 1e-12:
        return center_of_buoyancy(torpedo)
    return sum(cn * xcp for cn, xcp in cn_list) / total_cn


def static_margin(torpedo: "Torpedo", t: float = 0.0) -> float:
    """Static margin in calibers: (CP − CoG) / diameter.

    Positive = statically stable.
    """
    cp = center_of_pressure(torpedo)
    cg = center_of_gravity(torpedo, t)
    d = torpedo.max_diameter
    return (cp - cg) / d if d > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Added mass  (directional — Lamb k-factors for prolate ellipsoid)
# ═══════════════════════════════════════════════════════════════════════════

def added_mass_axial(torpedo: "Torpedo") -> float:
    """Axial (surge) added mass ≈ k1 · ρ · V.

    k1 for a slender body (L/d >> 1) is small, typically 0.02–0.10.
    We use Lamb's approximation for a prolate spheroid.
    """
    L = torpedo.total_length
    d = torpedo.max_diameter
    if d <= 0 or L <= 0:
        return 0.0
    e = math.sqrt(1.0 - (d / L) ** 2) if L > d else 0.0
    if e < 1e-6:
        alpha0 = 2.0 / 3.0
    else:
        alpha0 = (2.0 * (1.0 - e ** 2) / e ** 3) * (0.5 * math.log((1 + e) / (1 - e)) - e)
    k1 = alpha0 / (2.0 - alpha0)
    return k1 * RHO_WATER * total_volume(torpedo)


def added_mass_lateral(torpedo: "Torpedo") -> float:
    """Lateral (heave/sway) added mass ≈ k2 · ρ · V.

    k2 for slender bodies is much larger (0.5–1.0).
    """
    L = torpedo.total_length
    d = torpedo.max_diameter
    if d <= 0 or L <= 0:
        return 0.0
    e = math.sqrt(1.0 - (d / L) ** 2) if L > d else 0.0
    if e < 1e-6:
        beta0 = 2.0 / 3.0
    else:
        beta0 = (1.0 / e ** 2) - ((1.0 - e ** 2) / (2.0 * e ** 3)) * math.log((1 + e) / (1 - e))
    k2 = beta0 / (2.0 - beta0)
    return k2 * RHO_WATER * total_volume(torpedo)


# ═══════════════════════════════════════════════════════════════════════════
# Pitch damping
# ═══════════════════════════════════════════════════════════════════════════

def pitch_damping_moment(torpedo: "Torpedo", omega: float, speed: float,
                         t: float = 0.0, rho: float = RHO_WATER) -> float:
    """Hydrodynamic pitch damping torque: T = −Cmq · (ρ/2) · V · L² · A_ref · ω.

    Cmq is estimated from fin CLα and moment arm.
    """
    if speed < 1e-6:
        return 0.0
    from torpedo_model import Fin
    L = torpedo.total_length
    a_ref = frontal_area(torpedo)
    cg = center_of_gravity(torpedo, t)

    # Contribution from fins
    cmq = 0.0
    for c in torpedo.components:
        if isinstance(c, Fin):
            ar = c.aspect_ratio
            if ar > 0:
                cl_alpha = 2.0 * math.pi * ar / (ar + 2.0)
                arm = c.cp_x - cg
                # Cmq contribution: −CL_α · (arm/L)² per fin
                cmq_fin = -cl_alpha * c.count * (arm / L) ** 2 * c.plan_area / a_ref
                cmq += cmq_fin

    # Add a small body damping term
    cmq -= 0.5 * (torpedo.max_diameter / L) ** 2

    q = 0.5 * rho * speed
    return cmq * q * L ** 2 * a_ref * omega
