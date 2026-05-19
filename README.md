# OpenTorpedo

Physics-based design simulation and grid optimization for a **Teknofest Unmanned Underwater Systems** competition torpedo. A fixed **STEP hull** defines external geometry; tunable parameters are **PLA infill**, **ballast**, and **four identical parallel compression springs**.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/efeerdogmus0/opentorpedo/blob/main/notebooks/teknofest_colab.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

| Layer | Module | Role |
|-------|--------|------|
| Geometry | `cad_import.py` | STEP bounding box → length, diameter, volume, wetted area |
| Components | `torpedo_model.py` | `CadHull`, `BallastMass`, `LaunchSpring` (×4) |
| Hydrostatics | `physics_engine.py` | Mass, CoG, buoyancy, drag, lift (optional fins) |
| Dynamics | `simulator.py` | 3-DOF trajectory (`RK45`) |
| Search | `teknofest/grid_search.py` | Constrained grid over design vector |
| Feasibility | `teknofest/spring_feasibility.py` | Manufacturability rejection filter |

**Optimization objective:** maximize simulated peak speed  
\(\displaystyle v_{\max} = \max_t \|\mathbf{v}(t)\|\)  
subject to \(m_{\text{total}} \le 0.5\,\text{kg}\) and spring feasibility constraints.

---

## Technical model

### Coordinate system

- Body axis \(x\): nose → tail (meters, from STEP export mm ÷ 1000).
- Depth \(z\): positive downward (launch from `launch_depth` below the free surface).
- State vector: \(\mathbf{y} = [x,\, z,\, \theta,\, v_x,\, v_z,\, \omega]^\top\).

### CAD hull and mass

Hull dimensions come from the axis-aligned bounding box of `CARTESIAN_POINT` entities in the STEP file. Displacement volume and wetted area use a **cylinder + ellipsoidal nose** surrogate:

\[
V_{\text{nose}} = \frac{2}{3}\pi r^2 L_n,\quad
V_{\text{cyl}} = \pi r^2 L_c,\quad
V = V_{\text{nose}} + V_{\text{cyl}}
\]

Printed hull mass (PLA, tunable infill \(\phi\)):

\[
m_{\text{hull}} = \rho_{\text{PLA}}\,\phi\,V
\qquad (\rho_{\text{PLA}} = 1240\,\text{kg/m}^3)
\]

### Center of gravity

Point masses (ballast, springs) and distributed hull mass:

\[
x_{\text{CoG}} = \frac{\sum_i m_i\, x_i}{\sum_i m_i}
\]

Ballast is a scalar mass \(m_b\) at position \(x_b\) from the nose.

### Total mass

\[
m_{\text{total}} = m_{\text{hull}} + m_b + N_s\, m_{\text{spring,wire}}
\qquad (N_s = 4)
\]

Spring wire mass per spring (steel, \(\rho = 7850\,\text{kg/m}^3\)):

\[
m_{\text{spring,wire}} \approx \rho \cdot \frac{\pi d^2}{4} \cdot (n \pi D)
\]

where \(d\) = wire diameter, \(D\) = mean coil diameter, \(n\) = active coils.

---

### Launch springs (4× parallel, identical)

Each spring is a cylindrical compression spring. Stiffness (one spring, shear modulus \(G \approx 79\,\text{GPa}\)):

\[
k_1 = \frac{G\, d^4}{8\, D^3\, n}
\]

Parallel identical springs with common deflection \(\delta\):

\[
k_{\text{tot}} = N_s\, k_1,\qquad
F_{\text{tot}} = k_{\text{tot}}\,\delta,\qquad
F_1 = k_1\,\delta
\]

Usable stroke is capped by solid height \(h_s \approx n\,d\) and free length \(L_0\):

\[
\delta = \min\bigl(\delta_{\text{set}},\; L_0 - h_s\bigr),\qquad
\delta_{\text{set}} \le 0.45\,L_0 \;\text{(feasibility)}
\]

Elastic energy at release:

\[
E = N_s \cdot \tfrac{1}{2}\, k_1\, \delta^2
\]

