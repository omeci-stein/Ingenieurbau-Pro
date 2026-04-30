from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from backend import models
from sqlalchemy.orm import Session

class ProjectManager(QWidget):
    """
    Widget zur Verwaltung und Übersicht aller Projekte.
    Ermöglicht das Anlegen, Löschen und Wechseln von Projekten.
    """
    
    projectSwitched = Signal(int) # Emittiert die ID des gewählten Projekts

    def __init__(self, db: Session, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        self.refresh_projects()

    def _setup_ui(self) -> None:
        """Initialisiert die Benutzeroberfläche des Projekt-Managers."""
        layout = QVBoxLayout(self)
        
        # Header / Aktionen
        actions_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh_projects)
        
        self.btn_new = QPushButton("➕ Neues Projekt...")
        self.btn_new.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        
        actions_layout.addWidget(self.btn_refresh)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_new)
        layout.addLayout(actions_layout)
        
        # Projekt-Tabelle
        self.group_list = QGroupBox("Verfügbare Projekte")
        list_layout = QVBoxLayout(self.group_list)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Erstellt am", "Aktion"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        list_layout.addWidget(self.table)
        layout.addWidget(self.group_list)

    def refresh_projects(self) -> None:
        """Lädt die Projektliste aus der Datenbank und aktualisiert die Tabelle."""
        try:
            projects = self.db.query(models.Projekt).order_by(models.Projekt.id.desc()).all()
            self.table.setRowCount(len(projects))
            
            for i, proj in enumerate(projects):
                # ID
                id_item = QTableWidgetItem(str(proj.id))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, id_item)
                
                # Name
                name_item = QTableWidgetItem(proj.name)
                if i == 0:
                    font = name_item.font()
                    font.setBold(True)
                    name_item.setFont(font)
                self.table.setItem(i, 1, name_item)
                
                # Datum
                date_str = proj.erstellt_am.strftime("%d.%m.%Y %H:%M") if proj.erstellt_am else "–"
                self.table.setItem(i, 2, QTableWidgetItem(date_str))
                
                # Aktion-Buttons (Öffnen)
                btn_open = QPushButton("Öffnen")
                btn_open.clicked.connect(lambda checked=False, p_id=proj.id: self.projectSwitched.emit(p_id))
                self.table.setCellWidget(i, 3, btn_open)
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Projekte konnten nicht geladen werden: {e}")

    def add_project_to_db(self, name: str) -> int:
        """Legt ein neues Projekt in der DB an und gibt die ID zurück."""
        new_proj = models.Projekt(name=name)
        self.db.add(new_proj)
        self.db.commit()
        self.refresh_projects()
        return new_proj.id
