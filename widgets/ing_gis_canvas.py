import math
from typing import List, Optional, Tuple, Dict
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QTransform, QFont, QPixmap
from PySide6.QtWidgets import QWidget, QSizePolicy
from urllib.request import urlopen
from urllib.parse import urlencode

# --- WMS-Konfiguration (analog Sanierungsdashboard) ---
WMS_LAYERS = {
    "DOP (Luftbild)": {
        "url":   "https://www.wms.nrw.de/geobasis/wms_nw_dop",
        "layer": "nw_dop_rgb",
        "crs":   "EPSG:25832",
        "fmt":   "image/png",
    },
    "DTK (Topo)": {
        "url":   "https://www.wms.nrw.de/geobasis/wms_nw_dtk",
        "layer": "nw_dtk_col",
        "crs":   "EPSG:25832",
        "fmt":   "image/png",
    }
}

class WmsFetcher(QThread):
    """Holt WMS-Bilder im Hintergrund."""
    image_ready = Signal(bytes, float, float, float, float)

    def __init__(self, url, layer, crs, fmt, bbox, width, height):
        super().__init__()
        self._url, self._layer, self._crs, self._fmt = url, layer, crs, fmt
        self._bbox, self._width, self._height = bbox, width, height

    def run(self):
        min_x, min_y, max_x, max_y = self._bbox
        params = {
            "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
            "LAYERS": self._layer, "SRS": self._crs, "BBOX": f"{min_x},{min_y},{max_x},{max_y}",
            "WIDTH": str(self._width), "HEIGHT": str(self._height), "FORMAT": self._fmt, "TRANSPARENT": "TRUE"
        }
        try:
            full_url = f"{self._url}?{urlencode(params)}"
            with urlopen(full_url, timeout=10) as resp:
                data = resp.read()
            self.image_ready.emit(data, min_x, min_y, max_x, max_y)
        except: pass

