import os
from typing import Optional

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView supporting mouse wheel zoom and dragging (panning)."""

    zoom_changed = Signal(float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom_factor = 1.0

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom with Ctrl + Wheel
            zoom_in = event.angleDelta().y() > 0
            factor = 1.15 if zoom_in else (1.0 / 1.15)
            self.scale_by(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def scale_by(self, factor: float):
        new_zoom = self._zoom_factor * factor
        if 0.1 <= new_zoom <= 10.0:
            self._zoom_factor = new_zoom
            self.scale(factor, factor)
            self.zoom_changed.emit(self._zoom_factor)

    def reset_zoom(self):
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)


class PSTricksPreviewWidget(QWidget):
    """Widget responsible for displaying rendered PDF/image diagrams."""

    def __init__(self, parent=None, is_dark: bool = True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.current_pdf_path: Optional[str] = None
        self.dpi = 300
        self.transparent_grid = False

        self.scene = QGraphicsScene(self)
        self.view = ZoomableGraphicsView(self.scene, self)

        self.pixmap_item: Optional[QGraphicsPixmapItem] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Controls toolbar
        toolbar = QToolBar("Preview Controls", self)
        toolbar.setStyleSheet("QToolBar { border: none; background: transparent; }")

        btn_zoom_in = QPushButton("+", self)
        btn_zoom_in.setToolTip("Zoom In (Ctrl + Wheel Up)")
        btn_zoom_in.setFixedWidth(30)
        btn_zoom_in.clicked.connect(lambda: self.view.scale_by(1.2))

        btn_zoom_out = QPushButton("-", self)
        btn_zoom_out.setToolTip("Zoom Out (Ctrl + Wheel Down)")
        btn_zoom_out.setFixedWidth(30)
        btn_zoom_out.clicked.connect(lambda: self.view.scale_by(1 / 1.2))

        btn_reset_zoom = QPushButton("100%", self)
        btn_reset_zoom.setToolTip("Reset Zoom")
        btn_reset_zoom.clicked.connect(self.view.reset_zoom)

        btn_fit = QPushButton("Fit", self)
        btn_fit.setToolTip("Fit diagram to window")
        btn_fit.clicked.connect(self.fit_to_view)

        self.lbl_status = QLabel("Ready", self)
        self.lbl_status.setStyleSheet("color: gray; margin-left: 10px;")

        toolbar.addWidget(btn_zoom_in)
        toolbar.addWidget(btn_zoom_out)
        toolbar.addWidget(btn_reset_zoom)
        toolbar.addWidget(btn_fit)
        toolbar.addWidget(self.lbl_status)

        layout.addWidget(toolbar)
        layout.addWidget(self.view)

        self._update_background()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._update_background()

    def set_transparent_grid(self, enabled: bool):
        self.transparent_grid = enabled
        self._update_background()

    def _update_background(self):
        if self.transparent_grid:
            # Checkerboard pattern for transparency
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor("#E0E0E0") if not self.is_dark else QColor("#2D2D2D"))
            painter = QPainter(pixmap)
            c2 = QColor("#FFFFFF") if not self.is_dark else QColor("#1E1E1E")
            painter.fillRect(0, 0, 8, 8, c2)
            painter.fillRect(8, 8, 8, 8, c2)
            painter.end()
            self.scene.setBackgroundBrush(QBrush(pixmap))
        else:
            bg_color = QColor("#252526") if self.is_dark else QColor("#FAFAFA")
            self.scene.setBackgroundBrush(QBrush(bg_color))

    def load_pdf(self, pdf_path: str) -> bool:
        if not HAS_FITZ:
            self.lbl_status.setText("Error: PyMuPDF (fitz) is not installed.")
            return False

        if not os.path.exists(pdf_path):
            self.lbl_status.setText("PDF file not found.")
            return False

        try:
            doc = fitz.open(pdf_path)
            if doc.page_count < 1:
                return False

            page = doc.load_page(0)
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=True)

            # Create QImage from PyMuPDF pixmap buffer
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGBA8888)
            qpix = QPixmap.fromImage(qimg)

            self.scene.clear()
            self.pixmap_item = self.scene.addPixmap(qpix)
            self.scene.setSceneRect(QRectF(qpix.rect()))

            self.current_pdf_path = pdf_path
            self.lbl_status.setText(f"Size: {pix.width}x{pix.height} px")
            doc.close()
            return True
        except Exception as e:
            self.lbl_status.setText(f"Render Error: {e}")
            return False

    def fit_to_view(self):
        if self.pixmap_item:
            self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear_preview(self):
        self.scene.clear()
        self.pixmap_item = None
        self.lbl_status.setText("No Preview")

    def export_png(self, path: str) -> bool:
        """Render current PDF page to a PNG file at the configured DPI."""
        if not HAS_FITZ or not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            return False
        try:
            doc = fitz.open(self.current_pdf_path)
            if doc.page_count < 1:
                doc.close()
                return False
            page = doc.load_page(0)
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=True)
            pix.save(path)
            doc.close()
            return True
        except Exception:
            return False

    def export_svg(self, path: str) -> bool:
        """Export the current PDF page as SVG using PyMuPDF."""
        if not HAS_FITZ or not self.current_pdf_path or not os.path.exists(self.current_pdf_path):
            return False
        try:
            doc = fitz.open(self.current_pdf_path)
            if doc.page_count < 1:
                doc.close()
                return False
            page = doc.load_page(0)
            # get_svg_image returns an SVG string (PyMuPDF >= 1.18)
            svg = page.get_svg_image(matrix=fitz.Identity)
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            doc.close()
            return True
        except Exception:
            # Fallback: rasterize to PNG-like and wrap is not ideal; try pixmap path
            try:
                doc = fitz.open(self.current_pdf_path)
                page = doc.load_page(0)
                # Alternative API on some versions
                svg = page.get_text("svg")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                doc.close()
                return True
            except Exception:
                return False

