"""
KIS Datenbank-Modul
====================
SQLAlchemy Engine/Session, Audit-Log via Events, Sparte-Seed.
"""

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import text
from pathlib import Path
from datetime import datetime

# Basis-Verzeichnis für alle Projektdatenbanken
BASE_DIR = Path(__file__).parent.parent

import json
import os
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, Session as _Session
from pathlib import Path

# Basis-Verzeichnis
BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "db_config.json"

Base = declarative_base()

def get_db_url() -> str:
    """Lädt die PostgreSQL-Verbindungsdaten aus der Konfiguration oder liefert Fallback."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return cfg.get("url", "postgresql://postgres:postgres@localhost:5432/kis_gis")
        except Exception:
            pass
    return "postgresql://postgres:postgres@localhost:5432/kis_gis"

def save_db_url(url: str) -> None:
    """Speichert die Datenbank-URL ab."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"url": url}, f)

SQLALCHEMY_DATABASE_URL = get_db_url()

# Initialisiere die Engine nur einmal (Connection Pooling durch SQLA)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database_info() -> dict:
    return {
        "database_url": SQLALCHEMY_DATABASE_URL,
        "base_directory": str(BASE_DIR.absolute())
    }

def test_connection(url: str = None) -> tuple[bool, str]:
    """Testet die Verbindung zu einer Datenbank-URL.
    Gibt (Success, ErrorMessage) zurück.
    """
    test_url = url or SQLALCHEMY_DATABASE_URL
    try:
        temp_engine = create_engine(test_url, connect_args={"connect_timeout": 5})
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        temp_engine.dispose()
        return True, ""
    except Exception as e:
        return False, str(e)

# ============================================================
# SCHEMA CATEGORIZATION
# ============================================================
_GLOBAL_TABLES = {
    "sparte", "projekt", "audit_log", "netz", "massnahmen_katalog",
    "ing_bauwerk", "ing_teilbauwerk", "ing_bauteil", "ing_pruefung", "ing_schaden", "ing_schadens_foto"
}

def _get_project_tables():
    """Gibt alle Tabellen zurück, die projekt-spezifisch sind."""
    from backend import models  # Lokal importieren um Metadaten zu laden
    return [t for name, t in Base.metadata.tables.items() if name not in _GLOBAL_TABLES]

def _get_global_tables():
    """Gibt alle Tabellen zurück, die global (public) sind."""
    from backend import models  # Lokal importieren
    return [t for name, t in Base.metadata.tables.items() if name in _GLOBAL_TABLES]

# ============================================================
# Sparte-Seed-Daten
# ============================================================
_SPARTEN_SEED = [
    ("AW", "Abwasser"),
    ("WV", "Wasserversorgung"),
    ("GAS", "Gas"),
    ("STR", "Straße"),
]

def seed_sparten(session: Session) -> None:
    """Legt Standard-Sparten an, falls noch nicht vorhanden."""
    from .models import Sparte
    existing = {s.code for s in session.query(Sparte).all()}
    for code, name in _SPARTEN_SEED:
        if code not in existing:
            session.add(Sparte(code=code, name=name))
    session.commit()

# ============================================================
# Audit-Log via SQLAlchemy Events
# ============================================================
_AUDIT_SKIP_TABLES = {"audit_log", "sparte"}

def _get_audit_log_class():
    from .models import AuditLog
    return AuditLog

