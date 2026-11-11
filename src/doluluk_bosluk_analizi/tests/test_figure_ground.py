#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Figure-Ground & Solid-Void Analyzer
Validates:
  - English, Turkish, Chinese, and Indonesian language output schemas
  - Attribute precedence over geometric area
  - Direct Attribute Mode (single-layer calculation)
  - 2-Tier spatial aggregation (centroid + polygon intersection fallback)
  - Adaptive graduated symbology with multiple color palettes
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from figure_ground_engine import (
    FigureGroundEngine,
    apply_solid_void_symbology,
    get_field_type_double,
    get_field_type_int,
)


class TestFigureGroundEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
        cls.crs = QgsCoordinateReferenceSystem("EPSG:5253")

    @classmethod
    def tearDownClass(cls):
        cls.qgs.exitQgis()

    def _create_mock_layers(self):
        # Zone layer: 2 zones in EPSG:5253 (each 100m x 100m = 10,000 m²)
        zone_layer = QgsVectorLayer("Polygon?crs=EPSG:5253", "mock_zones", "memory")
        pr_z = zone_layer.dataProvider()
        pr_z.addAttributes([
            QgsField("id", get_field_type_int()),
            QgsField("alan_m2", get_field_type_double()),
        ])
        zone_layer.updateFields()

        # Zone 1: [500000, 4250000] to [500100, 4250100] (10,000 m²)
        f_z1 = QgsFeature(zone_layer.fields())
        f_z1.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500000, 4250000),
            QgsPointXY(500100, 4250000),
            QgsPointXY(500100, 4250100),
            QgsPointXY(500000, 4250100),
            QgsPointXY(500000, 4250000),
        ]]))
        f_z1.setAttributes([1, 10000.0])

        # Zone 2: [500100, 4250000] to [500200, 4250100] (10,000 m²)
        f_z2 = QgsFeature(zone_layer.fields())
        f_z2.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500100, 4250000),
            QgsPointXY(500200, 4250000),
            QgsPointXY(500200, 4250100),
            QgsPointXY(500100, 4250100),
            QgsPointXY(500100, 4250000),
        ]]))
        f_z2.setAttributes([2, 10000.0])

        pr_z.addFeatures([f_z1, f_z2])
        zone_layer.updateExtents()

        # Buildings layer:
        # In Zone 1: 3 buildings of 200 m² (total 600 m² -> 6% solid, 94% void)
        # In Zone 2: 2 buildings of 1000 m² (total 2000 m² -> 20% solid, 80% void)
        bldg_layer = QgsVectorLayer("Polygon?crs=EPSG:5253", "mock_bldgs", "memory")
        pr_b = bldg_layer.dataProvider()
        pr_b.addAttributes([
            QgsField("bldg_id", get_field_type_int()),
            QgsField("taban_m2", get_field_type_double()),
        ])
        bldg_layer.updateFields()

        bldg_feats = []
        for i, x in enumerate([500010, 500040, 500070]):
            f = QgsFeature(bldg_layer.fields())
            f.setGeometry(QgsGeometry.fromPolygonXY([[
                QgsPointXY(x, 4250010),
                QgsPointXY(x + 20, 4250010),
                QgsPointXY(x + 20, 4250020),
                QgsPointXY(x, 4250020),
                QgsPointXY(x, 4250010),
            ]]))
            f.setAttributes([101 + i, 200.0])
            bldg_feats.append(f)

        for i, x in enumerate([500110, 500140]):
            f = QgsFeature(bldg_layer.fields())
            f.setGeometry(QgsGeometry.fromPolygonXY([[
                QgsPointXY(x, 4250010),
                QgsPointXY(x + 20, 4250010),
                QgsPointXY(x + 20, 4250060),
                QgsPointXY(x, 4250060),
                QgsPointXY(x, 4250010),
            ]]))
            f.setAttributes([201 + i, 1000.0])
            bldg_feats.append(f)

        pr_b.addFeatures(bldg_feats)
        bldg_layer.updateExtents()

        return zone_layer, bldg_layer

    def test_calculation_english_and_palettes(self):
        z_lyr, b_lyr = self._create_mock_layers()
        engine = FigureGroundEngine(
            zone_layer=z_lyr,
            bldg_layer=b_lyr,
            zone_area_field="alan_m2",
            bldg_area_field="taban_m2",
            language="en",
            color_palette="urban_warm",
        )
        res = engine.run_analysis(generate_centroid_points=True)
        summary = res["summary"]

        self.assertEqual(summary["total_zones"], 2)
        self.assertEqual(summary["total_buildings_assigned"], 5)
        self.assertAlmostEqual(summary["total_zone_m2"], 20000.0, delta=1.0)
        self.assertAlmostEqual(summary["total_building_footprint_m2"], 2600.0, delta=1.0)
        self.assertAlmostEqual(summary["overall_solid_pct"], 13.0, delta=0.1)
        self.assertAlmostEqual(summary["overall_void_pct"], 87.0, delta=0.1)

        out_layer = res["layer"]
        self.assertTrue(out_layer.isValid())
        field_names = [f.name() for f in out_layer.fields()]
        self.assertIn("solid_pct", field_names)
        self.assertIn("void_pct", field_names)
        self.assertIn("bldg_footprint_m2", field_names)

        # Verify Centroid Layer
        c_layer = res["centroid_layer"]
        self.assertIsNotNone(c_layer)
        self.assertEqual(c_layer.featureCount(), 5)

        # Test Adaptive Symbology with all palettes
        apply_solid_void_symbology(out_layer, "solid_pct", language="en", palette="urban_warm")
        self.assertIsNotNone(out_layer.renderer())

        apply_solid_void_symbology(out_layer, "solid_pct", language="zh", palette="nolli_grayscale")
        self.assertIsNotNone(out_layer.renderer())

        apply_solid_void_symbology(out_layer, "solid_pct", language="id", palette="eco_traffic")
        self.assertIsNotNone(out_layer.renderer())

    def test_calculation_turkish(self):
        z_lyr, b_lyr = self._create_mock_layers()
        engine = FigureGroundEngine(
            zone_layer=z_lyr,
            bldg_layer=b_lyr,
            language="tr",
        )
        res = engine.run_analysis()
        out_layer = res["layer"]
        field_names = [f.name() for f in out_layer.fields()]
        self.assertIn("doluluk_pct", field_names)
        self.assertIn("bosluk_pct", field_names)
        self.assertIn("bina_taban_m2", field_names)
        self.assertIn("bina_sayisi", field_names)

    def test_direct_attribute_mode(self):
        """Tests Direct Attribute Mode when building area is already in the zone layer."""
        zone_layer = QgsVectorLayer("Polygon?crs=EPSG:5253", "direct_zones", "memory")
        pr = zone_layer.dataProvider()
        pr.addAttributes([
            QgsField("id", get_field_type_int()),
            QgsField("bolge_m2", get_field_type_double()),
            QgsField("bina_taban_m2", get_field_type_double()),
        ])
        zone_layer.updateFields()

        f = QgsFeature(zone_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500000, 4250000),
            QgsPointXY(500100, 4250000),
            QgsPointXY(500100, 4250100),
            QgsPointXY(500000, 4250100),
            QgsPointXY(500000, 4250000),
        ]]))
        # 4,000 m² building footprint in 10,000 m² zone -> exactly 40% solid, 60% void
        f.setAttributes([1, 10000.0, 4000.0])
        pr.addFeatures([f])
        zone_layer.updateExtents()

        engine = FigureGroundEngine(
            zone_layer=zone_layer,
            bldg_layer=None,  # Direct mode
            zone_area_field="bolge_m2",
            bldg_area_field="bina_taban_m2",
            language="en",
        )
        res = engine.run_analysis()
        out_layer = res["layer"]
        feat = list(out_layer.getFeatures())[0]

        self.assertAlmostEqual(feat["solid_pct"], 40.0, delta=0.01)
        self.assertAlmostEqual(feat["void_pct"], 60.0, delta=0.01)
        self.assertAlmostEqual(res["summary"]["overall_solid_pct"], 40.0, delta=0.01)

    def test_attribute_precedence_over_geometry(self):
        """Verifies that user-supplied attribute values take precedence over geometry area."""
        zone_layer = QgsVectorLayer("Polygon?crs=EPSG:5253", "prec_zones", "memory")
        pr_z = zone_layer.dataProvider()
        pr_z.addAttributes([
            QgsField("id", get_field_type_int()),
            QgsField("net_alan_m2", get_field_type_double()),
        ])
        zone_layer.updateFields()

        # Geometry area is 10,000 m², but net planning area attribute is 5,000 m²
        f_z = QgsFeature(zone_layer.fields())
        f_z.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500000, 4250000),
            QgsPointXY(500100, 4250000),
            QgsPointXY(500100, 4250100),
            QgsPointXY(500000, 4250100),
            QgsPointXY(500000, 4250000),
        ]]))
        f_z.setAttributes([1, 5000.0])
        pr_z.addFeatures([f_z])

        # Building geometry area is 200 m², but footprint attribute is 2,500 m²
        bldg_layer = QgsVectorLayer("Polygon?crs=EPSG:5253", "prec_bldgs", "memory")
        pr_b = bldg_layer.dataProvider()
        pr_b.addAttributes([
            QgsField("bldg_id", get_field_type_int()),
            QgsField("taks_m2", get_field_type_double()),
        ])
        bldg_layer.updateFields()

        f_b = QgsFeature(bldg_layer.fields())
        f_b.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500010, 4250010),
            QgsPointXY(500030, 4250010),
            QgsPointXY(500030, 4250020),
            QgsPointXY(500010, 4250020),
            QgsPointXY(500010, 4250010),
        ]]))
        f_b.setAttributes([1, 2500.0])
        pr_b.addFeatures([f_b])

        engine = FigureGroundEngine(
            zone_layer=zone_layer,
            bldg_layer=bldg_layer,
            zone_area_field="net_alan_m2",
            bldg_area_field="taks_m2",
            language="en",
        )
        res = engine.run_analysis()
        out_layer = res["layer"]
        feat = list(out_layer.getFeatures())[0]

        # 2,500 m² / 5,000 m² = 50.0% coverage (If geometry was used, it would be 200 / 10000 = 2%)
        self.assertAlmostEqual(feat["solid_pct"], 50.0, delta=0.01)
        self.assertAlmostEqual(feat["void_pct"], 50.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
