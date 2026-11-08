# Figure-Ground & Solid-Void Analyzer (Doluluk Boşluk Oranı Analiz Aracı)

**Standard Coordinate Reference System**: `EPSG:5253` (TUREF / TM30)  
**Compatibility**: QGIS 3.22+ and QGIS 4.0+ (Qt5 & Qt6 Compatible)  
**Author**: Baran Adsuna (Dokuz Eylül University, Department of Urban and Regional Planning)

---

## 1. Overview & Planning Methodology

The **Figure-Ground & Solid-Void Analyzer** is a high-performance QGIS plugin designed for urban planners, architects, and GIS researchers. It calculates the classical urban morphological metric of **Solid-Void (Doluluk - Boşluk) Ratio** by aggregating building footprints into planning zones (neighborhoods, study parcels, or urban blocks).

Inspired by Giambattista Nolli's 1748 Rome map (*Nuova Pianta di Roma*), solid-void representation distinguishes private built mass ("solid") from public open space ("void"), providing fundamental insights into urban permeability, building coverage, and open space availability.

---

## 2. Mathematical Formulation

For each planning zone $Z_j$:

1. **Total Building Footprint Area ($m^2$)**:
   $$A_{\text{building, total}} = \sum_{i \in Z_j} A_{\text{building}, i}$$

2. **Solid / Coverage Ratio (%)**:
   $$\text{Coverage / Solid (\%)} = \left(\frac{A_{\text{building, total}}}{A_{Z_j}}\right) \times 100$$

3. **Void Ratio (%)**:
   $$\text{Void (\%)} = 100 - \text{Coverage (\%)} = \left(\frac{A_{Z_j} - A_{\text{building, total}}}{A_{Z_j}}\right) \times 100$$

4. **Building Footprint Density ($m^2/\text{ha}$)**:
   $$\text{Density } (m^2/\text{ha}) = \frac{A_{\text{building, total}}}{A_{Z_j} / 10\,000}$$

5. **Average Building Footprint Area ($m^2$)**:
   $$\bar{A}_{\text{building}} = \frac{A_{\text{building, total}}}{N_{\text{building}}}$$

---

## 3. Bilingual UI & Attribute Schema

The plugin offers seamless dual-language support:

| Metric | Turkish Attribute (`tr`) | English Attribute (`en`) | Data Type |
| :--- | :--- | :--- | :--- |
| Zone Identifier | `bolge_id` | `zone_id` | Integer |
| Zone Area ($m^2$) | `bolge_m2` | `zone_m2` | Double |
| Zone Area (ha) | `bolge_ha` | `zone_ha` | Double |
| Total Building Footprint ($m^2$) | `bina_taban_m2` | `bldg_footprint_m2` | Double |
| Solid / Coverage Ratio (%) | `doluluk_pct` | `solid_pct` | Double |
| Void Ratio (%) | `bosluk_pct` | `void_pct` | Double |
| Building Count | `bina_sayisi` | `bldg_count` | Integer |
| Average Building Area ($m^2$) | `ort_bina_m2` | `avg_bldg_m2` | Double |
| Footprint Density ($m^2/\text{ha}$) | `taban_yogunlugu_m2_ha` | `density_m2_ha` | Double |

---

## 4. Key Engineering Features

- **Spatial Indexing ($O(N \log M)$)**: Uses `QgsSpatialIndex` to efficiently aggregate tens of thousands of buildings across study zones in milliseconds.
- **EPSG:5253 Planar Accuracy**: Enforces distortion-free planar metric calculations without geodesic distortion.
- **Automated Nolli Symbology**: Generates custom graduated choropleth styling (5 shades from light slate to dark charcoal/black).
- **Zero Hallucination Guarantee**: Operates strictly on deterministic user layers without synthetic or mocked data.
