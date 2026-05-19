"""Build a Teknofest torpedo model from the bundled CAD file."""

from __future__ import annotations

from pathlib import Path

from cad_import import CadGeometry, default_teknofest_cad_path, load_cad_geometry
from torpedo_model import BallastMass, CadHull, LaunchSpring, Torpedo
from teknofest.materials import DEFAULT_INFILL, PLA_DENSITY, PLA_NAME
from teknofest.spring_limits import (
    LAUNCH_SPRING_COUNT,
    SPRING_MAX_COIL_DIAMETER_M,
    SPRING_MAX_COILS,
    SPRING_MAX_COMPRESSION_M,
    SPRING_MAX_FREE_LENGTH_M,
    SPRING_MIN_COIL_DIAMETER_M,
    SPRING_MIN_COILS,
    SPRING_MIN_COMPRESSION_M,
    SPRING_MIN_FREE_LENGTH_M,
    SPRING_MIN_WIRE_DIAMETER_M,
    SPRING_MAX_WIRE_DIAMETER_M,
)

MAX_TOTAL_MASS_KG = 0.5


def create_teknofest_torpedo(
    cad_path: str | Path | None = None,
    *,
    ballast_mass: float = 0.05,
    ballast_position: float | None = None,
    infill: float = DEFAULT_INFILL,
    density: float = PLA_DENSITY,
    with_spring: bool = True,
) -> tuple[Torpedo, CadGeometry]:
    """Fixed CAD hull (PLA) + ballast + optional launch spring."""
    path = Path(cad_path) if cad_path else default_teknofest_cad_path()
    geom = load_cad_geometry(path)

    hull = CadHull(
        name="Teknofest Torpedo (CAD)",
        length=geom.length,
        diameter=geom.max_diameter,
        volume=geom.volume,
        wetted_area=geom.wetted_area,
        position=0.0,
        cad_source=geom.source_file,
        material=PLA_NAME,
        density=density,
        infill=infill,
    )
    ballast_pos = ballast_position if ballast_position is not None else geom.length * 0.45
    ballast = BallastMass(name="Ballast", mass=ballast_mass, position=ballast_pos)
    components: list = [hull, ballast]

    if with_spring:
        spring = LaunchSpring(
            name=f"Launch spring ×{LAUNCH_SPRING_COUNT}",
            wire_diameter=SPRING_MAX_WIRE_DIAMETER_M,
            coil_diameter=0.014,
            active_coils=8.0,
            free_length=0.050,
            compression=0.022,
            position=geom.length * 0.35,
            count=LAUNCH_SPRING_COUNT,
        )
        spring.clamp_to_limits(
            max_coil_diameter=SPRING_MAX_COIL_DIAMETER_M,
            max_free_length=SPRING_MAX_FREE_LENGTH_M,
            max_wire_diameter=SPRING_MAX_WIRE_DIAMETER_M,
        )
        components.append(spring)

    return Torpedo(components=components), geom


def default_sim_params() -> dict:
    return {
        "velocity": 0.0,
        "angle": 5.0,
        "spring_force": 0.0,
        "duration": 8.0,
        "max_depth": 50.0,
        "launch_depth": 0.5,
    }


def _component_indices(torpedo: Torpedo) -> dict[str, int]:
    return {type(c).__name__: i for i, c in enumerate(torpedo.components)}


def speed_optimization_setup(
    torpedo: Torpedo,
    *,
    max_mass_kg: float = MAX_TOTAL_MASS_KG,
) -> tuple[list[dict], list[dict]]:
    """Design variables + constraints for max speed under mass limit."""
    ix = _component_indices(torpedo)
    hull = torpedo.cad_hull
    L = hull.length if hull else 0.18
    design_vars: list[dict] = []

    if "CadHull" in ix:
        design_vars.append({
            "scope": "component",
            "component_index": ix["CadHull"],
            "attribute": "infill",
            "lower": 0.12,
            "upper": 0.30,
            "label": "Doluluk oranı",
        })

    if "BallastMass" in ix:
        design_vars.extend([
            {
                "scope": "component",
                "component_index": ix["BallastMass"],
                "attribute": "mass",
                "lower": 0.0,
                "upper": 0.25,
                "label": "Balast kütlesi (kg)",
            },
            {
                "scope": "component",
                "component_index": ix["BallastMass"],
                "attribute": "position",
                "lower": 0.02,
                "upper": max(L - 0.02, 0.05),
                "label": "Balast konumu (m)",
            },
        ])

    if "LaunchSpring" in ix:
        design_vars.extend([
            {
                "scope": "component",
                "component_index": ix["LaunchSpring"],
                "attribute": "wire_diameter",
                "lower": SPRING_MIN_WIRE_DIAMETER_M,
                "upper": SPRING_MAX_WIRE_DIAMETER_M,
                "label": "Tel çapı (m)",
            },
            {
                "scope": "component",
                "component_index": ix["LaunchSpring"],
                "attribute": "coil_diameter",
                "lower": SPRING_MIN_COIL_DIAMETER_M,
                "upper": SPRING_MAX_COIL_DIAMETER_M,
                "label": "Yay çapı (m)",
            },
            {
                "scope": "component",
                "component_index": ix["LaunchSpring"],
                "attribute": "active_coils",
                "lower": SPRING_MIN_COILS,
                "upper": SPRING_MAX_COILS,
                "label": "Aktif sarım sayısı",
            },
            {
                "scope": "component",
                "component_index": ix["LaunchSpring"],
                "attribute": "free_length",
                "lower": SPRING_MIN_FREE_LENGTH_M,
                "upper": SPRING_MAX_FREE_LENGTH_M,
                "label": "Yay uzunluğu (m)",
            },
            {
                "scope": "component",
                "component_index": ix["LaunchSpring"],
                "attribute": "compression",
                "lower": SPRING_MIN_COMPRESSION_M,
                "upper": SPRING_MAX_COMPRESSION_M,
                "label": "Yay sıkıştırma (m)",
            },
        ])

    constraints = [{
        "metric": "Total Mass (kg)",
        "op": "<=",
        "limit": max_mass_kg,
        "label": f"Toplam kütle ≤ {max_mass_kg * 1000:.0f} g",
    }]

    return design_vars, constraints


def default_design_variables(torpedo: Torpedo) -> list[dict]:
    """Manual tuning subset (wire diameter fixed at 2 mm)."""
    dvars, _ = speed_optimization_setup(torpedo)
    keep = {
        "Balast kütlesi (kg)",
        "Balast konumu (m)",
        "Yay çapı (m)",
        "Yay sıkıştırma (m)",
    }
    return [d for d in dvars if d["label"] in keep]