Ideal velocity increment applied at \(t=0\) (lumped mass, axial added mass \(m_{a,x}\)):

\[
\Delta v = \sqrt{\frac{2E}{m_0 + m_{a,x}}}
\]

Initial speed in simulation:

\[
v_0 = v_{\text{init}} + \Delta v
\]

#### Wahl shear stress (feasibility, per spring)

Spring index \(C = D/d\). Wahl factor:

\[
K_w = \frac{4C-1}{4C-2} + \frac{0.615}{C}
\]

Peak shear stress:

\[
\tau = K_w \cdot \frac{8 F_1 D}{\pi d^3}
\qquad (\tau \le 650\,\text{MPa in search filter})
\]

---

### Hydrodynamics (`physics_engine.py`)

Constants: \(\rho = 1000\,\text{kg/m}^3\), \(\nu = 10^{-6}\,\text{m}^2/\text{s}\), \(g = 9.81\,\text{m/s}^2\).

**Buoyancy / weight**

\[
F_b = \rho g V,\qquad F_g = m\,g
\]

**Drag** (reference area \(A_{\text{ref}} = \pi r^2\))

\[
F_d = \tfrac{1}{2}\rho C_d(v)\, v^2\, A_{\text{ref}}
\]

\(C_d\) combines ITTC-1957 skin friction with Hoerner form factor and a base-pressure term:

\[
C_f = \frac{0.075}{(\log_{10} Re - 2)^2},\quad
Re = \frac{v L}{\nu}
\]

\[
k = 1 + 1.5\left(\frac{d}{L}\right)^{1.5} + 7\left(\frac{d}{L}\right)^3
\]

\[
C_{d,\text{friction}} = (1+k)\, C_f\, \frac{S_{\text{wet}}}{A_{\text{ref}}}
\]

**Slender-body lift** (angle of attack \(\alpha\))

\[
F_{L,\text{body}} = 2\sin\alpha\cos\alpha \cdot \tfrac{1}{2}\rho v^2\, A_{\text{ref}}
\]

(Fin lift/drag included when fin components exist; Teknofest CAD preset is typically finless.)

**Added mass** (Lamb factors on hull) increases effective inertia in surge and heave; see `added_mass_axial` / `added_mass_lateral` in code.

---

### Trajectory integration (`simulator.py`)

Equations of motion in the inertial frame with pitch \(\theta\); forces projected from body/water axes. Integrated with `scipy.integrate.solve_ivp` (`RK45`, `max_step = 0.01` s).

Terminal events:

- Water surface crossing (\(z \to 0\) from below).
- Maximum depth limit.

The metric reported to the optimizer is \(\max_t v(t)\) over the simulated interval (default 8 s, launch angle 5°, launch depth 0.5 m).

---

## Design variables and constraints

### Optimized parameters

| Symbol | Parameter | Typical bounds |
|--------|-----------|----------------|
| \(\phi\) | PLA infill | 0.10 – 0.20 |
| \(m_b\) | Ballast mass | 0 – 0.15 kg |
| \(x_b\) | Ballast position | 0.06 – 0.14 m |
| \(d\) | Wire diameter | 1.0 – 2.0 mm |
| \(D\) | Mean coil diameter | 10 – 16 mm |
| \(n\) | Active coils | 6 – 8 |
| \(L_0\) | Free length | 50 – 60 mm |
| \(\delta\) | Compression | 18 – 36 mm |

### Competition / model limits

| Constraint | Value |
|------------|--------|
| \(m_{\text{total}}\) | ≤ 500 g |
| \(d\) | ≤ 2 mm |
| \(D\) | ≤ 16 mm |
| \(L_0\) | ≤ 60 mm |
| \(N_s\) | 4 (fixed) |

### Manufacturability filter (`spring_feasibility.py`)

| Check | Limit |
|-------|--------|
| Spring index \(C = D/d\) | 4 – 10 |
| \(\delta / L_0\) | ≤ 45% |
| Solid-height margin | \(L_0 - \delta \ge 1.15\, n d\) |
| \(F_{\text{tot}}\) | ≤ 520 N |
| \(F_1\) | ≤ 150 N |
| \(\tau\) (Wahl) | ≤ 650 MPa |
| \(\Delta v\) | ≤ 9 m/s |
| \(L_0 / D\) | ≤ 4.5 |

