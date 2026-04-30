import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog, QStatusBar,
    QInputDialog, QMenu, QTabWidget
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from backend.database import SessionLocal, engine, Base, init_postgres_schema
from backend import models
from widgets.ingenieurbau_tab import IngenieurbauTab
from widgets.project_manager import ProjectManager
from widgets.ing_gis_canvas import IngGisCanvas

class IngenieurbauProApp(QMainWindow):
    """
    Eigenständige Applikation für Bauwerksprüfungen nach DIN 1076.
    Abgeleitet aus dem Sanierungsdashboard.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ingenieurbau Pro - Standalone Inspection Suite")
        
        # Verzögerte Maximierung zur Umgehung von Windows/Qt Resize-Bugs
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.showMaximized)
        
        # Initialisiere Datenbank (SQLite für Standalone als Default)
        init_postgres_schema()
        self._db = SessionLocal()
        Base.metadata.create_all(bind=engine)
        
        # Dummy Projekt-Context für Kompatibilität mit dem Tab-Widget
        self._current_project_id = 1
        self._ensure_default_project()
        
        self._setup_menus()
        self._setup_ui()
        self._refresh_map()
        self.statusBar().showMessage("Bereit.")

    def _setup_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Datei")
        
        # Projekt-Aktionen
        act_new_proj = QAction("Neues Projekt anlegen...", self)
        act_new_proj.triggered.connect(self._on_new_project)
        file_menu.addAction(act_new_proj)
        
        act_switch_proj = QAction("Projekt wechseln...", self)
        act_switch_proj.triggered.connect(self._on_switch_project)
        file_menu.addAction(act_switch_proj)
        
        file_menu.addSeparator()
        
        act_exit = QAction("Beenden", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    def _on_new_project(self) -> None:
        """Dialog zum Anlegen eines neuen Projekts."""
        name, ok = QInputDialog.getText(self, "Neues Projekt", "Projektname:")
        if ok and name:
            p_id = self.project_manager.add_project_to_db(name)
            self._switch_to_project(p_id)
            QMessageBox.information(self, "Erfolg", f"Projekt '{name}' wurde angelegt.")

    def _on_switch_project(self) -> None:
        """Wechselt zum Projektübersicht-Tab."""
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage("Bitte wählen Sie ein Projekt aus der Liste.")

    def _switch_to_project(self, p_id: int) -> None:
        """Wechselt den globalen Kontext auf das gewählte Projekt."""
        self._current_project_id = p_id
        self.setWindowTitle(f"Ingenieurbau Pro - [Projekt: {p_id}]")
        self.ingenieurbau_tab.refresh_data()
        self._refresh_map()
        self.tabs.setCurrentIndex(2) # Automatisch zum Fach-Tab springen
        self.statusBar().showMessage(f"Projekt aktiv: ID {p_id}", 5000)

    def open_pruefung_tab(self, db, bauwerk) -> None:
        """Öffnet eine neue Prüfung in einem dedizierten Tab."""
        from widgets.ing_pruefung_dialog import IngPruefungWidget
        
        # Prüfen ob bereits ein Tab für dieses Bauwerk offen ist (optional)
        name = f"Prüfung: {bauwerk.asb_id}"
        
        widget = IngPruefungWidget(db, bauwerk, self)
        index = self.tabs.addTab(widget, name)
        
        # Signal zum Schließen des Tabs bei Fertigstellung
        widget.finished.connect(lambda: self._close_tab_by_widget(widget))
        
        self.tabs.setCurrentIndex(index)

    def _on_tab_close_requested(self, index: int) -> None:
        """Handhabt das Schließen von Tabs durch den Nutzer."""
        if index > 2: # Karte, Projektübersicht und Fachschale nicht schließen
            self.tabs.removeTab(index)

    def _close_tab_by_widget(self, widget: QWidget) -> None:
        """Schließt einen Tab anhand des enthaltenen Widgets."""
        index = self.tabs.indexOf(widget)
        if index != -1:
            self.tabs.removeTab(index)
            # Daten im Haupt-Tab aktualisieren
            self.ingenieurbau_tab.refresh_data()

    def _ensure_default_project(self) -> None:
        # Sparte sicherstellen (ID=1 wird vom Tab erwartet)
        sparte = self._db.get(models.Sparte, 1)
        if not sparte:
            sparte = models.Sparte(id=1, code="ING", name="Ingenieurbau")
            self._db.add(sparte)
            
        proj = self._db.get(models.Projekt, 1)
        if not proj:
            proj = models.Projekt(id=1, name="Standardprojekt Ingenieurbau")
            self._db.add(proj)
            
        self._db.commit()

    def _setup_ui(self) -> None:
        """Konfiguriert die zentrale UI-Struktur mit Tabs für Projekte und Fachschalen."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        
        # Tab-System für Übersicht und Facharbeit
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        
        # Tab 1: Karte (Natives GIS Dashboard)
        self.gis_container = QWidget()
        gis_layout = QVBoxLayout(self.gis_container)
        gis_layout.setContentsMargins(0, 0, 0, 0)
        gis_layout.setSpacing(0)
        
        # Toolbar für Karte
        from PySide6.QtWidgets import QToolBar
        self.gis_toolbar = QToolBar()
        self.gis_toolbar.setMovable(False)
        
        from widgets.ing_gis_canvas import WMS_LAYERS
        act_dtk = self.gis_toolbar.addAction("🗺️ Karte")
        act_dtk.triggered.connect(lambda: self.gis_tab.set_wms_layer(WMS_LAYERS["DTK (Topo)"]))
        
        act_dop = self.gis_toolbar.addAction("📸 Luftbild")
        act_dop.triggered.connect(lambda: self.gis_tab.set_wms_layer(WMS_LAYERS["DOP (Luftbild)"]))
        
        gis_layout.addWidget(self.gis_toolbar)
        
        self.gis_tab = IngGisCanvas()
        self.gis_tab.bauwerkSelected.connect(self._on_bauwerk_selected_from_map)
        gis_layout.addWidget(self.gis_tab)
        
        self.tabs.addTab(self.gis_container, "🌍 GIS-Karte")
        
        # Tab 2: Projektübersicht
        self.project_manager = ProjectManager(self._db, self)
        self.project_manager.projectSwitched.connect(self._switch_to_project)
        self.project_manager.btn_new.clicked.connect(self._on_new_project)
        self.tabs.addTab(self.project_manager, "📂 Projektübersicht")
        
        # Tab 3: Ingenieurbau Fachschale
        self.ingenieurbau_tab = IngenieurbauTab(self._db, self)
        self.tabs.addTab(self.ingenieurbau_tab, "🏗️ Ingenieurbau (DIN 1076)")
        
        layout.addWidget(self.tabs)
        
        # Initialen Zustand laden
        self.ingenieurbau_tab.refresh_data()

    def _current_netz_id(self):
        """Ermittelt das Netz für das aktuelle Projekt oder legt eines an."""
        pid = self._current_project_id
        netz = self._db.query(models.Netz).filter_by(projekt_id=pid).first()
        if not netz:
            netz = models.Netz(projekt_id=pid, name=f"Netz für Projekt {pid}", sparte_id=1)
            self._db.add(netz)
            self._db.commit()
        return netz.id

    def closeEvent(self, event):
        self._db.close()
        event.accept()

    def _on_bauwerk_selected_from_map(self, bauwerk_id):
        """Wird aufgerufen, wenn auf der Karte ein Bauwerk angeklickt wird."""
        self.statusBar().showMessage(f"Bauwerk ID {bauwerk_id} ausgewählt.")
        
        # 1. Zum Ingenieurbau-Tab wechseln
        self.tabs.setCurrentIndex(2)
        
        # 2. Im Ingenieurbau-Tab das Bauwerk selektieren
        # (Vorausgesetzt der Tab hat eine Methode zum Suchen/Wählen nach ID)
        self.ingenieurbau_tab.select_bauwerk_by_id(bauwerk_id)
        
    def _refresh_map(self):
        from backend.models import IngBauwerk
        from backend.database import get_geometry_as_wkt
        bauwerke = self._db.query(IngBauwerk).all()
        data = []
        for b in bauwerke:
            # X/Y aus Geometrie extrahieren (UTM EPSG:25832)
            x, y = None, None
            if b.geometrie is not None:
                try:
                    from geoalchemy2.shape import to_shape
                    point = to_shape(b.geometrie)
                    x, y = point.x, point.y
                except:
                    pass
            
            # Fallback falls Geometrie fehlt (für Demo-Daten)
            if x is None:
                x = 405000 + (b.id * 100)
                y = 5688000 + (b.id * 100)
                
            data.append({
                "id": b.id,
                "name": b.name,
                "x": x,
                "y": y,
                "asb_id": b.asb_id or f"BW-{b.id}"
            })
        self.gis_tab.update_bauwerke(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Modernerer Look als Standard Windows
    
    # Pfad-Fix für Icons etc.
    os.chdir(Path(__file__).parent)
    
    window = IngenieurbauProApp()
    window.showMaximized()
    sys.exit(app.exec())
