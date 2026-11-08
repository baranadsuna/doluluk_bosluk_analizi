#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-Ground & Solid-Void Analyzer Dialog
=========================================
Simple, accessible, and intuitive UI for urban figure-ground coverage analysis
with real-time English / Turkish language switching, EPSG:5253 support,
and Nolli-style graduated visualization.

Compatible with QGIS 3.22+ & QGIS 4.0+, Qt5 & Qt6.
"""

from typing import Any, Dict, Optional

from qgis.core import (
    QgsApplication,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsVectorLayer,
)
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from .figure_ground_engine import FigureGroundEngine, apply_solid_void_symbology
except ImportError:
    from figure_ground_engine import FigureGroundEngine, apply_solid_void_symbology

# Alignment flag helper for Qt5 / Qt6 compatibility
ALIGN_CENTER = getattr(Qt.AlignmentFlag, "AlignCenter", getattr(Qt, "AlignCenter", 0x0084))
ALIGN_RIGHT = getattr(Qt.AlignmentFlag, "AlignRight", getattr(Qt, "AlignRight", 0x0002))
ALIGN_LEFT = getattr(Qt.AlignmentFlag, "AlignLeft", getattr(Qt, "AlignLeft", 0x0001))
ALIGN_VCENTER = getattr(Qt.AlignmentFlag, "AlignVCenter", getattr(Qt, "AlignVCenter", 0x0080))

# Localization dictionary
STRINGS = {
    "en": {
        "title": "Figure-Ground & Solid-Void Analyzer",
        "subtitle": "Urban building footprint coverage & void ratio analysis (EPSG:5253)",
        "zone_group": "1. Planning Zones Layer (Bölgeler / Gri Alanlar)",
        "zone_layer_lbl": "Zones Vector Layer:",
        "zone_area_lbl": "Zone Area Field (m²):",
        "zone_auto_geom": "Use geometric area (m²) if attribute is missing or 0",
        "bldg_group": "2. Buildings Footprints Layer (Binalar / Taban Alanları)",
        "bldg_layer_lbl": "Buildings Vector Layer:",
        "bldg_area_lbl": "Footprint Area Field (m²):",
        "bldg_auto_geom": "Use geometric area (m²) if attribute is missing or 0",
        "options_group": "3. Visualization & Output Options",
        "style_chk": "Apply automatic graduated Solid-Void styling (Nolli shades)",
        "add_canvas_chk": "Add resulting layer to QGIS Map Canvas",
        "centroid_chk": "Create building centroid verification point layer",
        "output_dest_lbl": "Output Layer:",
        "output_mem": "Temporary Memory Layer",
        "output_file": "Save to File (GeoPackage)...",
        "btn_run": "Calculate Solid-Void Ratio",
        "btn_close": "Close",
        "kpi_zones": "Total Zones",
        "kpi_bldgs": "Total Buildings",
        "kpi_footprint": "Total Footprint Area",
        "kpi_zone_area": "Total Zone Area",
        "kpi_solid": "Overall Solid Ratio",
        "kpi_void": "Overall Void Ratio",
        "tbl_col_id": "Zone ID",
        "tbl_col_zm2": "Zone Area (m²)",
        "tbl_col_zha": "Zone Area (ha)",
        "tbl_col_bm2": "Building Area (m²)",
        "tbl_col_solid": "Solid / Coverage (%)",
        "tbl_col_void": "Void Ratio (%)",
        "tbl_col_count": "Building Count",
        "tbl_col_density": "Density (m²/ha)",
        "status_ready": "Ready to calculate.",
        "status_running": "Calculating figure-ground ratios...",
        "status_done": "Analysis completed successfully in EPSG:5253.",
        "err_no_zone": "Please select a valid Planning Zones layer.",
        "err_no_bldg": "Please select a valid Building Footprints layer.",
        "badge_crs": "EPSG:5253 (TUREF)",
    },
    "tr": {
        "title": "Doluluk Boşluk Oranı Analiz Aracı",
        "subtitle": "Kentsel bina taban alanı doluluk ve boşluk oranı analizi (EPSG:5253)",
        "zone_group": "1. Bölgeler / Mahalle Katmanı (Gri Alanlar)",
        "zone_layer_lbl": "Bölgeler Vektör Katmanı:",
        "zone_area_lbl": "Bölge Alanı Özniteliği (m²):",
        "zone_auto_geom": "Öznitelik boşsa alan büyüklüğünü geometriden otomatik hesapla",
        "bldg_group": "2. Binalar / Taban Alanları Katmanı (Siyah Yapılar)",
        "bldg_layer_lbl": "Binalar Vektör Katmanı:",
        "bldg_area_lbl": "Bina Taban Alanı Özniteliği (m²):",
        "bldg_auto_geom": "Öznitelik boşsa taban alanını geometriden otomatik hesapla",
        "options_group": "3. Görselleştirme ve Çıktı Ayarları",
        "style_chk": "Doluluk oranına göre otomatik dereceli renklendirme (Nolli) uygula",
        "add_canvas_chk": "Sonuç katmanını QGIS haritasına ekle",
        "centroid_chk": "Bina ağırlık merkezi doğrulama nokta katmanı üret",
        "output_dest_lbl": "Çıktı Hedefi:",
        "output_mem": "Geçici Bellek Katmanı (Memory)",
        "output_file": "Dosyaya Kaydet (GeoPackage)...",
        "btn_run": "Doluluk Boşluk Oranını Hesapla",
        "btn_close": "Kapat",
        "kpi_zones": "İncelenen Bölge",
        "kpi_bldgs": "Toplam Bina",
        "kpi_footprint": "Toplam Taban Alanı",
        "kpi_zone_area": "Toplam Bölge Alanı",
        "kpi_solid": "Genel Doluluk Oranı",
        "kpi_void": "Genel Boşluk Oranı",
        "tbl_col_id": "Bölge ID",
        "tbl_col_zm2": "Bölge Alanı (m²)",
        "tbl_col_zha": "Bölge Alanı (ha)",
        "tbl_col_bm2": "Bina Taban Alanı (m²)",
        "tbl_col_solid": "Doluluk Oranı (%)",
        "tbl_col_void": "Boşluk Oranı (%)",
        "tbl_col_count": "Bina Sayısı",
        "tbl_col_density": "Yoğunluk (m²/ha)",
        "status_ready": "Analiz için hazır.",
        "status_running": "Doluluk-boşluk oranları hesaplanıyor...",
        "status_done": "Analiz EPSG:5253 standardında başarıyla tamamlandı.",
        "err_no_zone": "Lütfen geçerli bir Bölgeler katmanı seçin.",
        "err_no_bldg": "Lütfen geçerli bir Binalar katmanı seçin.",
        "badge_crs": "EPSG:5253 (TUREF)",
    },
}


class FigureGroundDialog(QDialog):
    """Main calculation and visualization dialog for figure-ground solid-void analysis."""

    def __init__(self, parent: Optional[QWidget] = None, iface=None, language: str = "en"):
        super().__init__(parent)
        self.iface = iface
        self.cur_lang = "tr" if language.lower().startswith("tr") else "en"
        self._output_file_path: Optional[str] = None
        self._last_result_layer: Optional[QgsVectorLayer] = None

        self._init_ui()
        self._apply_translations()
        self._auto_select_layers()

    def _init_ui(self):
        self.resize(880, 720)
        self.setStyleSheet("""
            QDialog {
                background-color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 16px;
                padding-bottom: 12px;
                padding-left: 14px;
                padding-right: 14px;
                font-weight: 600;
                color: #1e293b;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding-left: 8px;
                padding-right: 8px;
                background-color: transparent;
                color: #0f172a;
            }
            QLabel {
                color: #334155;
                font-size: 12px;
            }
            QComboBox, QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                padding: 5px 8px;
                background-color: #ffffff;
                color: #0f172a;
                font-size: 12px;
                min-height: 24px;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 1.5px solid #0284c7;
            }
            QCheckBox {
                color: #334155;
                font-size: 12px;
                spacing: 6px;
            }
            QPushButton#btn_run {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0369a1);
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                min-height: 38px;
            }
            QPushButton#btn_run:hover {
                background: #0284c7;
            }
            QPushButton#btn_close {
                background-color: #e2e8f0;
                color: #334155;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 18px;
                min-height: 38px;
            }
            QPushButton#btn_close:hover {
                background-color: #cbd5e1;
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #e2e8f0;
                color: #0f172a;
                font-size: 11px;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #0284c7;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                gridline-color: #f1f5f9;
                font-size: 11.5px;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: 600;
                padding: 6px;
                border: none;
                border-bottom: 1.5px solid #cbd5e1;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        # 1. Header Banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #1e293b);
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(8, 6, 8, 6)

        title_vbox = QVBoxLayout()
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        self.lbl_subtitle = QLabel()
        self.lbl_subtitle.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.lbl_subtitle)
        h_layout.addLayout(title_vbox, stretch=1)

        # Language Selector & CRS Badge
        top_right_box = QHBoxLayout()
        top_right_box.setSpacing(8)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇹🇷 Türkçe (TR)", "tr")
        self.lang_combo.addItem("🇬🇧 English (EN)", "en")
        self.lang_combo.setCurrentIndex(0 if self.cur_lang == "tr" else 1)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        top_right_box.addWidget(self.lang_combo)

        self.crs_badge = QLabel("EPSG:5253")
        self.crs_badge.setStyleSheet("""
            QLabel {
                background-color: #0369a1;
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        top_right_box.addWidget(self.crs_badge)
        h_layout.addLayout(top_right_box)
        main_layout.addWidget(header_frame)

        # 2. Section 1: Planning Zones Layer
        self.grp_zones = QGroupBox()
        z_layout = QGridLayout(self.grp_zones)
        z_layout.setSpacing(8)

        self.lbl_z_layer = QLabel()
        self.combo_z_layer = QgsMapLayerComboBox()
        # Filter polygon layers
        poly_filter = getattr(QgsMapLayerProxyModel.Filter, "PolygonLayer", 0x0004)
        self.combo_z_layer.setFilters(poly_filter)

        self.lbl_z_field = QLabel()
        self.combo_z_field = QgsFieldComboBox()
        self.combo_z_field.setLayer(self.combo_z_layer.currentLayer())
        self.combo_z_field.setAllowEmptyFieldName(True)

        self.combo_z_layer.layerChanged.connect(self.combo_z_field.setLayer)
        self.combo_z_layer.layerChanged.connect(self._auto_detect_zone_field)

        self.chk_z_auto_geom = QCheckBox()
        self.chk_z_auto_geom.setChecked(True)

        z_layout.addWidget(self.lbl_z_layer, 0, 0)
        z_layout.addWidget(self.combo_z_layer, 0, 1)
        z_layout.addWidget(self.lbl_z_field, 1, 0)
        z_layout.addWidget(self.combo_z_field, 1, 1)
        z_layout.addWidget(self.chk_z_auto_geom, 2, 0, 1, 2)
        main_layout.addWidget(self.grp_zones)

        # 3. Section 2: Building Footprints Layer
        self.grp_bldgs = QGroupBox()
        b_layout = QGridLayout(self.grp_bldgs)
        b_layout.setSpacing(8)

        self.lbl_b_layer = QLabel()
        self.combo_b_layer = QgsMapLayerComboBox()
        self.combo_b_layer.setFilters(poly_filter)

        self.lbl_b_field = QLabel()
        self.combo_b_field = QgsFieldComboBox()
        self.combo_b_field.setLayer(self.combo_b_layer.currentLayer())
        self.combo_b_field.setAllowEmptyFieldName(True)

        self.combo_b_layer.layerChanged.connect(self.combo_b_field.setLayer)
        self.combo_b_layer.layerChanged.connect(self._auto_detect_bldg_field)

        self.chk_b_auto_geom = QCheckBox()
        self.chk_b_auto_geom.setChecked(True)

        b_layout.addWidget(self.lbl_b_layer, 0, 0)
        b_layout.addWidget(self.combo_b_layer, 0, 1)
        b_layout.addWidget(self.lbl_b_field, 1, 0)
        b_layout.addWidget(self.combo_b_field, 1, 1)
        b_layout.addWidget(self.chk_b_auto_geom, 2, 0, 1, 2)
        main_layout.addWidget(self.grp_bldgs)

        # 4. Section 3: Visualization & Output Options
        self.grp_opts = QGroupBox()
        opts_layout = QGridLayout(self.grp_opts)
        opts_layout.setSpacing(8)

        self.chk_style = QCheckBox()
        self.chk_style.setChecked(True)
        self.chk_add_canvas = QCheckBox()
        self.chk_add_canvas.setChecked(True)
        self.chk_centroids = QCheckBox()
        self.chk_centroids.setChecked(False)

        opts_layout.addWidget(self.chk_style, 0, 0)
        opts_layout.addWidget(self.chk_add_canvas, 0, 1)
        opts_layout.addWidget(self.chk_centroids, 1, 0, 1, 2)
        main_layout.addWidget(self.grp_opts)

        # 5. KPI Cards Frame (Dynamic Summary)
        self.kpi_frame = QFrame()
        self.kpi_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        kpi_grid = QGridLayout(self.kpi_frame)
        kpi_grid.setSpacing(10)

        self.kpi_card_zones = self._create_kpi_card("Total Zones", "-")
        self.kpi_card_bldgs = self._create_kpi_card("Total Buildings", "-")
        self.kpi_card_footprint = self._create_kpi_card("Building Footprint", "-")
        self.kpi_card_solid = self._create_kpi_card("Solid Ratio (%)", "-", highlight=True)
        self.kpi_card_void = self._create_kpi_card("Void Ratio (%)", "-")

        kpi_grid.addWidget(self.kpi_card_zones["widget"], 0, 0)
        kpi_grid.addWidget(self.kpi_card_bldgs["widget"], 0, 1)
        kpi_grid.addWidget(self.kpi_card_footprint["widget"], 0, 2)
        kpi_grid.addWidget(self.kpi_card_solid["widget"], 0, 3)
        kpi_grid.addWidget(self.kpi_card_void["widget"], 0, 4)
        main_layout.addWidget(self.kpi_frame)

        # 6. Results Table
        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMaximumHeight(160)
        main_layout.addWidget(self.table)

        # 7. Progress & Status
        prog_vbox = QVBoxLayout()
        prog_vbox.setSpacing(4)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        prog_vbox.addWidget(self.progress_bar)
        prog_vbox.addWidget(self.lbl_status)
        main_layout.addLayout(prog_vbox)

        # 8. Bottom Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_run = QPushButton()
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self._run_calculation)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self.close)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_close)
        main_layout.addLayout(btn_layout)

    def _create_kpi_card(self, title: str, value: str, highlight: bool = False) -> Dict[str, Any]:
        card = QFrame()
        bg_col = "#e0f2fe" if highlight else "#f8fafc"
        border_col = "#0284c7" if highlight else "#e2e8f0"
        val_col = "#0369a1" if highlight else "#0f172a"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 6px;
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 600;")
        lbl_t.setAlignment(ALIGN_CENTER)

        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"font-size: 14px; color: {val_col}; font-weight: bold;")
        lbl_v.setAlignment(ALIGN_CENTER)

        vbox.addWidget(lbl_t)
        vbox.addWidget(lbl_v)
        return {"widget": card, "title_lbl": lbl_t, "value_lbl": lbl_v}

    def _apply_translations(self):
        t = STRINGS[self.cur_lang]
        self.setWindowTitle(t["title"] + " (EPSG:5253)")
        self.lbl_title.setText(t["title"])
        self.lbl_subtitle.setText(t["subtitle"])
        self.crs_badge.setText(t["badge_crs"])

        self.grp_zones.setTitle(t["zone_group"])
        self.lbl_z_layer.setText(t["zone_layer_lbl"])
        self.lbl_z_field.setText(t["zone_area_lbl"])
        self.chk_z_auto_geom.setText(t["zone_auto_geom"])

        self.grp_bldgs.setTitle(t["bldg_group"])
        self.lbl_b_layer.setText(t["bldg_layer_lbl"])
        self.lbl_b_field.setText(t["bldg_area_lbl"])
        self.chk_b_auto_geom.setText(t["bldg_auto_geom"])

        self.grp_opts.setTitle(t["options_group"])
        self.chk_style.setText(t["style_chk"])
        self.chk_add_canvas.setText(t["add_canvas_chk"])
        self.chk_centroids.setText(t["centroid_chk"])

        self.btn_run.setText(t["btn_run"])
        self.btn_close.setText(t["btn_close"])
        self.lbl_status.setText(t["status_ready"])

        # Update KPI Titles
        self.kpi_card_zones["title_lbl"].setText(t["kpi_zones"])
        self.kpi_card_bldgs["title_lbl"].setText(t["kpi_bldgs"])
        self.kpi_card_footprint["title_lbl"].setText(t["kpi_footprint"])
        self.kpi_card_solid["title_lbl"].setText(t["kpi_solid"])
        self.kpi_card_void["title_lbl"].setText(t["kpi_void"])

        # Update Table Headers
        headers = [
            t["tbl_col_id"],
            t["tbl_col_zm2"],
            t["tbl_col_zha"],
            t["tbl_col_bm2"],
            t["tbl_col_solid"],
            t["tbl_col_void"],
            t["tbl_col_count"],
        ]
        self.table.setHorizontalHeaderLabels(headers)

    def _on_lang_changed(self, index: int):
        self.cur_lang = self.lang_combo.currentData()
        self._apply_translations()

    def _auto_select_layers(self):
        """Pre-select likely layers based on TOC layer names."""
        project = QgsProject.instance()
        layers = project.mapLayers().values()

        zone_candidates = ["kirilganlik", "parca", "bolge", "zone", "mahalle", "sinir"]
        bldg_candidates = ["yapi", "bina", "tire_yapilar", "building", "footprint"]

        for lyr in layers:
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == 2:  # Polygon
                name_lower = lyr.name().lower()
                for c in zone_candidates:
                    if c in name_lower and self.combo_z_layer.currentLayer() is None:
                        self.combo_z_layer.setLayer(lyr)
                        break
                for b in bldg_candidates:
                    if b in name_lower and self.combo_b_layer.currentLayer() is None:
                        self.combo_b_layer.setLayer(lyr)
                        break

        self._auto_detect_zone_field()
        self._auto_detect_bldg_field()

    def _auto_detect_zone_field(self):
        lyr = self.combo_z_layer.currentLayer()
        if not lyr:
            return
        fields = [f.name().lower() for f in lyr.fields()]
        candidates = ["m2", "alan_m2", "alan", "area_m2", "area", "hektar", "ha"]
        for c in candidates:
            for f in lyr.fields():
                if c == f.name().lower():
                    self.combo_z_field.setField(f.name())
                    return

    def _auto_detect_bldg_field(self):
        lyr = self.combo_b_layer.currentLayer()
        if not lyr:
            return
        candidates = ["taban_alani", "taban_m2", "bina_m2", "m2", "alan", "area"]
        for c in candidates:
            for f in lyr.fields():
                if c == f.name().lower():
                    self.combo_b_field.setField(f.name())
                    return

    def _feedback_cb(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)
        QgsApplication.processEvents()

    def _run_calculation(self):
        t = STRINGS[self.cur_lang]
        z_layer = self.combo_z_layer.currentLayer()
        b_layer = self.combo_b_layer.currentLayer()

        if not z_layer or not z_layer.isValid():
            QMessageBox.warning(self, "Warning", t["err_no_zone"])
            return
        if not b_layer or not b_layer.isValid():
            QMessageBox.warning(self, "Warning", t["err_no_bldg"])
            return

        self.btn_run.setEnabled(False)
        self.progress_bar.setValue(5)
        self.lbl_status.setText(t["status_running"])
        QgsApplication.processEvents()

        try:
            engine = FigureGroundEngine(
                zone_layer=z_layer,
                bldg_layer=b_layer,
                zone_area_field=self.combo_z_field.currentField(),
                bldg_area_field=self.combo_b_field.currentField(),
                auto_calc_zone_geom=self.chk_z_auto_geom.isChecked(),
                auto_calc_bldg_geom=self.chk_b_auto_geom.isChecked(),
                target_crs_authid="EPSG:5253",
                language=self.cur_lang,
            )

            res = engine.run_analysis(
                feedback_cb=self._feedback_cb,
                output_file_path=self._output_file_path,
                generate_centroid_points=self.chk_centroids.isChecked(),
            )

            out_layer = res["layer"]
            summary = res["summary"]

            # Symbology
            if self.chk_style.isChecked():
                apply_solid_void_symbology(out_layer, res["solid_field"], language=self.cur_lang)

            # Add to canvas
            if self.chk_add_canvas.isChecked():
                project = QgsProject.instance()
                project.addMapLayer(out_layer)
                if res["centroid_layer"]:
                    project.addMapLayer(res["centroid_layer"])

            self._last_result_layer = out_layer

            # Update KPI Cards
            self.kpi_card_zones["value_lbl"].setText(f"{summary['total_zones']:,}")
            self.kpi_card_bldgs["value_lbl"].setText(f"{summary['total_buildings_assigned']:,}")
            self.kpi_card_footprint["value_lbl"].setText(
                f"{summary['total_building_footprint_m2']:,.1f} m²\n({summary['total_building_footprint_ha']:.2f} ha)"
            )
            self.kpi_card_solid["value_lbl"].setText(f"%{summary['overall_solid_pct']:.2f}")
            self.kpi_card_void["value_lbl"].setText(f"%{summary['overall_void_pct']:.2f}")

            # Populate Results Table
            rows = summary["rows"]
            self.table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                id_item = QTableWidgetItem(str(r["zone_id"]))
                zm2_item = QTableWidgetItem(f"{r['zone_m2']:,.2f}")
                zha_item = QTableWidgetItem(f"{r['zone_ha']:.4f}")
                bm2_item = QTableWidgetItem(f"{r['bldg_m2']:,.2f}")
                sol_item = QTableWidgetItem(f"%{r['solid_pct']:.2f}")
                void_item = QTableWidgetItem(f"%{r['void_pct']:.2f}")
                cnt_item = QTableWidgetItem(str(r["bldg_count"]))

                id_item.setTextAlignment(ALIGN_CENTER)
                zm2_item.setTextAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
                zha_item.setTextAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
                bm2_item.setTextAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
                sol_item.setTextAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
                void_item.setTextAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
                cnt_item.setTextAlignment(ALIGN_CENTER)

                self.table.setItem(idx, 0, id_item)
                self.table.setItem(idx, 1, zm2_item)
                self.table.setItem(idx, 2, zha_item)
                self.table.setItem(idx, 3, bm2_item)
                self.table.setItem(idx, 4, sol_item)
                self.table.setItem(idx, 5, void_item)
                self.table.setItem(idx, 6, cnt_item)

            self.table.resizeColumnsToContents()
            self.lbl_status.setText(t["status_done"])

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"An error occurred during analysis:\n{str(exc)}")
            self.lbl_status.setText(f"Error: {str(exc)}")
        finally:
            self.btn_run.setEnabled(True)


    def exec(self) -> int:
        """Qt6 and QGIS 4 compatible exec shim."""
        exec_func = getattr(super(), "exec", None)
        if callable(exec_func):
            return exec_func()
        exec_old = getattr(super(), "exec_", None)
        if callable(exec_old):
            return exec_old()
        return 0

    def exec_(self) -> int:
        return self.exec()
