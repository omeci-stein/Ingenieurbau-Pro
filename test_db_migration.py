import sys
import os

# Pfad hinzufügen damit backend gefunden wird
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.database import SessionLocal, init_postgres_schema
from backend.models import IngBauwerk
from sqlalchemy import text

def test_migration():
    print("Starte Datenbank-Migration...")
    init_postgres_schema()
    
    db = SessionLocal()
    try:
        print("Teste Zugriff auf IngBauwerk mit GPS-Spalten...")
        # Rohes SQL um sicherzugehen dass die Spalten physisch da sind
        res = db.execute(text("SELECT gps_lat, gps_lon FROM ing_bauwerk LIMIT 1"))
        print("Erfolg: Spalten sind vorhanden.")
        return True
    except Exception as e:
        print(f"FEHLER: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if test_migration():
        print("--- TEST ERFOLGREICH ---")
        sys.exit(0)
    else:
        print("--- TEST FEHLGESCHLAGEN ---")
        sys.exit(1)
