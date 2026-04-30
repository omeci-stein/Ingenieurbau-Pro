# Entwicklungsregeln & KI-Konventionen

Diese Datei definiert die Arbeitsweise der KI (Antigravity) für das Projekt Ingenieurbau Pro.

## Session-Start (PFLICHT — immer zuerst ausführen)
Lies zu Beginn **jeder** Sitzung diese drei Dateien in dieser Reihenfolge:

1. `MASTERPLAN.md` — Architektur, Datenmodell, Konventionen, Entscheidungen
2. `PROGRESS.md` — Was in den letzten Sessions erreicht wurde, was noch offen ist
3. `KI-Vorgaben.md` — diese Datei (Rollen, Regeln, Konventionen)

Danach bei Bedarf: `Projekt_Knowledge/INDEX.md` → zuständige Domain-Datei.

## Session-Ende (PFLICHT)
Nach jeder Session `PROGRESS.md` aktualisieren:
- Neue Einträge oben einfügen (neueste Session zuerst)
- Abgeschlossenes mit ✅, Offenes mit 🔲 markieren
- **Validierung**: Kurzes Statement zur Agent-basierten Prüfung der Änderungen
- Nur Wesentliches — keine Commit-Listen, keine Code-Details

---

## KI-Kernrichtlinien (PFLICHT)

1. **Deterministisches Vorgehen**: Immer logisch strukturiert und reproduzierbar handeln. Keine zufälligen Abweichungen von etablierten Mustern.
2. **Menschliche Nachvollziehbarkeit**: Code so schreiben, dass er für einen menschlichen Entwickler sofort logisch und nachverfolgbar ist.
3. **Maximale Dokumentation & Kommentierung**: Jede Funktion, jede komplexe Logik-Sektion und jede nicht-triviale Änderung muss im Code ausführlich kommentiert werden. Begründungen ("Warum") sind wichtiger als Beschreibungen ("Was").
4. **Sprechende Namen**: Variablen, Funktionen und Klassen müssen selbsterklärend benannt sein (z.B. `schacht_tiefe_mm` statt `s_t`).
5. **20-Zeilen-Regel (Empfehlung)**: Funktionen sollten idealerweise nicht länger als 20–30 Zeilen sein. Wenn sie komplexer werden → in logische Teil-Funktionen aufteilen.
6. **Frühzeitiges Beenden (Early Return)**: Fehlerfälle und Randbedingungen sofort am Funktionsanfang abfangen und zurückkehren. Tiefe `if-else`-Verschachtelungen sind strikt zu vermeiden (Guard Clauses).
7. **Modulare Entwicklung**: Code strikt in logische Module und Verantwortlichkeiten trennen (Separation of Concerns).
8. **DRY (Don't Repeat Yourself)**: Redundanzen vermeiden. Gemeinsam genutzte Logik in Hilfsfunktionen oder Basisklassen auslagern.
9. **Type Hinting**: Konsequente Nutzung von Python Typ-Annotationen (`def func(name: str) -> bool:`) bzw. JSDoc für JavaScript.
10. **Docstrings / JSDoc**: Jede öffentliche Klasse und Methode muss einen Docstring haben, der Zweck, Parameter und Rückgabewerte beschreibt.
11. **Clean Code Standards**: Einhaltung allgemeiner Clean Code Prinzipien (Single Responsibility, Least Astonishment, SOLID-Grundlagen).