def install_audit_listeners(session_factory):
    @event.listens_for(session_factory, "after_flush")
    def after_flush(session, flush_context):
        if session.info.get("skip_audit"):
            return
        try:
            AuditLog = _get_audit_log_class()

            # INSERT
            for obj in session.new:
                try:
                    tbl = obj.__class__.__tablename__
                    if tbl in _AUDIT_SKIP_TABLES:
                        continue
                    pk = inspect(obj).identity
                    if pk:
                        session.add(AuditLog(
                            tabelle=tbl,
                            datensatz_id=pk[0],
                            aktion="INSERT",
                        ))
                except Exception:
                    pass  # Audit-Log Fehler nicht propagieren

            # UPDATE
            for obj in session.dirty:
                try:
                    tbl = obj.__class__.__tablename__
                    if tbl in _AUDIT_SKIP_TABLES:
                        continue
                    insp = inspect(obj)
                    pk = insp.identity
                    if not pk:
                        continue
                    for attr in insp.attrs:
                        hist = attr.history
                        if hist.has_changes() and hist.deleted:
                            old_val = hist.deleted[0] if hist.deleted else None
                            new_val = hist.added[0] if hist.added else None
                            session.add(AuditLog(
                                tabelle=tbl,
                                datensatz_id=pk[0],
                                feld=attr.key,
                                alter_wert=str(old_val)[:250] if old_val is not None else None,
                                neuer_wert=str(new_val)[:250] if new_val is not None else None,
                                aktion="UPDATE",
                            ))
                except Exception:
                    pass
        except Exception as e:
            print(f"WARNUNG: Audit-Log Listener Fehler: {e}")

        # DELETE
        for obj in session.deleted:
            try:
                tbl = obj.__class__.__tablename__
                if tbl in _AUDIT_SKIP_TABLES:
                    continue
                pk = inspect(obj).identity
                if pk:
                    session.add(AuditLog(
                        tabelle=tbl,
                        datensatz_id=pk[0],
                        aktion="DELETE",
                    ))
            except Exception:
                pass

install_audit_listeners(SessionLocal)

# ============================================================
# SCHEMA HANDLING (PostgreSQL search_path)
# ============================================================

@event.listens_for(_Session, "after_begin")
def receive_after_begin(session, transaction, connection):
    """
    Setzt den search_path bei jedem Transaktionsstart, falls eine 
    Projekt-Schema-ID in session.info hinterlegt ist.
    Dies stellt sicher, dass auch nach einem commit() (und möglichem 
    Verlust des Search-Paths auf der Connection) die richtige Tabelle
    gefunden wird.
    """
    schema = session.info.get("schema")
    if schema:
        connection.execute(text(f"SET search_path TO {schema}, public"))

def get_project_database_path(project_name: str = None, project_folder: str = None):
    """Fallback-Wrapper (für Abwärtskompatibilität)."""
    return SQLALCHEMY_DATABASE_URL

def get_schema_name(project_id: int) -> str:
    """Generiert einen sicheren Schema-Namen für ein Projekt."""
    return f"pr_{project_id}"



def _ensure_column(conn, table_name, column_name, column_type, schema=None):
    """Prüft ob eine Spalte existiert und fügt sie ggf. hinzu."""
    inspector = inspect(conn)
    if not inspector.has_table(table_name, schema=schema):
        return
    columns = [c['name'] for c in inspector.get_columns(table_name, schema=schema)]
    if column_name not in columns:
        full_table = f"{schema}.{table_name}" if schema else table_name
        conn.execute(text(f"ALTER TABLE {full_table} ADD COLUMN {column_name} {column_type}"))

