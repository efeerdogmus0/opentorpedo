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

$$v_{\max} = \max_t \|\mathbf{v}(t)\|$$

subject to $m_{\mathrm{total}} \le 0.5\ \mathrm{kg}$ and spring feasibility constraints.

> **Math on GitHub:** equations use `$...$` (inline) and `$$...$$` (display). If formulas look like raw LaTeX, open the file on [github.com](https://github.com/efeerdogmus0/opentorpedo) (not a plain-text preview).

---

## Technical model

### Coordinate system

- Body axis $x$: nose → tail (meters; STEP coordinates in mm are divided by 1000).
- Depth $z$: positive downward (launch from `launch_depth` below the free surface).
- State vector:

$$\mathbf{y} = [x,\ z,\ \theta,\ v_x,\ v_z,\ \omega]^\top$$

### CAD hull and mass

Hull dimensions come from the axis-aligned bounding box of `CARTESIAN_POINT` entities in the STEP file. Displacement volume and wetted area use a **cylinder + ellipsoidal nose** surrogate:

$$V_{\mathrm{nose}} = \frac{2}{3}\pi r^2 L_n$$

$$V_{\mathrm{cyl}} = \pi r^2 L_c$$

$$V = V_{\mathrm{nose}} + V_{\mathrm{cyl}}$$

Printed hull mass (PLA, tunable infill $\phi$):

$$m_{\mathrm{hull}} = \rho_{\mathrm{PLA}}\ \phi\ V \qquad (\rho_{\mathrm{PLA}} = 1240\ \mathrm{kg/m^3})$$

### Center of gravity

$$x_{\mathrm{CoG}} = \frac{\sum_i m_i x_i}{\sum_i m_i}$$

Ballast: mass $m_b$ at position $x_b$ from the nose.

### Total mass

$$m_{\mathrm{total}} = m_{\mathrm{hull}} + m_b + N_s m_{\mathrm{sw}} \qquad (N_s = 4)$$

Spring wire mass per spring (steel, $\rho_s = 7850\ \mathrm{kg/m^3}$):

$$m_{\mathrm{sw}} \approx \rho_s \frac{\pi d^2}{4} (n \pi D)$$

Symbols: $d$ wire diameter, $D$ mean coil diameter, $n$ active coils.

---

### Launch springs (4× parallel, identical)

Stiffness of one spring ($G \approx 79\ \mathrm{GPa}$):

$$k_1 = \frac{G d^4}{8 D^3 n}$$

Four parallel springs with common deflection $\delta$:

$$k_{\mathrm{tot}} = N_s k_1$$

$$F_{\mathrm{tot}} = k_{\mathrm{tot}}\ \delta$$

$$F_1 = k_1\ \delta$$

Stroke limit (solid height $h_s \approx n d$, free length $L_0$):

$$\delta = \min(\delta_{\mathrm{set}},\ L_0 - h_s)$$

$$\delta_{\mathrm{set}} \le 0.45 L_0 \quad \text{(feasibility filter)}$$

Stored elastic energy:

$$E = N_s \cdot \frac{1}{2} k_1 \delta^2$$

Launch speed increment ($m_0$ total mass, $m_{a,x}$ axial added mass):

$$\Delta v = \sqrt{\frac{2E}{m_0 + m_{a,x}}}$$

$$v_0 = v_{\mathrm{init}} + \Delta v$$

#### Wahl shear stress (per spring)

Spring index $C = D/d$. Wahl factor:

$$K_w = \frac{4C-1}{4C-2} + \frac{0.615}{C}$$

$$\tau = K_w \frac{8 F_1 D}{\pi d^3} \qquad (\tau \le 650\ \mathrm{MPa\ in\ filter})$$

---

### Hydrodynamics (`physics_engine.py`)

$\rho = 1000\ \mathrm{kg/m^3}$, $\nu = 10^{-6}\ \mathrm{m^2/s}$, $g = 9.81\ \mathrm{m/s^2}$.

**Buoyancy and weight**

$$F_b = \rho g V$$

$$F_g = m g$$

**Drag** ($A_{\mathrm{ref}} = \pi r^2$)

$$F_d = \frac{1}{2} \rho C_d(v) v^2 A_{\mathrm{ref}}$$

Skin friction (ITTC-1957):

$$C_f = \frac{0.075}{(\log_{10} Re - 2)^2}$$

$$Re = \frac{v L}{\nu}$$

Hoerner form factor:

$$k = 1 + 1.5\left(\frac{d}{L}\right)^{1.5} + 7\left(\frac{d}{L}\right)^3$$

$$C_{d,f} = (1+k) C_f \frac{S_{\mathrm{wet}}}{A_{\mathrm{ref}}}$$

**Slender-body lift** (angle of attack $\alpha$)

$$F_{L,b} = 2\sin\alpha\cos\alpha \cdot \frac{1}{2}\rho v^2 A_{\mathrm{ref}}$$

Fin lift/drag is included when fin components exist; the Teknofest CAD preset is usually finless.

**Added mass** (Lamb factors) increases effective inertia in surge and heave (`added_mass_axial`, `added_mass_lateral` in code).

---

### Trajectory integration (`simulator.py`)

Forces are resolved in the inertial frame with pitch $\theta$. Integration: `scipy.integrate.solve_ivp`, method RK45, `max_step = 0.01` s.

Terminal events: free surface ($z \to 0$), maximum depth.

Optimizer metric: $\max_t v(t)$ over the simulated interval (defaults: 8 s duration, 5° launch angle, 0.5 m launch depth).

---

## Design variables and constraints

### Optimized parameters

| Symbol | Parameter | Typical bounds |
|--------|-----------|----------------|
| φ | PLA infill | 0.10 – 0.20 |
| m_b | Ballast mass | 0 – 0.15 kg |
| x_b | Ballast position | 0.06 – 0.14 m |
| d | Wire diameter | 1.0 – 2.0 mm |
| D | Mean coil diameter | 10 – 16 mm |
| n | Active coils | 6 – 8 |
| L₀ | Free length | 50 – 60 mm |
| δ | Compression | 18 – 36 mm |

### Competition / model limits

| Constraint | Value |
|------------|--------|
| m_total | ≤ 500 g |
| d | ≤ 2 mm |
| D | ≤ 16 mm |
| L₀ | ≤ 60 mm |
| N_s | 4 (fixed) |

### Manufacturability filter

| Check | Limit |
|-------|--------|
| Spring index C = D/d | 4 – 10 |
| δ / L₀ | ≤ 45% |
| Solid-height margin | L₀ − δ ≥ 1.15 n d |
| F_tot | ≤ 520 N |
| F₁ | ≤ 150 N |
| τ (Wahl) | ≤ 650 MPa |
| Δv | ≤ 9 m/s |
| L₀ / D | ≤ 4.5 |

Failed grid points are skipped before simulation. Limits are defined in `teknofest/spring_feasibility.py`.

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

Output: `configs/teknofest_optimized.json`

---

## Quick start (Google Colab)

1. Open [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) → **Runtime → Run all**.
2. Cell 1 clones the repo into `/content/opentorpedo`.
3. Cell 3: `PRESET = "standard"`.
4. Cell 4 downloads `teknofest_optimized.json`.

If clone fails: **Runtime → Restart session**, then run all cells again.

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
  "spring": {
    "parallel_count": 4,
    "wire_diameter_mm": 2.0,
    "coil_diameter_mm": 16.0,
    "force_total_N": 424.3,
    "delta_v_m_s": 5.79
  }
}
```

Validate all values with physical tests and official competition rules.

---

## Repository layout

```
opentorpedo/
├── TORPIDO*.stp
├── cad_import.py
├── torpedo_model.py
├── physics_engine.py
├── simulator.py
├── teknofest/
│   ├── grid_search.py
│   ├── spring_feasibility.py
│   └── main.py
├── notebooks/teknofest_colab.ipynb
└── configs/teknofest_optimized.json
```

---

## CLI reference

| Command | Description |
|---------|-------------|
| `python -m teknofest.grid_search --preset standard` | Recommended search |
| `python -m teknofest.grid_search --preset full` | Widest search |
| `python -m teknofest.run_fast_opt` | `--preset fast` |
| `python -m teknofest.find_best` | `--preset standard` |

---

## Development

The **PyQt UI** (`teknofest/ui.py`, `ui_components.py`, `ui_theme.py`) and parts of the tooling were developed with assistance from **[Cursor](https://cursor.com)**.

## License

[MIT](LICENSE) — Copyright (c) 2026 Efe Erdoğmuş

## Disclaimer

For education and design support only. Verify competition rules and in-water performance against official Teknofest documentation and field tests.
