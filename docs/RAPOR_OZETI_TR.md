# OpenTorpedo — Rapor özeti (Türkçe)

Bu metni Teknofest proje raporuna uyarlayarak kullanabilirsiniz.

## Projenin amacı

Teknofest İnsansız Su Altı Sistemleri yarışmasında kullanılan torpido gövdesi CAD olarak sabittir. OpenTorpedo, gövde şeklini değiştirmeden **kabuk doluluk oranını (PLA infill)**, **balast kütlesini ve konumunu** ile **dört adet özdeş paralel fırlatma yayını** parametre olarak alır; her aday tasarımı bilgisayarda kısa bir su altı hareket simülasyonundan geçirir ve **simüle maksimum hızı** en yüksek olan kombinasyonu önerir.

Amaç, atölyede denenecek tasarım sayısını azaltmaktır. Simülasyon, havuz testi veya CFD’nin yerine geçmez; **ön tasarım ve karşılaştırmalı seçim** aracıdır.

## Geliştirilen yazılım bileşenleri

1. **CAD aktarımı:** STEP dosyasından boyut, hacim ve ıslak alan çıkarımı.
2. **Bileşen modeli:** PLA gövde, nokta balast, dört paralel sıkıştırma yayı (kütle ve konum dahil).
3. **Fizik motoru:** Kaldırma, ağırlık, sürükleme, ek kütle, isteğe bağlı kanat kuvvetleri.
4. **Yörünge simülatörü:** Yay ile başlangıç hızı, 3 serbestlik dereceli hareket (ileri, derinlik, yunuslama).
5. **Izgara optimizasyonu:** Kütlesi ve üretilebilir yay sınırları içinde binlerce kombinasyonu tarama.
6. **Google Colab entegrasyonu:** Ağır aramayı bulut sunucuda çalıştırma.
7. **Masaüstü arayüz (PyQt6):** Tek parametre değiştirip simülasyon çalıştırma.

## Kullanılan teknolojiler

- Python, NumPy, SciPy  
- PyQt6 (arayüz)  
- Google Colab (optimizasyon)  
- GitHub (sürüm kontrolü ve paylaşım)  
- Cursor IDE (arayüz ve araç geliştirmede yapay zekâ destekli düzenleme)

## Yarışma kısıtlarının modele yansıması

| Kural | Yazılımda |
|--------|-----------|
| Toplam kütle ≤ 500 g | Optimizasyon kısıtı |
| Yay tel çapı ≤ 2 mm | Üst sınır |
| Bobin çapı ≤ 16 mm | Üst sınır |
| Yay boyu ≤ 60 mm | Üst sınır |
| Dört yay | Paralel, özdeş model |

Ek olarak **üretilebilirlik filtresi** uygulanır: aşırı sıkıştırma, kopma riski yüksek gerilme, makul olmayan kuvvet ve burkulma oranları elenir.

## Çalışma akışı

1. Yarışma STEP dosyası projeye yüklenir.  
2. Colab veya yerel komut ile `standard` (önerilen) veya `fast` preset çalıştırılır.  
3. `teknofest_optimized.json` dosyası indirilir.  
4. Önerilen infill, balast ve yay ölçüleri ile prototip üretilir.  
5. Tartım, yay kuvveti ölçümü ve kısa menzil havuz deneyi ile doğrulama yapılır.

## Modelin sınırları (raporda dürüstçe belirtin)

- Gövde hacmi yaklaşık geometriden türetilir; kabuk kalınlığı ayrı mesh değildir.  
- Yay, anlık hız artışı olarak modellenir; fırlatıcı mekaniği yoktur.  
- Su özellikleri sabit alınır; pervane varsayılan Teknofest kurulumunda yoktur.  
- Optimizasyon çıktısı mutlak hızdan çok **tasarımlar arası karşılaştırma** içindir.

## Sonuç cümlesi örneği

*“Bu çalışmada, sabit CAD gövde için parametrik kütle ve dörtlü yay fırlatma modeli içeren OpenTorpedo yazılımı geliştirilmiş; Google Colab üzerinde ızgaralı arama ile üretilebilir sınırlar içinde en yüksek simüle performansı veren tasarım seçilmiş ve havuz testi ile doğrulama planlanmıştır.”*

---

İngilizce proje özeti: [README](../README.md) · Teknik varsayımlar: [MODEL_ASSUMPTIONS.md](MODEL_ASSUMPTIONS.md)