Grid points that fail any check are discarded before simulation.

---

## Grid search presets

| Preset | Combinations | Typical Colab runtime | Use case |
|--------|--------------|----------------------|----------|
| `quick` | 96 | ~2 min | Smoke test |
| `fast` | 128 | ~3 min | Fast local / Colab |
| `medium` | 2,592 | ~10 min | Moderate coverage |
| **`standard`** | **5,184** | **~15–20 min** | **Recommended** |
| `full` | 18,432 | ~45–90 min | Maximum coverage |

```bash
python -m teknofest.grid_search --preset standard
```

Output: `configs/teknofest_optimized.json` (geometry, masses, spring forces, simulated \(v_{\max}\)).

---

## Quick start (Google Colab)

1. Open [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) in Colab (**Runtime → Run all**).
2. Cell 1 clones this repository into `/content/opentorpedo` (resets cwd to `/content` before clone to avoid Colab path errors on re-run).
3. Cell 3: `PRESET = "standard"` by default.
4. Cell 4 downloads `teknofest_optimized.json`.

If clone fails with `getcwd` errors: **Runtime → Restart session**, then run all cells again.

---

## Local installation

```bash
git clone https://github.com/efeerdogmus0/opentorpedo.git
cd opentorpedo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m teknofest.grid_search --preset fast
```

Desktop UI (PyQt6):

```bash
pip install -r requirements-gui.txt
python -m teknofest.main
```

---

## Example output

```json
{
  "max_speed_m_s": 5.79,
  "total_mass_g": 278.2,
  "cog_cm": 8.69,
  "ballast": { "mass_g": 0.0, "position_cm": 8.0 },
  "spring": {
    "parallel_count": 4,
    "wire_diameter_mm": 2.0,
    "coil_diameter_mm": 16.0,
    "active_coils": 8,
    "free_length_mm": 50.0,
    "compression_mm": 22.0,
    "force_total_N": 424.3,
    "force_per_spring_N": 106.1,
    "compression_ratio_percent": 44.0,
    "spring_index_D_over_d": 8.0,
    "delta_v_m_s": 5.79
  }
}
```

Simulation values are **design recommendations** only; validate with pool tests and official rules.

---

## Repository layout

```
opentorpedo/
├── TORPIDO*.stp
├── cad_import.py
├── torpedo_model.py
├── physics_engine.py
├── simulator.py
├── optimizer.py
├── teknofest/
│   ├── grid_search.py
│   ├── preset.py
│   ├── spring_limits.py
│   ├── spring_feasibility.py
│   └── main.py
├── notebooks/teknofest_colab.ipynb
└── configs/teknofest_optimized.json
```

---

## CLI reference

| Command | Description |
|---------|-------------|
| `python -m teknofest.grid_search --preset standard` | Recommended Colab-equivalent search |
| `python -m teknofest.grid_search --preset full` | Widest search |
| `python -m teknofest.run_fast_opt` | Alias for `--preset fast` |
| `python -m teknofest.find_best` | Alias for `--preset standard` |
| `python scripts/make_colab_zip.py` | Offline Colab bundle → `dist/` |

---

## Development

The **PyQt desktop UI** (`teknofest/ui.py`, `ui_components.py`, `ui_theme.py`) and parts of the tooling were developed with assistance from **[Cursor](https://cursor.com)**. Physics, spring models, feasibility filters, and the Colab pipeline were implemented and reviewed in the same environment.

## Contributing

Issues and pull requests: [github.com/efeerdogmus0/opentorpedo/issues](https://github.com/efeerdogmus0/opentorpedo/issues)

## License

[MIT](LICENSE) — Copyright (c) 2026 Efe Erdoğmuş

## Disclaimer

This software is for education and design support. Competition rules, safety, and in-water performance must be verified against **official Teknofest documentation** and field testing. No warranty is provided for manufacturing or competition results.
