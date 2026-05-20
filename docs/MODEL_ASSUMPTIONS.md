# Model assumptions (for project reports)

Use this page when writing the Teknofest technical report. It describes what OpenTorpedo models and what it does not.

## Scope

OpenTorpedo optimizes **PLA infill**, **ballast**, and **four identical parallel launch springs** for a **fixed STEP hull**. External shape does not change during search.

## Geometry

- STEP file → axis-aligned bounding box → length, max diameter.
- Displaced volume and wetted area: cylinder + ellipsoidal nose approximation.
- Printed mass: `PLA density × infill × estimated volume` (not a full shell-thickness FEA mesh).

## Launch system

- Four springs in parallel, same stroke.
- Spring stiffness from standard coil formula (steel shear modulus).
- Release modeled as instantaneous velocity increment from stored elastic energy.
- Launcher friction, guide rails, and water-entry effects are not modeled.

## Underwater motion

- 3 DOF: surge, heave (depth), pitch.
- Constant water properties (fresh water, ~20 °C).
- Drag: ITTC-1957 skin friction + Hoerner-style form factor.
- Buoyancy on full displaced volume; weight on component masses.
- Body lift with moment about buoyancy center; fin forces if fins exist in the model.
- No roll/yaw, no propeller in the default Teknofest preset.

## Optimization

- Objective: maximum simulated speed over a short trajectory.
- Constraint: total mass ≤ 500 g.
- Spring feasibility filter: spring index, max stroke, force limits, Wahl stress, max Δv.
- Results are **comparative** between designs; absolute speed requires calibration against tests.

## Recommended validation

1. Weigh built torpedo and compare to predicted total mass.
2. Measure spring dimensions and bench-test spring force.
3. Short-range pool launch: time-of-flight / distance vs simulation trends.
4. Check static trim and buoyancy in water separately from launch speed.
