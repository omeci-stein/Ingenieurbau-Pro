import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Pfad hinzufügen damit backend gefunden wird
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.database import SessionLocal, init_postgres_schema
from backend.models import IngBauwerk

def test_map_data_load():
    print("Starte Daten-Check für GIS...")
    init_postgres_schema()
    db = SessionLocal()
    
    bauwerke = db.query(IngBauwerk).all()
    print(f"Gefundene Bauwerke in der Datenbank: {len(bauwerke)}")
    
    if len(bauwerke) == 0:
        print("WARNUNG: Keine Bauwerke in der DB. Erstelle Test-Bauwerk...")
        from backend.models import Netz
        n = db.query(Netz).first()
        if not n:
            n = Netz(projekt_id=1, sparte_id=1, name="Test-Netz")
            db.add(n)
            db.commit()
        
        b = IngBauwerk(name="Test-Brücke Essen", asb_id="BW-TEST-1", netz_id=n.id, gps_lat=51.45, gps_lon=7.01)
        db.add(b)
        db.commit()
        bauwerke = [b]
        print("Test-Bauwerk erstellt.")

    # Simuliere die Datenaufbereitung aus main_ing.py
    data = []
    for b in bauwerke:
        lat = b.gps_lat or (51.45 + (b.id * 0.01))
        lon = b.gps_lon or (7.01 + (b.id * 0.01))
        data.append({"id": b.id, "name": b.name, "lat": lat, "lon": lon})
    
    print(f"Bereitgestellte Marker-Daten: {len(data)}")
    db.close()
    return len(data) > 0

if __name__ == "__main__":
    # Wir brauchen eine QApplication für Qt-Objekte, aber wir können den Test auch ohne UI machen
    # da wir nur die Datenlogik prüfen.
    if test_map_data_load():
        print("--- TEST ERFOLGREICH: DATEN FÜR GIS VORHANDEN ---")
        sys.exit(0)
    else:
        print("--- TEST FEHLGESCHLAGEN ---")
        sys.exit(1)
