# OpenTorpedo

Teknofest insansız su altı torpido simülasyonu ve parametre optimizasyonu (CAD gövde, balast, fırlatma yayı).

## Colab (PC’yi yormadan optimizasyon)

1. [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) dosyasını Google Colab’da aç.
2. Hücreler otomatik olarak bu repoyu klonlar ve `full` grid aramasını çalıştırır.
3. `configs/teknofest_optimized.json` indirilir.

Alternatif: `python3 scripts/make_colab_zip.py` → `dist/opentorpedo_colab.zip` yükle.

## Yerel (hafif)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m teknofest.grid_search --preset fast
```

GUI: `python3 -m teknofest.main` (PyQt6 gerekir).

## Kısıtlar (Teknofest)

- Toplam kütle ≤ 500 g
- Yay tel çapı ≤ 2 mm, bobin çapı ≤ 16 mm, serbest uzunluk ≤ 60 mm
