"""
KI-Engine für Ingenieurbau Pro (Echte Bildanalyse).
Nutzt OpenCV zur Erkennung von Rissen und Abplatzungen basierend auf Bildmerkmalen.
"""

import cv2
import numpy as np
import time

def detect_damages(image_path):
    """
    Analysiert ein Foto auf Schäden mittels Bildverarbeitung.
    """
    # Lade Bild (Robust gegenüber Umlauten im Pfad)
    try:
        # Wir lesen das Bild erst als binären Buffer via numpy
        stream = open(str(image_path), "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
        if img is None:
            return []
    except Exception as e:
        print(f"Fehler beim Laden des Bildes: {e}")
        return []

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Rauschunterdrückung
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 1. Riss-Erkennung via Canny & Dilatation
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    contours_edges, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    suggestions = []
    
    # 2. Analyse der Konturen
    for cnt in contours_edges:
        area = cv2.contourArea(cnt)
        if area < 1000: continue # Signifikante Erhöhung: Filtert Poren und Micro-Rauschen
        
        # Bounding Box / Rotated Rect
        rect = cv2.minAreaRect(cnt)
        (x, y), (w_box, h_box), angle = rect
        aspect_ratio = max(w_box, h_box) / (min(w_box, h_box) + 1e-5)
        
        # Heuristik: Lange, dünne Objekte sind Risse
        if aspect_ratio > 4 and area > 1500:
            # Vereinfache Kontur zu einer Linie für die UI
            box = cv2.boxPoints(rect)
            p1 = box[0]
            p2 = box[2]
            
            suggestions.append({
                "type": "line",
                "rel_x1": float(p1[0] / w), "rel_y1": float(p1[1] / h),
                "rel_x2": float(p2[0] / w), "rel_y2": float(p2[1] / h),
                "code": "1100",
                "label": "KI: Riss-Verdacht",
                "confidence": min(0.95, aspect_ratio * 0.1)
            })
            
        # Heuristik: Eher kompakte Objekte sind Abplatzungen
        elif aspect_ratio < 3 and area > 4000:
            suggestions.append({
                "type": "point",
                "rel_x": float(x / w), "rel_y": float(y / h),
                "code": "1200",
                "label": "KI: Schadensstelle (Abplatzung?)",
                "confidence": 0.7
            })

    # Limit auf Top-Vorschläge um UI nicht zu fluten
    suggestions = sorted(suggestions, key=lambda x: x['confidence'], reverse=True)[:15]
    
    # Simuliere eine kurze Rechenzeit für das "KI-Gefühl"
    time.sleep(0.5)
    
    return suggestions
