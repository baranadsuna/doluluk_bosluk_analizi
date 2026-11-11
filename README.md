# Figure-Ground & Building Coverage Analyzer (图底与实虚比 / Doluluk-Boşluk / Solid-Void)

**Standard Coordinate Reference System**: `EPSG:5253` (TUREF / TM30)  
**Compatibility**: QGIS 3.22+ and QGIS 4.0+ (Qt5 & Qt6 Compatible)  
**Author**: Baran Adsuna (Dokuz Eylül University, Department of Urban and Regional Planning)  
**Latest Version**: `1.2.1` (Universal Multi-Language Release — Verified for `plugins.qgis.org`)

---

## 1. Overview & Universal Urban Morphology

The **Figure-Ground & Solid-Void Analyzer** is a high-performance, universal QGIS plugin designed for urban planners, architects, researchers, and municipal authorities across the globe. It calculates the core urban morphological metric of **Solid-Void (Figure-Ground) Coverage Ratio** by analyzing the built mass ("solid") against open public and private space ("void").

Inspired by Giambattista Nolli's 1748 Rome map (*Nuova Pianta di Roma*), the tool supports both:
1. **Spatial Overlay Mode**: Spatially aggregates thousands of individual building footprint geometries into planning zones or urban blocks with a robust 2-tier spatial containment index (centroid containment + boundary intersection fallback).
2. **Direct Attribute Mode**: Directly calculates coverage and void ratios from existing attribute columns (e.g. `bina_taban_m2` / `bolge_m2`) within a single planning zone or parcel layer.

---

## 2. Universal 4-Language Support (Bilingual & International)

The plugin features instant, runtime language switching across 4 global languages:

| Flag & Language | Code | Terminology Focus |
| :--- | :--- | :--- |
| 🇬🇧 **English** | `en` | Figure-Ground, Solid-Void Ratio, Footprint Coverage, Nolli Symbology |
| 🇹🇷 **Türkçe** | `tr` | Doluluk-Boşluk Oranı, Taban Alanı (TAKS), Planlama Bölgeleri |
| 🇨🇳 **简体中文** | `zh` | 图底分析, 建筑基底覆盖率 (实), 开敞空间空隙率 (虚) |
| 🇮🇩 **Bahasa Indonesia** | `id` | Analisis Solid-Void, Rasio KDB / Tutupan Bangunan, Ruang Terbuka |

---

## 3. Key Algorithmic & UI Features (v1.2.0)

- **Attribute Precedence Guarantee**: User-specified attribute fields (`zone_area_field`, `bldg_area_field`) are strictly prioritized and never overwritten by geometric area calculations unless explicitly missing or empty.
- **2-Tier Spatial Aggregation ($O(N \log M)$)**:
  - *Tier 1*: Fast spatial index centroid test (`QgsSpatialIndex`).
  - *Tier 2*: Boundary and attached building fallback test (intersection overlap). Guarantees that attached (bitişik nizam) and complex polygon buildings on boundaries are never dropped.
- **Adaptive Graduated Symbology**:
  - Automatically calculates the dataset's actual min/max values and dynamically adjusts 5 balanced classification intervals so maps are never monochromatic.
  - Three built-in planning palettes:
    1. **Urban Density Heatmap** (Soft Amber $\rightarrow$ Orange $\rightarrow$ Crimson $\rightarrow$ Deep Burgundy)
    2. **Architectural Nolli** (White $\rightarrow$ Slate Gray $\rightarrow$ Charcoal $\rightarrow$ Deep Black)
    3. **Eco-Morphology** (Light Emerald $\rightarrow$ Yellow $\rightarrow$ Crimson)
- **Responsive Screen-Fit Guarantee**: Minimum size `540x480` px with scrollable parameter cards. The **Calculate Solid-Void** button is pinned at the bottom footer, remaining 100% visible and clickable on any laptop display scaling (125%, 150%).
- **Instant Results & Export**: Auto-switches to the *Results & Statistics* tab upon calculation, featuring KPI summary cards, formatted data table, one-click clipboard copying, and CSV export.

---

## 4. Mathematical Formulation

For each study zone or block $Z_j$:

1. **Total Building Footprint Area ($m^2$)**:
   $$A_{\text{building, total}} = \sum_{i \in Z_j} A_{\text{building}, i}$$

2. **Solid / Coverage Ratio (%)**:
   $$\text{Coverage / Solid (\%)} = \left(\frac{A_{\text{building, total}}}{A_{Z_j}}\right) \times 100$$

3. **Void Ratio (%)**:
   $$\text{Void (\%)} = 100 - \text{Coverage (\%)} = \left(\frac{A_{Z_j} - A_{\text{building, total}}}{A_{Z_j}}\right) \times 100$$

4. **Building Footprint Density ($m^2/\text{ha}$)**:
   $$\text{Density } (m^2/\text{ha}) = \frac{A_{\text{building, total}}}{A_{Z_j} / 10\,000}$$

---

## 5. Multi-Language Attribute Schema

| Metric | English (`en`) | Turkish (`tr`) | Chinese (`zh`) | Indonesian (`id`) | Data Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Zone Identifier | `zone_id` | `bolge_id` | `zone_id` | `zone_id` | Integer |
| Zone Area ($m^2$) | `zone_m2` | `bolge_m2` | `zone_m2` | `zone_m2` | Double |
| Zone Area (ha) | `zone_ha` | `bolge_ha` | `zone_ha` | `zone_ha` | Double |
| Footprint Area ($m^2$) | `bldg_footprint_m2` | `bina_taban_m2` | `bldg_footprint_m2` | `bldg_footprint_m2` | Double |
| Solid Ratio (%) | `solid_pct` | `doluluk_pct` | `solid_pct` | `solid_pct` | Double |
| Void Ratio (%) | `void_pct` | `bosluk_pct` | `void_pct` | `void_pct` | Double |
| Building Count | `bldg_count` | `bina_sayisi` | `bldg_count` | `bldg_count` | Integer |
| Average Building ($m^2$)| `avg_bldg_m2` | `ort_bina_m2` | `avg_bldg_m2` | `avg_bldg_m2` | Double |
| Density ($m^2/\text{ha}$) | `density_m2_ha` | `taban_yogunlugu_m2_ha` | `density_m2_ha` | `density_m2_ha` | Double |

---

## 6. Verification and Packaging Commands

```powershell
# Run Unit & Math Integration Tests
& "C:\Program Files\QGIS 3.44.14\bin\python-qgis-ltr.bat" 02_gelistirilen_eklentiler/doluluk_bosluk_analizi/src/doluluk_bosluk_analizi/tests/test_figure_ground.py

# Run 4-Language UI Smoke & Lifecycle Tests
& "C:\Program Files\QGIS 3.44.14\bin\python-qgis-ltr.bat" 02_gelistirilen_eklentiler/doluluk_bosluk_analizi/src/doluluk_bosluk_analizi/tests/test_smoke.py

# Run Qt5/Qt6 & QGIS 3/4 Compatibility Scan
& "C:\Program Files\QGIS 3.44.14\bin\python-qgis-ltr.bat" 04_test_ve_dogrulama_laboratuvari/qt5_qt6_qgis34_scanner.py

# Package clean .zip for plugins.qgis.org
& "C:\Program Files\QGIS 3.44.14\bin\python-qgis-ltr.bat" 05_araclar_ve_rehberler/plugin_packager.py --src 02_gelistirilen_eklentiler/doluluk_bosluk_analizi/src/doluluk_bosluk_analizi --out 02_gelistirilen_eklentiler/doluluk_bosluk_analizi/releases/doluluk_bosluk_analizi_v1.2.0.zip
```
