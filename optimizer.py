"""
optimizer.py — Parameter optimization for torpedo design.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from scipy.optimize import minimize

import physics_engine as pe
from simulator import SimulationResult, run_simulation
from torpedo_model import Torpedo


class ObjectiveGoal(Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ConstraintOp(Enum):
    GEQ = ">="
    LEQ = "<="


@dataclass
class DesignVariable:
    """A parameter to optimise."""
    component_index: int
    attribute: str
    lower: float
    upper: float
    label: str = ""
    scope: str = "component"

    def __post_init__(self):
        if not self.label:
            if self.scope == "sim_params":
                self.label = f"sim.{self.attribute}"
            else:
                self.label = f"comp[{self.component_index}].{self.attribute}"


@dataclass
class Constraint:
    """A constraint on a simulation/physics metric."""
    metric: str
    op: ConstraintOp
    limit: float
    label: str = ""


@dataclass
class OptimizationResult:
    success: bool
    message: str
    initial_params: Dict[str, float]
    final_params: Dict[str, float]
    initial_value: float
    final_value: float
    n_iterations: int
    n_func_evals: int


def _run_sim(torpedo: Torpedo, sim_params: dict) -> SimulationResult:
    v_boost = sim_params.get("spring_velocity_boost")
    spring_force = sim_params.get("spring_force", 0.0)
    spring = torpedo.launch_spring

    if v_boost is None and spring is not None:
        m_launch = pe.total_mass(torpedo) + pe.added_mass_axial(torpedo)
        v_boost = spring.launch_velocity_boost(m_launch)
        spring_force = 0.0

    return run_simulation(
        torpedo,
        initial_velocity=sim_params.get("velocity", 0.0),
        launch_angle_deg=sim_params.get("angle", 5.0),
        spring_force=spring_force,
        spring_velocity_boost=v_boost,
        duration=sim_params.get("duration", 5.0),
        cd_override=sim_params.get("cd_override"),
        max_depth=sim_params.get("max_depth", 50.0),
        launch_depth=sim_params.get("launch_depth", 0.5),
    )


def metric_total_mass(torpedo: Torpedo, sim_params: dict) -> float:
    return pe.total_mass(torpedo)


def metric_total_volume(torpedo: Torpedo, sim_params: dict) -> float:
    return pe.total_volume(torpedo)


def metric_final_speed(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(r.speed[-1])


def metric_max_speed(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(np.max(r.speed))


def metric_max_depth(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(np.max(r.z))


def metric_range(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(r.x[-1])


def metric_static_margin(torpedo: Torpedo, sim_params: dict) -> float:
    return pe.static_margin(torpedo)


def metric_buoyancy_ratio(torpedo: Torpedo, sim_params: dict) -> float:
    m = pe.total_mass(torpedo)
    vol = pe.total_volume(torpedo)
    if m <= 0:
        return 0.0
    return pe.buoyancy_force(vol) / pe.gravity_force(m)


def metric_min_speed(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(np.min(r.speed))


def metric_avg_speed(torpedo: Torpedo, sim_params: dict) -> float:
    r = _run_sim(torpedo, sim_params)
    return float(np.mean(r.speed))


def metric_launch_accel(torpedo: Torpedo, sim_params: dict) -> float:
    spring = torpedo.launch_spring
    if spring is None:
        return 0.0
    return spring.launch_acceleration(pe.total_mass(torpedo))


METRIC_FUNCTIONS: Dict[str, Callable[[Torpedo, dict], float]] = {
    "Total Mass (kg)": metric_total_mass,
    "Total Volume (m³)": metric_total_volume,
    "Final Speed (m/s)": metric_final_speed,
    "Max Speed (m/s)": metric_max_speed,
    "Min Speed (m/s)": metric_min_speed,
    "Avg Speed (m/s)": metric_avg_speed,
    "Max Depth (m)": metric_max_depth,
    "Range (m)": metric_range,
    "Static Margin (cal)": metric_static_margin,
    "Buoyancy Ratio": metric_buoyancy_ratio,
    "Launch accel (m/s²)": metric_launch_accel,
}


def run_optimization(
    torpedo: Torpedo,
    sim_params: dict,
    objective_metric: str,
    goal: ObjectiveGoal,
    design_vars: List[DesignVariable],
    constraints: List[Constraint],
    callback: Optional[Callable[[int, float], None]] = None,
    maxiter: int = 200,
    maxfun: int | None = None,
) -> OptimizationResult:
    """Run SLSQP optimization on the torpedo design."""
    if objective_metric not in METRIC_FUNCTIONS:
        raise ValueError(f"Unknown metric: {objective_metric}")
    obj_fn = METRIC_FUNCTIONS[objective_metric]
    sign = 1.0 if goal == ObjectiveGoal.MINIMIZE else -1.0
    base_sim = dict(sim_params)

    initial_params: Dict[str, float] = {}
    x0: List[float] = []
    bounds: List[tuple[float, float]] = []
    for dv in design_vars:
        if dv.scope == "sim_params":
            val = base_sim.get(dv.attribute, 0.0)
        else:
            val = getattr(torpedo.components[dv.component_index], dv.attribute)
        initial_params[dv.label] = float(val)
        x0.append(float(val))
        bounds.append((dv.lower, dv.upper))

    x0_arr = np.array(x0, dtype=float)
    initial_obj = obj_fn(torpedo, base_sim)
    iter_count = [0]

    def _apply_params(x: np.ndarray, torp: Torpedo, sim: dict) -> None:
        for i, dv in enumerate(design_vars):
            if dv.scope == "sim_params":
                sim[dv.attribute] = float(x[i])
            else:
                comp = torp.components[dv.component_index]
                setattr(comp, dv.attribute, float(x[i]))
        spring = torp.launch_spring
        if spring is not None:
            try:
                from teknofest.spring_limits import (
                    SPRING_MAX_COIL_DIAMETER_M,
                    SPRING_MAX_FREE_LENGTH_M,
                    SPRING_MAX_WIRE_DIAMETER_M,
                )

                spring.clamp_to_limits(
                    max_coil_diameter=SPRING_MAX_COIL_DIAMETER_M,
                    max_free_length=SPRING_MAX_FREE_LENGTH_M,
                    max_wire_diameter=SPRING_MAX_WIRE_DIAMETER_M,
                )
                try:
                    from teknofest.spring_feasibility import MAX_COMPRESSION_RATIO

                    max_comp = spring.free_length * MAX_COMPRESSION_RATIO
                    spring.compression = min(spring.compression, max_comp)
                except ImportError:
                    pass
            except ImportError:
                spring.clamp_to_limits()

    def _eval(x: np.ndarray) -> tuple[Torpedo, dict]:
        t_copy = copy.deepcopy(torpedo)
        sim = dict(base_sim)
        _apply_params(x, t_copy, sim)
        return t_copy, sim

    def _objective(x: np.ndarray) -> float:
        t_copy, sim = _eval(x)
        spring = t_copy.launch_spring
        if spring is not None:
            try:
                from teknofest.spring_feasibility import is_producible_spring

                if not is_producible_spring(spring, total_mass_kg=pe.total_mass(t_copy)):
                    return sign * 1e6
            except ImportError:
                pass
        val = obj_fn(t_copy, sim)
        iter_count[0] += 1
        if callback is not None:
            callback(iter_count[0], val)
        return sign * val

    scipy_constraints = []
    for con in constraints:
        if con.metric not in METRIC_FUNCTIONS:
            raise ValueError(f"Unknown constraint metric: {con.metric}")
        cfn = METRIC_FUNCTIONS[con.metric]

        if con.op == ConstraintOp.GEQ:

            def _con_fn(x, _cfn=cfn, _lim=con.limit):
                t_copy, sim = _eval(x)
                return _cfn(t_copy, sim) - _lim

        else:

            def _con_fn(x, _cfn=cfn, _lim=con.limit):
                t_copy, sim = _eval(x)
                return _lim - _cfn(t_copy, sim)

        scipy_constraints.append({"type": "ineq", "fun": _con_fn})

    options: Dict[str, Any] = {"maxiter": maxiter, "ftol": 1e-4, "disp": False}
    if maxfun is not None:
        options["maxfun"] = maxfun

    result = minimize(
        _objective,
        x0_arr,
        method="SLSQP",
        bounds=bounds,
        constraints=scipy_constraints,
        options=options,
    )

    final_params: Dict[str, float] = {}
    t_final, sim_final = _eval(result.x)
    for i, dv in enumerate(design_vars):
        final_params[dv.label] = float(result.x[i])

    final_obj = obj_fn(t_final, sim_final)

    return OptimizationResult(
        success=bool(result.success),
        message=str(result.message),
        initial_params=initial_params,
        final_params=final_params,
        initial_value=float(initial_obj),
        final_value=float(final_obj),
        n_iterations=int(getattr(result, "nit", iter_count[0])),
        n_func_evals=int(getattr(result, "nfev", iter_count[0])),
    )
