"""
simulator.py — Enhanced 3-DOF underwater torpedo trajectory solver.

State vector: [x, z, θ, vx, vz, ω]
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy.integrate import solve_ivp

import physics_engine as pe

if TYPE_CHECKING:
    from torpedo_model import Torpedo, Motor, Fin


@dataclass
class SimulationResult:
    """Output arrays from a simulation run."""
    t: np.ndarray
    x: np.ndarray
    z: np.ndarray
    theta: np.ndarray
    vx: np.ndarray
    vz: np.ndarray
    omega: np.ndarray
    speed: np.ndarray
    alpha_deg: np.ndarray

    @property
    def depth(self) -> np.ndarray:
        """Alias for z (positive downward)."""
        return self.z


@dataclass
class _TorpedoConstants:
    """Pre-computed values that don't change during the sim (except mass for motor)."""
    m0: float
    vol: float
    a_ref: float
    L: float
    d: float
    s_wet: float
    has_motor: bool
    motor_thrust: float
    motor_burn_time: float
    motor_mass_rate: float
    has_fins: bool
    fin_ar: float
    fin_count: int
    fin_plan_area: float
    fin_cp_x: float
    m_add_axial: float
    m_add_lateral: float
    moi0: float
    cog0: float


def _precompute(torpedo: "Torpedo") -> _TorpedoConstants:
    from torpedo_model import Motor, Fin

    m0 = pe.total_mass(torpedo, t=0.0)
    vol = pe.total_volume(torpedo)
    a_ref = pe.frontal_area(torpedo)
    L = torpedo.total_length
    d = torpedo.max_diameter
    s_wet = pe.total_wetted_area(torpedo)

    motor = torpedo.motor
    has_motor = motor is not None
    motor_thrust = motor.thrust if motor else 0.0
    motor_burn_time = motor.burn_time if motor else 0.0
    motor_mass_rate = (
        (motor.mass - motor.dry_mass) / motor.burn_time
        if motor and motor.burn_time > 0
        else 0.0
    )

    fins = torpedo.fins
    has_fins = fins is not None
    fin_ar = fins.aspect_ratio if fins else 0.0
    fin_count = fins.count if fins else 0
    fin_plan_area = fins.plan_area if fins else 0.0
    fin_cp_x = fins.cp_x if fins else 0.0

    return _TorpedoConstants(
        m0=m0,
        vol=vol,
        a_ref=a_ref,
        L=L,
        d=d,
        s_wet=s_wet,
        has_motor=has_motor,
        motor_thrust=motor_thrust,
        motor_burn_time=motor_burn_time,
        motor_mass_rate=motor_mass_rate,
        has_fins=has_fins,
        fin_ar=fin_ar,
        fin_count=fin_count,
        fin_plan_area=fin_plan_area,
        fin_cp_x=fin_cp_x,
        m_add_axial=pe.added_mass_axial(torpedo),
        m_add_lateral=pe.added_mass_lateral(torpedo),
        moi0=pe.moment_of_inertia(torpedo, t=0.0),
        cog0=pe.center_of_gravity(torpedo, t=0.0),
    )


