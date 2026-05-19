"""Physical limits for the Teknofest launch spring."""

# Aynı geometride paralel yay sayısı (fırlatma düzeneği)
LAUNCH_SPRING_COUNT = 4

# Tel çapı: en fazla 2 mm (optimize edilebilir)
SPRING_WIRE_MM_MAX = 2.0
SPRING_MAX_WIRE_DIAMETER_M = SPRING_WIRE_MM_MAX / 1000.0
SPRING_MIN_WIRE_DIAMETER_M = 0.001   # 1 mm

# Coil (mean) diameter
SPRING_MAX_COIL_DIAMETER_M = 0.016   # 16 mm
SPRING_MIN_COIL_DIAMETER_M = 0.008   # 8 mm

# Free length
SPRING_MAX_FREE_LENGTH_M = 0.060     # 60 mm
SPRING_MIN_FREE_LENGTH_M = 0.025     # 25 mm

SPRING_MAX_COMPRESSION_M = 0.050
SPRING_MIN_COMPRESSION_M = 0.008

SPRING_MIN_COILS = 4.0
SPRING_MAX_COILS = 14.0
