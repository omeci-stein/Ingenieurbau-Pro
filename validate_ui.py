import sys
import os
from PySide6.QtWidgets import QApplication
from main_ing import IngenieurbauProApp
from PySide6.QtCore import QTimer

def validate_ui():
    """
    KI-Agent Tester: Überprüft, ob die Applikation startet, 
    die Projektliste geladen wird und kein Font-Fehler auftritt.
    """
    app = QApplication(sys.argv)
    
    try:
        print("Starte UI-Validierung...")
        window = IngenieurbauProApp()
        
        # Warte kurz auf den QTimer für showMaximized
        from PySide6.QtTest import QTest
        QTest.qWait(200)
        
        # Prüfe Maximized-Modus
        if window.isMaximized():
            print("[OK] Hauptfenster startet im Vollbildmodus.")
        else:
            print("[WARNING] Hauptfenster ist nicht maximiert.")
            
        # Prüfe ob ProjectManager geladen wurde
        if hasattr(window, 'project_manager'):
            print("[OK] ProjectManager initialisiert.")
            
            # Prüfe Tab-Struktur
            if window.tabs.count() >= 2:
                print(f"[OK] Tab-Struktur korrekt ({window.tabs.count()} Tabs).")
            else:
                print("[ERROR] Fehler: Tabs fehlen.")
                sys.exit(1)
                
            # Prüfe Tabelle
            row_count = window.project_manager.table.rowCount()
            print(f"[OK] Projekt-Tabelle geladen ({row_count} Projekte).")
            
        else:
            print("[ERROR] Fehler: ProjectManager fehlt im Hauptfenster.")
            sys.exit(1)

        # Prüfe Tab-Logic
        if hasattr(window, 'open_pruefung_tab'):
            print("[OK] Hauptfenster unterstützt dynamische Tabs.")
        else:
            print("[ERROR] Fehler: open_pruefung_tab fehlt.")
            sys.exit(1)

        # Prüfe Widget-Instanziierung
        from widgets.ing_pruefung_dialog import IngPruefungWidget
        from backend import models
        bw = window._db.query(models.IngBauwerk).first()
        if bw:
            widget = IngPruefungWidget(window._db, bw)
            print("[OK] IngPruefungWidget erfolgreich instanziiert.")
        else:
            print("[SKIP] Kein Bauwerk vorhanden, Widget-Test übersprungen.")

        print("[OK] UI-Validierung erfolgreich abgeschlossen.")
        # Kurzes Anzeigen und dann schließen
        QTimer.singleShot(1000, app.quit)
        # app.exec() # Auskommentiert für automatisierten Test
        
    except Exception as e:
        print(f"[ERROR] KRITISCHER UI-FEHLER: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_ui()