def _derivatives(
    t: float,
    y: np.ndarray,
    tc: _TorpedoConstants,
    torpedo: "Torpedo",
    cd_override: float | None,
) -> list[float]:
    x, z, theta, vx, vz, omega = y
    speed = math.sqrt(vx * vx + vz * vz)

    if tc.has_motor and t < tc.motor_burn_time:
        m_curr = max(tc.m0 - tc.motor_mass_rate * t, 1e-6)
    else:
        m_curr = max(tc.m0 - (tc.motor_mass_rate * tc.motor_burn_time if tc.has_motor else 0.0), 1e-6)

    f_grav = pe.gravity_force(m_curr)
    f_buoy = pe.buoyancy_force(tc.vol)

    alpha = theta - math.atan2(vz, vx) if speed > 1e-6 else 0.0

    if cd_override is not None:
        cd = cd_override
    else:
        cd = pe.drag_coefficient(torpedo, speed)

    f_drag = pe.drag_force(pe.RHO_WATER, speed, cd, tc.a_ref) if speed > 1e-6 else 0.0

    f_lift_body = pe.body_lift_force(torpedo, alpha, speed) if speed > 1e-6 else 0.0
    f_lift_fin = 0.0
    f_drag_induced = 0.0
    if tc.has_fins and speed > 1e-6:
        fins = torpedo.fins
        assert fins is not None
        f_lift_fin, f_drag_induced = pe.fin_forces(fins, alpha, speed)

    f_thrust = tc.motor_thrust if tc.has_motor and t < tc.motor_burn_time else 0.0

    # Forces in inertial frame (x forward, z down)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    f_net_x = (
        f_thrust * cos_t
        - f_drag * (vx / speed if speed > 1e-6 else 1.0)
        + (f_lift_body + f_lift_fin) * (-sin_t)
    )
    f_net_z = (
        f_thrust * sin_t
        + f_buoy
        - f_grav
        - f_drag * (vz / speed if speed > 1e-6 else 0.0)
        + (f_lift_body + f_lift_fin) * cos_t
        - f_drag_induced * (vz / speed if speed > 1e-6 else 0.0)
    )

    m_eff_x = m_curr + tc.m_add_axial
    m_eff_z = m_curr + tc.m_add_lateral
    ax = f_net_x / m_eff_x
    az = f_net_z / m_eff_z

    moi = max(pe.moment_of_inertia(torpedo, t), 1e-12)
    t_damp = pe.pitch_damping_moment(torpedo, omega, speed, t)
    alpha_moment = (f_lift_body + f_lift_fin) * (tc.fin_cp_x - tc.cog0) if tc.has_fins else 0.0
    alpha_dot = (alpha_moment + t_damp) / moi

    return [vx, vz, omega, ax, az, alpha_dot]


def _surface_event(t: float, y: np.ndarray, *args) -> float:
    if t > 0.1:
        return y[1]
    return 1.0


_surface_event.terminal = True
_surface_event.direction = -1


def _ground_event_factory(max_depth: float):
    def _ground(t: float, y: np.ndarray, *args) -> float:
        return max_depth - y[1]

    _ground.terminal = True
    _ground.direction = -1
    return _ground


def run_simulation(
    torpedo: "Torpedo",
    initial_velocity: float = 5.0,
    launch_angle_deg: float = 10.0,
    spring_force: float = 0.0,
    spring_velocity_boost: float | None = None,
    duration: float = 5.0,
    cd_override: float | None = None,
    max_depth: float = 50.0,
    launch_depth: float = 0.5,
) -> SimulationResult:
    """Run enhanced 3-DOF trajectory simulation."""
    tc = _precompute(torpedo)
    angle_rad = math.radians(launch_angle_deg)
    m_eff_fwd = tc.m0 + tc.m_add_axial

    if spring_velocity_boost is not None:
        v_boost = spring_velocity_boost
    elif m_eff_fwd > 0:
        v_boost = spring_force / m_eff_fwd
    else:
        v_boost = 0.0

    v0 = initial_velocity + v_boost
    vx0 = v0 * math.cos(angle_rad)
    vz0 = v0 * math.sin(angle_rad)
    y0 = [0.0, launch_depth, -angle_rad, vx0, vz0, 0.0]

    events = [_surface_event, _ground_event_factory(max_depth)]

    sol = solve_ivp(
        lambda t, y: _derivatives(t, y, tc, torpedo, cd_override),
        (0.0, duration),
        y0,
        method="RK45",
        max_step=0.01,
        args=(),
        events=events,
        dense_output=True,
    )

    t_arr = sol.t
    y_arr = sol.y
    speed = np.sqrt(y_arr[3] ** 2 + y_arr[4] ** 2)
    alpha = y_arr[2] - np.arctan2(y_arr[4], y_arr[3])
    alpha_deg = np.degrees(alpha)

    return SimulationResult(
        t=t_arr,
        x=y_arr[0],
        z=y_arr[1],
        theta=y_arr[2],
        vx=y_arr[3],
        vz=y_arr[4],
        omega=y_arr[5],
        speed=speed,
        alpha_deg=alpha_deg,
    )
