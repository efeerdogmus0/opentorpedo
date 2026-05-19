"""
cad_import.py — Extract torpedo geometry from STEP/IGES CAD exports.

Uses axis-aligned bounding boxes from STEP CARTESIAN_POINT entities (mm → m).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CadGeometry:
    """Fixed hull dimensions derived from a CAD file (metres)."""
    source_file: str
    length: float           # primary axis (nose → tail)
    max_diameter: float     # max cross-section
    width: float
    height: float
    volume: float           # displaced volume estimate (m³)
    wetted_area: float      # approximate wetted area (m²)
    hull_mass: float        # fixed shell mass (kg), excluding tunable ballast

    @property
    def radius(self) -> float:
        return self.max_diameter / 2.0


def _bbox_from_step(path: Path) -> tuple[tuple[float, float], ...]:
    pts: list[tuple[float, float, float]] = []
    text = path.read_text(errors="ignore")
    pat = re.compile(
        r"CARTESIAN_POINT\([^)]*\(([^)]+)\)\)",
        re.IGNORECASE,
    )
    for m in pat.finditer(text):
        parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
        if len(parts) >= 3:
            try:
                pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                continue
    if not pts:
        raise ValueError(f"No CARTESIAN_POINT data found in {path.name}")
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


_GEOMETRY_CACHE: dict[str, CadGeometry] = {}


def _estimate_volume_and_wetted(length_m: float, diameter_m: float) -> tuple[float, float]:
    """Cylinder + ellipsoidal nose approximation for displacement and wetted area."""
    r = diameter_m / 2.0
    nose_len = min(length_m * 0.25, length_m)
    cyl_len = max(length_m - nose_len, 1e-6)
    vol_nose = (2.0 / 3.0) * math.pi * r ** 2 * nose_len
    vol_cyl = math.pi * r ** 2 * cyl_len
    volume = vol_nose + vol_cyl
    area_nose = 2.0 * math.pi * r * nose_len * 0.85
    area_cyl = math.pi * diameter_m * cyl_len
    wetted = area_nose + area_cyl
    return volume, wetted


def load_cad_geometry(
    path: str | Path,
    *,
    hull_mass: float = 0.15,
    length_axis: str = "x",
) -> CadGeometry:
    """Load geometry from STEP (.stp/.step). Falls back to sibling STEP if only IGS given."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    cache_key = f"{path.resolve()}:{length_axis.lower()}"
    if cache_key in _GEOMETRY_CACHE:
        return _GEOMETRY_CACHE[cache_key]

    step_path = path
    if path.suffix.lower() in (".igs", ".iges"):
        sibling = path.with_suffix(".stp")
        if not sibling.exists():
            sibling = path.with_name(path.stem + ".step")
        if sibling.exists():
            step_path = sibling
        else:
            raise ValueError(
                f"IGES alone is not parsed reliably; place a .stp next to {path.name}"
            )

    if step_path.suffix.lower() not in (".stp", ".step"):
        raise ValueError(f"Unsupported CAD format: {step_path.suffix}")

    (x0, x1), (y0, y1), (z0, z1) = _bbox_from_step(step_path)
    # NX export is in millimetres
    sx, sy, sz = (x1 - x0) / 1000.0, (y1 - y0) / 1000.0, (z1 - z0) / 1000.0

    if length_axis.lower() == "x":
        length, width, height = sx, sy, sz
    elif length_axis.lower() == "y":
        length, width, height = sy, sx, sz
    else:
        length, width, height = sz, sx, sy

    length = max(length, 1e-4)
    max_diameter = max(width, height, 1e-4)
    volume, wetted = _estimate_volume_and_wetted(length, max_diameter)

    geom = CadGeometry(
        source_file=str(path.resolve()),
        length=length,
        max_diameter=max_diameter,
        width=width,
        height=height,
        volume=volume,
        wetted_area=wetted,
        hull_mass=hull_mass,
    )
    _GEOMETRY_CACHE[cache_key] = geom
    return geom


def default_teknofest_cad_path(base_dir: str | Path | None = None) -> Path:
    """Return the bundled Teknofest torpedo STEP file path."""
    base = Path(base_dir or Path(__file__).resolve().parent)
    candidates = list(base.glob("TORPIDO*.stp")) + list(base.glob("TORPIDO*.step"))
    if not candidates:
        raise FileNotFoundError(
            "Teknofest torpedo STEP not found. Add TORPIDO*.stp to the project folder."
        )
    return candidates[0]
