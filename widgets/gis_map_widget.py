import json
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot, Signal, QUrl

class MapBridge(QObject):
    """Bridge zur Kommunikation zwischen JavaScript (Leaflet) und Python."""
    bauwerkOpened = Signal(int)

    @Slot(int)
    def openBauwerk(self, bauwerk_id):
        self.bauwerkOpened.emit(bauwerk_id)

class GisMapWidget(QWidget):
    """
    Widget zur Anzeige einer interaktiven Karte mit Bauwerks-Markern.
    """
    bauwerkSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self._is_loaded = False
        self._pending_bauwerke = None
        
        # Bridge für JS-Call-Backs
        self.channel = QWebChannel()
        self.bridge = MapBridge()
        self.bridge.bauwerkOpened.connect(self.bauwerkSelected.emit)
        self.channel.registerObject("pythonConnector", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Lade-Status überwachen
        self.web_view.loadFinished.connect(self._on_load_finished)

        # Lade Template
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "map_template.html")
        self.web_view.setUrl(QUrl.fromLocalFile(template_path))
        
        layout.addWidget(self.web_view)

    def _on_load_finished(self, ok):
        self._is_loaded = ok
        if ok and self._pending_bauwerke:
            self.update_bauwerke(self._pending_bauwerke)
            self._pending_bauwerke = None

    def update_bauwerke(self, bauwerke_list):
        """
        Aktualisiert die Marker auf der Karte.
        """
        if not self._is_loaded:
            self._pending_bauwerke = bauwerke_list
            return

        json_data = json.dumps(bauwerke_list)
        script = f"updateMarkers('{json_data}');"
        self.web_view.page().runJavaScript(script)
