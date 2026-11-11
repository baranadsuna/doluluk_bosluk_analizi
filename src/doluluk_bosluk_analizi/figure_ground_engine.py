#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-Ground & Solid-Void Ratio Analysis Engine
===============================================
Computes planar building footprint aggregation, zone-level solid-void
(figure-ground) percentages, and spatial density metrics in EPSG:5253 (TUREF / TM30).

Supports both:
  1. Spatial Aggregation Mode (Zones layer + Buildings footprint layer)
  2. Direct Attribute Mode (Single zone/block layer with building & zone area fields)

Compatible with QGIS 3.22+ and QGIS 4.0+, Qt5 & Qt6.
Universal 4-language support: English (en), Turkish (tr), Chinese (zh), Indonesian (id).
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsPointXY,
    QgsProject,
    QgsRendererRange,
    QgsSpatialIndex,
    QgsSymbol,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType, QVariant
from qgis.PyQt.QtGui import QColor


def get_field_type_double():
    if hasattr(QMetaType, "Type") and hasattr(QMetaType.Type, "Double"):
        return QMetaType.Type.Double
    return QVariant.Double


def get_field_type_int():
    if hasattr(QMetaType, "Type") and hasattr(QMetaType.Type, "Int"):
        return QMetaType.Type.Int
    return QVariant.Int


def get_field_type_string():
    if hasattr(QMetaType, "Type") and hasattr(QMetaType.Type, "QString"):
        return QMetaType.Type.QString
    return QVariant.String


