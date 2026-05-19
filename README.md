# OpenTorpedo

Design simulation and parameter optimization for a **Teknofest Unmanned Underwater Systems** competition torpedo.

Given a fixed **CAD hull** (STEP), the tool tunes **PLA infill**, **ballast mass and position**, and **four identical parallel launch springs** to maximize simulated speed while respecting mass and manufacturability limits. Heavy grid searches are intended to run on **Google Colab** so local machines are not overloaded.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/efeerdogmus0/opentorpedo/blob/main/notebooks/teknofest_colab.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Features

| Component | Description |
|-----------|-------------|
| **CAD hull** | Dimensions from bundled `TORPIDO*.stp` (~181 mm length, ~111 mm max diameter) |
| **Hull mass** | PLA at 1240 kg/m³; infill ratio is a design variable |
| **Ballast** | Mass (g) and position from nose (cm) for center-of-gravity control |
| **Launch springs** | Four identical springs in parallel; wire, coil, turns, length, compression |
| **Simulation** | 3-DOF underwater trajectory; objective: maximum speed |
| **Feasibility filter** | Rejects unrealistic force, stroke, spring index, and shear stress |

---

## Quick start (Google Colab)

1. Open the notebook via **Open in Colab** above, or  
   [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) on GitHub → **Open in Colab**.
2. Use **Runtime → Run all** (four code cells, top to bottom).
3. In cell 3, set `PRESET` (`quick`, `fast`, `medium`, or `full`).
4. Download `teknofest_optimized.json` from cell 4 and place it in `configs/`.

### Search presets

| Preset | Combinations | Typical runtime (Colab) |
|--------|--------------|-------------------------|
| `quick` | 96 | ~2 min |
| `fast` | 128 | ~3 min |
| `medium` | 2,592 | ~10 min |
| `full` | 18,432 | ~45–90 min |

Start with `quick` or `fast` to verify the pipeline; use `full` for the widest search.

### Colab runtime notes

- The first **code** cell clones this repository from GitHub (`git clone`).
- The second code cell only checks NumPy/SciPy; it does not fetch the repo.
- Keep the browser tab active while the optimization cell runs; disconnecting the runtime stops execution.
- If the session resets, run all cells again from the top.

---

## Local installation

### Optimization only (no GUI)

```bash
git clone https://github.com/efeerdogmus0/opentorpedo.git
cd opentorpedo
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m teknofest.grid_search --preset fast
```

Output: `configs/teknofest_optimized.json`

### Desktop UI (PyQt6)

```bash
pip install -r requirements-gui.txt
python -m teknofest.main
```

---

## Model constraints

| Parameter | Limit |
|-----------|--------|
| Total mass | ≤ **500 g** |
| Spring wire diameter | ≤ **2 mm** (upper bound, optimizable) |
| Spring mean coil diameter | ≤ **16 mm** |
| Spring free length | ≤ **60 mm** |
| Parallel springs | **4** identical springs |
| Hull material | PLA; infill searched in ~10–20% (preset-dependent) |

### Manufacturability filter

Configurations that fail these checks are skipped during grid search (see `teknofest/spring_feasibility.py`):

| Check | Limit |
|-------|--------|
| Spring index \(C = D/d\) | 4 – 10 |
| Compression / free length | ≤ **45%** |
| Total launch force (4 springs) | ≤ **520 N** |
| Force per spring | ≤ **150 N** |
| Shear stress (Wahl) | ≤ **650 MPa** |
| Launch Δv from springs (sim.) | ≤ **9 m/s** |
| Free length / coil diameter (buckling) | ≤ **4.5** |

---

## Example output

`configs/teknofest_optimized.json`:

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
    "delta_v_m_s": 5.79
  }
}
```

Values are **simulation recommendations** and must be validated with physical tests and official competition rules.

---

## Repository layout

```
opentorpedo/
├── TORPIDO*.stp                 # CAD hull (fixed geometry)
├── cad_import.py                # STEP → dimensions
├── torpedo_model.py             # Hull, ballast, spring models
├── physics_engine.py            # Mass, CoG, buoyancy
├── simulator.py                 # Trajectory integration
├── optimizer.py                 # SLSQP for GUI fine-tuning
├── teknofest/
│   ├── grid_search.py           # Grid search (CLI / Colab)
│   ├── preset.py                # Teknofest torpedo setup
│   ├── spring_limits.py         # Competition spring bounds
│   ├── spring_feasibility.py    # Manufacturability checks
│   └── main.py                  # PyQt UI entry point
├── notebooks/
│   └── teknofest_colab.ipynb    # Colab workflow
├── configs/
│   └── teknofest_optimized.json
└── scripts/
    └── make_colab_zip.py        # Offline Colab bundle
```

---

## CLI reference

| Command | Description |
|---------|-------------|
| `python -m teknofest.grid_search --preset fast` | Local quick search |
| `python -m teknofest.grid_search --preset full` | Local full search |
| `python -m teknofest.run_fast_opt` | Alias for `--preset fast` |
| `python -m teknofest.find_best` | Alias for `--preset medium` |
| `python scripts/make_colab_zip.py` | Build `dist/opentorpedo_colab.zip` |

---

## Contributing

Issues and pull requests are welcome on [GitHub](https://github.com/efeerdogmus0/opentorpedo/issues).

## License

[MIT](LICENSE) — Copyright (c) 2026 Efe Erdoğmuş

## Disclaimer

This software is for education and design support only. Competition rules, safety requirements, and in-water performance must be verified against **official Teknofest documentation** and field testing. The authors provide no warranty for manufacturing or competition results.
