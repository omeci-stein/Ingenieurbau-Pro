# Fortschritt: Ingenieurbau Pro

## [2026-04-30] - Session 1: Standalone Stabilisierung & KI-UI
**Status: In Bearbeitung**

### ✅ Abgeschlossen
- Technische Trennung vom Sanierungsdashboard erfolgreich validiert.
- Behebung des `psycopg2.errors.ForeignKeyViolation` Fehlers durch Sparte-Seeding (ID 1).
- Implementierung der Projektverwaltung (Neuanlage/Wechsel) in `main_ing.py`.
- Modernisierung der SQLAlchemy-Abfragen (`query.get` -> `session.get`) zur Behebung von `LegacyAPIWarning`.
- **KI-Assistenz im Visual Inspector (UI-Gerüst & Logik)**:
    - ✨ KI-Scan Button hinzugefügt.
    - Logik für Ghost-Markings (blaue gestrichelte Linien/Kreise) implementiert.
    - Interaktiver Validierungs-Workflow (Klick zum Übernehmen) eingebaut.
    - ✅ **Auto-Kodierung**: Automatische Zuweisung von RI-EBW-PRÜF Codes und S-V-D Default-Werten bei Annahme eines Vorschlags.
    - Mock-Backend `backend/ai_engine.py` auf Basis des Realkatalogs erstellt.

### 🔲 Offen
- **GIS-Integration (Meilenstein 1)**: Einbettung der Leaflet-Karte als Hauptansicht.
- **Echte KI-Inferenz**: Anbindung eines realen YOLO/ONNX-Modells für die Risserkennung.
- **3D/BIM Viewer**: Integration eines OBJ/IFC-Viewers (Meilenstein 3).
