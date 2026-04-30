import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QFileDialog, QLabel, QToolBar
)
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter, QBrush, QAction, QCursor
from PySide6.QtCore import Qt, QPointF, Signal, QRectF, QEvent, QSize

class VisualInspector(QWidget):
    """
    Widget zur interaktiven Markierung von Schäden auf Fotos (Smart Tagging).
    Unterstützt Punkte, Linien und Flächen.
    """
    markingChanged = Signal(str) # Sendet JSON-String der Markierungen
    ghostMarkAccepted = Signal(dict) # Sendet die Daten des akzeptierten KI-Vorschlags

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.marks = [] # Liste von Markierungs-Objekten
        self.ghost_marks = [] # KI-Vorschläge
        self.mode = "point" # "point", "line", "area", "pan"
        self._temp_points = [] # Zwischenspeicher für Polygone/Linien
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        self.toolbar = QToolBar()
        
        self.act_pan = QAction("✋ Verschieben", self)
        self.act_pan.setCheckable(True)
        self.act_pan.triggered.connect(lambda: self._set_mode("pan"))
        
        self.act_point = QAction("📍 Punkt", self)
        self.act_point.setCheckable(True)
        self.act_point.setChecked(True)
        self.act_point.triggered.connect(lambda: self._set_mode("point"))
        
        self.act_line = QAction("📏 Linie", self)
        self.act_line.setCheckable(True)
        self.act_line.triggered.connect(lambda: self._set_mode("line"))
        
        self.act_area = QAction("📐 Fläche", self)
        self.act_area.setCheckable(True)
        self.act_area.triggered.connect(lambda: self._set_mode("area"))
        
        self.act_clear = QAction("🗑️ Leeren", self)
        self.act_clear.triggered.connect(self.clear_marks)
        
        self.toolbar.addSeparator()
        
        self.act_ai_scan = QAction("✨ KI-Scan", self)
        self.act_ai_scan.setToolTip("KI-Vorschläge für Schäden generieren")
        self.act_ai_scan.triggered.connect(self.trigger_ai_scan)
        
        self.toolbar.addAction(self.act_pan)
        self.toolbar.addAction(self.act_point)
        self.toolbar.addAction(self.act_line)
        self.toolbar.addAction(self.act_area)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_ai_scan)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_clear)
        
        layout.addWidget(self.toolbar)
        
        # Scene & View
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        # Standardmäßig kein Drag, damit Clicks zum Zeichnen durchgehen
        self.view.setDragMode(QGraphicsView.NoDrag)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Mouse Events abfangen
        self.view.viewport().installEventFilter(self)
        
        layout.addWidget(self.view)
        
        self.status = QLabel("Kein Bild geladen. Nutzen Sie 'Sammelimport' im Prüfungsdialog.")
        layout.addWidget(self.status)

    def load_image(self, path):
        """Lädt ein Foto in den Inspektor."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.status.setText("Fehler beim Laden des Bildes.")
            return
            
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
        self.current_image_path = path
        self.status.setText(f"Bild: {path}")
        self.marks = []

    def _set_mode(self, mode):
        self.mode = mode
        self.act_pan.setChecked(mode == "pan")
        self.act_point.setChecked(mode == "point")
        self.act_line.setChecked(mode == "line")
        self.act_area.setChecked(mode == "area")
        self._temp_points = [] # Reset bei Moduswechsel
        
        if mode == "pan":
            self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.view.setDragMode(QGraphicsView.NoDrag)

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    # Prüfen, ob ein Ghost-Item angeklickt wurde
                    ghost_item = self._get_ghost_at(event.pos())
                    if ghost_item:
                        self.accept_ghost_mark(ghost_item)
                        return True
                        
                    if self.mode != "pan":
                        scene_pos = self.view.mapToScene(event.pos())
                        self._add_mark(scene_pos)
                        return True
                elif event.button() == Qt.RightButton or event.type() == QEvent.MouseButtonDblClick:
                    # Abschluss von Polygonen/Linien
                    if self.mode in ["line", "area"] and self._temp_points:
                        self._finish_multi_point_mark()
                        return True
            elif event.type() == QEvent.MouseMove:
                # Cursor-Feedback für Ghost-Items
                if self._get_ghost_at(event.pos()):
                    self.view.setCursor(QCursor(Qt.PointingHandCursor))
                else:
                    self.view.setCursor(QCursor(Qt.ArrowCursor if self.mode != "pan" else Qt.OpenHandCursor))
            
            elif event.type() == QEvent.Wheel:
                # Zoom-Logik
                zoom_in_factor = 1.25
                zoom_out_factor = 1 / zoom_in_factor
                if event.angleDelta().y() > 0:
                    self.view.scale(zoom_in_factor, zoom_in_factor)
                else:
                    self.view.scale(zoom_out_factor, zoom_out_factor)
                return True
                    
        return super().eventFilter(source, event)

    def resizeEvent(self, event):
        """Sorgt dafür, dass das Bild beim Ändern der Fenstergröße angepasst wird."""
        super().resizeEvent(event)
        if self.current_image_path:
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def _get_ghost_at(self, pos):
        """Ermittelt das oberste Ghost-Item an einer View-Position."""
        items = self.view.items(pos)
        for item in items:
            if hasattr(item, "is_ghost") and item.is_ghost:
                return item
        return None

    def _add_mark(self, pos, silent=False):
        """Fügt eine Markierung an der Scene-Position hinzu."""
        # Dynamische Größe basierend auf Bilddimensionen
        view_scale = self.pixmap_item.pixmap().width() / 100.0 if hasattr(self, 'pixmap_item') else 1.0
        
        if self.mode == "point":
            radius = max(15, 1.5 * view_scale) 
            ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, radius*2, radius*2)
            ellipse.setPen(QPen(Qt.yellow, max(2, 0.2 * view_scale)))
            ellipse.setBrush(QBrush(QColor(255, 255, 0, 180)))
            self.scene.addItem(ellipse)
            
            if not silent:
                self.marks.append({"type": "point", "x": pos.x(), "y": pos.y()})
                self._emit_change()
        
        elif self.mode in ["line", "area"]:
            self._temp_points.append(pos)
            # Feedback-Punkt (Skaliert mit Bildgröße)
            dot_radius = max(5, 0.5 * view_scale)
            dot = QGraphicsEllipseItem(pos.x() - dot_radius, pos.y() - dot_radius, dot_radius*2, dot_radius*2)
            dot.setBrush(Qt.cyan if self.mode == "area" else Qt.blue)
            dot.setPen(QPen(Qt.white, max(1, 0.1 * view_scale)))
            self.scene.addItem(dot)
            # Bei Linie mit 2 Punkten direkt fertig (optional, hier flexibel)
            if self.mode == "line" and len(self._temp_points) == 2:
                self._finish_multi_point_mark()

    def _finish_multi_point_mark(self, silent=False):
        """Schließt eine Linien- oder Flächenmarkierung ab."""
        if len(self._temp_points) < 2: return
        
        # Dynamische Größe basierend auf Bilddimensionen
        view_scale = self.pixmap_item.pixmap().width() / 100.0 if hasattr(self, 'pixmap_item') else 1.0
        
        item = QGraphicsPathItem()
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(self._temp_points[0])
        for p in self._temp_points[1:]:
            path.lineTo(p)
            
        if self.mode == "area":
            path.closeSubpath()
            item.setBrush(QBrush(QColor(255, 165, 0, 120))) # Orange für Flächen
            item.setPen(QPen(Qt.orange, max(2, 0.3 * view_scale)))
        else:
            item.setPen(QPen(Qt.red, max(3, 0.4 * view_scale)))
            
        item.setPath(path)
        self.scene.addItem(item)
        
        if not silent:
            # Speichern nur wenn nicht silent (Ladevorgang)
            m_data = {"type": self.mode, "points": [{"x": p.x(), "y": p.y()} for p in self._temp_points]}
            self.marks.append(m_data)
            self._emit_change()
            # Cleanup der Hilfspunkte
            self._draw_all_marks()

        self._temp_points = []

    def trigger_ai_scan(self):
        """Startet den KI-Scan über das Backend."""
        if not self.current_image_path:
            self.status.setText("⚠️ Bitte zuerst ein Bild laden.")
            return
            
        self.status.setText("🧠 KI analysiert Bild... Bitte warten.")
        
        # In der Realität: QThread für non-blocking UI. 
        # Hier für die Demo ein simpler Timer-Aufruf, der die Engine nutzt.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, self._process_ai_results)

    def _process_ai_results(self):
        from backend.ai_engine import detect_damages
        try:
            suggestions = detect_damages(self.current_image_path)
            
            if not hasattr(self, 'pixmap_item') or not self.pixmap_item:
                self.status.setText("❌ Fehler: Kein Bild-Objekt in der Szene.")
                return
                
            pix = self.pixmap_item.pixmap()
            if pix.isNull():
                self.status.setText("❌ Fehler: Pixmap ist ungültig.")
                return
                
            rect = pix.rect()
            print(f"KI-Inferenz abgeschlossen. Bildgröße: {rect.width()}x{rect.height()}")
            
            for s in suggestions:
                if s["type"] == "line":
                    data = {
                        "type": "line",
                        "x1": s["rel_x1"] * rect.width(),
                        "y1": s["rel_y1"] * rect.height(),
                        "x2": s["rel_x2"] * rect.width(),
                        "y2": s["rel_y2"] * rect.height(),
                        "code": s["code"],
                        "label": s["label"]
                    }
                else:
                    data = {
                        "type": "point",
                        "x": s["rel_x"] * rect.width(),
                        "y": s["rel_y"] * rect.height(),
                        "code": s["code"],
                        "label": s["label"]
                    }
                self.add_ghost_mark(data)
            
            self.status.setText(f"✅ {len(suggestions)} KI-Vorschläge gefunden. Klicken zum Bestätigen.")
        except Exception as e:
            self.status.setText(f"❌ KI-Fehler: {e}")

    def add_ghost_mark(self, data):
        """Fügt einen KI-Vorschlag (Ghost Mark) zur Szene hinzu."""
        self.ghost_marks.append(data)
        item = None
        
        # Dynamische Größe basierend auf Bilddimensionen (ca. 2% der Breite)
        view_scale = self.pixmap_item.pixmap().width() / 100.0
        
        if data["type"] == "point":
            radius = max(30, 2.5 * view_scale) # Noch größer für bessere Sichtbarkeit
            item = QGraphicsEllipseItem(data["x"] - radius, data["y"] - radius, radius*2, radius*2)
            pen = QPen(QColor(255, 0, 255, 255), max(4, 0.4 * view_scale), Qt.DashLine)
            item.setPen(pen)
            item.setBrush(QBrush(QColor(255, 0, 255, 120))) # Höhere Deckkraft
            
        elif data["type"] == "line":
            item = QGraphicsPathItem()
            from PySide6.QtGui import QPainterPath
            path = QPainterPath()
            path.moveTo(data["x1"], data["y1"])
            path.lineTo(data["x2"], data["y2"])
            item.setPath(path)
            # Dickere Linie proportional zur Bildgröße
            line_width = max(5, 0.5 * view_scale)
            item.setPen(QPen(QColor(0, 255, 255, 255), line_width, Qt.DotLine, Qt.RoundCap))
            
        if item:
            item.is_ghost = True
            item.ghost_data = data
            item.setZValue(1000) # Extrem hoch, um über allem zu liegen
            item.setOpacity(0.7) # Leicht transparent für High-Tech Look
            item.setToolTip(f"{data.get('label', 'Vorschlag')} - Klick zum Bestätigen")
            item.setAcceptHoverEvents(True)
            self.scene.addItem(item)
            # Kleiner Effekt: Item kurz 'aufleuchten' lassen (über Farbe)
            self.status.setText(f"✨ Vorschlag hinzugefügt: {data.get('label')}")

    def accept_ghost_mark(self, item):
        """Wandelt einen Vorschlag in eine echte Markierung um."""
        data = item.ghost_data
        self.scene.removeItem(item)
        if data in self.ghost_marks:
            self.ghost_marks.remove(data)
            
        # Als echte Markierung hinzufügen
        if data["type"] == "point":
            self.mode = "point"
            self._add_mark(QPointF(data["x"], data["y"]))
        elif data["type"] == "line":
            self.mode = "line"
            self._temp_points = [QPointF(data["x1"], data["y1"])]
            self._add_mark(QPointF(data["x2"], data["y2"]))
            
        self.status.setText(f"✅ Markierung übernommen: {data.get('code', '')}")
        self.ghostMarkAccepted.emit(data)

    def clear_marks(self):
        self.marks = []
        self.ghost_marks = []
        self._temp_points = []
        # Alles außer Pixmap entfernen
        for item in self.scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                self.scene.removeItem(item)
        self._emit_change()
        self.status.setText("Alle Markierungen gelöscht.")

    def load_json(self, json_str):
        """Lädt Markierungen aus einem JSON-String."""
        if not json_str: 
            self.marks = []
            self._draw_all_marks() # Bild säubern
            return
        try:
            self.marks = json.loads(json_str)
            self._draw_all_marks()
        except Exception as e:
            print(f"Fehler beim Laden der Markierungen: {e}")

    def _draw_all_marks(self):
        # UI säubern
        for item in self.scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                self.scene.removeItem(item)
        
        # Neu zeichnen (silent)
        for m in self.marks:
            if m["type"] == "point":
                old_mode = self.mode
                self.mode = "point"
                self._add_mark(QPointF(m["x"], m["y"]), silent=True)
                self.mode = old_mode
            elif m["type"] in ["line", "area"]:
                old_mode = self.mode
                self.mode = m["type"]
                self._temp_points = [QPointF(p["x"], p["y"]) for p in m["points"]]
                self._finish_multi_point_mark(silent=True) # WICHTIG: silent=True verhindert Rekursion
                self.mode = old_mode

    def _emit_change(self):
        self.markingChanged.emit(json.dumps(self.marks))

    def get_json(self):
        return json.dumps(self.marks)