def init_project_schema(project_id: int) -> str:
    """
    Initialisiert das PostgreSQL-Schema für ein spezifisches Projekt.
    Erstellt das Schema und alle projekt-spezifischen Tabellen.
    """
    schema_name = get_schema_name(project_id)
    with engine.connect() as conn:
        # Schema erstellen
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()
        
    with engine.begin() as conn:
        # Search Path setzen damit metadata.create_all im Schema arbeitet
        conn.execute(text(f"SET search_path TO {schema_name}, public"))
        
        # Nur Projekt-Tabellen in diesem Schema initialisieren
        project_tables = _get_project_tables()
        Base.metadata.create_all(bind=conn, tables=project_tables)
        
        # Migrationen für projekt-spezifische Tabellen
        _ensure_column(conn, "gis_strassen_info", "osm_wasser_m", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_gleise_m", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_parkplatz_m", "DOUBLE PRECISION", schema=schema_name)
        
        # Phase 1 Logistik (Bäume, Gebäude, Landnutzung)
        _ensure_column(conn, "gis_strassen_info", "osm_baum_n_m", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_baum_anzahl", "INTEGER", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_gebaeude_res", "INTEGER", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_gebaeude_com", "INTEGER", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_landuse", "VARCHAR(100)", schema=schema_name)
        _ensure_column(conn, "gis_strassen_info", "osm_pflegeheim_m", "DOUBLE PRECISION", schema=schema_name)

        # Gemeinsame Migrationen für Haltung/Schacht (BaSYS/Kandis Style)
        for tbl in ["haltung", "schacht"]:
            _ensure_column(conn, tbl, "anlagenummer", "VARCHAR(50)", schema=schema_name)
            _ensure_column(conn, tbl, "bauweise", "VARCHAR(50)", schema=schema_name)
            _ensure_column(conn, tbl, "reinigungsintervall", "VARCHAR(50)", schema=schema_name)
            _ensure_column(conn, tbl, "restnutzungsdauer", "INTEGER", schema=schema_name)
            _ensure_column(conn, tbl, "schadenswert", "DOUBLE PRECISION", schema=schema_name)
            _ensure_column(conn, tbl, "zugaenglichkeit", "VARCHAR(100)", schema=schema_name)

        # Haltungs-spezifisch
        _ensure_column(conn, "haltung", "kb_wert", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "haltung", "deckelhoehe_zulauf", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "haltung", "deckelhoehe_ablauf", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "haltung", "auskleidung", "VARCHAR(100)", schema=schema_name)
        _ensure_column(conn, "haltung", "relining", "BOOLEAN", schema=schema_name)
        _ensure_column(conn, "haltung", "abwasserart", "VARCHAR(100)", schema=schema_name)

        # Schacht-spezifisch
        _ensure_column(conn, "schacht", "bauform", "VARCHAR(100)", schema=schema_name)
        _ensure_column(conn, "schacht", "deckelzustand", "VARCHAR(100)", schema=schema_name)

        # Inspektion-spezifisch (Kodiersystem-Modernisierung Phase 1)
        _ensure_column(conn, "inspektion_haltung", "kodiersystem", "VARCHAR(100)", schema=schema_name)
        _ensure_column(conn, "inspektion_schacht", "kodiersystem", "VARCHAR(100)", schema=schema_name)
        
        # Ingenieurbau-spezifisch (GIS Integration)
        _ensure_column(conn, "ing_bauwerk", "gps_lat", "DOUBLE PRECISION", schema=schema_name)
        _ensure_column(conn, "ing_bauwerk", "gps_lon", "DOUBLE PRECISION", schema=schema_name)
        
    return schema_name

def delete_project_schema(project_id: int) -> None:
    """Löscht das PostgreSQL-Schema eines Projekts (CASCADE)."""
    schema_name = get_schema_name(project_id)
    with engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        conn.commit()

def create_project_session(project_id: int):
    """
    Erstellt eine Session, die für das spezifische Projekt-Schema konfiguriert ist.
    Returns: (Session, DatabaseURL)
    """
    if project_id is None:
        return SessionLocal(), SQLALCHEMY_DATABASE_URL
        
    schema_name = init_project_schema(project_id)
    session = SessionLocal()
    
    # Schema-Info für Event-Listener hinterlegen (nach_begin)
    session.info['schema'] = schema_name
    
    # Initiale Ausführung für den aktuellen Stand
    session.execute(text(f"SET search_path TO {schema_name}, public"))
    
    return session, SQLALCHEMY_DATABASE_URL

