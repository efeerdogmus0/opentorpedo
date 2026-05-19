"""
torpedo_model.py — Data model classes for torpedo components.

Each component knows its geometry, mass, volume, and longitudinal
centroid position (distance from the nose tip along the body axis).
Supports JSON serialization via to_dict() / from_dict() class methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NoseCone:
    """Elliptical nose cone (half-ellipsoid of revolution)."""
    name: str = "Nose Cone"
    length: float = 0.05
    diameter: float = 0.04
    density: float = 1200.0
    position: float = 0.0

    @property
    def radius(self) -> float:
        return self.diameter / 2.0

    @property
    def volume(self) -> float:
        """Volume of a half-ellipsoid: (2/3) π r² L."""
        return (2.0 / 3.0) * math.pi * self.radius ** 2 * self.length

    @property
    def mass(self) -> float:
        return self.volume * self.density

    @property
    def centroid_x(self) -> float:
        """Centroid of a half-ellipsoid from the tip = 5L/8."""
        return self.position + 5.0 * self.length / 8.0

    @property
    def wetted_area(self) -> float:
        """Approximate wetted surface area of a half-ellipsoid."""
        return 2.0 * math.pi * self.radius * self.length * 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "NoseCone",
            "name": self.name,
            "length": self.length,
            "diameter": self.diameter,
            "density": self.density,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NoseCone":
        return cls(
            name=d.get("name", "Nose Cone"),
            length=d["length"],
            diameter=d["diameter"],
            density=d.get("density", 1200.0),
            position=d.get("position", 0.0),
        )


@dataclass
class BodyTube:
    """Cylindrical body tube."""
    name: str = "Body Tube"
    length: float = 0.20
    diameter: float = 0.04
    mass: float = 0.10
    position: float = 0.05
    wall_thickness: float = 0.002

    @property
    def radius(self) -> float:
        return self.diameter / 2.0

    @property
    def volume(self) -> float:
        """Volume of a cylinder."""
        return math.pi * self.radius ** 2 * self.length

    @property
    def density(self) -> float:
        vol = self.volume
        return self.mass / vol if vol > 0 else 0.0

    @property
    def centroid_x(self) -> float:
        return self.position + self.length / 2.0

    @property
    def wetted_area(self) -> float:
        """Lateral surface area of a cylinder."""
        return math.pi * self.diameter * self.length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "BodyTube",
            "name": self.name,
            "length": self.length,
            "diameter": self.diameter,
            "mass": self.mass,
            "position": self.position,
            "wall_thickness": self.wall_thickness,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BodyTube":
        return cls(
            name=d.get("name", "Body Tube"),
            length=d["length"],
            diameter=d["diameter"],
            mass=d["mass"],
            position=d.get("position", 0.0),
            wall_thickness=d.get("wall_thickness", 0.002),
        )


@dataclass
class Fin:
    """A set of identical trapezoidal fins."""
    name: str = "Fins"
    count: int = 4
    span: float = 0.015
    root_chord: float = 0.03
    tip_chord: float = 0.015
    thickness: float = 0.002
    density: float = 1200.0
    position: float = 0.0
    sweep_angle: float = 0.0

    @property
    def plan_area(self) -> float:
        """Planform area of one fin (trapezoid)."""
        return 0.5 * (self.root_chord + self.tip_chord) * self.span

    @property
    def aspect_ratio(self) -> float:
        """AR = span² / plan_area (single fin)."""
        pa = self.plan_area
        return self.span ** 2 / pa if pa > 0 else 0.0

    @property
    def mass(self) -> float:
        return self.plan_area * self.thickness * self.density * self.count

    @property
    def volume(self) -> float:
        return 0.0

    @property
    def centroid_x(self) -> float:
        return self.position + self.root_chord / 3.0

    @property
    def cp_x(self) -> float:
        """Approximate centre of pressure of the fins (Barrowman)."""
        return self.position + self.root_chord / 3.0

    @property
    def wetted_area(self) -> float:
        """Both sides of all fins."""
        return 2.0 * self.plan_area * self.count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Fin",
            "name": self.name,
            "count": self.count,
            "span": self.span,
            "root_chord": self.root_chord,
            "tip_chord": self.tip_chord,
            "thickness": self.thickness,
            "density": self.density,
            "position": self.position,
            "sweep_angle": self.sweep_angle,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Fin":
        return cls(
            name=d.get("name", "Fins"),
            count=int(d.get("count", 4)),
            span=d["span"],
            root_chord=d["root_chord"],
            tip_chord=d["tip_chord"],
            thickness=d.get("thickness", 0.002),
            density=d.get("density", 1200.0),
            position=d.get("position", 0.0),
            sweep_angle=d.get("sweep_angle", 0.0),
        )


@dataclass
class CadHull:
    """Fixed hull geometry imported from CAD (STEP). Geometry is not tunable."""
    name: str = "CAD Hull"
    length: float = 0.18
    diameter: float = 0.11
    volume: float = 0.0017
    wetted_area: float = 0.08
    position: float = 0.0
    cad_source: str = ""
    material: str = "PLA"
    density: float = 1240.0
    infill: float = 0.30

    @property
    def hull_mass(self) -> float:
        """Printed mass from CAD volume × PLA density × infill."""
        return self.volume * self.density * self.infill

    @property
    def mass(self) -> float:
        return self.hull_mass

    @property
    def centroid_x(self) -> float:
        return self.position + self.length / 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "CadHull",
            "name": self.name,
            "length": self.length,
            "diameter": self.diameter,
            "volume": self.volume,
            "wetted_area": self.wetted_area,
            "position": self.position,
            "cad_source": self.cad_source,
            "material": self.material,
            "density": self.density,
            "infill": self.infill,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CadHull":
        return cls(
            name=d.get("name", "CAD Hull"),
            length=d["length"],
            diameter=d["diameter"],
            volume=d["volume"],
            wetted_area=d["wetted_area"],
            position=d.get("position", 0.0),
            cad_source=d.get("cad_source", ""),
            material=d.get("material", "PLA"),
            density=d.get("density", 1240.0),
            infill=d.get("infill", 0.30),
        )


@dataclass
class BallastMass:
    """A point-mass ballast inside the torpedo for trimming."""
    name: str = "Ballast"
    mass: float = 0.05
    position: float = 0.03

    @property
    def volume(self) -> float:
        return 0.0

    @property
    def centroid_x(self) -> float:
        return self.position

    @property
    def wetted_area(self) -> float:
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "BallastMass",
            "name": self.name,
            "mass": self.mass,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BallastMass":
        return cls(
            name=d.get("name", "Ballast"),
            mass=d["mass"],
            position=d.get("position", 0.0),
        )


@dataclass
class LaunchSpring:
    """Helical launch spring — geometry maps to k, force, and launch energy."""
    name: str = "Launch spring"
    wire_diameter: float = 0.002
    coil_diameter: float = 0.020
    active_coils: float = 8.0
    free_length: float = 0.080
    compression: float = 0.030
    position: float = 0.04
    shear_modulus: float = 79e9

    @property
    def spring_constant(self) -> float:
        """k = G d^4 / (8 D^3 n)."""
        d, D, n = self.wire_diameter, self.coil_diameter, max(self.active_coils, 1.0)
        if D <= 0 or d <= 0:
            return 0.0
        return self.shear_modulus * d ** 4 / (8.0 * D ** 3 * n)

    @property
    def installed_length(self) -> float:
        """Approximate spring body length (compressed height)."""
        solid = self.wire_diameter * max(self.active_coils, 1.0)
        return max(self.free_length - self.effective_compression, solid)

    @property
    def effective_compression(self) -> float:
        solid = self.wire_diameter * max(self.active_coils, 1.0)
        max_stroke = max(0.0, self.free_length - solid)
        return min(max(self.compression, 0.0), max_stroke)

    def clamp_to_limits(
        self,
        *,
        max_coil_diameter: float = 0.016,
        max_free_length: float = 0.060,
        max_wire_diameter: float = 0.004,
    ) -> None:
        """Clamp geometry to competition spring envelope."""
        self.wire_diameter = min(max(self.wire_diameter, 0.001), max_wire_diameter)
        self.coil_diameter = min(
            max(self.coil_diameter, self.wire_diameter * 2.5),
            max_coil_diameter,
        )
        self.free_length = min(max(self.free_length, 0.02), max_free_length)
        self.active_coils = max(self.active_coils, 1.0)
        max_comp = max(0.0, self.free_length - self.wire_diameter * self.active_coils)
        self.compression = min(max(self.compression, 0.0), max_comp)

    @property
    def launch_force(self) -> float:
        return self.spring_constant * self.effective_compression

    def launch_velocity_boost(self, total_mass: float) -> float:
        """v = sqrt(2E/m), E = 0.5 k x^2."""
        if total_mass <= 0:
            return 0.0
        x = self.effective_compression
        e = 0.5 * self.spring_constant * x * x
        return math.sqrt(2.0 * e / total_mass)

    def launch_acceleration(self, total_mass: float) -> float:
        if total_mass <= 0:
            return 0.0
        return self.launch_force / total_mass

    @property
    def mass(self) -> float:
        """Steel wire mass estimate."""
        rho = 7850.0
        d, D, n = self.wire_diameter, self.coil_diameter, max(self.active_coils, 1.0)
        wire_len = n * math.pi * D
        vol = math.pi * (d / 2.0) ** 2 * wire_len
        return vol * rho

    @property
    def volume(self) -> float:
        return 0.0

    @property
    def centroid_x(self) -> float:
        return self.position

    @property
    def wetted_area(self) -> float:
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "LaunchSpring",
            "name": self.name,
            "wire_diameter": self.wire_diameter,
            "coil_diameter": self.coil_diameter,
            "active_coils": self.active_coils,
            "free_length": self.free_length,
            "compression": self.compression,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LaunchSpring":
        return cls(
            name=d.get("name", "Launch spring"),
            wire_diameter=d["wire_diameter"],
            coil_diameter=d["coil_diameter"],
            active_coils=d.get("active_coils", 8.0),
            free_length=d.get("free_length", 0.08),
            compression=d["compression"],
            position=d.get("position", 0.04),
        )


@dataclass
class Motor:
    """A motor / thruster providing constant thrust over a burn time."""
    name: str = "Motor"
    thrust: float = 10.0
    burn_time: float = 2.0
    mass: float = 0.05
    dry_mass: float = 0.02
    position: float = 0.10

    @property
    def total_mass(self) -> float:
        return self.mass

    def mass_at(self, t: float) -> float:
        """Mass at time t (propellant consumed linearly)."""
        if self.burn_time <= 0 or t >= self.burn_time:
            return self.dry_mass
        frac = t / self.burn_time
        return self.mass - (self.mass - self.dry_mass) * frac

    def thrust_at(self, t: float) -> float:
        """Thrust at time t."""
        return self.thrust if t < self.burn_time else 0.0

    @property
    def volume(self) -> float:
        return 0.0

    @property
    def centroid_x(self) -> float:
        return self.position

    @property
    def wetted_area(self) -> float:
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Motor",
            "name": self.name,
            "thrust": self.thrust,
            "burn_time": self.burn_time,
            "mass": self.mass,
            "dry_mass": self.dry_mass,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Motor":
        return cls(
            name=d.get("name", "Motor"),
            thrust=d["thrust"],
            burn_time=d.get("burn_time", 2.0),
            mass=d["mass"],
            dry_mass=d.get("dry_mass", 0.02),
            position=d.get("position", 0.0),
        )


_COMPONENT_CLASSES = {
    "NoseCone": NoseCone,
    "BodyTube": BodyTube,
    "Fin": Fin,
    "BallastMass": BallastMass,
    "Motor": Motor,
    "CadHull": CadHull,
    "LaunchSpring": LaunchSpring,
}


def component_from_dict(d: Dict[str, Any]):
    """Deserialize any component dict."""
    cls = _COMPONENT_CLASSES.get(d["type"])
    if cls is None:
        raise ValueError(f"Unknown component type: {d.get('type')}")
    return cls.from_dict(d)


@dataclass
class Torpedo:
    """Collection of components that make up a complete torpedo."""
    components: List[Any] = field(default_factory=list)

    @property
    def nose(self) -> Optional[NoseCone]:
        return next((c for c in self.components if isinstance(c, NoseCone)), None)

    @property
    def body(self) -> Optional[BodyTube]:
        return next((c for c in self.components if isinstance(c, BodyTube)), None)

    @property
    def fins(self) -> Optional[Fin]:
        return next((c for c in self.components if isinstance(c, Fin)), None)

    @property
    def motor(self) -> Optional[Motor]:
        return next((c for c in self.components if isinstance(c, Motor)), None)

    @property
    def cad_hull(self) -> Optional[CadHull]:
        return next((c for c in self.components if isinstance(c, CadHull)), None)

    @property
    def launch_spring(self) -> Optional[LaunchSpring]:
        return next((c for c in self.components if isinstance(c, LaunchSpring)), None)

    @property
    def total_length(self) -> float:
        max_rear = 0.0
        for c in self.components:
            if isinstance(c, (NoseCone, BodyTube, CadHull)):
                max_rear = max(max_rear, c.position + c.length)
            elif isinstance(c, Fin):
                max_rear = max(max_rear, c.position + c.root_chord)
            elif isinstance(c, (BallastMass, Motor, LaunchSpring)):
                max_rear = max(max_rear, c.position)
        return max_rear

    @property
    def max_diameter(self) -> float:
        d = 0.0
        for c in self.components:
            if hasattr(c, "diameter"):
                d = max(d, c.diameter)
        return d

    @property
    def total_wetted_area_override(self) -> Optional[float]:
        """If a CAD hull is present, use its measured wetted area."""
        ch = self.cad_hull
        return ch.wetted_area if ch is not None else None

    @property
    def total_wetted_area(self) -> float:
        ov = self.total_wetted_area_override
        if ov is not None:
            return ov
        return sum(c.wetted_area for c in self.components)

    def mass_at(self, t: float = 0.0) -> float:
        """Total mass at time t (accounts for motor burn)."""
        total = 0.0
        for c in self.components:
            if isinstance(c, Motor):
                total += c.mass_at(t)
            else:
                total += c.mass
        return total

    def to_dict(self) -> Dict[str, Any]:
        return {"components": [c.to_dict() for c in self.components]}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Torpedo":
        return cls(components=[component_from_dict(c) for c in d["components"]])


def create_default_torpedo() -> Torpedo:
    """Build the default torpedo described in the spec."""
    nose = NoseCone(name="Nose Cone", length=0.05, diameter=0.04, density=1200)
    body = BodyTube(
        name="Body Tube",
        length=0.2,
        diameter=0.04,
        mass=0.1,
        position=nose.length,
    )
    fins = Fin(
        name="Fins (×4)",
        count=4,
        span=0.015,
        root_chord=0.03,
        tip_chord=0.015,
        thickness=0.002,
        density=1200,
        position=body.position + body.length - 0.03,
    )
    ballast = BallastMass(name="Ballast", mass=0.05, position=0.03)
    return Torpedo(components=[nose, body, fins, ballast])
