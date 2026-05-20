# OpenTorpedo

Open-source design and simulation toolchain for a **Teknofest Unmanned Underwater Systems** competition torpedo. The project turns a fixed **CAD hull** into tunable mass, center-of-gravity, and launch-spring parameters, then evaluates candidates with a **3-DOF underwater flight model** and automated grid search.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/efeerdogmus0/opentorpedo/blob/main/notebooks/teknofest_colab.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What we built

| Deliverable | Description |
|-------------|-------------|
| **Geometry pipeline** | Imports competition `TORPIDO*.stp`, extracts length, diameter, volume, and wetted area |
| **Parametric torpedo model** | PLA hull infill, ballast mass/position, four parallel launch springs |
| **Physics kernel** | Buoyancy, drag, added mass, optional fin forces, pitch dynamics |
| **Trajectory simulator** | RK45 integration with launch spring impulse and depth/surface limits |
| **Grid optimizer** | Searches thousands of designs under mass and manufacturability rules |
| **Colab workflow** | Runs heavy search on Google servers without loading a local PC |
| **Desktop UI** | PyQt6 app for manual tuning and single-run simulation (Teknofest mode) |

The goal is not to replace pool testing or CFD, but to **narrow the design space** before building hardware: which infill, ballast, and spring geometry are worth prototyping.

---

## System workflow

```
  STEP file (fixed hull)
         │
         ▼
  cad_import  ──►  dimensions + volume estimate
         │
         ▼
  torpedo_model  ──►  CadHull + Ballast + 4× LaunchSpring
         │
         ├──────────────────────┐
         ▼                      ▼
  grid_search (Colab/CLI)    teknofest UI (PyQt)
         │                      │
         ▼                      ▼
  physics_engine + simulator
         │
         ▼
  teknofest_optimized.json  ──►  build sheet (infill, ballast, spring dims)
```

1. **Input:** Bundled Teknofest torpedo STEP (geometry fixed by competition CAD).
2. **Tunable:** Shell infill (%), ballast (g, position), spring wire/coil/turns/length/compression.
3. **Filter:** Total mass ≤ 500 g; spring wire ≤ 2 mm; coil ≤ 16 mm; free length ≤ 60 mm; producibility checks (force, stress, stroke).
4. **Evaluate:** Short underwater trajectory; record peak speed.
5. **Output:** JSON with recommended build parameters and simulated performance.

---

## Physical model (summary)

The simulator uses a **lumped-parameter 3-DOF model** (forward motion, depth, pitch):

- **Hull:** Mass from PLA density × CAD volume × infill. Buoyancy from displaced volume.
- **Launch:** Four identical compression springs in parallel; energy converted to initial speed (with axial added mass).
- **Hydrodynamics:** ITTC-1957 friction drag, Hoerner form factor, slender-body lift, Lamb added mass; optional fin model if fins are defined.
- **Integration:** `scipy.integrate.solve_ivp` (RK45), 8 s horizon by default, launch from 0.5 m depth.

Known simplifications (state these in your report):

- CAD volume is a bounding-box / nose–cylinder surrogate, not a full shell-thickness mesh.
- Spring launch is an instantaneous Δv, not a coupled launcher mechanism.
- Fresh water at 20 °C; no propeller in the Teknofest preset.
- Optimization peak speed is often dominated by spring energy when initial velocity is zero.

Detailed assumptions for academic reports: [docs/MODEL_ASSUMPTIONS.md](docs/MODEL_ASSUMPTIONS.md).

---

## Technology stack

| Layer | Tools |
|-------|--------|
| Language | Python 3.12+ |
| Numerics | NumPy, SciPy (`solve_ivp`, optional SLSQP in UI) |
| Desktop UI | PyQt6 |
| Cloud | Google Colab (notebook clones repo, runs grid search) |
| CAD | STEP text parse (no external CAD kernel required) |
| Version control | Git / GitHub |

Parts of the **PyQt UI** and tooling were developed with assistance from [Cursor](https://cursor.com). Physics, spring models, feasibility filters, and the Colab pipeline were implemented and reviewed in the same environment.

---

## Grid search presets

| Preset | Combinations | Typical Colab time | When to use |
|--------|--------------|-------------------|-------------|
| `quick` | 96 | ~2 min | Pipeline check |
| `fast` | 128 | ~3 min | Quick local/Colab trial |
| `medium` | 2,592 | ~10 min | Broader search |
| **`standard`** | **5,184** | **~15–20 min** | **Recommended default** |
| `full` | 18,432 | ~45–90 min | Maximum coverage |

```bash
python -m teknofest.grid_search --preset standard
```

---

## Quick start

### Google Colab (recommended for optimization)

1. Open [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) → **Runtime → Run all**.
2. Default preset: `standard`.
3. Download `teknofest_optimized.json` and copy to `configs/` on your machine.

### Local

```bash
git clone https://github.com/efeerdogmus0/opentorpedo.git
cd opentorpedo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m teknofest.grid_search --preset fast
```

### Desktop UI

```bash
pip install -r requirements-gui.txt
python -m teknofest.main
```

---

## Repository layout

```
opentorpedo/
├── TORPIDO*.stp              # Competition hull CAD
├── cad_import.py             # STEP → geometry
├── torpedo_model.py          # Components (hull, ballast, spring)
├── physics_engine.py         # Forces, CoG, drag, added mass
├── simulator.py              # 3-DOF trajectory
├── teknofest/
│   ├── grid_search.py        # Preset grid search
│   ├── spring_feasibility.py # Manufacturability filter
│   └── main.py               # UI entry
├── notebooks/teknofest_colab.ipynb
├── docs/MODEL_ASSUMPTIONS.md # Report-oriented limitations
└── configs/                  # Optimization results (JSON)
```

---

## Example result

After optimization you receive a JSON build sheet: total mass, CoG, infill %, ballast, and per-spring dimensions (wire, coil, turns, length, compression, forces). Validate every value with **scale measurements** and **pool tests** before competition.

---

## License & disclaimer

[MIT](LICENSE) — Copyright (c) 2026 Efe Erdoğmuş.

This software supports education and design exploration. Official Teknofest rules, safety, and measured performance take precedence over simulation output.