def init_postgres_schema() -> None:
    """
    Initialisiert das globale PostgreSQL Schema (public) inklusive PostGIS.
    """
    try:
        # engine.begin() sorgt für automatischen Commit am Ende des Blocks
        # oder Rollback bei Fehlern innerhalb des Blocks.
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    except Exception as e:
        print("WARNUNG: Konnte PostGIS Extension nicht initialisieren. Fehler:", e)

    # Nur globale Tabellen in 'public' erstellen
    try:
        global_tables = _get_global_tables()
        Base.metadata.create_all(bind=engine, tables=global_tables)
        
        # Migrationen für globale Tabellen
        with engine.begin() as conn:
            _ensure_column(conn, "projekt", "settings_use_gis_fj", "BOOLEAN DEFAULT FALSE")
            
            # Falls Legacy-Tabellen im public Schema liegen, auch diese migrieren
            for tbl in ["haltung", "schacht"]:
                _ensure_column(conn, tbl, "anlagenummer", "VARCHAR(50)")
                _ensure_column(conn, tbl, "bauweise", "VARCHAR(50)")
                _ensure_column(conn, tbl, "reinigungsintervall", "VARCHAR(50)")
                _ensure_column(conn, tbl, "restnutzungsdauer", "INTEGER")
                _ensure_column(conn, tbl, "schadenswert", "DOUBLE PRECISION")
                _ensure_column(conn, tbl, "zugaenglichkeit", "VARCHAR(100)")

            _ensure_column(conn, "haltung", "kb_wert", "DOUBLE PRECISION")
            _ensure_column(conn, "haltung", "deckelhoehe_zulauf", "DOUBLE PRECISION")
            _ensure_column(conn, "haltung", "deckelhoehe_ablauf", "DOUBLE PRECISION")
            _ensure_column(conn, "haltung", "auskleidung", "VARCHAR(100)")
            _ensure_column(conn, "haltung", "relining", "BOOLEAN")
            _ensure_column(conn, "haltung", "abwasserart", "VARCHAR(100)")

            _ensure_column(conn, "schacht", "bauform", "VARCHAR(100)")
            _ensure_column(conn, "schacht", "deckelzustand", "VARCHAR(100)")

            # Inspektion-spezifisch (Kodiersystem-Modernisierung Phase 1)
            _ensure_column(conn, "inspektion_haltung", "kodiersystem", "VARCHAR(100)")
            _ensure_column(conn, "inspektion_schacht", "kodiersystem", "VARCHAR(100)")
            
            # Ingenieurbau-spezifisch (GIS Integration)
            _ensure_column(conn, "ing_bauwerk", "gps_lat", "DOUBLE PRECISION")
            _ensure_column(conn, "ing_bauwerk", "gps_lon", "DOUBLE PRECISION")
            
            # GIS Migrationen für Public (Legacy-Projekte)
            _ensure_column(conn, "gis_strassen_info", "osm_wasser_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_gleise_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_parkplatz_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_baum_n_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_baum_anzahl", "INTEGER")
            _ensure_column(conn, "gis_strassen_info", "osm_gebaeude_res", "INTEGER")
            _ensure_column(conn, "gis_strassen_info", "osm_gebaeude_com", "INTEGER")
            _ensure_column(conn, "gis_strassen_info", "osm_landuse", "VARCHAR(100)")
            _ensure_column(conn, "gis_strassen_info", "osm_pflegeheim_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_krankenhaus_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_feuerwehr_m", "DOUBLE PRECISION")
            _ensure_column(conn, "gis_strassen_info", "osm_schule_m", "DOUBLE PRECISION")
            
    except Exception as e:
        print("FEHLER bei create_all (global):", e)
    
    db = SessionLocal()
    try:
        seed_sparten(db)
    except Exception as e:
        db.rollback()
        print("FEHLER: Konnte Sparten-Seed nicht durchführen:", e)
        # Wir werfen den Fehler nicht unbedingt weiter, damit die App starten kann,
        # aber die Transaktion ist nun sauber zurückgerollt.
    finally:
        db.close()
    
    # Alle bestehenden Projekt-Schemas ebenfalls migrieren
    try:
        from . import models
        db = SessionLocal()
        projekte = db.query(models.Projekt).all()
        for p in projekte:
            try:
                init_project_schema(p.id)
            except Exception as ex:
                print(f"WARNUNG: Konnte Schema für Projekt {p.id} nicht migrieren: {ex}")
        db.close()
    except Exception as e:
        print(f"FEHLER bei Projekt-Migrationen: {e}")

    # Pool leeren, damit die Main-App mit frischen Verbindungen startet
    engine.dispose()

def get_geometry_as_wkt(geom_obj) -> str | None:
    """
    Konvertiert ein PostGIS-Geometrie-Objekt (WKBElement) in WKT (String).
    Unterstützt auch Legacy-WKT-Strings (SQLite Fallback).
    """
    if geom_obj is None:
        return None
    if isinstance(geom_obj, str):
        return geom_obj
    try:
        from geoalchemy2.shape import to_shape
        return to_shape(geom_obj).wkt
    except Exception:
        # Fallback: Versuche String-Repräsentation (oft hex bei PostGIS ohne to_shape)
        return str(geom_obj)
