import yaml
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialogButtonBox, QMessageBox, QGroupBox, QSpinBox, QSplitter, QFileDialog,
    QWidget, QStatusBar
)
from PySide6.QtCore import Qt, QDate, Signal
from backend import models
from backend.logic_ing import berechne_zustandsnote_din1076
from widgets.visual_inspector import VisualInspector

class IngPruefungWidget(QWidget):
    """
    Widget zur Erfassung einer Bauwerksprüfung nach DIN 1076.
    Wird als Tab im Hauptfenster geöffnet.
    """
    finished = Signal() # Signal zum Schließen des Tabs

    def __init__(self, db, bauwerk, parent=None):
        super().__init__(parent)
        self.db = db
        self.bauwerk = bauwerk
        
        self.catalog = self._load_catalog()
        self.temp_schaeden = []
        self.current_schaden_index = -1
        
        # Sicherstellen, dass mindestens ein Bauteil existiert (Auto-Fallback)
        self._get_default_bauteil_id()
        
        self._setup_ui()

    def _load_catalog(self):
        cat_path = Path(__file__).parent.parent / "regelwerke" / "asb_ing" / "ri_ebw_pruef_katalog.yaml"
        if cat_path.exists():
            with open(cat_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Kopfdaten
        header_group = QGroupBox("Prüfungs-Stammdaten")
        h_layout = QHBoxLayout(header_group)
        
        self.de_datum = QDateEdit(QDate.currentDate())
        self.cb_art = QComboBox()
        self.cb_art.addItems(["Hauptprüfung (H1)", "Einfache Prüfung (E1)", "Sonderprüfung"])
        self.le_pruefer = QLineEdit()
        self.le_pruefer.setPlaceholderText("Name des Prüfers")
        
        h_layout.addWidget(QLabel("Datum:"))
        h_layout.addWidget(self.de_datum)
        h_layout.addWidget(QLabel("Prüfart:"))
        h_layout.addWidget(self.cb_art)
        h_layout.addWidget(QLabel("Prüfer:"))
        h_layout.addWidget(self.le_pruefer)
        
        # Stammdaten kompakt halten
        header_group.setMaximumHeight(100)
        layout.addWidget(header_group)
        
        # Splitter für Tabelle (links) und Visual Inspector (rechts)
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Linker Bereich: Schadenserfassung
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        schaden_group = QGroupBox("Schadenserfassung (S-V-D)")
        s_layout = QVBoxLayout(schaden_group)
        
        toolbar = QHBoxLayout()
        self.btn_add_schaden = QPushButton("+ Schaden")
        self.btn_add_schaden.clicked.connect(self._on_add_schaden)
        self.btn_bulk_photo = QPushButton("📸 Sammelimport")
        self.btn_bulk_photo.clicked.connect(self._on_bulk_import_photos)
        self.btn_del_schaden = QPushButton("🗑️ Löschen")
        self.btn_del_schaden.clicked.connect(self._on_delete_schaden)
        
        toolbar.addWidget(self.btn_add_schaden)
        toolbar.addWidget(self.btn_bulk_photo)
        toolbar.addWidget(self.btn_del_schaden)
        toolbar.addStretch()
        self.lbl_zn = QLabel("<b>ZN: 1.0</b>")
        toolbar.addWidget(self.lbl_zn)
        
        s_layout.addLayout(toolbar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Bauteil", "Schaden", "S", "V", "D", "📸"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        s_layout.addWidget(self.table)
        
        left_layout.addWidget(schaden_group)
        self.main_splitter.addWidget(left_widget)
        
        # Rechter Bereich: Visual Inspector
        right_group = QGroupBox("Visual Asset Management / Skizze")
        r_layout = QVBoxLayout(right_group)
        self.inspector = VisualInspector()
        self.inspector.markingChanged.connect(self._on_marking_changed)
        self.inspector.ghostMarkAccepted.connect(self._on_ghost_mark_accepted)
        r_layout.addWidget(self.inspector)
        
        self.main_splitter.addWidget(right_group)
        # 30% Links (Liste), 70% Rechts (Inspector)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 7)
        
        layout.addWidget(self.main_splitter, 1) # Stretch 1 für maximale Höhe
        
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Discard)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.finished.emit)
        layout.addWidget(btns)

    def statusBar(self):
        return self.status_bar

    def _on_add_schaden(self):
        from PySide6.QtWidgets import QDialog, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Neuer Schaden")
        form = QFormLayout(dlg)
        
        # Bauteil-Wahl
        cb_bt = QComboBox()
        all_bauteile = []
        for tbw in self.bauwerk.teilbauwerke:
            for bt in tbw.bauteile:
                cb_bt.addItem(f"{tbw.name}: {bt.name}", bt.id)
                all_bauteile.append(bt)
        
        # Schadens-Wahl aus Katalog
        cb_code = QComboBox()
        codes = self.catalog.get("schadenskatalog", [])
        for c in codes:
            cb_code.addItem(f"{c['code']} - {c['name']}", c)
            
        spin_s = QSpinBox(); spin_s.setRange(0, 4)
        spin_v = QSpinBox(); spin_v.setRange(0, 4)
        spin_d = QSpinBox(); spin_d.setRange(0, 4)
        
        def _update_defaults():
            data = cb_code.currentData()
            if data and "defaults" in data:
                spin_s.setValue(data["defaults"].get("S", 0))
                spin_v.setValue(data["defaults"].get("V", 0))
                spin_d.setValue(data["defaults"].get("D", 0))
        
        cb_code.currentIndexChanged.connect(_update_defaults)
        _update_defaults() # Initial
        
        form.addRow("Bauteil:", cb_bt)
        form.addRow("Schaden (Katalog):", cb_code)
        form.addRow("Standsicherheit (S):", spin_s)
        form.addRow("Verkehrssicherheit (V):", spin_v)
        form.addRow("Dauerhaftigkeit (D):", spin_d)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        
        if dlg.exec() == QDialog.Accepted:
            cat_data = cb_code.currentData()
            schaden = models.IngSchaden(
                bauteil_id=cb_bt.currentData(),
                code=str(cat_data["code"]),
                beschreibung=cat_data["name"],
                bewertung_s=spin_s.value(),
                bewertung_v=spin_v.value(),
                bewertung_d=spin_d.value(),
                skizze_json=None
            )
            self.temp_schaeden.append(schaden)
            self._refresh_table()

    def _on_bulk_import_photos(self):
        """Erlaubt das Auswählen mehrerer Fotos und erstellt dafür direkt Schadens-Einträge (Photo-First)."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Bilder für Schadenserfassung wählen", "", "Bilder (*.jpg *.jpeg *.png)"
        )
        if not files:
            return
            
        # Standard-Bauteil finden (wird ggf. automatisch angelegt)
        default_bt_id = self._get_default_bauteil_id()

        for f in files:
            new_s = models.IngSchaden(
                bauteil_id=default_bt_id,
                code="NEU",
                beschreibung=f"Importiertes Foto: {Path(f).name}",
                bewertung_s=0,
                bewertung_v=0,
                bewertung_d=0,
                skizze_json=None
            )
            new_s._temp_path = f # Temporär speichern
            self.temp_schaeden.append(new_s)
            
        self._refresh_table()
        # Den letzten neuen Eintrag auswählen
        self.table.setCurrentCell(len(self.temp_schaeden) - 1, 0)

    def _on_delete_schaden(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.temp_schaeden):
            self.temp_schaeden.pop(row)
            self._refresh_table()
            self.inspector.scene.clear()

    def _on_row_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.temp_schaeden):
            self.current_schaden_index = -1
            return
            
        self.current_schaden_index = row
        schaden = self.temp_schaeden[row]
        
        # Foto automatisch im Inspector laden
        if hasattr(schaden, "_temp_path"):
            self.inspector.load_image(schaden._temp_path)
        elif schaden.fotos:
            self.inspector.load_image(schaden.fotos[0].dateipfad)
        else:
            self.inspector.scene.clear()
            self.inspector.status.setText("Kein Bild für diesen Schaden hinterlegt.")
            
        # Bestehende Markierungen laden
        if schaden.skizze_json:
            self.inspector.load_json(schaden.skizze_json)
        else:
            # Wenn kein JSON da ist, aber wir ein Bild haben, Markierungen im Scene-Layer leeren
            # Aber nicht das Bild selbst! Der inspector.load_image macht das schon.
            pass

    def _on_marking_changed(self, json_str):
        if self.current_schaden_index >= 0:
            self.temp_schaeden[self.current_schaden_index].skizze_json = json_str

    def _on_ghost_mark_accepted(self, data):
        """Wird aufgerufen, wenn ein KI-Vorschlag im Inspector bestätigt wurde."""
        if self.current_schaden_index < 0:
            return
            
        schaden = self.temp_schaeden[self.current_schaden_index]
        
        # Automatische Kodierung
        if "code" in data:
            schaden.code = data["code"]
            # Name aus Katalog suchen für die Beschreibung
            for item in self.catalog.get("schadenskatalog", []):
                if str(item["code"]) == str(data["code"]):
                    schaden.beschreibung = item["name"]
                    break
        
        # Automatische Bewertung (S-V-D)
        if "defaults" in data:
            d = data["defaults"]
            schaden.bewertung_s = d.get("S", schaden.bewertung_s)
            schaden.bewertung_v = d.get("V", schaden.bewertung_v)
            schaden.bewertung_d = d.get("D", schaden.bewertung_d)
            
        self._refresh_table()
        self.statusBar().showMessage(f"KI-Vorschlag übernommen: {schaden.beschreibung}", 3000)

    def _refresh_table(self):
        self.table.setRowCount(len(self.temp_schaeden))
        for i, s in enumerate(self.temp_schaeden):
            bt = self.db.get(models.IngBauteil, s.bauteil_id) if s.bauteil_id else None
            self.table.setItem(i, 0, QTableWidgetItem(bt.name if bt else "Nicht zugeordnet"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{s.code} - {s.beschreibung}"))
            self.table.setItem(i, 2, QTableWidgetItem(str(s.bewertung_s)))
            self.table.setItem(i, 3, QTableWidgetItem(str(s.bewertung_v)))
            self.table.setItem(i, 4, QTableWidgetItem(str(s.bewertung_d)))
            
            has_foto = "📸" if (hasattr(s, "_temp_path") or s.fotos) else ""
            self.table.setItem(i, 5, QTableWidgetItem(has_foto))
            
        # Gesamtnote berechnen
        zn = berechne_zustandsnote_din1076(self.temp_schaeden)
        self.lbl_zn.setText(f"<b>ZN: {zn:.1f}</b>")
        if zn >= 3.0: self.lbl_zn.setStyleSheet("font-size: 16px; color: #d32f2f; font-weight: bold;")
        elif zn >= 2.0: self.lbl_zn.setStyleSheet("font-size: 16px; color: #f57c00; font-weight: bold;")
        else: self.lbl_zn.setStyleSheet("font-size: 16px; color: #388e3c; font-weight: bold;")

    def _on_save(self):
        """Validiert und speichert die Prüfung inkl. aller Schäden."""
        if not self._validate_schaeden():
            return
            
        zn = berechne_zustandsnote_din1076(self.temp_schaeden)
        pruefung = models.IngPruefung(
            bauwerk_id=self.bauwerk.id,
            datum=self.de_datum.date().toPython(),
            pruefart=self.cb_art.currentText(),
            pruefer=self.le_pruefer.text(),
            zustandsnote=zn
        )
        self.db.add(pruefung)
        self.db.flush()
        
        for s in self.temp_schaeden:
            s.pruefung_id = pruefung.id
            self.db.add(s)
            self.db.flush()
            
            # Foto-Referenz anlegen falls vorhanden
            if hasattr(s, "_temp_path"):
                foto = models.IngSchadensFoto(
                    schaden_id=s.id,
                    dateipfad=s._temp_path,
                    dateiname=Path(s._temp_path).name
                )
                self.db.add(foto)
            
        self.db.commit()
        self.finished.emit()

    def _get_default_bauteil_id(self) -> int:
        """Ermittelt das erste verfügbare Bauteil oder legt ein Standard-Bauteil an."""
        # 1. Bestehendes Bauteil suchen
        if self.bauwerk.teilbauwerke and self.bauwerk.teilbauwerke[0].bauteile:
            return self.bauwerk.teilbauwerke[0].bauteile[0].id
            
        # 2. Automatisches Anlegen einer Basis-Struktur (Fallback)
        # Wir brauchen ein Teilbauwerk und ein Bauteil
        tbw = models.IngTeilbauwerk(bauwerk_id=self.bauwerk.id, name="Gesamtbauwerk (Standard)")
        self.db.add(tbw)
        self.db.flush() # ID generieren
        
        bt = models.IngBauteil(teilbauwerk_id=tbw.id, name="Allgemeines Bauteil")
        self.db.add(bt)
        self.db.commit()
        
        # Lokales Objekt aktualisieren, damit die UI es sofort sieht
        self.db.refresh(self.bauwerk)
        
        return bt.id

    def _validate_schaeden(self) -> bool:
        """Prüft, ob alle erfassten Schäden valide sind (z.B. Bauteil-Zuordnung)."""
        for i, s in enumerate(self.temp_schaeden):
            if not s.bauteil_id:
                QMessageBox.warning(self, "Validierung", f"Schaden {i+1} ('{s.beschreibung}') ist keinem Bauteil zugeordnet.")
                self.table.setCurrentCell(i, 0)
                return False
        return True
