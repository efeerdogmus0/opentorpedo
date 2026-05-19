# OpenTorpedo

**Teknofest İnsansız Su Altı Sistemleri** yarışması için torpido tasarım simülasyonu ve parametre optimizasyonu.

Sabit **CAD gövde** (STEP), ayarlanabilir **PLA doluluk oranı**, **balast kütlesi/konumu** ve **fırlatma yayı** ile toplam kütle sınırı altında maksimum hız hedeflenir. Ağır aramalar **Google Colab** üzerinde çalıştırılabilir; böylece kendi bilgisayarın ısınmaz.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/efeerdogmus0/opentorpedo/blob/main/notebooks/teknofest_colab.ipynb)

---

## Ne yapar?

| Bileşen | Açıklama |
|--------|----------|
| **CAD gövde** | `TORPIDO*.stp` dosyasından boyutlar (uzunluk ~181 mm, max çap ~111 mm) |
| **Gövde kütlesi** | PLA, yoğunluk 1240 kg/m³, doluluk oranı (infill) ayarlanır |
| **Balast** | Kütle (g) ve burundan konum (cm) — ağırlık merkezi için |
| **Fırlatma yayı** | Tel çapı, bobin çapı, sarım, serbest uzunluk, sıkıştırma → kuvvet ve Δv |
| **Simülasyon** | 3-DOF su altı yolu; hedef: maksimum hız |

---

## Hızlı başlangıç — Google Colab (önerilen)

Optimizasyon PC’de değil, **Colab sunucusunda** koşar.

### 1. Notebook’u aç

- Yukarıdaki **Open in Colab** rozeti, veya  
- [notebooks/teknofest_colab.ipynb](notebooks/teknofest_colab.ipynb) → Colab’da aç

### 2. Dört kod hücresini sırayla çalıştır

| # | Ne yapar? | Süre (yaklaşık) |
|---|-----------|------------------|
| **1** | GitHub’dan repoyu klonlar | ~30 sn |
| **2** | NumPy / SciPy kontrolü | ~5 sn |
| **3** | Grid optimizasyonu (`PRESET`) | **2–25 dk** |
| **4** | Sonucu gösterir, `teknofest_optimized.json` indirir | ~5 sn |

İlk hücre sadece açıklama metnidir; çalıştırmana gerek yok.

### 3. Preset seç (3. hücre)

```python
PRESET = "quick"   # ~96 deneme, ~2 dk — ilk test
PRESET = "fast"    # ~160 deneme, ~3 dk — hızlı sonuç
PRESET = "medium"  # ~1900 deneme, ~8 dk
PRESET = "full"    # ~6900 deneme, ~15–25 dk — en kapsamlı (Colab)
```

### 4. JSON’u bilgisayarına al

İndirilen `teknofest_optimized.json` dosyasını proje içinde `configs/` klasörüne koy.

### Colab’ı kapatır mıyım?

| Durum | Sonuç |
|--------|--------|
| Sekme **açık**, PC **uyanık** | Optimizasyon devam eder |
| Sekmeyi / tarayıcıyı **kapattın** | Genelde **durur** |
| Bilgisayar **uyku** moduna girdi | Kesilebilir |

Yemek molası için: **3. hücre çalışırken sekmeyi açık bırak**, uyku modunu kapat. Kesilirse 1→4 hücrelerini yeniden çalıştır.

---

## Yerel kurulum

### Sadece optimizasyon (GUI yok)

```bash
git clone https://github.com/efeerdogmus0/opentorpedo.git
cd opentorpedo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Hafif arama (~160 deneme, PC dostu)
python -m teknofest.grid_search --preset fast
```

Sonuç: `configs/teknofest_optimized.json`

### Masaüstü arayüz (PyQt6)

```bash
pip install -r requirements-gui.txt
python -m teknofest.main
```

---

## Yarışma kısıtları (modelde)

| Parametre | Sınır |
|-----------|--------|
| Toplam kütle | ≤ **500 g** |
| Yay tel çapı | ≤ **2 mm** (optimize edilebilir, üst sınır) |
| Yay bobin (orta) çapı | ≤ **16 mm** |
| Yay serbest uzunluk | ≤ **60 mm** |
| Gövde malzemesi | PLA, %10–30 doluluk (arama aralığına göre) |

---

## Çıktı dosyası örneği

`configs/teknofest_optimized.json`:

```json
{
  "max_speed_m_s": 7.33,
  "total_mass_g": 245.9,
  "cog_cm": 8.99,
  "ballast": { "mass_g": 0.0, "position_cm": 8.0 },
  "spring": {
    "wire_diameter_mm": 2.0,
    "coil_diameter_mm": 12.0,
    "active_coils": 8,
    "free_length_mm": 50.0,
    "compression_mm": 34.0,
    "force_N": 388.6,
    "delta_v_m_s": 7.33
  }
}
```

Bu değerler **simülasyon önerisidir**; atış testi ve üretim toleranslarıyla doğrulanmalıdır.

---

## Proje yapısı

```
opentorpedo/
├── TORPIDO*.stp              # CAD gövde (sabit geometri)
├── cad_import.py             # STEP → boyutlar
├── torpedo_model.py          # Gövde, balast, yay modelleri
├── physics_engine.py         # Kütle, CoG, kaldırma
├── simulator.py              # Yörünge integrasyonu
├── optimizer.py              # SLSQP (GUI içi ince ayar)
├── teknofest/
│   ├── grid_search.py        # Grid arama (Colab / CLI)
│   ├── preset.py             # Teknofest torpido kurulumu
│   ├── spring_limits.py      # Yay fiziksel sınırları
│   └── main.py               # PyQt arayüz
├── notebooks/
│   └── teknofest_colab.ipynb # Colab giriş noktası
├── configs/
│   └── teknofest_optimized.json
└── scripts/
    └── make_colab_zip.py     # İnternetsiz Colab için zip paketi
```

---

## Komut özeti

| Komut | Açıklama |
|--------|----------|
| `python -m teknofest.grid_search --preset fast` | Yerel hızlı arama |
| `python -m teknofest.grid_search --preset full` | Yerel tam arama (uzun) |
| `python -m teknofest.run_fast_opt` | `fast` preset kısayolu |
| `python -m teknofest.find_best` | `medium` preset |
| `python scripts/make_colab_zip.py` | Colab zip paketi (`dist/`) |

---

## Katkı ve lisans

- **Lisans:** [MIT](LICENSE)
- Hata / öneri için [Issues](https://github.com/efeerdogmus0/opentorpedo/issues) açabilirsin.

---

## Sorumluluk reddi

Bu yazılım eğitim ve tasarım desteği içindir. Gerçek yarışma kuralları, güvenlik gereksinimleri ve su testi sonuçları **resmi Teknofest dokümanları** ve saha denemeleriyle doğrulanmalıdır. Yazarlar, üretim veya yarışma performansı için garanti vermez.
