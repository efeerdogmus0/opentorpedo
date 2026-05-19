#!/usr/bin/env python3
"""OpenTorpedo Colab paketi: sadece simülasyon + optimizasyon (PyQt yok)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "opentorpedo_colab.zip"

INCLUDE_PY = [
    "physics_engine.py",
    "simulator.py",
    "torpedo_model.py",
    "optimizer.py",
    "cad_import.py",
    "teknofest/materials.py",
    "teknofest/spring_limits.py",
    "teknofest/spring_feasibility.py",
    "teknofest/preset.py",
    "teknofest/grid_search.py",
    "teknofest/find_best.py",
]

INCLUDE_GLOB = ["TORPIDO*.stp", "TORPIDO*.step"]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_PY:
            path = ROOT / rel
            if not path.exists():
                raise FileNotFoundError(path)
            zf.write(path, rel)

        for pattern in INCLUDE_GLOB:
            for path in ROOT.glob(pattern):
                zf.write(path, path.name)

        zf.writestr("configs/.gitkeep", "")

    mb = OUT.stat().st_size / (1024 * 1024)
    print(f"Oluşturuldu: {OUT} ({mb:.2f} MB)")
    print("Colab'da: Dosyalar → opentorpedo_colab.zip yükle → aşağıdaki hücreyi çalıştır.")


if __name__ == "__main__":
    main()
