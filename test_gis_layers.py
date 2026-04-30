import sys
import os
from PySide6.QtWidgets import QApplication

# Pfad hinzufügen damit widgets gefunden werden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from widgets.ing_gis_canvas import IngGisCanvas, WMS_LAYERS

def test_layer_switch():
    app = QApplication(sys.argv)
    canvas = IngGisCanvas()
    
    print("Teste Standard-Layer...")
    if canvas._wms_cfg != WMS_LAYERS["DTK (Topo)"]:
        print("Fehler: Standard-Layer nicht DTK.")
        return False
        
    print("Umschalten auf Luftbild...")
    canvas.set_wms_layer(WMS_LAYERS["DOP (Luftbild)"])
    if canvas._wms_cfg != WMS_LAYERS["DOP (Luftbild)"]:
        print("Fehler: Umschaltung auf DOP fehlgeschlagen.")
        return False
        
    if canvas._bg_pixmap is not None:
        print("Fehler: Pixmap wurde nicht zurückgesetzt.")
        return False
        
    print("Erfolg: Layer-Umschaltung funktioniert.")
    return True

if __name__ == "__main__":
    if test_layer_switch():
        print("--- TEST ERFOLGREICH ---")
        sys.exit(0)
    else:
        print("--- TEST FEHLGESCHLAGEN ---")
        sys.exit(1)
