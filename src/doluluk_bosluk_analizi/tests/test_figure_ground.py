#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Figure-Ground & Solid-Void Analyzer
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

# Ensure module path is accessible
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
        # Bldg 1 (Zone 1): 10x20 = 200 m²
        f = QgsFeature(bldg_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500010, 4250010),
            QgsPointXY(500030, 4250010),
            QgsPointXY(500030, 4250020),
            QgsPointXY(500010, 4250020),
            QgsPointXY(500010, 4250010),
        ]]))
        f.setAttributes([101, 200.0])
        bldg_feats.append(f)

        # Bldg 2 (Zone 1): 10x20 = 200 m²
        f = QgsFeature(bldg_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500040, 4250010),
            QgsPointXY(500060, 4250010),
            QgsPointXY(500060, 4250020),
            QgsPointXY(500040, 4250020),
            QgsPointXY(500040, 4250010),
        ]]))
        f.setAttributes([102, 200.0])
        bldg_feats.append(f)

        # Bldg 3 (Zone 1): 10x20 = 200 m²
        f = QgsFeature(bldg_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500070, 4250010),
            QgsPointXY(500090, 4250010),
            QgsPointXY(500090, 4250020),
            QgsPointXY(500070, 4250020),
            QgsPointXY(500070, 4250010),
        ]]))
        f.setAttributes([103, 200.0])
        bldg_feats.append(f)

        # Bldg 4 (Zone 2): 20x50 = 1000 m²
        f = QgsFeature(bldg_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500110, 4250010),
            QgsPointXY(500130, 4250010),
            QgsPointXY(500130, 4250060),
            QgsPointXY(500110, 4250060),
            QgsPointXY(500110, 4250010),
        ]]))
        f.setAttributes([201, 1000.0])
        bldg_feats.append(f)

        # Bldg 5 (Zone 2): 20x50 = 1000 m²
        f = QgsFeature(bldg_layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[
            QgsPointXY(500140, 4250010),
            QgsPointXY(500160, 4250010),
            QgsPointXY(500160, 4250060),
            QgsPointXY(500140, 4250060),
            QgsPointXY(500140, 4250010),
        ]]))
        f.setAttributes([202, 1000.0])
        bldg_feats.append(f)

        pr_b.addFeatures(bldg_feats)
        bldg_layer.updateExtents()

        return zone_layer, bldg_layer

    def test_calculation_english(self):
        z_lyr, b_lyr = self._create_mock_layers()
        engine = FigureGroundEngine(
            zone_layer=z_lyr,
            bldg_layer=b_lyr,
            zone_area_field="alan_m2",
            bldg_area_field="taban_m2",
            language="en",
        )
        res = engine.run_analysis(generate_centroid_points=True)
        summary = res["summary"]

        self.assertEqual(summary["total_zones"], 2)
        self.assertEqual(summary["total_buildings_assigned"], 5)
        self.assertAlmostEqual(summary["total_zone_m2"], 20000.0, delta=1.0)
        self.assertAlmostEqual(summary["total_building_footprint_m2"], 2600.0, delta=1.0)
        # 2600 / 20000 = 13.0%
        self.assertAlmostEqual(summary["overall_solid_pct"], 13.0, delta=0.1)
        self.assertAlmostEqual(summary["overall_void_pct"], 87.0, delta=0.1)

        # Check Output Layer fields
        out_layer = res["layer"]
        self.assertTrue(out_layer.isValid())
        field_names = [f.name() for f in out_layer.fields()]
        self.assertIn("solid_pct", field_names)
        self.assertIn("void_pct", field_names)
        self.assertIn("bldg_footprint_m2", field_names)

        # Check values per feature
        rows = list(out_layer.getFeatures())
        self.assertEqual(len(rows), 2)
        r1 = [r for r in rows if r["zone_id"] == 1][0]
        self.assertAlmostEqual(r1["solid_pct"], 6.0, delta=0.1)
        self.assertAlmostEqual(r1["void_pct"], 94.0, delta=0.1)
        self.assertEqual(r1["bldg_count"], 3)
        self.assertAlmostEqual(r1["bldg_footprint_m2"], 600.0, delta=1.0)

        r2 = [r for r in rows if r["zone_id"] == 2][0]
        self.assertAlmostEqual(r2["solid_pct"], 20.0, delta=0.1)
        self.assertAlmostEqual(r2["void_pct"], 80.0, delta=0.1)
        self.assertEqual(r2["bldg_count"], 2)
        self.assertAlmostEqual(r2["bldg_footprint_m2"], 2000.0, delta=1.0)

        # Check Symbology
        apply_solid_void_symbology(out_layer, "solid_pct", language="en")
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


if __name__ == "__main__":
    unittest.main()
