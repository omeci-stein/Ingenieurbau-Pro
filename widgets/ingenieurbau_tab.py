from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QSplitter, QGroupBox,
    QFormLayout, QLineEdit, QComboBox, QDateEdit, QMessageBox,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QFileDialog, QMenu
)
from PySide6.QtCore import Qt, QDate
from backend import models
from backend.import_v195 import V195Importer
from backend.pdf_ing_bericht import erstelle_ing_bericht

class IngenieurbauTab(QWidget):
    """
    Modularer Tab für Ingenieurbauwerke (Brücken, Durchlässe etc.)
    nach DIN 1076 / ASB-ING.
    """
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        
        self._setup_ui()
        # Hinweis: refresh_data wird nun explizit vom MainWindow nach dem Projekt-Load aufgerufen

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header / Toolbar
        toolbar = QHBoxLayout()
        self.btn_neu = QPushButton("Neues Bauwerk…")
        self.btn_neu.clicked.connect(self._on_neu)
        self.btn_import = QPushButton("📥 Import (.V195)")
        self.btn_import.clicked.connect(self._on_import_v195)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.clicked.connect(self._on_delete)
        
        toolbar.addWidget(self.btn_neu)
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Splitter für Liste und Details
        self.splitter = QSplitter(Qt.Horizontal) # Horizontaler Splitter wirkt professioneller
        
        # Linke Seite: Liste der Bauwerke
        self.list_group = QGroupBox("Bauwerksverzeichnis")
        list_vbox = QVBoxLayout(self.list_group)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ASB-ID", "Name", "Typ", "Bauart", "Baujahr", "Note"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        list_vbox.addWidget(self.table)
        
        self.splitter.addWidget(self.list_group)
        
        # Rechte Seite: Detail-Bereich
        self.details_tabs = QTabWidget()
        
        # Detail-Tab 1: Stammdaten & Bauteile
        self.tab_bauteile = QWidget()
        self.bt_layout = QVBoxLayout(self.tab_bauteile)
        
        self.bt_tree = QTreeWidget()
        self.bt_tree.setHeaderLabels(["Bauteil / Gruppe", "Material", "Menge", "ID"])
        self.bt_tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.bt_layout.addWidget(self.bt_tree)
        
        bt_btns = QHBoxLayout()
        self.btn_add_bt = QPushButton("+ Bauteil")
        self.btn_add_bt.clicked.connect(self._on_add_bauteil)
        bt_btns.addWidget(self.btn_add_bt)
        bt_btns.addStretch()
        self.bt_layout.addLayout(bt_btns)
        
        self.details_tabs.addTab(self.tab_bauteile, "Bauteile (ASB-ING)")
        
        # Detail-Tab 2: Prüfungen (DIN 1076)
        self.tab_pruefung = QWidget()
        self.pr_layout = QVBoxLayout(self.tab_pruefung)
        self.pr_table = QTableWidget()
        self.pr_table.setColumnCount(4)
        self.pr_table.setHorizontalHeaderLabels(["Datum", "Art", "Prüfer", "Note"])
        self.pr_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pr_table.customContextMenuRequested.connect(self._on_pruefung_context_menu)
        self.pr_layout.addWidget(self.pr_table)
        
        pr_btns = QHBoxLayout()
        self.btn_add_pr = QPushButton("+ Neue Prüfung")
        self.btn_add_pr.clicked.connect(self._on_add_pruefung)
        pr_btns.addWidget(self.btn_add_pr)
        pr_btns.addStretch()
        self.pr_layout.addLayout(pr_btns)
        
        self.details_tabs.addTab(self.tab_pruefung, "Prüfungshistorie")
        
        self.splitter.addWidget(self.details_tabs)
        self.splitter.setSizes([500, 700])
        layout.addWidget(self.splitter)

    def refresh_data(self):
        """Lädt die Bauwerke aus der Datenbank."""
        pid = self.main_window._current_project_id
        db = self.main_window._db
        
        if not pid or not db:
            self.table.setRowCount(0)
            return
            
        try:
            bauwerke = db.query(models.IngBauwerk).all()
            self.table.setRowCount(len(bauwerke))
            
            for i, bw in enumerate(bauwerke):
                self.table.setItem(i, 0, QTableWidgetItem(bw.asb_id or ""))
                self.table.setItem(i, 1, QTableWidgetItem(bw.name or ""))
                self.table.setItem(i, 2, QTableWidgetItem(bw.typ or ""))
                self.table.setItem(i, 3, QTableWidgetItem(bw.bauart or ""))
                self.table.setItem(i, 4, QTableWidgetItem(str(bw.baujahr or "")))
                
                letzte_pruefung = db.query(models.IngPruefung).filter_by(bauwerk_id=bw.id).order_by(models.IngPruefung.datum.desc()).first()
                zn = f"{letzte_pruefung.zustandsnote:.1f}" if letzte_pruefung and letzte_pruefung.zustandsnote else "–"
                zn_item = QTableWidgetItem(zn)
                if letzte_pruefung and letzte_pruefung.zustandsnote:
                    from PySide6.QtGui import QColor
                    if letzte_pruefung.zustandsnote >= 3.0: zn_item.setBackground(QColor("#FFCDD2"))
                    elif letzte_pruefung.zustandsnote <= 2.0: zn_item.setBackground(QColor("#C8E6C9"))
                
                self.table.setItem(i, 5, zn_item)
                self.table.item(i, 0).setData(Qt.UserRole, bw.id)
        except Exception as e:
            print(f"Fehler beim Laden der Ingenieurbauwerke: {e}")
            self.table.setRowCount(0)

    def _on_selection_changed(self):
        row = self.table.currentRow()
        if row < 0:
            self.bt_tree.clear()
            return
            
        bw_id = self.table.item(row, 0).data(Qt.UserRole)
        bw = self.db.get(models.IngBauwerk, bw_id)
        
        self._load_bauteile(bw)
        self._load_pruefungen(bw)

    def _load_bauteile(self, bw):
        self.bt_tree.clear()
        for tbw in bw.teilbauwerke:
            parent = QTreeWidgetItem(self.bt_tree, [tbw.name, "", "", str(tbw.id)])
            parent.setBackground(0, Qt.lightGray)
            for bt in tbw.bauteile:
                QTreeWidgetItem(parent, [bt.name, bt.material or "", f"{bt.menge or 0} {bt.einheit or ''}", str(bt.id)])
        self.bt_tree.expandAll()

    def _load_pruefungen(self, bw):
        self.pr_table.setRowCount(len(bw.pruefungen))
        for i, pr in enumerate(bw.pruefungen):
            self.pr_table.setItem(i, 0, QTableWidgetItem(pr.datum.strftime("%d.%m.%Y") if pr.datum else ""))
            self.pr_table.item(i, 0).setData(Qt.UserRole, pr.id) # WICHTIG für PDF Export
            self.pr_table.setItem(i, 1, QTableWidgetItem(pr.pruefart or ""))
            self.pr_table.setItem(i, 2, QTableWidgetItem(pr.pruefer or ""))
            self.pr_table.setItem(i, 3, QTableWidgetItem(f"{pr.zustandsnote:.1f}" if pr.zustandsnote else "–"))

    def _on_add_bauteil(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Auswahl", "Bitte zuerst ein Bauwerk auswählen.")
            return
            
        bw_id = self.table.item(row, 0).data(Qt.UserRole)
        bw = self.db.get(models.IngBauwerk, bw_id)
        
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QGroupBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Bauteil hinzufügen")
        form = QFormLayout(dlg)
        
        # Teilbauwerk Auswahl/Neu
        cb_tbw = QComboBox()
        for tbw in bw.teilbauwerke:
            cb_tbw.addItem(tbw.name, tbw.id)
        cb_tbw.addItem("+ Neues Teilbauwerk erstellen...", -1)
        
        le_new_tbw = QLineEdit()
        le_new_tbw.setPlaceholderText("Name des neuen Teilbauwerks (z.B. Überbau)")
        le_new_tbw.setVisible(False)
        
        cb_tbw.currentIndexChanged.connect(lambda i: le_new_tbw.setVisible(cb_tbw.currentData() == -1))
        
        form.addRow("Teilbauwerk:", cb_tbw)
        form.addRow("", le_new_tbw)
        
        # Bauteil Daten
        le_name = QLineEdit()
        le_mat = QLineEdit()
        le_menge = QLineEdit()
        
        form.addRow("Bauteil-Name:", le_name)
        form.addRow("Material:", le_mat)
        form.addRow("Menge/Einheit:", le_menge)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        
        if dlg.exec() == QDialog.Accepted:
            tbw_id = cb_tbw.currentData()
            if tbw_id == -1:
                # Neues Teilbauwerk
                new_tbw = models.IngTeilbauwerk(bauwerk_id=bw.id, name=le_new_tbw.text())
                self.db.add(new_tbw)
                self.db.flush()
                tbw_id = new_tbw.id
            
            new_bt = models.IngBauteil(
                teilbauwerk_id=tbw_id,
                name=le_name.text(),
                material=le_mat.text(),
                menge=float(le_menge.text()) if le_menge.text().replace(".","",1).isdigit() else 0
            )
            self.db.add(new_bt)
            self.db.commit()
            self._load_bauteile(bw)

    def _on_neu(self):
        # Einfacher Dialog für neues Bauwerk
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Neues Ingenieurbauwerk")
        form = QFormLayout(dlg)
        
        le_asb = QLineEdit()
        le_name = QLineEdit()
        cb_typ = QComboBox()
        cb_typ.addItems(["Brücke", "Durchlass", "Stützwand", "Pumpwerk"])
        le_jahr = QLineEdit()
        
        form.addRow("ASB-ID:", le_asb)
        form.addRow("Name:", le_name)
        form.addRow("Typ:", cb_typ)
        form.addRow("Baujahr:", le_jahr)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        
        if dlg.exec() == QDialog.Accepted:
            new_bw = models.IngBauwerk(
                netz_id=self.main_window._current_netz_id() if hasattr(self.main_window, '_current_netz_id') else 1, # Fallback
                asb_id=le_asb.text(),
                name=le_name.text(),
                typ=cb_typ.currentText(),
                baujahr=int(le_jahr.text()) if le_jahr.text().isdigit() else None
            )
            self.db.add(new_bw)
            self.db.commit()
            self.refresh_data()

    def _on_import_v195(self):
        """Öffnet Dateidialog für .V195 Import."""
        path, _ = QFileDialog.getOpenFileName(
            self, "ASB-ING Datei importieren (.V195)", "", "Austauschdateien (*.V195 *.v195 *.txt)"
        )
        if not path:
            return
            
        try:
            # Netz-ID dynamisch ermitteln (erstes verfügbares Netz im Projekt)
            netz = self.main_window._db.query(models.Netz).first()
            if not netz:
                # Falls kein Netz existiert (leeres Projekt), legen wir ein Standardnetz an
                netz = models.Netz(projekt_id=self.main_window._current_project_id, name="Standardnetz", sparte_id=1)
                self.main_window._db.add(netz)
                self.main_window._db.flush()
            
            importer = V195Importer(self.main_window._db, netz.id)
            count = importer.import_file(path)
            QMessageBox.information(self, "Erfolg", f"{count} Bauwerke wurden erfolgreich importiert.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Import-Fehler", f"Fehler beim Import: {e}")

    def _on_pruefung_context_menu(self, pos):
        menu = QMenu()
        export_act = menu.addAction("📄 DIN 1076 Bericht exportieren (PDF)")
        action = menu.exec(self.pr_table.mapToGlobal(pos))
        if action == export_act:
            self._on_export_pdf()

    def _on_export_pdf(self):
        row = self.pr_table.currentRow()
        if row < 0: return
        
        pruefung_id = self.pr_table.item(row, 0).data(Qt.UserRole)
        bw_row = self.table.currentRow()
        if bw_row < 0: return
        bw_id = self.table.item(bw_row, 0).data(Qt.UserRole)
        bw_name = self.table.item(bw_row, 1).text()
        
        path, _ = QFileDialog.getSaveFileName(self, "Bericht speichern", f"Pruefbericht_{bw_name}.pdf", "PDF (*.pdf)")
        if path:
            try:
                # Projekt-Name aus DB holen oder Platzhalter
                proj = self.db.get(models.Projekt, self.main_window._current_project_id)
                proj_name = proj.name if proj else "NETSAN PRO Projekt"
                
                erstelle_ing_bericht(
                    self.db,
                    bw_id,
                    pruefung_id,
                    path,
                    proj_name
                )
                QMessageBox.information(self, "Erfolg", "Bericht wurde erfolgreich erstellt.")
                import os
                os.startfile(path)
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen: {e}")

    def _on_delete(self):
        row = self.table.currentRow()
        if row < 0: return
        
        bw_id = self.table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Löschen", "Bauwerk wirklich löschen?") == QMessageBox.Yes:
            bw = self.db.get(models.IngBauwerk, bw_id)
            self.db.delete(bw)
            self.db.commit()
            self.refresh_data()

    def _on_add_pruefung(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Auswahl", "Bitte zuerst ein Bauwerk auswählen.")
            return
            
        bw_id = self.table.item(row, 0).data(Qt.UserRole)
        bw = self.db.get(models.IngBauwerk, bw_id)
        
        # Statt QDialog.exec() nutzen wir nun das Tab-System des Hauptfensters
        if hasattr(self.main_window, "open_pruefung_tab"):
            self.main_window.open_pruefung_tab(self.db, bw)
        else:
            # Fallback falls direkt gestartet (unwahrscheinlich in Standalone)
            from widgets.ing_pruefung_dialog import IngPruefungWidget
            self._fallback_dlg = IngPruefungWidget(self.db, bw)
            self._fallback_dlg.show()

    def select_bauwerk_by_id(self, bauwerk_id: int):
        """Wählt ein Bauwerk in der Tabelle anhand seiner ID aus."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == bauwerk_id:
                self.table.selectRow(row)
                self.table.setCurrentCell(row, 0)
                break