class FigureGroundEngine:
    """
    High-performance calculation engine for figure-ground & solid-void ratio analysis.
    Supports multi-tier spatial aggregation and direct attribute modes.
    """

    def __init__(
        self,
        zone_layer: QgsVectorLayer,
        bldg_layer: Optional[QgsVectorLayer] = None,
        zone_area_field: Optional[str] = None,
        bldg_area_field: Optional[str] = None,
        auto_calc_zone_geom: bool = True,
        auto_calc_bldg_geom: bool = True,
        target_crs_authid: str = "EPSG:5253",
        language: str = "en",
        color_palette: str = "urban_warm",
    ):
        self.zone_layer = zone_layer
        self.bldg_layer = bldg_layer
        self.zone_area_field = zone_area_field
        self.bldg_area_field = bldg_area_field
        self.auto_calc_zone_geom = auto_calc_zone_geom
        self.auto_calc_bldg_geom = auto_calc_bldg_geom
        self.target_crs = QgsCoordinateReferenceSystem(target_crs_authid)
        if not self.target_crs.isValid():
            self.target_crs = QgsCoordinateReferenceSystem("EPSG:5253")

        lang_code = str(language).lower()[:2]
        self.language = lang_code if lang_code in ("en", "tr", "zh", "id") else "en"
        self.color_palette = color_palette

    def run_analysis(
        self,
        feedback_cb: Optional[Callable[[int, str], None]] = None,
        output_file_path: Optional[str] = None,
        generate_centroid_points: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes solid-void metrics calculation.
        Handles both:
          - Spatial overlay when bldg_layer is distinct from zone_layer.
          - Direct attribute calculation when bldg_layer is None or same as zone_layer.
        """
        if feedback_cb:
            feedback_cb(5, "Validating input layers and spatial coordinate systems...")

        if not self.zone_layer or not self.zone_layer.isValid():
            raise ValueError("Planning zones layer is invalid or missing.")

        is_direct_mode = (
            self.bldg_layer is None
            or self.bldg_layer == self.zone_layer
            or (self.bldg_layer.id() == self.zone_layer.id())
        )

        project = QgsProject.instance()
        transform_zones = None
        if self.zone_layer.crs().authid() != self.target_crs.authid():
            transform_zones = QgsCoordinateTransform(self.zone_layer.crs(), self.target_crs, project)

        # -------------------------------------------------------------
        # 1. Read and Process Zone Features
        # -------------------------------------------------------------
        if feedback_cb:
            feedback_cb(15, "Indexing planning zone geometries in EPSG:5253...")

        zone_features: Dict[int, Dict[str, Any]] = {}
        zone_index = QgsSpatialIndex()

        for f in self.zone_layer.getFeatures():
            geom = QgsGeometry(f.geometry())
            if geom.isNull() or geom.isEmpty():
                continue
            if transform_zones:
                geom.transform(transform_zones)

            fid = f.id()

            # Determine Zone Area (m²):
            # PRIORITY 1: User-specified attribute field
            zone_m2 = 0.0
            if self.zone_area_field and self.zone_area_field in f.fields().names():
                val = f[self.zone_area_field]
                try:
                    if val is not None and not (isinstance(val, QVariant) and val.isNull()):
                        zone_m2 = float(val)
                except (ValueError, TypeError):
                    zone_m2 = 0.0

            # PRIORITY 2: If attribute is missing, 0, or user wants geometry computation
            if zone_m2 <= 0.0 and self.auto_calc_zone_geom and not geom.isEmpty():
                zone_m2 = geom.area()

            direct_bldg_m2 = 0.0
            if is_direct_mode and self.bldg_area_field and self.bldg_area_field in f.fields().names():
                val_b = f[self.bldg_area_field]
                try:
                    if val_b is not None and not (isinstance(val_b, QVariant) and val_b.isNull()):
                        direct_bldg_m2 = float(val_b)
                except (ValueError, TypeError):
                    direct_bldg_m2 = 0.0

            zone_features[fid] = {
                "feature": f,
                "geom": geom,
                "zone_m2": max(0.0, zone_m2),
                "bldg_count": 1 if (is_direct_mode and direct_bldg_m2 > 0) else 0,
                "total_bldg_m2": direct_bldg_m2 if is_direct_mode else 0.0,
            }

            # Insert transformed feature into spatial index
            idx_f = QgsFeature(fid)
            idx_f.setGeometry(geom)
            zone_index.addFeature(idx_f)

        if not zone_features:
            raise ValueError("No valid zone polygon features found to analyze.")

        centroid_point_data: List[Tuple[QgsPointXY, int, float]] = []
        bldg_processed = 0
        bldgs_assigned = 0
        total_footprint_all = 0.0

        # -------------------------------------------------------------
        # 2. Spatial Aggregation Mode (Buildings Layer Provided)
        # -------------------------------------------------------------
        if not is_direct_mode:
            if not self.bldg_layer or not self.bldg_layer.isValid():
                raise ValueError("Building footprints layer is invalid or missing.")

            transform_bldgs = None
            if self.bldg_layer.crs().authid() != self.target_crs.authid():
                transform_bldgs = QgsCoordinateTransform(self.bldg_layer.crs(), self.target_crs, project)

            if feedback_cb:
                feedback_cb(35, "Aggregating building footprints with robust spatial containment...")

            total_bldg_feats = self.bldg_layer.featureCount()

            for b_feat in self.bldg_layer.getFeatures():
                bldg_processed += 1
                if feedback_cb and total_bldg_feats > 0 and bldg_processed % 500 == 0:
                    pct = 35 + int((bldg_processed / total_bldg_feats) * 45)
                    feedback_cb(pct, f"Processing building {bldg_processed}/{total_bldg_feats}...")

                b_geom = b_feat.geometry()
                if b_geom.isNull() or b_geom.isEmpty():
                    continue

                if transform_bldgs:
                    b_geom = QgsGeometry(b_geom)
                    b_geom.transform(transform_bldgs)

                # Determine building footprint area (m²):
                # PRIORITY 1: User-specified attribute field
                bldg_m2 = 0.0
                if self.bldg_area_field and self.bldg_area_field in b_feat.fields().names():
                    val = b_feat[self.bldg_area_field]
                    try:
                        if val is not None and not (isinstance(val, QVariant) and val.isNull()):
                            bldg_m2 = float(val)
                    except (ValueError, TypeError):
                        bldg_m2 = 0.0

                # PRIORITY 2: Geometric area calculation if attribute is empty or <= 0
                if bldg_m2 <= 0.0 and self.auto_calc_bldg_geom and not b_geom.isEmpty():
                    bldg_m2 = b_geom.area()

                if bldg_m2 <= 0.0:
                    continue

                # 2-Tier Spatial Matching:
                # Step A: Point-in-polygon test via building centroid / point on surface
                c_geom = b_geom.centroid()
                if c_geom.isNull() or c_geom.isEmpty():
                    c_geom = b_geom.pointOnSurface()

                c_pt = c_geom.asPoint()
                candidate_fids = zone_index.intersects(c_geom.boundingBox())

                matched_zid = None
                for zid in candidate_fids:
                    if zid in zone_features:
                        z_geom = zone_features[zid]["geom"]
                        if z_geom.contains(c_geom):
                            matched_zid = zid
                            break

                # Step B: Fallback if centroid falls on boundary, road, or courtyard:
                # Check polygon intersection with candidate zones and assign to max overlap
                if matched_zid is None:
                    b_candidates = zone_index.intersects(b_geom.boundingBox())
                    max_overlap = 0.0
                    for zid in b_candidates:
                        if zid in zone_features:
                            z_geom = zone_features[zid]["geom"]
                            if z_geom.intersects(b_geom):
                                inter = z_geom.intersection(b_geom)
                                if not inter.isEmpty():
                                    overlap_m2 = inter.area()
                                    if overlap_m2 > max_overlap:
                                        max_overlap = overlap_m2
                                        matched_zid = zid

                if matched_zid is not None:
                    zone_features[matched_zid]["bldg_count"] += 1
                    zone_features[matched_zid]["total_bldg_m2"] += bldg_m2
                    bldgs_assigned += 1
                    total_footprint_all += bldg_m2
                    if generate_centroid_points:
                        centroid_point_data.append((c_pt, matched_zid, bldg_m2))

        else:
            # Direct Mode stats
            for zid, zdata in zone_features.items():
                if zdata["total_bldg_m2"] > 0:
                    bldgs_assigned += 1
                    total_footprint_all += zdata["total_bldg_m2"]
            bldg_processed = bldgs_assigned

        # -------------------------------------------------------------
        # 3. Build Result Polygon Layer
        # -------------------------------------------------------------
        if feedback_cb:
            feedback_cb(85, "Synthesizing coverage ratios and creating output layers...")

        is_tr = (self.language == "tr")
        out_layer_name = (
            "Doluluk_Bosluk_Orani_EPSG5253" if is_tr else "Solid_Void_Coverage_EPSG5253"
        )

        out_fields = QgsFields()
        if is_tr:
            out_fields.append(QgsField("bolge_id", get_field_type_int()))
            out_fields.append(QgsField("bolge_m2", get_field_type_double()))
            out_fields.append(QgsField("bolge_ha", get_field_type_double()))
            out_fields.append(QgsField("bina_taban_m2", get_field_type_double()))
            out_fields.append(QgsField("doluluk_pct", get_field_type_double()))
            out_fields.append(QgsField("bosluk_pct", get_field_type_double()))
            out_fields.append(QgsField("bina_sayisi", get_field_type_int()))
            out_fields.append(QgsField("ort_bina_m2", get_field_type_double()))
            out_fields.append(QgsField("taban_yogunlugu_m2_ha", get_field_type_double()))
        else:
            out_fields.append(QgsField("zone_id", get_field_type_int()))
            out_fields.append(QgsField("zone_m2", get_field_type_double()))
            out_fields.append(QgsField("zone_ha", get_field_type_double()))
            out_fields.append(QgsField("bldg_footprint_m2", get_field_type_double()))
            out_fields.append(QgsField("solid_pct", get_field_type_double()))
            out_fields.append(QgsField("void_pct", get_field_type_double()))
            out_fields.append(QgsField("bldg_count", get_field_type_int()))
            out_fields.append(QgsField("avg_bldg_m2", get_field_type_double()))
            out_fields.append(QgsField("density_m2_ha", get_field_type_double()))

        memory_uri = f"MultiPolygon?crs={self.target_crs.authid()}"
        out_layer = QgsVectorLayer(memory_uri, out_layer_name, "memory")
        pr = out_layer.dataProvider()
        pr.addAttributes(list(out_fields))
        out_layer.updateFields()

        out_features = []
        rows_data = []
        total_zone_m2_all = 0.0

        for zid, zdata in zone_features.items():
            z_m2 = round(zdata["zone_m2"], 2)
            z_ha = round(z_m2 / 10000.0, 4)
            b_m2 = round(zdata["total_bldg_m2"], 2)
            b_count = int(zdata["bldg_count"])

            total_zone_m2_all += z_m2

            # Coverage & Void Ratios
            coverage_pct = round((b_m2 / z_m2 * 100.0), 2) if z_m2 > 0 else 0.0
            void_pct = round(max(0.0, 100.0 - coverage_pct), 2)
            density_m2_ha = round((b_m2 / z_ha), 2) if z_ha > 0 else 0.0
            avg_b_m2 = round((b_m2 / b_count), 2) if b_count > 0 else 0.0

            feat = QgsFeature(out_fields)
            feat.setGeometry(zdata["geom"])
            feat.setAttributes([
                int(zid),
                float(z_m2),
                float(z_ha),
                float(b_m2),
                float(coverage_pct),
                float(void_pct),
                int(b_count),
                float(avg_b_m2),
                float(density_m2_ha),
            ])
            out_features.append(feat)

            rows_data.append({
                "zone_id": zid,
                "zone_m2": z_m2,
                "zone_ha": z_ha,
                "bldg_m2": b_m2,
                "solid_pct": coverage_pct,
                "void_pct": void_pct,
                "bldg_count": b_count,
                "avg_bldg_m2": avg_b_m2,
                "density_m2_ha": density_m2_ha,
            })

        pr.addFeatures(out_features)
        out_layer.updateExtents()

        # Optional: Save to GeoPackage / Shapefile
        final_layer = out_layer
        if output_file_path:
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG" if output_file_path.endswith(".gpkg") else "ESRI Shapefile"
            save_options.fileEncoding = "UTF-8"
            err, msg = QgsVectorFileWriter.writeAsVectorFormatV2(
                out_layer, output_file_path, project.transformContext(), save_options
            )
            if err == QgsVectorFileWriter.WriterError.NoError:
                final_layer = QgsVectorLayer(output_file_path, out_layer_name, "ogr")

        # -------------------------------------------------------------
        # 4. Centroid Verification Layer (Optional)
        # -------------------------------------------------------------
        centroid_layer = None
        if generate_centroid_points and centroid_point_data:
            pt_name = "Bina_Agirlik_Merkezleri_EPSG5253" if is_tr else "Building_Centroids_EPSG5253"
            pt_uri = f"Point?crs={self.target_crs.authid()}"
            centroid_layer = QgsVectorLayer(pt_uri, pt_name, "memory")
            pt_pr = centroid_layer.dataProvider()
            pt_fields = QgsFields()
            pt_fields.append(QgsField("zone_id" if not is_tr else "bolge_id", get_field_type_int()))
            pt_fields.append(QgsField("bldg_m2" if not is_tr else "bina_m2", get_field_type_double()))
            pt_pr.addAttributes(list(pt_fields))
            centroid_layer.updateFields()

            pt_feats = []
            for pt, zid, bm2 in centroid_point_data:
                pf = QgsFeature(pt_fields)
                pf.setGeometry(QgsGeometry.fromPointXY(pt))
                pf.setAttributes([int(zid), round(bm2, 2)])
                pt_feats.append(pf)
            pt_pr.addFeatures(pt_feats)
            centroid_layer.updateExtents()

        # Summary KPIs
        overall_coverage = (
            round((total_footprint_all / total_zone_m2_all * 100.0), 2)
            if total_zone_m2_all > 0
            else 0.0
        )
        overall_void = round(max(0.0, 100.0 - overall_coverage), 2)

        summary = {
            "total_zones": len(zone_features),
            "total_buildings_examined": bldg_processed,
            "total_buildings_assigned": bldgs_assigned,
            "total_zone_m2": round(total_zone_m2_all, 2),
            "total_zone_ha": round(total_zone_m2_all / 10000.0, 4),
            "total_building_footprint_m2": round(total_footprint_all, 2),
            "total_building_footprint_ha": round(total_footprint_all / 10000.0, 4),
            "overall_solid_pct": overall_coverage,
            "overall_void_pct": overall_void,
            "rows": rows_data,
        }

        if feedback_cb:
            feedback_cb(100, "Analysis complete.")

        return {
            "layer": final_layer,
            "centroid_layer": centroid_layer,
            "summary": summary,
            "solid_field": "doluluk_pct" if is_tr else "solid_pct",
            "language": self.language,
        }


def apply_solid_void_symbology(
    layer: QgsVectorLayer,
    solid_field: str,
    language: str = "en",
    palette: str = "urban_warm",
) -> None:
    """
    Applies an adaptive graduated choropleth styling to the result layer based on
    actual solid/coverage percentage distribution and chosen color palette.
    """
    if not layer or not layer.isValid():
        return

    lang_code = str(language).lower()[:2]
    lang = lang_code if lang_code in ("en", "tr", "zh", "id") else "en"

    # Extract actual min and max values to produce adaptive, balanced classification
    vals: List[float] = []
    for f in layer.getFeatures():
        v = f[solid_field]
        if v is not None and not (isinstance(v, QVariant) and v.isNull()):
            try:
                vals.append(float(v))
            except (ValueError, TypeError):
                pass

    min_val = min(vals) if vals else 0.0
    max_val = max(vals) if vals else 100.0

    # If dataset spans a narrow or specific sub-range, adapt intervals dynamically
    if max_val - min_val > 0.1:
        span = max_val - min_val
        b1 = round(min_val + span * 0.2, 1)
        b2 = round(min_val + span * 0.4, 1)
        b3 = round(min_val + span * 0.6, 1)
        b4 = round(min_val + span * 0.8, 1)
        max_b = round(max_val, 1)
        min_b = round(min_val, 1)
    else:
        min_b, b1, b2, b3, b4, max_b = 0.0, 10.0, 25.0, 40.0, 60.0, 100.0

    # Palette color definitions
    if palette == "nolli_grayscale":
        colors = ["#f8fafc", "#cbd5e1", "#94a3b8", "#475569", "#0f172a"]
        border_hex = "#1e293b"
    elif palette == "eco_traffic":
        colors = ["#bbf7d0", "#86efac", "#fde047", "#fb923c", "#ef4444"]
        border_hex = "#334155"
    else:
        # Default: urban_warm (Soft cream -> Amber -> Orange -> Crimson -> Deep Burgundy)
        colors = ["#fef08a", "#f97316", "#ef4444", "#b91c1c", "#7f1d1d"]
        border_hex = "#475569"

    # Multilingual class level labels
    labels_map = {
        "en": [
            f"Very Low ({min_b:.1f}% - {b1:.1f}%)",
            f"Low ({b1:.1f}% - {b2:.1f}%)",
            f"Moderate ({b2:.1f}% - {b3:.1f}%)",
            f"High ({b3:.1f}% - {b4:.1f}%)",
            f"Very High (> {b4:.1f}%)",
        ],
        "tr": [
            f"Çok Düşük (%{min_b:.1f} - %{b1:.1f})",
            f"Düşük (%{b1:.1f} - %{b2:.1f})",
            f"Orta (%{b2:.1f} - %{b3:.1f})",
            f"Yüksek (%{b3:.1f} - %{b4:.1f})",
            f"Çok Yüksek (> %{b4:.1f})",
        ],
        "zh": [
            f"极低覆盖 ({min_b:.1f}% - {b1:.1f}%)",
            f"低覆盖 ({b1:.1f}% - {b2:.1f}%)",
            f"中等覆盖 ({b2:.1f}% - {b3:.1f}%)",
            f"高覆盖 ({b3:.1f}% - {b4:.1f}%)",
            f"极高密集 (> {b4:.1f}%)",
        ],
        "id": [
            f"Sangat Rendah ({min_b:.1f}% - {b1:.1f}%)",
            f"Rendah ({b1:.1f}% - {b2:.1f}%)",
            f"Sedang ({b2:.1f}% - {b3:.1f}%)",
            f"Tinggi ({b3:.1f}% - {b4:.1f}%)",
            f"Sangat Padat (> {b4:.1f}%)",
        ],
    }
    lbls = labels_map.get(lang, labels_map["en"])

    ranges_cfg = [
        (min_b, b1, colors[0], border_hex, lbls[0]),
        (b1, b2, colors[1], border_hex, lbls[1]),
        (b2, b3, colors[2], border_hex, lbls[2]),
        (b3, b4, colors[3], border_hex, lbls[3]),
        (b4, max(max_b, 100.0), colors[4], border_hex, lbls[4]),
    ]

    range_list = []
    for lower, upper, fill_hex, b_hex, label in ranges_cfg:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        if symbol:
            symbol.setColor(QColor(fill_hex))
            symbol.symbolLayer(0).setStrokeColor(QColor(b_hex))
            symbol.symbolLayer(0).setStrokeWidth(0.35)
        renderer_range = QgsRendererRange(lower, upper, symbol, label)
        range_list.append(renderer_range)

    renderer = QgsGraduatedSymbolRenderer(solid_field, range_list)
    layer.setRenderer(renderer)
    layer.triggerRepaint()
