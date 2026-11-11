#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure-Ground & Solid-Void Analyzer Dialog
=========================================
Modern, responsive, and intuitive interface for urban figure-ground coverage analysis.
Provides real-time 4-language switching (English, Turkish, Chinese, Indonesian),
EPSG:5253 planar accuracy, adaptive graduated styling (Urban Heatmap, Nolli Grayscale,
Eco-Traffic), and support for both spatial overlay aggregation and direct attribute modes.

Compatible with QGIS 3.22+ & QGIS 4.0+, Qt5 & Qt6.
"""

import csv
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
    QAbstractItemView,
    QApplication,
    QButtonGroup,
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
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
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

# Localization dictionary for 4 languages: English, Turkish, Chinese, Indonesian
STRINGS = {
    "en": {
        "title": "Figure-Ground & Solid-Void Analyzer",
        "subtitle": "Building footprint coverage & void ratio analysis (EPSG:5253)",
        "tab_params": "Parameters",
        "tab_results": "Results & Statistics",
        "mode_group": "Analysis Mode",
        "mode_spatial": "Spatial Overlay (Zones + Buildings Layer)",
        "mode_direct": "Direct Attribute (Calculate from Zone Layer Fields)",
        "zone_group": "Planning Zones",
        "zone_layer_lbl": "Zone Layer:",
        "zone_area_lbl": "Zone Area Field (m²):",
        "zone_auto_geom": "Compute area from geometry if attribute is missing",
        "bldg_group": "Building Footprints",
        "bldg_layer_lbl": "Buildings Layer:",
        "bldg_area_lbl": "Footprint Area Field (m²):",
        "bldg_auto_geom": "Compute footprint from geometry if attribute is missing",
        "direct_bldg_lbl": "Total Building Footprint Field (m²):",
        "options_group": "Display & Output Options",
        "palette_lbl": "Color Scheme:",
        "pal_urban": "Urban Density Heatmap (Amber - Crimson)",
        "pal_nolli": "Architectural Nolli (Monochrome Grayscale)",
        "pal_eco": "Eco-Morphology (Green - Yellow - Red)",
        "style_chk": "Apply adaptive graduated styling",
        "add_canvas_chk": "Add resulting layer to map canvas",
        "centroid_chk": "Generate building centroid verification points",
        "output_dest_lbl": "Destination:",
        "output_mem": "Temporary memory layer",
        "output_file": "Save to GeoPackage (*.gpkg)",
        "btn_browse": "Browse...",
        "btn_run": "Calculate Solid-Void",
        "btn_close": "Close",
        "btn_copy": "Copy Table",
        "btn_export_csv": "Export CSV",
        "kpi_solid": "Coverage / Solid",
        "kpi_void": "Void Ratio",
        "kpi_bldgs": "Buildings",
        "kpi_footprint": "Footprint Area",
        "kpi_zone_area": "Zone Area",
        "tbl_col_id": "Zone ID",
        "tbl_col_zm2": "Zone Area (m²)",
        "tbl_col_zha": "Zone Area (ha)",
        "tbl_col_bm2": "Footprint (m²)",
        "tbl_col_solid": "Solid (%)",
        "tbl_col_void": "Void (%)",
        "tbl_col_count": "Count",
        "tbl_col_density": "Density (m²/ha)",
        "status_ready": "Ready to calculate.",
        "status_running": "Calculating figure-ground ratios...",
        "status_done": "Analysis completed successfully in EPSG:5253.",
        "err_no_zone": "Please select a valid Planning Zones layer.",
        "err_no_bldg": "Please select a valid Building Footprints layer.",
        "badge_crs": "EPSG:5253",
        "copied_clipboard": "Results table copied to clipboard.",
        "export_success": "Results successfully exported to:\n{}",
    },
    "tr": {
        "title": "Doluluk Boşluk Oranı Analiz Aracı",
        "subtitle": "Kentsel bina taban alanı doluluk ve boşluk oranı analizi (EPSG:5253)",
        "tab_params": "Parametreler",
        "tab_results": "Sonuçlar ve İstatistikler",
        "mode_group": "Analiz Modu",
        "mode_spatial": "Mekânsal Kesişim (Bölgeler + Binalar Katmanı)",
        "mode_direct": "Doğrudan Öznitelik (Bölge Katmanı Alanlarından)",
        "zone_group": "Planlama Bölgeleri",
        "zone_layer_lbl": "Bölge Katmanı:",
        "zone_area_lbl": "Bölge Alanı Özniteliği (m²):",
        "zone_auto_geom": "Öznitelik boşsa alan büyüklüğünü geometriden hesapla",
        "bldg_group": "Bina Taban Alanları",
        "bldg_layer_lbl": "Binalar Katmanı:",
        "bldg_area_lbl": "Taban Alanı Özniteliği (m²):",
        "bldg_auto_geom": "Öznitelik boşsa taban alanını geometriden hesapla",
        "direct_bldg_lbl": "Toplam Bina Taban Alanı Özniteliği (m²):",
        "options_group": "Görselleştirme ve Çıktı Ayarları",
        "palette_lbl": "Renk Paleti:",
        "pal_urban": "Kentsel Yoğunluk Sıcak Renkler (Sarı - Kızıl)",
        "pal_nolli": "Klasik Nolli Morfoloji (Siyah - Beyaz)",
        "pal_eco": "Ekolojik Yoğunluk (Yeşil - Sarı - Kırmızı)",
        "style_chk": "Uyumlu dereceli doluluk renklendirmesini uygula",
        "add_canvas_chk": "Sonuç katmanını haritaya ekle",
        "centroid_chk": "Bina ağırlık merkezi doğrulama noktaları üret",
        "output_dest_lbl": "Çıktı Hedefi:",
        "output_mem": "Geçici bellek katmanı (Memory)",
        "output_file": "GeoPackage olarak kaydet (*.gpkg)",
        "btn_browse": "Gözat...",
        "btn_run": "Doluluk-Boşluk Hesapla",
        "btn_close": "Kapat",
        "btn_copy": "Tabloyu Kopyala",
        "btn_export_csv": "CSV Olarak Kaydet",
        "kpi_solid": "Genel Doluluk",
        "kpi_void": "Genel Boşluk",
        "kpi_bldgs": "Bina Sayısı",
        "kpi_footprint": "Taban Alanı",
        "kpi_zone_area": "Bölge Alanı",
        "tbl_col_id": "Bölge ID",
        "tbl_col_zm2": "Bölge Alanı (m²)",
        "tbl_col_zha": "Bölge Alanı (ha)",
        "tbl_col_bm2": "Bina Taban Alanı (m²)",
        "tbl_col_solid": "Doluluk (%)",
        "tbl_col_void": "Boşluk (%)",
        "tbl_col_count": "Bina Adedi",
        "tbl_col_density": "Yoğunluk (m²/ha)",
        "status_ready": "Analiz için hazır.",
        "status_running": "Doluluk-boşluk oranları hesaplanıyor...",
        "status_done": "Analiz EPSG:5253 standardında başarıyla tamamlandı.",
        "err_no_zone": "Lütfen geçerli bir Bölgeler katmanı seçin.",
        "err_no_bldg": "Lütfen geçerli bir Binalar katmanı seçin.",
        "badge_crs": "EPSG:5253",
        "copied_clipboard": "Sonuç tablosu panoya kopyalandı.",
        "export_success": "Sonuçlar başarıyla kaydedildi:\n{}",
    },
    "zh": {
        "title": "图底与实虚比分析工具",
        "subtitle": "城市建筑基底覆盖率与开敞空间空隙率分析 (EPSG:5253)",
        "tab_params": "参数设置",
        "tab_results": "分析结果与统计",
        "mode_group": "分析模式",
        "mode_spatial": "空间叠置聚合 (片区图层 + 建筑基底图层)",
        "mode_direct": "直接属性计算 (由片区图层内部字段直接计算)",
        "zone_group": "规划片区图层",
        "zone_layer_lbl": "片区矢量图层:",
        "zone_area_lbl": "片区面积字段 (m²):",
        "zone_auto_geom": "若属性为空则自动根据几何图形计算面积",
        "bldg_group": "建筑基底图层",
        "bldg_layer_lbl": "建筑矢量图层:",
        "bldg_area_lbl": "基底面积字段 (m²):",
        "bldg_auto_geom": "若属性为空则自动根据几何图形计算基底",
        "direct_bldg_lbl": "建筑总基底面积字段 (m²):",
        "options_group": "显示与输出选项",
        "palette_lbl": "色彩方案:",
        "pal_urban": "城市密度热力图 (暖橙 - 猩红)",
        "pal_nolli": "经典诺利图 (建筑灰度黑白)",
        "pal_eco": "生态形态分级 (浅绿 - 明黄 - 艳红)",
        "style_chk": "应用自适应分级色彩渲染",
        "add_canvas_chk": "添加分析结果至地图画布",
        "centroid_chk": "生成建筑质心校验点图层",
        "output_dest_lbl": "输出目标:",
        "output_mem": "临时内存图层",
        "output_file": "保存为 GeoPackage (*.gpkg)",
        "btn_browse": "浏览...",
        "btn_run": "计算实虚比 / 覆盖率",
        "btn_close": "关闭",
        "btn_copy": "复制表格",
        "btn_export_csv": "导出 CSV",
        "kpi_solid": "建筑覆盖率 (实)",
        "kpi_void": "空间空隙率 (虚)",
        "kpi_bldgs": "建筑数量",
        "kpi_footprint": "总基底面积",
        "kpi_zone_area": "片区总面积",
        "tbl_col_id": "片区编号",
        "tbl_col_zm2": "片区面积 (m²)",
        "tbl_col_zha": "片区面积 (ha)",
        "tbl_col_bm2": "基底面积 (m²)",
        "tbl_col_solid": "覆盖率 (%)",
        "tbl_col_void": "空隙率 (%)",
        "tbl_col_count": "建筑总数",
        "tbl_col_density": "密度 (m²/ha)",
        "status_ready": "准备就绪。",
        "status_running": "正在精确计算图底与实虚比...",
        "status_done": "分析已在 EPSG:5253 坐标系下成功完成。",
        "err_no_zone": "请选择有效的规划片区图层。",
        "err_no_bldg": "请选择有效的建筑基底图层。",
        "badge_crs": "EPSG:5253",
        "copied_clipboard": "结果表格已成功复制到剪贴板。",
        "export_success": "结果已成功导出至:\n{}",
    },
    "id": {
        "title": "Alat Analisis Solid-Void & Figure-Ground",
        "subtitle": "Analisis tutupan tapak bangunan dan rasio ruang terbuka kota (EPSG:5253)",
        "tab_params": "Parameter",
        "tab_results": "Hasil & Statistik",
        "mode_group": "Mode Analisis",
        "mode_spatial": "Agregasi Spasial (Lapisan Zona + Lapisan Bangunan)",
        "mode_direct": "Atribut Langsung (Hitung dari Kolom Lapisan Zona)",
        "zone_group": "Zona Perencanaan",
        "zone_layer_lbl": "Lapisan Zona:",
        "zone_area_lbl": "Kolom Luas Zona (m²):",
        "zone_auto_geom": "Hitung luas dari geometri jika atribut kosong",
        "bldg_group": "Tapak Bangunan (Footprint)",
        "bldg_layer_lbl": "Lapisan Bangunan:",
        "bldg_area_lbl": "Kolom Luas Tapak (m²):",
        "bldg_auto_geom": "Hitung tapak dari geometri jika atribut kosong",
        "direct_bldg_lbl": "Kolom Total Tapak Bangunan (m²):",
        "options_group": "Opsi Tampilan & Keluaran",
        "palette_lbl": "Skema Warna:",
        "pal_urban": "Kepadatan Kota (Gradasi Oranye - Merah)",
        "pal_nolli": "Monokrom Nolli Klasik (Abu-abu / Hitam)",
        "pal_eco": "Eko-Morfologi (Hijau - Kuning - Merah)",
        "style_chk": "Terapkan pewarnaan bertingkat adaptif",
        "add_canvas_chk": "Tambahkan lapisan hasil ke peta QGIS",
        "centroid_chk": "Hasilkan titik sentroid verifikasi bangunan",
        "output_dest_lbl": "Tujuan Keluaran:",
        "output_mem": "Lapisan memori sementara",
        "output_file": "Simpan ke GeoPackage (*.gpkg)",
        "btn_browse": "Telusuri...",
        "btn_run": "Hitung Rasio Solid-Void",
        "btn_close": "Tutup",
        "btn_copy": "Salin Tabel",
        "btn_export_csv": "Ekspor CSV",
        "kpi_solid": "Rasio Solid / KDB",
        "kpi_void": "Rasio Void (Terbuka)",
        "kpi_bldgs": "Jumlah Bangunan",
        "kpi_footprint": "Total Luas Tapak",
        "kpi_zone_area": "Total Luas Zona",
        "tbl_col_id": "ID Zona",
        "tbl_col_zm2": "Luas Zona (m²)",
        "tbl_col_zha": "Luas Zona (ha)",
        "tbl_col_bm2": "Luas Tapak (m²)",
        "tbl_col_solid": "Solid (%)",
        "tbl_col_void": "Void (%)",
        "tbl_col_count": "Jml Bangunan",
        "tbl_col_density": "Kepadatan (m²/ha)",
        "status_ready": "Siap melakukan analisis.",
        "status_running": "Menghitung rasio solid-void...",
        "status_done": "Analisis berhasil diselesaikan dalam EPSG:5253.",
        "err_no_zone": "Silakan pilih lapisan Zona Perencanaan yang valid.",
        "err_no_bldg": "Silakan pilih lapisan Tapak Bangunan yang valid.",
        "badge_crs": "EPSG:5253",
        "copied_clipboard": "Tabel hasil berhasil disalin ke papan klip.",
        "export_success": "Hasil berhasil diekspor ke:\n{}",
    },
}


class FigureGroundDialog(QDialog):
    """Modern, responsive calculation and visualization dialog for figure-ground solid-void analysis."""

    def __init__(self, parent: Optional[QWidget] = None, iface=None, language: str = "en"):
        super().__init__(parent)
        self.iface = iface
        lang_code = str(language).lower()[:2]
        self.cur_lang = lang_code if lang_code in ("en", "tr", "zh", "id") else "en"
        self._output_file_path: Optional[str] = None
        self._last_result_layer: Optional[QgsVectorLayer] = None
        self._last_summary: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._apply_translations()
        self._auto_select_layers()

    def _init_ui(self):
        # Responsive sizing: fits 1080p laptops with 125%-150% scaling, and can shrink to 520x460
        self.setMinimumSize(540, 480)
        self.resize(650, 560)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding if hasattr(QSizePolicy, "Policy") else QSizePolicy.Expanding,
            QSizePolicy.Policy.Expanding if hasattr(QSizePolicy, "Policy") else QSizePolicy.Expanding,
        )

        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                background-color: #ffffff;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f1f5f9;
                color: #64748b;
                padding: 7px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #e2e8f0;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0f172a;
                border-color: #cbd5e1;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e2e8f0;
                color: #1e293b;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 7px;
                margin-top: 8px;
                padding-top: 12px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                font-weight: 600;
                color: #0f172a;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding-left: 6px;
                padding-right: 6px;
                background-color: #ffffff;
                color: #1e293b;
            }
            QLabel {
                color: #334155;
                font-size: 11.5px;
            }
            QComboBox, QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                padding: 4px 8px;
                background-color: #ffffff;
                color: #0f172a;
                font-size: 12px;
                min-height: 22px;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 1.5px solid #2563eb;
            }
            QCheckBox, QRadioButton {
                color: #334155;
                font-size: 11.5px;
                spacing: 6px;
            }
            QPushButton#btn_run {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                min-height: 32px;
            }
            QPushButton#btn_run:hover {
                background: #1d4ed8;
            }
            QPushButton#btn_run:pressed {
                background: #1e40af;
            }
            QPushButton#btn_run:disabled {
                background: #94a3b8;
            }
            QPushButton#btn_close {
                background-color: #f1f5f9;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 16px;
                min-height: 32px;
            }
            QPushButton#btn_close:hover {
                background-color: #e2e8f0;
                color: #0f172a;
            }
            QPushButton.secondary-btn {
                background-color: #f8fafc;
                color: #334155;
                font-size: 11.5px;
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                padding: 4px 10px;
            }
            QPushButton.secondary-btn:hover {
                background-color: #e2e8f0;
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                background-color: #f1f5f9;
                color: #0f172a;
                font-size: 10.5px;
                font-weight: 600;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                gridline-color: #f1f5f9;
                font-size: 11.5px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: 600;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #cbd5e1;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # ---------------------------------------------------------
        # 1. Header Banner with 4-Language Selector
        # ---------------------------------------------------------
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #1e293b);
                border-radius: 7px;
                padding: 6px 12px;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(4, 2, 4, 2)
        h_layout.setSpacing(10)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        self.lbl_subtitle = QLabel()
        self.lbl_subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.lbl_subtitle)
        h_layout.addLayout(title_vbox, stretch=1)

        # Top Controls: 4 Languages + CRS Badge
        top_controls = QHBoxLayout()
        top_controls.setSpacing(6)

        self.lang_combo = QComboBox()
        # Keep index 0=TR, 1=EN for backward compatibility with test_smoke and scripts
        self.lang_combo.addItem("🇹🇷 Türkçe (TR)", "tr")
        self.lang_combo.addItem("🇬🇧 English (EN)", "en")
        self.lang_combo.addItem("🇨🇳 简体中文 (ZH)", "zh")
        self.lang_combo.addItem("🇮🇩 Bahasa Indonesia (ID)", "id")

        if self.cur_lang == "tr":
            init_idx = 0
        elif self.cur_lang == "zh":
            init_idx = 2
        elif self.cur_lang == "id":
            init_idx = 3
        else:
            init_idx = 1
        self.lang_combo.setCurrentIndex(init_idx)

        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 5px;
                padding: 3px 8px;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        top_controls.addWidget(self.lang_combo)

        self.crs_badge = QLabel("EPSG:5253")
        self.crs_badge.setStyleSheet("""
            QLabel {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                font-size: 10.5px;
                border-radius: 4px;
                padding: 3px 7px;
            }
        """)
        top_controls.addWidget(self.crs_badge)
        h_layout.addLayout(top_controls)
        root_layout.addWidget(header_frame)

        # ---------------------------------------------------------
        # 2. Main Tabs
        # ---------------------------------------------------------
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        # ---- Tab 1: Parameters ----
        self.tab_params = QWidget()
        params_scroll = QScrollArea()
        params_scroll.setWidgetResizable(True)
        params_scroll.setFrameShape(
            QFrame.Shape.NoFrame if hasattr(QFrame, "Shape") else QFrame.NoFrame
        )
        params_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        params_inner = QWidget()
        params_layout = QVBoxLayout(params_inner)
        params_layout.setContentsMargins(4, 4, 4, 4)
        params_layout.setSpacing(8)

        # Mode Selection Card
        self.grp_mode = QGroupBox()
        mode_box = QHBoxLayout(self.grp_mode)
        mode_box.setContentsMargins(8, 6, 8, 6)
        self.rb_mode_spatial = QRadioButton()
        self.rb_mode_spatial.setChecked(True)
        self.rb_mode_direct = QRadioButton()

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_mode_spatial, 0)
        self.mode_group.addButton(self.rb_mode_direct, 1)
        self.rb_mode_spatial.toggled.connect(self._on_mode_changed)

        mode_box.addWidget(self.rb_mode_spatial)
        mode_box.addWidget(self.rb_mode_direct)
        mode_box.addStretch(1)
        params_layout.addWidget(self.grp_mode)

        poly_filter = getattr(QgsMapLayerProxyModel.Filter, "PolygonLayer", 0x0004)

        # Group 1: Planning Zones
        self.grp_zones = QGroupBox()
        z_grid = QGridLayout(self.grp_zones)
        z_grid.setContentsMargins(8, 8, 8, 8)
        z_grid.setSpacing(6)

        self.lbl_z_layer = QLabel()
        self.combo_z_layer = QgsMapLayerComboBox()
        self.combo_z_layer.setFilters(poly_filter)

        self.lbl_z_field = QLabel()
        self.combo_z_field = QgsFieldComboBox()
        self.combo_z_field.setLayer(self.combo_z_layer.currentLayer())
        self.combo_z_field.setAllowEmptyFieldName(True)

        self.combo_z_layer.layerChanged.connect(self.combo_z_field.setLayer)
        self.combo_z_layer.layerChanged.connect(self._auto_detect_zone_field)

        self.chk_z_auto_geom = QCheckBox()
        self.chk_z_auto_geom.setChecked(True)

        z_grid.addWidget(self.lbl_z_layer, 0, 0)
        z_grid.addWidget(self.combo_z_layer, 0, 1)
        z_grid.addWidget(self.lbl_z_field, 1, 0)
        z_grid.addWidget(self.combo_z_field, 1, 1)
        z_grid.addWidget(self.chk_z_auto_geom, 2, 0, 1, 2)
        z_grid.setColumnStretch(1, 1)
        params_layout.addWidget(self.grp_zones)

        # Group 2: Building Footprints (For Spatial Mode)
        self.grp_bldgs = QGroupBox()
        b_grid = QGridLayout(self.grp_bldgs)
        b_grid.setContentsMargins(8, 8, 8, 8)
        b_grid.setSpacing(6)

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

        b_grid.addWidget(self.lbl_b_layer, 0, 0)
        b_grid.addWidget(self.combo_b_layer, 0, 1)
        b_grid.addWidget(self.lbl_b_field, 1, 0)
        b_grid.addWidget(self.combo_b_field, 1, 1)
        b_grid.addWidget(self.chk_b_auto_geom, 2, 0, 1, 2)
        b_grid.setColumnStretch(1, 1)
        params_layout.addWidget(self.grp_bldgs)

        # Direct Mode Building Field (Shown when Direct Mode is selected)
        self.grp_direct = QGroupBox()
        d_grid = QGridLayout(self.grp_direct)
        d_grid.setContentsMargins(8, 8, 8, 8)
        d_grid.setSpacing(6)
        self.lbl_direct_bldg = QLabel()
        self.combo_direct_bldg = QgsFieldComboBox()
        self.combo_direct_bldg.setLayer(self.combo_z_layer.currentLayer())
        self.combo_direct_bldg.setAllowEmptyFieldName(False)
        self.combo_z_layer.layerChanged.connect(self.combo_direct_bldg.setLayer)
        d_grid.addWidget(self.lbl_direct_bldg, 0, 0)
        d_grid.addWidget(self.combo_direct_bldg, 0, 1)
        d_grid.setColumnStretch(1, 1)
        self.grp_direct.setVisible(False)
        params_layout.addWidget(self.grp_direct)

        # Group 3: Options, Palette & Destination
        self.grp_opts = QGroupBox()
        opts_layout = QVBoxLayout(self.grp_opts)
        opts_layout.setContentsMargins(8, 8, 8, 8)
        opts_layout.setSpacing(6)

        # Color scheme selector
        pal_row = QHBoxLayout()
        pal_row.setSpacing(6)
        self.lbl_palette = QLabel()
        self.combo_palette = QComboBox()
        self.combo_palette.addItem("Urban Density Heatmap (Amber - Crimson)", "urban_warm")
        self.combo_palette.addItem("Architectural Nolli (Monochrome Grayscale)", "nolli_grayscale")
        self.combo_palette.addItem("Eco-Morphology (Green - Yellow - Red)", "eco_traffic")
        pal_row.addWidget(self.lbl_palette)
        pal_row.addWidget(self.combo_palette, stretch=1)
        opts_layout.addLayout(pal_row)

        chk_row = QHBoxLayout()
        self.chk_style = QCheckBox()
        self.chk_style.setChecked(True)
        self.chk_add_canvas = QCheckBox()
        self.chk_add_canvas.setChecked(True)
        chk_row.addWidget(self.chk_style)
        chk_row.addWidget(self.chk_add_canvas)
        opts_layout.addLayout(chk_row)

        self.chk_centroids = QCheckBox()
        self.chk_centroids.setChecked(False)
        opts_layout.addWidget(self.chk_centroids)

        # Destination line
        dest_box = QHBoxLayout()
        dest_box.setSpacing(6)
        self.lbl_output_dest = QLabel()
        self.rb_mem = QRadioButton()
        self.rb_mem.setChecked(True)
        self.rb_file = QRadioButton()
        self.txt_file = QLineEdit()
        self.txt_file.setPlaceholderText("output.gpkg")
        self.txt_file.setEnabled(False)
        self.btn_browse = QPushButton()
        self.btn_browse.setProperty("class", "secondary-btn")
        self.btn_browse.setEnabled(False)
        self.btn_browse.clicked.connect(self._browse_output_file)

        self.rb_file.toggled.connect(self._on_dest_toggled)

        dest_box.addWidget(self.lbl_output_dest)
        dest_box.addWidget(self.rb_mem)
        dest_box.addWidget(self.rb_file)
        dest_box.addWidget(self.txt_file, stretch=1)
        dest_box.addWidget(self.btn_browse)
        opts_layout.addLayout(dest_box)

        params_layout.addWidget(self.grp_opts)
        params_layout.addStretch(1)

        params_scroll.setWidget(params_inner)
        tab1_vbox = QVBoxLayout(self.tab_params)
        tab1_vbox.setContentsMargins(0, 0, 0, 0)
        tab1_vbox.addWidget(params_scroll)
        self.tabs.addTab(self.tab_params, "Parameters")

        # ---- Tab 2: Results & Statistics ----
        self.tab_results = QWidget()
        res_vbox = QVBoxLayout(self.tab_results)
        res_vbox.setContentsMargins(8, 8, 8, 8)
        res_vbox.setSpacing(8)

        # KPI Summary Cards
        self.kpi_cards_layout = QHBoxLayout()
        self.kpi_cards_layout.setSpacing(6)

        self.kpi_solid = self._create_kpi_card("Coverage / Solid", "-", highlight=True)
        self.kpi_void = self._create_kpi_card("Void Ratio", "-")
        self.kpi_bldgs = self._create_kpi_card("Buildings", "-")
        self.kpi_footprint = self._create_kpi_card("Footprint Area", "-")
        self.kpi_zones = self._create_kpi_card("Zones", "-")

        self.kpi_cards_layout.addWidget(self.kpi_solid["widget"])
        self.kpi_cards_layout.addWidget(self.kpi_void["widget"])
        self.kpi_cards_layout.addWidget(self.kpi_bldgs["widget"])
        self.kpi_cards_layout.addWidget(self.kpi_footprint["widget"])
        self.kpi_cards_layout.addWidget(self.kpi_zones["widget"])
        res_vbox.addLayout(self.kpi_cards_layout)

        # Results Table
        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
            if hasattr(QAbstractItemView, "SelectionBehavior")
            else QAbstractItemView.SelectRows
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        res_vbox.addWidget(self.table, stretch=1)

        # Table quick actions
        tbl_actions = QHBoxLayout()
        tbl_actions.setSpacing(8)
        self.btn_copy_table = QPushButton()
        self.btn_copy_table.setProperty("class", "secondary-btn")
        self.btn_copy_table.clicked.connect(self._copy_table_to_clipboard)

        self.btn_export_csv = QPushButton()
        self.btn_export_csv.setProperty("class", "secondary-btn")
        self.btn_export_csv.clicked.connect(self._export_to_csv)

        tbl_actions.addStretch(1)
        tbl_actions.addWidget(self.btn_copy_table)
        tbl_actions.addWidget(self.btn_export_csv)
        res_vbox.addLayout(tbl_actions)

        self.tabs.addTab(self.tab_results, "Results & Statistics")

        # ---------------------------------------------------------
        # 3. Persistent Fixed Bottom Footer (Always pinned and visible)
        # ---------------------------------------------------------
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.setSpacing(6)

        prog_layout = QHBoxLayout()
        prog_layout.setSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 11px;")
        prog_layout.addWidget(self.progress_bar, stretch=1)
        prog_layout.addWidget(self.lbl_status)
        footer_layout.addLayout(prog_layout)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_run = QPushButton()
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self._run_calculation)

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("btn_close")
        self.btn_close.clicked.connect(self.close)

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_close)
        footer_layout.addLayout(btn_row)

        root_layout.addLayout(footer_layout)

    def _create_kpi_card(self, title: str, value: str, highlight: bool = False) -> Dict[str, Any]:
        card = QFrame()
        bg_col = "#eff6ff" if highlight else "#ffffff"
        border_col = "#3b82f6" if highlight else "#e2e8f0"
        val_col = "#1d4ed8" if highlight else "#0f172a"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 4px 6px;
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(2, 2, 2, 2)
        vbox.setSpacing(1)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 9.5px; color: #64748b; font-weight: 600;")
        lbl_t.setAlignment(ALIGN_CENTER)

        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"font-size: 13px; color: {val_col}; font-weight: bold;")
        lbl_v.setAlignment(ALIGN_CENTER)

        vbox.addWidget(lbl_t)
        vbox.addWidget(lbl_v)
        return {"widget": card, "title_lbl": lbl_t, "value_lbl": lbl_v}

    def _on_mode_changed(self):
        is_spatial = self.rb_mode_spatial.isChecked()
        self.grp_bldgs.setVisible(is_spatial)
        self.grp_direct.setVisible(not is_spatial)
        self.chk_centroids.setEnabled(is_spatial)

    def _apply_translations(self):
        t = STRINGS.get(self.cur_lang, STRINGS["en"])
        self.setWindowTitle(t["title"] + " (EPSG:5253)")
        self.lbl_title.setText(t["title"])
        self.lbl_subtitle.setText(t["subtitle"])
        self.crs_badge.setText(t["badge_crs"])

        # Tab titles
        self.tabs.setTabText(0, t["tab_params"])
        self.tabs.setTabText(1, t["tab_results"])

        # Mode Selection
        self.grp_mode.setTitle(t["mode_group"])
        self.rb_mode_spatial.setText(t["mode_spatial"])
        self.rb_mode_direct.setText(t["mode_direct"])

        # Parameters Group 1
        self.grp_zones.setTitle(t["zone_group"])
        self.lbl_z_layer.setText(t["zone_layer_lbl"])
        self.lbl_z_field.setText(t["zone_area_lbl"])
        self.chk_z_auto_geom.setText(t["zone_auto_geom"])

        # Parameters Group 2
        self.grp_bldgs.setTitle(t["bldg_group"])
        self.lbl_b_layer.setText(t["bldg_layer_lbl"])
        self.lbl_b_field.setText(t["bldg_area_lbl"])
        self.chk_b_auto_geom.setText(t["bldg_auto_geom"])

        # Direct Group
        self.grp_direct.setTitle(t["mode_direct"])
        self.lbl_direct_bldg.setText(t["direct_bldg_lbl"])

        # Options & Output
        self.grp_opts.setTitle(t["options_group"])
        self.lbl_palette.setText(t["palette_lbl"])
        self.combo_palette.setItemText(0, t["pal_urban"])
        self.combo_palette.setItemText(1, t["pal_nolli"])
        self.combo_palette.setItemText(2, t["pal_eco"])

        self.chk_style.setText(t["style_chk"])
        self.chk_add_canvas.setText(t["add_canvas_chk"])
        self.chk_centroids.setText(t["centroid_chk"])
        self.lbl_output_dest.setText(t["output_dest_lbl"])
        self.rb_mem.setText(t["output_mem"])
        self.rb_file.setText(t["output_file"])
        self.btn_browse.setText(t["btn_browse"])

        # Actions
        self.btn_run.setText(t["btn_run"])
        self.btn_close.setText(t["btn_close"])
        self.btn_copy_table.setText(t["btn_copy"])
        self.btn_export_csv.setText(t["btn_export_csv"])
        self.lbl_status.setText(t["status_ready"])

        # KPI Titles
        self.kpi_solid["title_lbl"].setText(t["kpi_solid"])
        self.kpi_void["title_lbl"].setText(t["kpi_void"])
        self.kpi_bldgs["title_lbl"].setText(t["kpi_bldgs"])
        self.kpi_footprint["title_lbl"].setText(t["kpi_footprint"])
        self.kpi_zones["title_lbl"].setText(t["kpi_zone_area"])

        # Table Headers
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
        data = self.lang_combo.itemData(index) if hasattr(self.lang_combo, "itemData") else None
        if not data:
            data = self.lang_combo.currentData()
        if data:
            self.cur_lang = str(data)
        elif index == 0:
            self.cur_lang = "tr"
        elif index == 1:
            self.cur_lang = "en"
        elif index == 2:
            self.cur_lang = "zh"
        elif index == 3:
            self.cur_lang = "id"

        if self.lang_combo.currentIndex() != index:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(index)
            self.lang_combo.blockSignals(False)
        self._apply_translations()

    def set_language(self, lang_code: str):
        """Programmatic language switcher ('en', 'tr', 'zh', 'id')."""
        code = str(lang_code).lower()[:2]
        idx_map = {"tr": 0, "en": 1, "zh": 2, "id": 3}
        idx = idx_map.get(code, 1)
        self._on_lang_changed(idx)

    def _on_dest_toggled(self, checked: bool):
        self.txt_file.setEnabled(checked)
        self.btn_browse.setEnabled(checked)
        if not checked:
            self._output_file_path = None

    def _browse_output_file(self):
        t = STRINGS.get(self.cur_lang, STRINGS["en"])
        path, _ = QFileDialog.getSaveFileName(
            self,
            t["output_file"],
            "",
            "GeoPackage (*.gpkg);;All Files (*)",
        )
        if path:
            if not path.lower().endswith(".gpkg"):
                path += ".gpkg"
            self.txt_file.setText(path)
            self._output_file_path = path

    def _auto_select_layers(self):
        """Pre-select likely layers based on TOC layer names."""
        project = QgsProject.instance()
        layers = project.mapLayers().values()

        zone_candidates = ["kirilganlik", "parca", "bolge", "zone", "mahalle", "sinir", "ada", "study", "parsel"]
        bldg_candidates = ["yapi", "bina", "tire_yapilar", "building", "footprint", "binalar", "structures"]

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
        candidates = ["m2", "alan_m2", "alan", "area_m2", "area", "hektar", "ha", "bolge_m2"]
        for c in candidates:
            for f in lyr.fields():
                if c == f.name().lower():
                    self.combo_z_field.setField(f.name())
                    return

    def _auto_detect_bldg_field(self):
        lyr = self.combo_b_layer.currentLayer()
        if lyr:
            candidates = ["taban_alani", "taban_m2", "bina_m2", "m2", "alan", "area", "bldg_m2", "footprint_m2"]
            for c in candidates:
                for f in lyr.fields():
                    if c == f.name().lower():
                        self.combo_b_field.setField(f.name())
                        break

        # Also auto detect direct building area on zone layer
        z_lyr = self.combo_z_layer.currentLayer()
        if z_lyr:
            d_candidates = ["bina_taban_m2", "taban_alani", "toplam_taban_m2", "bina_m2", "bldg_m2"]
            for c in d_candidates:
                for f in z_lyr.fields():
                    if c == f.name().lower():
                        self.combo_direct_bldg.setField(f.name())
                        return

    def _feedback_cb(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)
        QgsApplication.processEvents()

    def _run_calculation(self):
        t = STRINGS.get(self.cur_lang, STRINGS["en"])
        z_layer = self.combo_z_layer.currentLayer()
        is_spatial = self.rb_mode_spatial.isChecked()
        b_layer = self.combo_b_layer.currentLayer() if is_spatial else None

        if not z_layer or not z_layer.isValid():
            QMessageBox.warning(self, "Warning", t["err_no_zone"])
            return
        if is_spatial and (not b_layer or not b_layer.isValid()):
            QMessageBox.warning(self, "Warning", t["err_no_bldg"])
            return

        out_path = self.txt_file.text().strip() if self.rb_file.isChecked() else None
        if out_path:
            self._output_file_path = out_path

        selected_palette = self.combo_palette.currentData() or "urban_warm"
        bldg_field = (
            self.combo_b_field.currentField() if is_spatial else self.combo_direct_bldg.currentField()
        )

        self.btn_run.setEnabled(False)
        self.progress_bar.setValue(5)
        self.lbl_status.setText(t["status_running"])
        QgsApplication.processEvents()

        try:
            engine = FigureGroundEngine(
                zone_layer=z_layer,
                bldg_layer=b_layer if is_spatial else None,
                zone_area_field=self.combo_z_field.currentField(),
                bldg_area_field=bldg_field,
                auto_calc_zone_geom=self.chk_z_auto_geom.isChecked(),
                auto_calc_bldg_geom=self.chk_b_auto_geom.isChecked(),
                target_crs_authid="EPSG:5253",
                language=self.cur_lang,
                color_palette=selected_palette,
            )

            res = engine.run_analysis(
                feedback_cb=self._feedback_cb,
                output_file_path=self._output_file_path,
                generate_centroid_points=(self.chk_centroids.isChecked() and is_spatial),
            )

            out_layer = res["layer"]
            summary = res["summary"]
            self._last_result_layer = out_layer
            self._last_summary = summary

            # Apply Adaptive Symbology with chosen palette
            if self.chk_style.isChecked():
                apply_solid_void_symbology(
                    out_layer,
                    res["solid_field"],
                    language=self.cur_lang,
                    palette=selected_palette,
                )

            # Add to map canvas
            if self.chk_add_canvas.isChecked():
                project = QgsProject.instance()
                project.addMapLayer(out_layer)
                if res.get("centroid_layer"):
                    project.addMapLayer(res["centroid_layer"])

            # Update KPI Cards
            self.kpi_solid["value_lbl"].setText(f"%{summary['overall_solid_pct']:.2f}")
            self.kpi_void["value_lbl"].setText(f"%{summary['overall_void_pct']:.2f}")
            self.kpi_bldgs["value_lbl"].setText(f"{summary['total_buildings_assigned']:,}")
            self.kpi_footprint["value_lbl"].setText(
                f"{summary['total_building_footprint_m2']:,.0f} m²"
            )
            self.kpi_zones["value_lbl"].setText(
                f"{summary['total_zones']} ({summary['total_zone_ha']:.1f} ha)"
            )

            # Populate Results Table
            rows = summary.get("rows", [])
            self.table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                id_item = QTableWidgetItem(str(r["zone_id"]))
                zm2_item = QTableWidgetItem(f"{r['zone_m2']:,.1f}")
                zha_item = QTableWidgetItem(f"{r['zone_ha']:.3f}")
                bm2_item = QTableWidgetItem(f"{r['bldg_m2']:,.1f}")
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

            # Switch automatically to Results & Statistics tab to present data
            self.tabs.setCurrentIndex(1)

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"An error occurred during analysis:\n{str(exc)}")
            self.lbl_status.setText(f"Error: {str(exc)}")
        finally:
            self.btn_run.setEnabled(True)

    def _copy_table_to_clipboard(self):
        """Copies formatted table rows to system clipboard as tab-delimited text."""
        t = STRINGS.get(self.cur_lang, STRINGS["en"])
        headers = [self.table.horizontalHeaderItem(c).text() for c in range(self.table.columnCount())]
        lines = ["\t".join(headers)]

        for r in range(self.table.rowCount()):
            row_vals = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                row_vals.append(item.text() if item else "")
            lines.append("\t".join(row_vals))

        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            self.lbl_status.setText(t["copied_clipboard"])

    def _export_to_csv(self):
        """Exports table contents to a UTF-8 CSV file."""
        t = STRINGS.get(self.cur_lang, STRINGS["en"])
        if self.table.rowCount() == 0:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            t["btn_export_csv"],
            "solid_void_results.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(c).text() for c in range(self.table.columnCount())]
                writer.writerow(headers)

                for r in range(self.table.rowCount()):
                    row_vals = []
                    for c in range(self.table.columnCount()):
                        item = self.table.item(r, c)
                        row_vals.append(item.text() if item else "")
                    writer.writerow(row_vals)

            self.lbl_status.setText(t["export_success"].format(path))
            QMessageBox.information(self, "Export", t["export_success"].format(path))
        except Exception as err:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {err}")

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