class IngGisCanvas(QWidget):
    """
    Native GIS-Karte für Ingenieurbauwerke (CAD-Stil).
    Portiert aus dem Sanierungsdashboard (network_visualization.py).
    """
    bauwerkSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bauwerke = [] # Liste von Dicts mit {id, name, x, y}
        self.selected_id = None
        
        # Viewport-Transformation
        self._zoom = 0.5
        self._pan = QPointF(0, 0)
        self._pan_last = QPointF()
        
        # WMS-Background
        self._bg_pixmap = None
        self._bg_bbox = None
        self._wms_cfg = WMS_LAYERS["DTK (Topo)"]
        self._wms_timer = QTimer(self)
        self._wms_timer.setSingleShot(True)
        self._wms_timer.setInterval(500)
        self._wms_timer.timeout.connect(self._request_wms)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #f0f0f0;")

    def update_bauwerke(self, bauwerke_list):
        self.bauwerke = bauwerke_list
        if not self._pan.x() and not self._pan.y() and self.bauwerke:
            self.fit_to_content()
        self.update()

    def set_wms_layer(self, cfg: Optional[dict]):
        """Wechselt den Hintergrund-Layer (z.B. DOP oder DTK)."""
        self._wms_cfg = cfg
        self._bg_pixmap = None
        self._bg_bbox = None
        self._request_wms()
        self.update()

    def fit_to_content(self):
        if not self.bauwerke: return
        xs = [b['x'] for b in self.bauwerke if b.get('x')]
        ys = [b['y'] for b in self.bauwerke if b.get('y')]
        if not xs: return
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        w, h = self.width() or 800, self.height() or 600
        self._zoom = min(w / (max_x - min_x + 100), h / (max_y - min_y + 100))
        self._pan = QPointF(w/2 - ((min_x+max_x)/2)*self._zoom, h/2 + ((min_y+max_y)/2)*self._zoom)
        self._request_wms()
        self.update()

    def _request_wms(self):
        if not self._wms_cfg: return
        
        # Alten Fetcher stoppen falls er noch läuft (Sicherheitsprüfung gegen RuntimeError)
        try:
            if hasattr(self, "_wms_fetcher") and self._wms_fetcher and self._wms_fetcher.isRunning():
                self._wms_fetcher.image_ready.disconnect()
                self._wms_fetcher.terminate()
                self._wms_fetcher.wait()
        except RuntimeError:
            # Objekt wurde bereits von C++ gelöscht, alles okay
            self._wms_fetcher = None

        w, h = self.width(), self.height()
        if w <= 0 or h <= 0: return

        min_x = (0 - self._pan.x()) / self._zoom
        max_x = (w - self._pan.x()) / self._zoom
        max_y = self._pan.y() / self._zoom
        min_y = (self._pan.y() - h) / self._zoom
        
        self._wms_fetcher = WmsFetcher(self._wms_cfg['url'], self._wms_cfg['layer'], 
                                       self._wms_cfg['crs'], self._wms_cfg['fmt'], 
                                       (min_x, min_y, max_x, max_y), w, h)
        self._wms_fetcher.image_ready.connect(self._on_wms_ready)
        
        # Sicherer Cleanup: Referenz löschen wenn fertig
        def cleanup():
            self._wms_fetcher = None
            
        self._wms_fetcher.finished.connect(cleanup)
        self._wms_fetcher.finished.connect(self._wms_fetcher.deleteLater)
        self._wms_fetcher.start()

    def _on_wms_ready(self, data, min_x, min_y, max_x, max_y):
        pix = QPixmap()
        if pix.loadFromData(data):
            self._bg_pixmap = pix
            self._bg_bbox = (min_x, min_y, max_x, max_y)
            self.update()

    def paintEvent(self, event):
        if not self.isVisible() or self.width() <= 0: return
        
        p = QPainter(self)
        if not p.isActive(): return
        
        # 1. Transformation (Y-Spiegelung für Norden=Oben)
        t = QTransform()
        t.translate(self._pan.x(), self._pan.y())
        t.scale(self._zoom, -self._zoom)
        
        # 2. WMS Hintergrund
        if self._bg_pixmap and self._bg_bbox:
            min_x, min_y, max_x, max_y = self._bg_bbox
            rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            p.setTransform(t)
            p.drawPixmap(rect, self._bg_pixmap, QRectF(self._bg_pixmap.rect()))
            p.resetTransform()

        p.setTransform(t)
        
        # 3. Bauwerke zeichnen
        for b in self.bauwerke:
            x, y = b.get('x'), b.get('y')
            if x is None or y is None: continue
            
            is_sel = b['id'] == self.selected_id
            p.setPen(QPen(Qt.black, 2/self._zoom))
            p.setBrush(QBrush(QColor("#ff5722") if not is_sel else Qt.yellow))
            
            # Quadrat als Bauwerkssymbol
            size = 15 / self._zoom
            p.drawRect(QRectF(x - size/2, y - size/2, size, size))
            
            # Beschriftung
            p.save()
            p.resetTransform()
            screen_pos = t.map(QPointF(x, y))
            p.setPen(Qt.black)
            p.setFont(QFont("Arial", 9, QFont.Bold))
            p.drawText(screen_pos.x() + 10, screen_pos.y() - 10, b['name'])
            p.restore()

    def mousePressEvent(self, event):
        if event.button() in [Qt.LeftButton, Qt.MiddleButton]:
            self._pan_last = event.position()
        
        # Selektion prüfen
        t = QTransform()
        t.translate(self._pan.x(), self._pan.y())
        t.scale(self._zoom, -self._zoom)
        inv, _ = t.inverted()
        world_pos = inv.map(event.position())
        
        for b in self.bauwerke:
            if abs(b['x'] - world_pos.x()) < 20/self._zoom and abs(b['y'] - world_pos.y()) < 20/self._zoom:
                self.selected_id = b['id']
                self.bauwerkSelected.emit(b['id'])
                self.update()
                break

    def mouseMoveEvent(self, event):
        if event.buttons() & (Qt.LeftButton | Qt.MiddleButton):
            delta = event.position() - self._pan_last
            self._pan += delta
            self._pan_last = event.position()
            self._wms_timer.start()
            self.update()

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 0.9
        
        # Zoom zum Mauszeiger
        mpos = event.position()
        wx = (mpos.x() - self._pan.x()) / self._zoom
        wy = -(mpos.y() - self._pan.y()) / self._zoom
        
        self._zoom *= factor
        self._pan = QPointF(mpos.x() - wx * self._zoom, mpos.y() + wy * self._zoom)
        self._wms_timer.start()
        self.update()
