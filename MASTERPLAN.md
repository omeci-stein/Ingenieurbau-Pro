# Ingenieurbau Pro - Masterplan

## 1. Vision & Zielsetzung
Ingenieurbau Pro ist eine spezialisierte Standalone-Lösung für die Prüfung von Ingenieurbauwerken nach DIN 1076 / ASB-ING. Ursprünglich aus einem Sanierungsdashboard ausgekoppelt, zielt die Applikation auf maximale Effizienz im Arbeitsalltag von Brückenprüfern ab.

## 2. Architektur & Tech-Stack
*   **Sprache:** Python 3.11+
*   **UI-Framework:** PySide6 (Qt)
*   **Datenbank:** PostgreSQL (via SQLAlchemy ORM)
*   **Kernmodule:**
    *   `main_ing.py`: Haupteinstiegspunkt & Projektverwaltung.
    *   `backend/`: Datenmodelle (`models.py`), Import-Logik (`import_v195.py`), PDF-Export (`pdf_ing_bericht.py`).
    *   `widgets/`: Modulare UI-Komponenten (`ingenieurbau_tab.py`, `visual_inspector.py`).
    *   `backend/ai_engine.py`: Schnittstelle für KI-unterstützte Schadenserkennung.

## 3. Datenmodell (Auszug)
*   **Projekt**: Klammer für alle Daten.
*   **Sparte**: Fachbereich (Default: ID 1, "Ingenieurbau").
*   **Netz**: Gruppierung von Bauwerken innerhalb eines Projekts.
*   **IngBauwerk**: Stammdaten (ASB-ID, Name, Typ, Baujahr, Geometrie).
*   **IngPruefung**: DIN 1076 Prüfungsereignis (Hauptprüfung, Einfach, etc.) mit Zustandsnote.
*   **IngSchaden**: Einzelschaden mit S-V-D Bewertung und Skizze (JSON).

## 4. Konventionen & Entscheidungen
*   **Standalone-Split**: Die Applikation wurde technisch vom Sanierungsdashboard getrennt.
*   **Mapping**: "Map-First" Ansatz via Leaflet.js in QWebEngine (geplant).
*   **KI-Assistenz**: "Ghost-Markings" im Visual Inspector zur Beschleunigung der Erfassung.
*   **Zustandsnoten**: Berechnung nach RI-EBW-PRÜF (DIN 1076).

## 5. Zukünftige Module
*   BIM/3D-Viewer Integration.
*   Tablet/Offline-Optimierung.
*   Export für SIB-Bauwerke.
