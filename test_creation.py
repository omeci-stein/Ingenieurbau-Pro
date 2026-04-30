from backend.database import SessionLocal, engine, Base
from backend import models
import sys

def test_project_creation():
    db = SessionLocal()
    try:
        print("Sicherung der Tabellen...")
        Base.metadata.create_all(bind=engine)
        
        print("Erstelle neues Projekt...")
        new_proj = models.Projekt(name="Testprojekt_Terminal")
        db.add(new_proj)
        db.commit()
        print(f"Projekt erfolgreich erstellt! ID: {new_proj.id}")
        
        # Prüfen ob Sparte existiert (wichtig für Netz)
        sparte = db.get(models.Sparte, 1)
        if not sparte:
            print("Erstelle Standard-Sparte...")
            sparte = models.Sparte(id=1, code="ING", name="Ingenieurbau")
            db.add(sparte)
            db.commit()
            
        print("Erstelle Netz für das Projekt...")
        netz = models.Netz(projekt_id=new_proj.id, name="Testnetz", sparte_id=1)
        db.add(netz)
        db.commit()
        print("Netz erfolgreich erstellt!")
        
    except Exception as e:
        print(f"FEHLER: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_project_creation()
