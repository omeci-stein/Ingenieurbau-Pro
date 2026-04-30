import math

def berechne_zustandsnote_din1076(schaeden):
    """
    Berechnet die Zustandsnote (ZN) nach DIN 1076 / RI-EBW-PRÜF.
    
    Logik (vereinfacht):
    ZN = max(S, V, D) + Aufschlag
    S, V, D sind die Noten für Standsicherheit, Verkehrssicherheit, Dauerhaftigkeit (0-4).
    """
    if not schaeden:
        return 1.0 # Sehr gut
        
    max_s = max([s.bewertung_s or 0 for s in schaeden])
    max_v = max([s.bewertung_v or 0 for s in schaeden])
    max_d = max([s.bewertung_d or 0 for s in schaeden])
    
    basis_note = max(max_s, max_v, max_d)
    
    # Vereinfachter Aufschlag-Algorithmus:
    # 0 -> 1.0, 1 -> 1.5, 2 -> 2.2, 3 -> 3.0, 4 -> 4.0
    mapping = {
        0: 1.0,
        1: 1.5,
        2: 2.2,
        3: 3.0,
        4: 4.0
    }
    
    zn = mapping.get(basis_note, 1.0)
    
    # Bonus für Häufung (exemplarisch)
    if len(schaeden) > 5 and zn < 3.5:
        zn += 0.2
        
    return min(zn, 4.0)
