# Roadmap: Ingenieurbau Pro - Standalone Solution

Nach der erfolgreichen technischen Trennung folgt nun der Ausbau zur marktführenden Fachlösung für Ingenieurbauwerke nach DIN 1076.

## 🚀 Strategische Meilensteine

### 1. KI-Assistenz im Visual Inspector
**Priorität: KRITISCH (Arbeitsalltag-Revolution)**
*   **Ziel:** Automatisierte Schadenserkennung zur Effizienzsteigerung ("Der digitale Assistent").
*   **Features:**
    *   **Auto-Scan:** Hintergrund-Analyse beim Laden von Fotos (YOLO-basiert).
    *   **Ghost-Markings:** Transparente Vorschläge (Risse, Abplatzungen), die der Ingenieur nur noch validieren muss.
    *   **Auto-Kodierung:** Vorschlag des RI-EBW-PRÜF Schadenscodes (z.B. "101 - Riss").
    *   **Validierungs-Workflow:** Einfaches Bestätigen (Click) oder Verwerfen (Swipe/Rechtsklick).

### 2. GIS-Integration (Map-First Ansicht)
**Priorität: Hoch (Präsentation & Übersicht)**
*   **Ziel:** Interaktive Übersicht aller Bauwerke auf einer Karte.
*   **Features:**
    *   OSM-Integration via `QtWebEngine` und `Leaflet.js`.
    *   Dynamische Marker: Farbe basierend auf Zustandsnote (ZN).
    *   Bidirektionale Kopplung: Klick auf Marker öffnet Detailansicht.

### 3. BIM & 3D-Viewer
*   **Ziel:** Räumliche Schadensverortung an digitalen Zwillingen.

### 4. Tablet-Optimierung (Vor-Ort-Prüfung)
*   **Ziel:** Produktivität im Außendienst durch Touch-UI und Offline-Modus.

### 5. Multi-Schnittstellen (Import/Export)
*   **Ziel:** Maximale Interoperabilität (SIB-Bauwerke, V195, JSON).

---

## 🛠️ Konzept zur Umsetzung: KI-Assistenz (Punkt 1)

Der Fokus liegt auf einer nahtlosen Integration in den bestehenden `VisualInspector`.

### Technische Architektur
*   **Inferenz-Engine:** Integration von `ONNX Runtime` für performante lokale KI-Ausführung ohne Cloud-Zwang.
*   **Vorschlags-Layer:** Ein separater `QGraphicsScene` Layer für "Ghost-Items", die visuell von finalen Markierungen unterschieden werden.
*   **Interaktions-Logik:** Ghost-Items reagieren auf Klicks. Ein Klick wandelt das `QGraphicsItem` in ein permanentes Datenbank-Objekt um.

### Implementierungsschritte
1.  **UI-Erweiterung:** 
    *   Hinzufügen eines "✨ KI-Scan" Buttons in der Toolbar von `visual_inspector.py`.
    *   Implementierung der "Ghost-Markierung" (gestrichelte Linien, semi-transparent).
2.  **Inferenz-Mockup:** Erstellung eines Moduls `backend/ai_engine.py`, das vorerst simulierte Koordinaten liefert (später echtes YOLO-Modell).
3.  **Vorschlags-Manager:** Logik zum Verwalten der KI-Vorschläge (Zusammenführung von KI-Output und RI-EBW-Codes).
4.  **Validierungs-UI:** "Alle bestätigen" Button und Kontextmenü für Einzel-Vorschläge.

---

## 🖼️ UI-Mockup (KI-Inspector)
![KI Inspector Mockup](C:\Users\omeci\.gemini\antigravity\brain\f298a764-df5a-4406-84d5-8e4abab8a41e\ai_visual_inspector_mockup_1777547330488.png)
*Visualisierung des "Digitalen Assistenten" mit Ghost-Markings und Auto-Kodierung.*
