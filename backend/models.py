"""
KIS Datenmodell – SQLAlchemy ORM nach KONZEPT.md v1.4
=====================================================
Tabellen: sparte, projekt, netz, schacht, haltung,
          inspektion_haltung, inspektion_schacht, inspektion_video,
          befund_haltung, befund_schacht,
          bewertung_haltung, bewertung_schacht,
          sanierungsprojekt, massnahmen_katalog, massnahme,
          massnahme_befund, lv_position, audit_log
"""

import datetime

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, Boolean,
    DateTime, Date, UniqueConstraint, CheckConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from .database import Base


# ============================================================
# STAMMDATEN
# ============================================================

class Sparte(Base):
    __tablename__ = "sparte"

    id   = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)   # 'AW', 'WV', 'GAS', 'STR'
    name = Column(String(100), nullable=False)                # 'Abwasser', …

    netze = relationship("Netz", back_populates="sparte")


class Projekt(Base):
    __tablename__ = "projekt"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(255), nullable=False)
    auftraggeber   = Column(String(255), nullable=True)
    ort            = Column(String(255), nullable=True)
    projekt_ordner        = Column(Text, nullable=True)
    beschreibung          = Column(Text, nullable=True)
    medien_pfad_bilder    = Column(Text, nullable=True)
    medien_pfad_video     = Column(Text, nullable=True)
    medien_pfad_dokumente = Column(Text, nullable=True)
    
    # Einstellungen für Berechnungen
    settings_use_gis_fj   = Column(Boolean, default=False) # Smart Fj via OSM (Wasser/Gleise)

    status         = Column(String(50), nullable=False, default="Import offen")
    bewertungs_system = Column(String(20), nullable=True)
    qualitaets_index  = Column(Float, nullable=True)  # Qualitätsindex (0.0 - 1.0)

    # NULL = noch kein Import, "DWA" = DWA-M 149-3, "ISYBAU" = ISYBAU-Konvention
    # Bestimmt ZK-Skala, Aggregation, Einzelfall-Support, Labels/Farben.
    # Wird beim ersten Import gesetzt. Projekt darf nur EIN System haben.
    erstellt_am    = Column(DateTime, server_default=func.now())
    geaendert_am   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    netze              = relationship("Netz", back_populates="projekt", cascade="all, delete-orphan")
    sanierungsprojekte = relationship("Sanierungsprojekt", back_populates="projekt", cascade="all, delete-orphan")
    oertlichkeit_fotos = relationship("OertlichkeitsFoto", back_populates="projekt", cascade="all, delete-orphan")


class Netz(Base):
    __tablename__ = "netz"
    __table_args__ = (
        UniqueConstraint("projekt_id", "sparte_id", name="uq_netz_projekt_sparte"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    projekt_id = Column(Integer, ForeignKey("projekt.id", ondelete="CASCADE"), nullable=False, index=True)
    sparte_id  = Column(Integer, ForeignKey("sparte.id"), nullable=False, index=True)
    name           = Column(String(255), nullable=True)
    kbs            = Column(String(50), nullable=False, default="EPSG:25832")
    import_quelle  = Column(String(100), nullable=True)   # "DWA-M150", "ISYBAU-XML", …

    projekt   = relationship("Projekt", back_populates="netze")
    sparte    = relationship("Sparte", back_populates="netze")
    schaechte = relationship("Schacht", back_populates="netz", cascade="all, delete-orphan")
    haltungen = relationship("Haltung", back_populates="netz", cascade="all, delete-orphan")


# ============================================================
# NETZ-OBJEKTE
# ============================================================

class Schacht(Base):
    __tablename__ = "schacht"

    id         = Column(Integer, primary_key=True, index=True)
    netz_id    = Column(Integer, ForeignKey("netz.id", ondelete="CASCADE"), nullable=False, index=True)
    externe_id = Column(String(255), nullable=True, index=True)  # KG001
    geometrie  = Column(Geometry('POINTZ', srid=25832), nullable=True)  # WKT/WKB POINT Z

    # Höhen
    deckelhoehe  = Column(Float, nullable=True)   # KG206
    sohle        = Column(Float, nullable=True)    # KG207
    schachttiefe = Column(Float, nullable=True)    # KG211

    # KG-Stammdaten
    alternative_bezeichnung    = Column(String(255), nullable=True)  # KG002
    strassenschluessel         = Column(String(50), nullable=True)   # KG101
    strassenname               = Column(String(255), nullable=True)  # KG102
    ortsteilschluessel         = Column(String(50), nullable=True)   # KG103
    ortsteilname               = Column(String(255), nullable=True)  # KG104
    gemeindeschluessel         = Column(String(50), nullable=True)   # KG105
    gebietsschluessel          = Column(String(50), nullable=True)   # KG106
    einzugsgebietsschluessel   = Column(String(50), nullable=True)   # KG107
    klaeranlage_nummer         = Column(String(50), nullable=True)   # KG108
    kanalart                   = Column(String(50), nullable=True)   # KG301
    kanalnutzung               = Column(String(50), nullable=True)   # KG302
    baujahr                    = Column(Integer, nullable=True)      # KG303
    materialart                = Column(String(50), nullable=True)   # KG304
    knotenart                  = Column(String(50), nullable=True)   # KG305
    bauwerksart                = Column(String(50), nullable=True)   # KG306
    schachtform                = Column(String(50), nullable=True)   # KG307
    schachtlaenge              = Column(Float, nullable=True)        # KG308
    schachtbreite              = Column(Float, nullable=True)        # KG309
    deckelform                 = Column(String(50), nullable=True)   # KG310
    deckelmaterial             = Column(String(50), nullable=True)   # KG311
    deckelklasse               = Column(String(50), nullable=True)   # KG312
    deckelbreite               = Column(Float, nullable=True)        # KG313
    deckellaenge               = Column(Float, nullable=True)        # KG314
    deckel_verschraubt         = Column(String(50), nullable=True)   # KG315
    gerinneform                = Column(String(50), nullable=True)   # KG316
    gerinnematerial            = Column(String(50), nullable=True)   # KG317
    gerinnebreite              = Column(Float, nullable=True)        # KG318
    gerinnelaenge              = Column(Float, nullable=True)        # KG319
    bermematerial              = Column(String(50), nullable=True)   # KG320
    innenschutz                = Column(String(50), nullable=True)   # KG321
    innenschutzmaterial        = Column(String(50), nullable=True)   # KG322
    steighilfe                 = Column(String(50), nullable=True)   # KG323
    anzahl_steigeisen          = Column(Integer, nullable=True)      # KG324
    steighilfenwerkstoff       = Column(String(50), nullable=True)   # KG325
    messtechnik                = Column(String(50), nullable=True)   # KG326
    funktionszustand           = Column(String(50), nullable=True)   # KG401
    eigentum                   = Column(String(50), nullable=True)   # KG402
    wasserschutzzone           = Column(String(50), nullable=True)   # KG403
    lage_verkehrsraum          = Column(String(50), nullable=True)   # KG404
    grundwasserstand           = Column(String(50), nullable=True)   # KG405
    ueberschwemmungsgebiet     = Column(String(50), nullable=True)   # KG406
    status_daten               = Column(String(50), nullable=True)   # KG407
    einstauhaeufigkeit         = Column(String(50), nullable=True)   # KG408
    bodengruppe                = Column(String(50), nullable=True)   # KG409
    dokument                   = Column(String(255), nullable=True)  # KG998
    bemerkung                  = Column(Text, nullable=True)         # KG999
    
    # Erweiterte Fachdaten (BaSYS/Kandis Style)
    anlagenummer               = Column(String(50),  nullable=True)
    bauweise                   = Column(String(50),  nullable=True)
    reinigungsintervall        = Column(String(50),  nullable=True)
    restnutzungsdauer          = Column(Integer,     nullable=True)
    schadenswert               = Column(Float,       nullable=True)

    # BaSYS/Kandis spezifisch
    zugaenglichkeit            = Column(String(100), nullable=True)
    bauform                    = Column(String(100), nullable=True)
    deckelzustand              = Column(String(100), nullable=True)

    # BIM 
    ifc_guid                   = Column(String(50), nullable=True)
    pset_json                  = Column(JSONB, nullable=True, default=dict, server_default='{}')

    # Anschlusspunkt-Kennzeichnung
    ist_anschlusspunkt         = Column(Boolean, default=False, server_default="0")  # True = Anschlusspunkt, False = Schacht

    # Sanierungsplanung: Randbedingungen
    ueberdeckung               = Column(Float, nullable=True)        # Überdeckung in m (berechnet oder manuell)

    # Metadaten
    erstellt_am  = Column(DateTime, server_default=func.now())
    geaendert_am = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    netz           = relationship("Netz", back_populates="schaechte")
    haltungen_von  = relationship("Haltung", foreign_keys="[Haltung.von_schacht_id]", back_populates="von_schacht")
    haltungen_nach = relationship("Haltung", foreign_keys="[Haltung.nach_schacht_id]", back_populates="nach_schacht")
    inspektionen   = relationship("InspektionSchacht", back_populates="schacht", cascade="all, delete-orphan")
    massnahmen     = relationship("Massnahme", back_populates="schacht")

    # --- Helper-Properties fuer Abwaertskompatibilitaet ---
    @property
    def aktive_inspektion(self):
        """Gibt die relevanteste aktive Inspektion zurück.
        Priorität: 1. Nutzer-Override (nutzer_aktiv=True), 2. hat Befunde UND vollständig
        (≥85% der Haltungslänge befahren), 3. hat Befunde, 4. jüngstes Datum, 5. meiste Befunde, 6. höchste ID.
        """
        # 1. Nutzer-Override
        user_choice = next((i for i in self.inspektionen if i.nutzer_aktiv), None)
        if user_choice:
            return user_choice
        kandidaten = [i for i in self.inspektionen if i.aktiv] or list(self.inspektionen)
        if not kandidaten:
            return None
        return max(kandidaten, key=lambda i: (
            bool(i.befunde),
            i.datum or datetime.date.min,
            len(i.befunde),
            i.id,
        ))

    @property
    def bewertung(self):
        insp = self.aktive_inspektion
        return insp.bewertung if insp else None

    @property
    def befunde(self):
        insp = self.aktive_inspektion
        return insp.befunde if insp else []

    @property
    def projekt_id(self):
        return self.netz.projekt_id if self.netz else None


class Haltung(Base):
    __tablename__ = "haltung"

    id              = Column(Integer, primary_key=True, index=True)
    netz_id         = Column(Integer, ForeignKey("netz.id", ondelete="CASCADE"), nullable=False, index=True)
    externe_id      = Column(String(255), nullable=True, index=True)  # HG001
    von_schacht_id  = Column(Integer, ForeignKey("schacht.id"), nullable=True, index=True)
    nach_schacht_id = Column(Integer, ForeignKey("schacht.id"), nullable=True, index=True)
    geometrie       = Column(Geometry('LINESTRINGZ', srid=25832), nullable=True)  # WKT/WKB LINESTRING Z

    # Kernfelder
    laenge      = Column(Float, nullable=True)        # HG310
    durchmesser = Column(Float, nullable=True)        # HG306
    material    = Column(String(100), nullable=True)   # HG304
    baujahr     = Column(Integer, nullable=True)       # HG303

    # HG-Stammdaten
    alternative_bezeichnung        = Column(String(255), nullable=True)  # HG002
    endpunkt_bezeichnung           = Column(String(255), nullable=True)  # HG005
    haltungsstatus                 = Column(String(50), nullable=True)   # HG006
    stationierung_anschluss        = Column(String(255), nullable=True)  # HG007
    profilform                     = Column(String(50), nullable=True)   # HG008
    profilgroesse                  = Column(String(50), nullable=True)   # HG009
    typ_endpunkt                   = Column(String(255), nullable=True)  # HG010
    name_bezeichnung               = Column(String(255), nullable=True)  # HG011
    kind_von                       = Column(String(255), nullable=True)  # HG012
    ist_konnektion                 = Column(Boolean, default=False, server_default="0")  # True wenn HG012 vorhanden
    strassenschluessel             = Column(String(50), nullable=True)   # HG101
    strassenname                   = Column(String(255), nullable=True)  # HG102
    ortsteilschluessel             = Column(String(50), nullable=True)   # HG103
    ort_ortsteil                   = Column(String(255), nullable=True)  # HG104
    gemeindeschluessel             = Column(String(50), nullable=True)   # HG105
    gebietsschluessel              = Column(String(50), nullable=True)   # HG106
    einzugsgebietsschluessel       = Column(String(50), nullable=True)   # HG107
    klaeranlage_nummer             = Column(String(50), nullable=True)   # HG108
    kanalart                       = Column(String(50), nullable=True)   # HG301
    kanalnutzung                   = Column(String(50), nullable=True)   # HG302
    funktion                       = Column(String(50), nullable=True)   # HG301 (alt)
    materialtyp                    = Column(String(50), nullable=True)   # HG302 (alt)
    materialart                    = Column(String(50), nullable=True)   # HG304
    profilart                      = Column(String(50), nullable=True)   # HG305
    durchmesser1                   = Column(Float, nullable=True)        # HG304
    durchmesser2                   = Column(Float, nullable=True)        # HG305
    nennweite                      = Column(Float, nullable=True)        # HG306
    profilbreite                   = Column(Float, nullable=True)        # HG306
    profilhoehe                    = Column(Float, nullable=True)        # HG307
    profilauskleidung              = Column(String(50), nullable=True)   # HG308
    profilauskleidung_material     = Column(String(50), nullable=True)   # HG309
    haltungslaenge                 = Column(Float, nullable=True)        # HG310
    haltungsgefaelle               = Column(Float, nullable=True)        # HG311
    gefaelle                       = Column(Float, nullable=True)        # HG311 (Promille)
    mittlere_tiefe                 = Column(Float, nullable=True)        # HG312
    haltungsart                    = Column(String(50), nullable=True)   # HG313
    rohrlaenge                     = Column(Float, nullable=True)        # HG314
    status_profilangaben           = Column(String(50), nullable=True)   # HG315
    profilauskleidung_selbsttragend = Column(String(50), nullable=True)  # HG316
    funktionszustand               = Column(String(50), nullable=True)   # HG401
    eigentum                       = Column(String(50), nullable=True)   # HG402
    wasserschutzzone               = Column(String(50), nullable=True)   # HG403
    lage_verkehrsraum              = Column(String(50), nullable=True)   # HG404
    grundwasserstand               = Column(String(50), nullable=True)   # HG405
    ueberschwemmungsgebiet         = Column(String(50), nullable=True)   # HG406
    status_daten                   = Column(String(50), nullable=True)   # HG407
    einstauhaeufigkeit             = Column(String(50), nullable=True)   # HG408
    bodengruppe                    = Column(String(50), nullable=True)   # HG409
    wanddicke                      = Column(Float, nullable=True)        # HG410
    lagerungsart                   = Column(String(50), nullable=True)   # HG411
    dokument                       = Column(String(255), nullable=True)  # HG998
    bemerkung                      = Column(Text, nullable=True)         # HG999
    
    # Erweiterte Fachdaten (BaSYS/Kandis Style)
    anlagenummer                   = Column(String(50),  nullable=True)
    bauweise                       = Column(String(50),  nullable=True)
    reinigungsintervall            = Column(String(50),  nullable=True)
    restnutzungsdauer              = Column(Integer,     nullable=True)
    schadenswert                   = Column(Float,       nullable=True)
    
    # BaSYS/Kandis spezifisch (für Baustellenplanung)
    zugaenglichkeit                = Column(String(100), nullable=True) # Fahrbahn, Gehweg, etc.
    deckelhoehe_zulauf             = Column(Float,       nullable=True)
    deckelhoehe_ablauf             = Column(Float,       nullable=True)
    auskleidung                    = Column(String(100), nullable=True) # z.B. GFK-Liner
    relining                       = Column(Boolean,     nullable=True)
    kb_wert                        = Column(Float,       nullable=True)
    abwasserart                    = Column(String(100), nullable=True) # häuslich, gewerblich, etc.

    # BIM
    ifc_guid                       = Column(String(50), nullable=True)
    lod_stufe                      = Column(Integer, nullable=True, default=200)
    pset_json                      = Column(JSONB, nullable=True, default=dict, server_default='{}')

    # Abgeleitete Felder (aus Befunden berechnet, nach Import / Werkzeuge-Aufruf)
    # Quellen: DIN EN 13508 → BCA+ch2=A/B; ATV/ISYBAU96 → S***/A*** (offen) | SU**/AU** (geschlossen)
    anzahl_zulaeufe_offen          = Column(Integer, nullable=True)      # offene Hausanschlüsse
    anzahl_zulaeufe_geschlossen    = Column(Integer, nullable=True)      # geschlossene/überwachsene Anschlüsse
    anzahl_zulaeufe                = Column(Integer, nullable=True)      # Summe offen + geschlossen

    # Sanierungsplanung: Randbedingungen (§3.4 Plan)
    ueberdeckung                   = Column(Float, nullable=True)        # Überdeckung in m (berechnet oder manuell)
    hydraul_auslastung             = Column(String(50), nullable=True)   # "eingehalten" / "nicht_eingehalten"
    kote_oben                      = Column(Float, nullable=True)        # Sohlhöhe am Startknoten (m ü. NHN)
    kote_unten                     = Column(Float, nullable=True)        # Sohlhöhe am Endknoten (m ü. NHN)

    # Metadaten
    erstellt_am  = Column(DateTime, server_default=func.now())
    geaendert_am = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    netz         = relationship("Netz", back_populates="haltungen")
    von_schacht  = relationship("Schacht", foreign_keys=[von_schacht_id], back_populates="haltungen_von")
    nach_schacht = relationship("Schacht", foreign_keys=[nach_schacht_id], back_populates="haltungen_nach")
    inspektionen = relationship("InspektionHaltung", back_populates="haltung", cascade="all, delete-orphan")
    massnahmen        = relationship("Massnahme", back_populates="haltung")
    gis_strassen_info = relationship("GisStrassenInfo", back_populates="haltung",
                                     uselist=False, cascade="all, delete-orphan")

    # --- Helper-Properties fuer Abwaertskompatibilitaet ---
    @property
    def aktive_inspektion(self):
        """Gibt die relevanteste aktive Inspektion zurück.
        Priorität: 1. Nutzer-Override, 2. hat Befunde, 3. jüngstes Datum, 4. meiste Befunde, 5. höchste ID.
        """
        user_choice = next((i for i in self.inspektionen if i.nutzer_aktiv), None)
        if user_choice:
            return user_choice
        kandidaten = [i for i in self.inspektionen if i.aktiv] or list(self.inspektionen)
        if not kandidaten:
            return None
        return max(kandidaten, key=lambda i: (
            bool(i.befunde),
            i.datum or datetime.date.min,
            len(i.befunde),
            i.id,
        ))

    @property
    def bewertung(self):
        insp = self.aktive_inspektion
        return insp.bewertung if insp else None

    @property
    def befunde(self):
        insp = self.aktive_inspektion
        return insp.befunde if insp else []

    @hybrid_property
    def laenge(self):
        return self.haltungslaenge

    @laenge.setter
    def laenge(self, value):
        self.haltungslaenge = value

    @property
    def projekt_id(self):
        return self.netz.projekt_id if self.netz else None


# ============================================================
# INSPEKTIONEN (mehrfach je Objekt)
# ============================================================

class InspektionHaltung(Base):
    __tablename__ = "inspektion_haltung"
    __table_args__ = (
        UniqueConstraint("haltung_id", "inspektionsnr", name="uq_insp_haltung_nr"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    haltung_id      = Column(Integer, ForeignKey("haltung.id", ondelete="CASCADE"), nullable=False, index=True)
    inspektionsnr   = Column(Integer, nullable=False, default=1)
    datum           = Column(Date, nullable=True)           # HI104
    anlass          = Column(String(100), nullable=True)    # HI004: Inspektionsgrund (N=Erstinspektion, J=SüvKan, K=Abnahme, W=Wiederholung)
    firma           = Column(String(255), nullable=True)    # HI111 Auftragnehmer
    inspekteur      = Column(String(255), nullable=True)    # HI112 Inspekteur/Person
    verfahren       = Column(String(100), nullable=True)    # HI103: KTV, BG, ...
    richtung        = Column(String(10),  nullable=True)    # HI101: I=in Fließrichtung, G=gegen
    wetter          = Column(String(100), nullable=True)    # HI106
    import_datei    = Column(String(500), nullable=True)    # Quell-XML-Dateiname
    import_datum    = Column(DateTime, server_default=func.now())
    aktiv           = Column(Boolean, default=True)
    nutzer_aktiv    = Column(Boolean, default=False, nullable=False, server_default="0")
    bemerkung           = Column(Text, nullable=True)           # HI115
    dokument_inspektion = Column(String(255), nullable=True)    # HI998
    kodiersystem        = Column(String(100), nullable=True)    # HI005 (z.B. DIN-13508-2011-DWA)
    pset_json           = Column(JSONB, nullable=True, default=dict, server_default='{}')

    haltung   = relationship("Haltung", back_populates="inspektionen")
    befunde   = relationship("BefundHaltung", back_populates="inspektion", cascade="all, delete-orphan")
    bewertung = relationship("BewertungHaltung", uselist=False, back_populates="inspektion", cascade="all, delete-orphan")
    videos    = relationship("InspektionVideo", back_populates="inspektion_haltung", cascade="all, delete-orphan")


class InspektionSchacht(Base):
    __tablename__ = "inspektion_schacht"
    __table_args__ = (
        UniqueConstraint("schacht_id", "inspektionsnr", name="uq_insp_schacht_nr"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    schacht_id      = Column(Integer, ForeignKey("schacht.id", ondelete="CASCADE"), nullable=False, index=True)
    inspektionsnr   = Column(Integer, nullable=False, default=1)
    datum           = Column(Date, nullable=True)           # KI104
    anlass          = Column(String(100), nullable=True)    # KI004: Inspektionsgrund
    firma           = Column(String(255), nullable=True)    # KI111
    inspekteur      = Column(String(255), nullable=True)    # KI112
    verfahren       = Column(String(100), nullable=True)    # KI102/KI103
    import_datei    = Column(String(500), nullable=True)
    import_datum    = Column(DateTime, server_default=func.now())
    aktiv           = Column(Boolean, default=True)
    nutzer_aktiv    = Column(Boolean, default=False, nullable=False, server_default="0")
    bemerkung           = Column(Text, nullable=True)           # KI999
    dokument_inspektion = Column(String(255), nullable=True)    # KI998
    kodiersystem        = Column(String(100), nullable=True)    # KI005
    pset_json           = Column(JSONB, nullable=True, default=dict, server_default='{}')

    schacht   = relationship("Schacht", back_populates="inspektionen")
    befunde   = relationship("BefundSchacht", back_populates="inspektion", cascade="all, delete-orphan")
    bewertung = relationship("BewertungSchacht", uselist=False, back_populates="inspektion", cascade="all, delete-orphan")
    videos    = relationship("InspektionVideo", back_populates="inspektion_schacht", cascade="all, delete-orphan")


class InspektionVideo(Base):
    __tablename__ = "inspektion_video"
    __table_args__ = (
        CheckConstraint(
            "inspektion_h_id IS NOT NULL OR inspektion_s_id IS NOT NULL",
            name="ck_video_inspektion"
        ),
    )

    id              = Column(Integer, primary_key=True, index=True)
    inspektion_h_id = Column(Integer, ForeignKey("inspektion_haltung.id", ondelete="CASCADE"), nullable=True, index=True)
    inspektion_s_id = Column(Integer, ForeignKey("inspektion_schacht.id", ondelete="CASCADE"), nullable=True, index=True)
    video_pfad      = Column(Text, nullable=False)
    video_format    = Column(String(20), nullable=True)   # 'MP4', 'AVI', 'WMV', 'MPG', 'IPF'
    dauer_sekunden  = Column(Float, nullable=True)
    startzeit       = Column(Float, default=0)
    richtung        = Column(String(100), nullable=True)
    bemerkung       = Column(Text, nullable=True)

    inspektion_haltung = relationship("InspektionHaltung", back_populates="videos")
    inspektion_schacht = relationship("InspektionSchacht", back_populates="videos")


# ============================================================
# BEFUNDE (= Einzelschäden, pro Inspektion)
# ============================================================

class BefundHaltung(Base):
    __tablename__ = "befund_haltung"

    id            = Column(Integer, primary_key=True, index=True)
    inspektion_id = Column(Integer, ForeignKey("inspektion_haltung.id", ondelete="CASCADE"), nullable=False, index=True)
    code          = Column(String(100), nullable=False)  # HZ002 (BAA, BAB, …)
    ch1           = Column(String(255), nullable=True)   # HZ014 Charakterisierung 1
    ch2           = Column(String(255), nullable=True)   # HZ015 Charakterisierung 2
    quanti1       = Column(String(255), nullable=True)   # HZ003 Quantifizierung 1
    quanti2       = Column(String(255), nullable=True)   # HZ004 Quantifizierung 2
    position      = Column(Float, nullable=True)         # HZ001 Stationierung
    position_bis  = Column(Float, nullable=True)         # reserviert (nicht DWA/ISYBAU genutzt)
    streckenschaden = Column(Boolean, default=False)
    # Streckenschaden-Felder (U126): typ normalisiert A=Anfang, E=Ende, C=Änderung, G=Gesamt, R=Baulänge
    streckenschaden_typ   = Column(String(5),  nullable=True)  # HZ005-Präfix→normalisiert / ISYBAU <Streckenschaden>
    streckenschaden_lfdnr = Column(Integer,    nullable=True)  # HZ005-Zahl / ISYBAU <StreckenschadenLfdNr>
    videozaehler  = Column(String(255), nullable=True)   # HZ007
    bildname      = Column(String(255), nullable=True)   # HZ008
    beschreibung  = Column(Text, nullable=True)          # Langtext
    bemerkung     = Column(Text, nullable=True)

    # Segment-Info (für Export: Zuordnung zum Original-HG-Block)
    endpunkt_bezeichnung = Column(String(80), nullable=True)   # HG005 des HG-Blocks
    inspektionsrichtung  = Column(String(5), nullable=True)    # HI101: G=Gegenstrom, I=Fließrichtung

    # Herkunft des Schadenscodes – wichtig für Format-übergreifende Auswertung
    # Mögliche Werte: "DWA-M150" | "DIN13508-2" | "ISYBAU" | "ATV" | "BaSYS" | "manuell"
    code_system   = Column(String(50), nullable=True, server_default="DWA-M150")

    # ISYBAU: Uhrzeitposition am Rohrumfang (PositionVon/PositionBis, Integer 0-12)
    # EN 13508-2: 12=Sohle, 06=Scheitel, 03=rechts, 09=links
    position_von_uhr = Column(Integer, nullable=True)   # ISYBAU: <RZustand><PositionVon>
    position_bis_uhr = Column(Integer, nullable=True)   # ISYBAU: <RZustand><PositionBis>
    # ISYBAU: Lage an Bauteilverbindung (Stutzen): <RZustand><Verbindung>
    an_verbindung    = Column(Boolean, nullable=True)    # 0→False, >0→True

    # Bewertungsergebnis (pro Befund)
    # ZK-Werte werden NATIV gespeichert – keine Umrechnung beim Speichern.
    # DWA-Import:    0=schlimmster, 5=schadensfrei  (zk_konvention in BewertungHaltung = "DWA")
    # ISYBAU-Import: 5=schlimmster, 0=schadensfrei  (zk_konvention in BewertungHaltung = "ISYBAU")
    # Für korrekte Anzeige immer get_zk_system(projekt.bewertungs_system) verwenden.
    zk_S          = Column(Integer, nullable=True)       # ZK Standsicherheit (nativ je System)
    zk_D          = Column(Integer, nullable=True)       # ZK Dichtheit (nativ je System)
    zk_B          = Column(Integer, nullable=True)       # ZK Betriebssicherheit (nativ je System)
    regelwerk_ver = Column(String(50), nullable=True)    # z.B. "2024-05"

    erstellt_am   = Column(DateTime, server_default=func.now())
    pset_json     = Column(JSONB, nullable=True, default=dict, server_default='{}')

    inspektion         = relationship("InspektionHaltung", back_populates="befunde")
    massnahme_befunde  = relationship("MassnahmeBefund", back_populates="befund_haltung")
    fotos              = relationship("SchadensFoto", back_populates="befund_haltung", cascade="all, delete-orphan")


class BefundSchacht(Base):
    __tablename__ = "befund_schacht"

    id            = Column(Integer, primary_key=True, index=True)
    inspektion_id = Column(Integer, ForeignKey("inspektion_schacht.id", ondelete="CASCADE"), nullable=False, index=True)
    code          = Column(String(100), nullable=False)  # KZ002 (DAA, DAB, …)
    ch1           = Column(String(255), nullable=True)
    ch2           = Column(String(255), nullable=True)
    quanti1       = Column(String(255), nullable=True)
    quanti2       = Column(String(255), nullable=True)
    position      = Column(String(255), nullable=True)   # KZ001 Station / Bereich
    bereich       = Column(String(50),  nullable=True)   # KZ013 Schachtbereich (A=Einstieg, B=Konus, …J=Gerinne)
    beschreibung  = Column(Text, nullable=True)
    bemerkung     = Column(Text, nullable=True)
    videozaehler  = Column(String(255), nullable=True)   # KZ008
    bildname      = Column(String(255), nullable=True)   # KZ009

    # Herkunft des Schadenscodes (analog BefundHaltung)
    code_system   = Column(String(50), nullable=True, server_default="DWA-M150")

    # ISYBAU: Lage an Bauteilverbindung (Stutzen): <KZustand><Verbindung>
    an_verbindung    = Column(Boolean, nullable=True)    # 0→False, >0→True

    # Streckenschaden-Felder (U126): analog BefundHaltung
    streckenschaden_typ   = Column(String(5),  nullable=True)  # ISYBAU <Streckenschaden> normalisiert
    streckenschaden_lfdnr = Column(Integer,    nullable=True)  # ISYBAU <StreckenschadenLfdNr>

    # Bewertungsergebnis (ZK nativ je System: DWA 0=schlimmster; ISYBAU 5=schlimmster)
    zk_S          = Column(Integer, nullable=True)
    zk_D          = Column(Integer, nullable=True)
    zk_B          = Column(Integer, nullable=True)
    regelwerk_ver = Column(String(50), nullable=True)

    erstellt_am   = Column(DateTime, server_default=func.now())
    pset_json     = Column(JSONB, nullable=True, default=dict, server_default='{}')

    inspektion         = relationship("InspektionSchacht", back_populates="befunde")
    massnahme_befunde  = relationship("MassnahmeBefund", back_populates="befund_schacht")
    fotos              = relationship("SchadensFoto", back_populates="befund_schacht", cascade="all, delete-orphan")


# ============================================================
# FOTOS (mehrere Fotos pro Befund)
# ============================================================

class SchadensFoto(Base):
    __tablename__ = "schadens_foto"
    __table_args__ = (
        CheckConstraint(
            "befund_h_id IS NOT NULL OR befund_s_id IS NOT NULL",
            name="ck_schadensfoto_befund"
        ),
    )

    id           = Column(Integer, primary_key=True, index=True)
    befund_h_id  = Column(Integer, ForeignKey("befund_haltung.id", ondelete="CASCADE"), nullable=True, index=True)
    befund_s_id  = Column(Integer, ForeignKey("befund_schacht.id", ondelete="CASCADE"), nullable=True, index=True)
    dateipfad    = Column(Text, nullable=False)           # Vollständiger Pfad (Basispfad + Dateiname)
    dateiname    = Column(String(255), nullable=True)     # Nur Dateiname (für Anzeige + Export)
    sortierung   = Column(Integer, nullable=False, default=0, server_default="0")
    beschreibung = Column(Text, nullable=True)            # Optionale Bildunterschrift
    typ          = Column(String(50), nullable=True, server_default="foto")  # "foto" | "skizze"
    erstellt_am  = Column(DateTime, server_default=func.now())

    befund_haltung = relationship("BefundHaltung", back_populates="fotos")
    befund_schacht = relationship("BefundSchacht", back_populates="fotos")


# ============================================================
# BEWERTUNG (aggregiert pro Inspektion)
# ============================================================

class BewertungHaltung(Base):
    __tablename__ = "bewertung_haltung"

    id            = Column(Integer, primary_key=True, index=True)
    inspektion_id = Column(Integer, ForeignKey("inspektion_haltung.id"), nullable=False, unique=True)
    zk_gesamt     = Column(Integer, nullable=True)   # Gesamt-ZK in DWA-Konvention (0=schlimmster)
    zk_S          = Column(Integer, nullable=True)
    zk_D          = Column(Integer, nullable=True)
    zk_B          = Column(Integer, nullable=True)
    regelwerk_ver = Column(String(20), nullable=True)   # z.B. "2024-05"

    # Bewertungsmethode: vollständiger Bezeichner inkl. Format und Version
    # Beispiele: "DWA-M149-3:2024-05" | "ISYBAU:2017" | "ATV" | "import" (aus Datei übernommen)
    bewertungs_methode = Column(String(100), nullable=True, server_default="DWA-M149-3:2024-05")

    # ZK-Konvention: legt fest, wie zk_gesamt/zk_S/D/B zu interpretieren sind.
    # "DWA"   → 0=schlimmster, 5=schadensfrei (Standard-Speicherformat in dieser DB)
    # "ISYBAU"→ 5=schlimmster, 0=schadensfrei (nur wenn Werte unverändert aus ISYBAU übernommen)
    # Regel: Bei DWA-Import und bei manueller Bewertung immer "DWA".
    #        Bei direktem ISYBAU-Objektklassen-Import ohne Umrechnung: "ISYBAU".
    zk_konvention = Column(String(10), nullable=True, server_default="DWA")

    prioritaet    = Column(Integer, nullable=True)
    bemerkung     = Column(Text, nullable=True)
    berechnet_am  = Column(DateTime, server_default=func.now())

    # Schadensdichte DWA-M 149-3
    sd_S          = Column(Float, nullable=True)   # Schadensdichte Standsicherheit
    sd_D          = Column(Float, nullable=True)   # Schadensdichte Dichtheit
    sd_B          = Column(Float, nullable=True)   # Schadensdichte Betriebssicherheit
    zp_S          = Column(Float, nullable=True)   # Zustandspunkte S
    zp_D          = Column(Float, nullable=True)   # Zustandspunkte D
    zp_B          = Column(Float, nullable=True)   # Zustandspunkte B
    sz            = Column(Float, nullable=True)   # Sanierungsbedarfszahl (max BPj)

    # Schadensdichte BFR/ISYBAU
    slz           = Column(Float, nullable=True)   # Schadenslängenzahl
    oze           = Column(Float, nullable=True)   # Endgültige Objektzahl
    ok_bfr        = Column(Integer, nullable=True) # BFR Objektklasse (0–5)

    # Einzelfallbetrachtung: True wenn ≥1 Befund ZK=6 (Einzelfall erforderlich)
    # server_default="0" nötig damit ALTER TABLE ADD COLUMN in SQLite klappt (NOT NULL braucht DEFAULT)
    hat_einzelfaelle = Column(Boolean, nullable=False, server_default="0", default=False)

    # Sanierungsstrategie (persistent, berechnet beim Bewertungslauf)
    strategie   = Column(String(50), nullable=True)  # Erneuerung | Renovierung | Reparatur | keine
    begruendung = Column(Text,       nullable=True)  # Fachliche Begründung

    inspektion = relationship("InspektionHaltung", back_populates="bewertung")


class BewertungSchacht(Base):
    __tablename__ = "bewertung_schacht"

    id            = Column(Integer, primary_key=True, index=True)
    inspektion_id = Column(Integer, ForeignKey("inspektion_schacht.id"), nullable=False, unique=True)
    zk_gesamt     = Column(Integer, nullable=True)
    zk_S          = Column(Integer, nullable=True)
    zk_D          = Column(Integer, nullable=True)
    zk_B          = Column(Integer, nullable=True)
    regelwerk_ver = Column(String(20), nullable=True)   # z.B. "2024-05"

    # Bewertungsmethode und ZK-Konvention (analog BewertungHaltung, s.d.)
    bewertungs_methode = Column(String(100), nullable=True, server_default="DWA-M149-3:2024-05")
    zk_konvention      = Column(String(10), nullable=True, server_default="DWA")

    prioritaet    = Column(Integer, nullable=True)
    bemerkung     = Column(Text, nullable=True)
    berechnet_am  = Column(DateTime, server_default=func.now())

    # Schadensdichte und Zustandspunkte (analog Haltung)
    sd_S          = Column(Float, nullable=True)
    sd_D          = Column(Float, nullable=True)
    sd_B          = Column(Float, nullable=True)
    zp_S          = Column(Float, nullable=True)   # KI210 Zustandspunkte Standsicherheit
    zp_D          = Column(Float, nullable=True)   # KI209 Zustandspunkte Dichtheit
    zp_B          = Column(Float, nullable=True)   # KI211 Zustandspunkte Betriebssicherheit
    sz            = Column(Float, nullable=True)
    slz           = Column(Float, nullable=True)
    oze           = Column(Float, nullable=True)
    ok_bfr        = Column(Integer, nullable=True)

    # Einzelfallbetrachtung: True wenn ≥1 Befund ZK=6
    # server_default="0" nötig damit ALTER TABLE ADD COLUMN in SQLite klappt (NOT NULL braucht DEFAULT)
    hat_einzelfaelle = Column(Boolean, nullable=False, server_default="0", default=False)

    # Sanierungsstrategie (persistent, berechnet beim Bewertungslauf)
    strategie   = Column(String(50), nullable=True)  # Erneuerung | Renovierung | Reparatur | keine
    begruendung = Column(Text,       nullable=True)  # Fachliche Begründung

    inspektion = relationship("InspektionSchacht", back_populates="bewertung")


# ============================================================
# SANIERUNG
# ============================================================

class Sanierungsprojekt(Base):
    __tablename__ = "sanierungsprojekt"
    __table_args__ = (
        UniqueConstraint("projekt_id", "version", name="uq_san_projekt_version"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    projekt_id   = Column(Integer, ForeignKey("projekt.id", ondelete="CASCADE"), nullable=False, index=True)
    version      = Column(Integer, nullable=False, default=1)
    name         = Column(String(255), nullable=True)    # "Erstplanung", "Rev. nach AG"
    status       = Column(String(50), default="Entwurf") # Entwurf/Geprüft/Freigegeben/Ausgeschrieben
    erstellt_am  = Column(DateTime, server_default=func.now())
    erstellt_von = Column(String(255), nullable=True)
    bemerkung    = Column(Text, nullable=True)

    projekt      = relationship("Projekt", back_populates="sanierungsprojekte")
    massnahmen   = relationship("Massnahme", back_populates="san_projekt", cascade="all, delete-orphan")
    lv_positionen = relationship("LVPosition", back_populates="san_projekt", cascade="all, delete-orphan")
    sanierungsabschnitte = relationship("SanierungsAbschnitt", back_populates="san_projekt", cascade="all, delete-orphan")


# ============================================================
# VORPLANUNG — Sanierungsabschnitt (SA) mit Straßenraum & Bypass
# ============================================================

class SanierungsAbschnitt(Base):
    """
    Ein Sanierungsabschnitt (SA) gruppiert zusammenhängende Haltungen/Lose
    für die Vorplanung. Enthält Straßenraum-Daten (Modul A) und
    Bypass/Überleitung-Daten (Modul B) für den Vorplanungsbericht.
    """
    __tablename__ = "sanierungsabschnitt"
    __table_args__ = (
        UniqueConstraint("san_projekt_id", "bezeichnung", name="uq_sa_projekt_bez"),
    )

    id             = Column(Integer, primary_key=True, index=True)
    san_projekt_id = Column(Integer, ForeignKey("sanierungsprojekt.id", ondelete="CASCADE"), nullable=False, index=True)
    bezeichnung    = Column(String(100), nullable=False)   # z.B. "SA-01", "Los 1"
    los            = Column(String(100), nullable=True)    # Los-Name aus Massnahme.los (Verknüpfung über Text)
    beschreibung   = Column(Text, nullable=True)
    von_schacht_id = Column(Integer, ForeignKey("schacht.id"), nullable=True)  # topologischer Anfang
    bis_schacht_id = Column(Integer, ForeignKey("schacht.id"), nullable=True)  # topologisches Ende
    sort_order     = Column(Integer, default=0)

    # --- Modul A: Straßenraum / Verkehr ---
    strasse_name        = Column(String(255), nullable=True)   # Straßenname
    strasse_typ         = Column(String(50),  nullable=True)   # Anlieger / Gemeindestraße / Kreisstraße / Bundesstraße / Autobahn
    strasse_breite_m    = Column(Float,       nullable=True)   # Fahrbahnbreite in m
    gehweg_vorhanden    = Column(Boolean,     nullable=True)
    strassenbelag       = Column(String(50),  nullable=True)   # Asphalt / Pflaster / Beton / Schotter / sonstig
    tempolimit_kmh      = Column(Integer,     nullable=True)   # Tempolimit (km/h), 0 = unbekannt
    beleuchtung         = Column(Boolean,     nullable=True)   # Straßenbeleuchtung vorhanden
    busverkehr          = Column(Boolean,     nullable=True, default=False)
    busverkehr_linie    = Column(String(255), nullable=True)   # z.B. "Linie 261, 262"
    busverkehr_takt_min = Column(Integer,     nullable=True)   # Takt in Minuten
    tramverkehr         = Column(Boolean,     nullable=True, default=False)  # Straßenbahn in der Nähe
    baustellenklasse    = Column(String(5),   nullable=True)   # A / B / B+ / C / C+ (schlimmste der SA-Haltungen)
    vs_kosten_typisch   = Column(Float,       nullable=True)   # Typische Verkehrssicherungskosten (€, aus OSM)
    baustellen_hinweis  = Column(Text,        nullable=True)   # bestehende / geplante Baustellen
    verkehr_besonderheiten = Column(Text,     nullable=True)   # Schulzone, Feuerwehr-Zufahrt, etc.
    verkehr_umleitungsweg  = Column(Text,     nullable=True)   # beschreibung Umleitungsweg
    halteverbot_laenge_m   = Column(Float,    nullable=True)   # benötigte Halteverbot-Länge
    rsa21_plan_id          = Column(String(50), nullable=True)   # gewählter Regelplan (z.B. "B I/6")
    vs_kosten_formel       = Column(Text,       nullable=True)   # Herleitung der Kosten (z.B. "RSA 21 B I/6: ...")

    # --- Modul B: Abwasserüberleitung / Bypass ---
    bypass_erforderlich    = Column(Boolean,     nullable=True, default=False)
    bypass_art             = Column(String(100), nullable=True)  # "Pumpenhose", "offene Überleitung", "Druckleitung", etc.
    bypass_laenge_m        = Column(Float,       nullable=True)
    bypass_schacht_von_id  = Column(Integer, ForeignKey("schacht.id"), nullable=True)  # Einspeiseschacht
    bypass_schacht_bis_id  = Column(Integer, ForeignKey("schacht.id"), nullable=True)  # Ausleitschacht
    bypass_pumpe_leistung  = Column(String(100), nullable=True)  # z.B. "2 × 10 l/s"
    bypass_zulaeufe        = Column(Text,        nullable=True)   # aktive Zuläufe (aus BCA-Befunden, JSON-Liste)
    bypass_bemerkung       = Column(Text,        nullable=True)

    # --- Modul B: Abwasserlenkung (Erweiterung) ---
    al_ew_anzahl            = Column(Integer, nullable=True)   # Einwohnerwerte (EW)
    al_qt_l_s               = Column(Float,   nullable=True)   # Trockenwetterabfluss (l/s)
    al_qt_max_l_s           = Column(Float,   nullable=True)   # Spitzenabfluss (l/s)
    al_rueckhaltung_vol_m3  = Column(Float,   nullable=True)   # Berechnetes Rückstauvolumen
    al_pumpe_anzahl         = Column(Integer, nullable=True)
    al_blasen_anzahl        = Column(Integer, nullable=True)
    al_dauer_tage           = Column(Integer, nullable=True, default=1)  # Dauer der Lenkung in Tagen
    bypass_pfad_ids         = Column(Text,    nullable=True)   # JSON-Liste der Schacht-IDs für die Überleitung
    al_kosten_einrichtung   = Column(Float,   nullable=True)   # Einmalkosten (€)
    al_kosten_vorhaltung_tag = Column(Float,  nullable=True)   # Vorhaltung (€/Tag)

    # --- Allgemein / Bericht ---
    vorort_datum        = Column(Date,  nullable=True)   # Datum der Ortsbegehung
    bearbeiter          = Column(String(255), nullable=True)
    bericht_bemerkung   = Column(Text,  nullable=True)   # freier Text für Bericht-Kapitel

    # --- Modul C: Einbaulängen-Limit (Schlauchliner-Logistik) ---
    liner_typ        = Column(String(20), nullable=True)   # "GFK" / "SF" / "Sonstige"
    max_laenge_m     = Column(Float,      nullable=True)   # aus YAML-Limits (überschreibbar)
    gewicht_kg       = Column(Float,      nullable=True)   # berechnetes Liner-Gewicht
    einzel_einbau    = Column(Boolean,    nullable=True, default=False)  # True = jede Haltung einzeln

    san_projekt  = relationship("Sanierungsprojekt", back_populates="sanierungsabschnitte")
    von_schacht  = relationship("Schacht", foreign_keys=[von_schacht_id])
    bis_schacht  = relationship("Schacht", foreign_keys=[bis_schacht_id])
    bypass_schacht_von = relationship("Schacht", foreign_keys=[bypass_schacht_von_id])
    bypass_schacht_bis = relationship("Schacht", foreign_keys=[bypass_schacht_bis_id])
    fotos        = relationship("OertlichkeitsFoto", back_populates="san_abschnitt", cascade="all, delete-orphan")
    haltung_links = relationship("SanierungsAbschnittHaltung", back_populates="san_abschnitt",
                                 cascade="all, delete-orphan", order_by="SanierungsAbschnittHaltung.reihenfolge")


class OertlichkeitsFoto(Base):
    """
    Foto aus der örtlichen Begehung (Ortsbegehung).
    GPS-Koordinaten aus EXIF → automatisches Schacht-Matching (30m-Radius).
    """
    __tablename__ = "oertlichkeit_foto"

    id                 = Column(Integer, primary_key=True, index=True)
    projekt_id         = Column(Integer, ForeignKey("projekt.id", ondelete="CASCADE"), nullable=False, index=True)
    san_abschnitt_id   = Column(Integer, ForeignKey("sanierungsabschnitt.id", ondelete="SET NULL"), nullable=True, index=True)
    schacht_id         = Column(Integer, ForeignKey("schacht.id", ondelete="SET NULL"), nullable=True, index=True)

    dateipfad          = Column(Text,    nullable=False)   # absoluter Pfad (oder relativ zu Projekt-Ordner)
    dateiname_original = Column(String(255), nullable=True)
    aufnahme_zeitpunkt = Column(DateTime, nullable=True)   # aus EXIF DateTimeOriginal
    gps_lat            = Column(Float,   nullable=True)    # WGS84 Breitengrad
    gps_lon            = Column(Float,   nullable=True)    # WGS84 Längengrad
    gps_easting        = Column(Float,   nullable=True)    # EPSG:25832 Easting (nach Transformation)
    gps_northing       = Column(Float,   nullable=True)    # EPSG:25832 Northing (nach Transformation)
    match_distanz_m    = Column(Float,   nullable=True)    # Abstand zum auto-gematchten Schacht
    match_modus        = Column(String(20), nullable=True, default="keiner")  # "auto", "manuell", "keiner"
    beschriftung       = Column(Text,    nullable=True)    # Freitext für Bildunterschrift im Bericht
    kategorie          = Column(String(50), nullable=True, default="Schacht")  # Schacht / Strasse / Umfeld / Sonstiges
    sort_order         = Column(Integer, default=0)

    projekt      = relationship("Projekt")
    san_abschnitt = relationship("SanierungsAbschnitt", back_populates="fotos")
    schacht      = relationship("Schacht")


# ============================================================
# SA-Haltungs-Zuordnung (N:M mit Einbaureihenfolge)
# ============================================================

class SanierungsAbschnittHaltung(Base):
    """
    Explizite Zuordnung einer Haltung zu einem Sanierungsabschnitt.
    Enthält die Einbaureihenfolge (Schlauchliner-Zugrichtung).
    """
    __tablename__ = "san_abschnitt_haltung"
    __table_args__ = (
        UniqueConstraint("san_abschnitt_id", "haltung_id", name="uq_sa_haltung"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    san_abschnitt_id = Column(Integer, ForeignKey("sanierungsabschnitt.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    haltung_id       = Column(Integer, ForeignKey("haltung.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    reihenfolge      = Column(Integer, default=0)   # Einbaureihenfolge innerhalb des SA

    san_abschnitt = relationship("SanierungsAbschnitt", back_populates="haltung_links")
    haltung       = relationship("Haltung")


class MassnahmenKatalog(Base):
    __tablename__ = "massnahmen_katalog"

    id                 = Column(Integer, primary_key=True, index=True)
    kategorie          = Column(String(50), nullable=False)   # 'Reparatur', 'Renovierung', 'Erneuerung'
    verfahren          = Column(String(255), nullable=False)   # 'Kurzliner', 'Schlauchliner', …
    verfahren_detail   = Column(Text, nullable=True)           # 'GFK-Schlauchliner DN 200-400'
    beschreibung       = Column(Text, nullable=True)
    anwendungsbereich  = Column(String(255), nullable=True)    # 'DN 150-600'
    dn_min             = Column(Integer, nullable=True)
    dn_max             = Column(Integer, nullable=True)
    einheit            = Column(String(20), nullable=False, default="m")  # 'm', 'Stk', 'psch'
    ep_netto           = Column(Float, nullable=True)          # Einheitspreis netto (Richtwert)
    ep_quelle          = Column(String(255), nullable=True)    # Preisquelle / Stand
    verfahren_id       = Column(String(50), nullable=True)     # Link zum YAML-Katalog (z.B. "REP_INJ_HARZ")
    gaeb_oz            = Column(String(50), nullable=True)     # GAEB Ordnungszahl
    gaeb_kurztext      = Column(String(255), nullable=True)
    gaeb_langtext      = Column(Text, nullable=True)
    katalog_name       = Column(String(255), nullable=True)    # Name der GAEB-Bibliothek (z.B. "TLK Dortmund 2026")
    aktiv              = Column(Boolean, default=True)
    sortierung         = Column(Integer, default=0)

    massnahmen    = relationship("Massnahme", back_populates="katalog")
    lv_positionen = relationship("LVPosition", back_populates="katalog")


class Massnahme(Base):
    __tablename__ = "massnahme"
    __table_args__ = (
        CheckConstraint(
            "haltung_id IS NOT NULL OR schacht_id IS NOT NULL",
            name="ck_massnahme_objekt"
        ),
    )

    id               = Column(Integer, primary_key=True, index=True)
    san_projekt_id   = Column(Integer, ForeignKey("sanierungsprojekt.id", ondelete="CASCADE"), nullable=False, index=True)
    haltung_id       = Column(Integer, ForeignKey("haltung.id"), nullable=True, index=True)
    schacht_id       = Column(Integer, ForeignKey("schacht.id"), nullable=True, index=True)
    katalog_id       = Column(Integer, ForeignKey("massnahmen_katalog.id"), nullable=True, index=True)
    verfahren_id     = Column(String(50), nullable=True)     # YAML-Katalog-ID (z.B. "REP_INJ_HARZ")
    kategorie        = Column(String(50), nullable=False)    # 'Reparatur', 'Renovierung', 'Erneuerung'
    verfahren        = Column(String(255), nullable=False)
    verfahren_detail = Column(Text, nullable=True)
    eignung_score    = Column(String(10), nullable=True)     # xxx/xx/x/o/oo
    laenge           = Column(Float, nullable=True)           # Haltungslänge (bei Renovierung/Erneuerung)
    menge            = Column(Float, nullable=True)           # Menge in Einheit (m, St, h)
    schadens_laenge  = Column(Float, nullable=True)           # Länge des Schadens in m (bei Reparatur)
    kosten_einheit   = Column(Float, nullable=True)
    kosten_gesamt    = Column(Float, nullable=True)
    einheit          = Column(String(20), nullable=True)     # m, St, h, psch
    prioritaet       = Column(Integer, nullable=True)
    geplantes_jahr   = Column(Integer, nullable=True)           # geplantes Ausführungsjahr
    los              = Column(String(100), nullable=True)        # Sanierungsabschnitt / Los (z.B. "Los 1", "Abschnitt Nord")
    status           = Column(String(50), default="Vorschlag")  # Vorschlag / Geprüft / Freigegeben / zurückgestellt / kein HB
    quelle           = Column(String(50), default="automatisch")
    begruendung      = Column(Text, nullable=True)
    bemerkung        = Column(Text, nullable=True)

    san_projekt      = relationship("Sanierungsprojekt", back_populates="massnahmen")
    haltung          = relationship("Haltung", back_populates="massnahmen")
    schacht          = relationship("Schacht", back_populates="massnahmen")
    katalog          = relationship("MassnahmenKatalog", back_populates="massnahmen")
    befund_links     = relationship("MassnahmeBefund", back_populates="massnahme", cascade="all, delete-orphan")


class MassnahmeBefund(Base):
    __tablename__ = "massnahme_befund"
    __table_args__ = (
        CheckConstraint(
            "befund_h_id IS NOT NULL OR befund_s_id IS NOT NULL",
            name="ck_massnahme_befund_ref"
        ),
    )

    id           = Column(Integer, primary_key=True, index=True)
    massnahme_id = Column(Integer, ForeignKey("massnahme.id", ondelete="CASCADE"), nullable=False, index=True)
    befund_h_id  = Column(Integer, ForeignKey("befund_haltung.id"), nullable=True, index=True)
    befund_s_id  = Column(Integer, ForeignKey("befund_schacht.id"), nullable=True, index=True)
    bemerkung    = Column(Text, nullable=True)

    massnahme      = relationship("Massnahme", back_populates="befund_links")
    befund_haltung = relationship("BefundHaltung", back_populates="massnahme_befunde")
    befund_schacht = relationship("BefundSchacht", back_populates="massnahme_befunde")


class LVPosition(Base):
    __tablename__ = "lv_position"

    id             = Column(Integer, primary_key=True, index=True)
    san_projekt_id = Column(Integer, ForeignKey("sanierungsprojekt.id", ondelete="CASCADE"), nullable=False, index=True)
    katalog_id     = Column(Integer, ForeignKey("massnahmen_katalog.id"), nullable=True, index=True)
    ordnungszahl   = Column(String(50), nullable=False)   # GAEB-OZ
    kurztext       = Column(String(255), nullable=False)
    langtext       = Column(Text, nullable=True)
    einheit        = Column(String(20), nullable=False)
    menge          = Column(Float, nullable=False, default=0)
    ep_netto       = Column(Float, nullable=True)
    gp_netto       = Column(Float, nullable=True)         # = menge × ep_netto
    bemerkung      = Column(Text, nullable=True)

    san_projekt = relationship("Sanierungsprojekt", back_populates="lv_positionen")
    katalog     = relationship("MassnahmenKatalog", back_populates="lv_positionen")


# ============================================================
# AUDIT-LOG
# ============================================================

class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_tabelle", "tabelle", "datensatz_id"),
        Index("idx_audit_zeit", "zeitstempel"),
    )

    id           = Column(Integer, primary_key=True)
    zeitstempel  = Column(DateTime, server_default=func.now())
    benutzer     = Column(String(255), default="system")
    tabelle      = Column(String(100), nullable=False)
    datensatz_id = Column(Integer, nullable=False)
    aktion       = Column(String(10), nullable=False)  # INSERT, UPDATE, DELETE
    feld         = Column(String(255), nullable=True)
    alter_wert   = Column(Text, nullable=True)
    neuer_wert   = Column(Text, nullable=True)
    grund        = Column(Text, nullable=True)


# ============================================================
# GIS – Straßeninformation (1:1 zu Haltung, aus OSM)
# ============================================================

class GisStrassenInfo(Base):
    """
    Straßen- und Verkehrsinformationen je Haltung, abgefragt aus OpenStreetMap.
    Wird separat befüllt (Werkzeuge → "Straßendaten aus OSM laden").
    """
    __tablename__ = "gis_strassen_info"

    id         = Column(Integer, primary_key=True, index=True)
    haltung_id = Column(Integer, ForeignKey("haltung.id", ondelete="CASCADE"),
                        nullable=False, unique=True, index=True)

    # OSM-Rohdaten (Straße selbst, 80m-Radius)
    osm_way_id            = Column(String(50),  nullable=True)   # OSM Way-ID des nächstgelegenen Segments
    osm_highway_tag       = Column(String(50),  nullable=True)   # z.B. "residential", "secondary"
    osm_name              = Column(String(255), nullable=True)   # Straßenname aus OSM
    osm_maxspeed          = Column(Integer,     nullable=True)   # Tempolimit (km/h), None = unbekannt
    osm_lanes             = Column(Integer,     nullable=True)   # Fahrspuren
    osm_strassenbreite_m  = Column(Float,       nullable=True)   # Fahrbahnbreite aus width-Tag (m)
    osm_surface           = Column(String(50),  nullable=True)   # Oberfläche ("asphalt", "cobblestone", …)
    osm_lit               = Column(String(10),  nullable=True)   # "yes" / "no"
    osm_oneway            = Column(String(10),  nullable=True)   # "yes" / "no" / "-1"
    osm_einbahnstrasse    = Column(Boolean,     nullable=True)   # True wenn oneway=yes/-1
    osm_sidewalk          = Column(String(20),  nullable=True)   # "both"/"left"/"right"/"no"/"none"

    # OSM-Rohdaten (ÖPNV, 80m-Radius)
    osm_bus_stop_m        = Column(Float,       nullable=True)   # Abstand zur nächsten Bushaltestelle (m)
    osm_tram_stop_m       = Column(Float,       nullable=True)   # Abstand zur nächsten Tramhaltestelle (m)

    # OSM-Rohdaten (Umgebung, größere Radien)
    osm_krankenhaus_m     = Column(Float,       nullable=True)   # Abstand zum nächsten Krankenhaus (m), 800m-Radius
    osm_feuerwehr_m       = Column(Float,       nullable=True)   # Abstand zur nächsten Feuerwehrwache (m), 1000m-Radius
    osm_schule_m          = Column(Float,       nullable=True)   # Abstand zur nächsten Schule (m), 200m-Radius
    osm_pflegeheim_m      = Column(Float,       nullable=True)   # Abstand zum nächsten Pflegeheim (m), 200m-Radius
    osm_baum_n_m          = Column(Float,       nullable=True)   # Abstand zum nächsten Baum (m), 50m-Radius
    osm_baum_anzahl       = Column(Integer,     nullable=True)   # Anzahl Bäume im 15m-Radius
    osm_gebaeude_res      = Column(Integer,     nullable=True)   # Anzahl Wohngebäude im 50m-Radius
    osm_gebaeude_com      = Column(Integer,     nullable=True)   # Anzahl Gewerbegebäude im 50m-Radius
    osm_landuse           = Column(String(100), nullable=True)   # Dominante Landnutzung (residential, industrial, etc.)

    # Neue Logistik- & Umweltfelder
    osm_wasser_m     = Column(Float)  # Distanz zum nächsten Gewässer (Fj-Faktor)
    osm_gleise_m     = Column(Float)  # Distanz zu Bahngleisen (Erschütterung)
    osm_parkplatz_m  = Column(Float)  # Distanz zur nächsten BE-Fläche (Parkplatz)

    osm_abfrage_ts        = Column(DateTime,    nullable=True)   # Zeitstempel der OSM-Abfrage

    # Klassifizierung
    baustellenklasse = Column(String(5),   nullable=True)   # "A" | "B" | "B+" | "C" | "C+"
    oepnv_naehe      = Column(Boolean,     nullable=True, default=False)  # Haltestelle ≤ 50 m

    # Kostenabschätzung Verkehrssicherung (aus vs_kosten.yaml)
    vs_kosten_min    = Column(Float, nullable=True)   # € (Baustelle gesamt)
    vs_kosten_max    = Column(Float, nullable=True)
    vs_kosten_typisch = Column(Float, nullable=True)

    # Zusatzinfos (manuell ergänzbar)
    bemerkung        = Column(Text, nullable=True)

    abgefragt_am     = Column(DateTime, server_default=func.now())
    geaendert_am     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    haltung = relationship("Haltung", back_populates="gis_strassen_info")


# ============================================================
# Kompatibilität: Alte Modellnamen als Aliase
# (für schrittweise Migration von main_desktop.py)
# ============================================================

# Alte Klasse → Neue Klasse
Project = Projekt
Schaden = BefundHaltung  # Achtung: Schaden hatte haltung_id + schacht_id, BefundHaltung hat nur inspektion_id
Zustandsbewertung = BewertungHaltung
ZustandsbewertungSchacht = BewertungSchacht
Sanierungsvorschlag = Massnahme


# ============================================================
# INGENIEURBAUWERKE (DIN 1076 / ASB-ING)
# ============================================================

class IngBauwerk(Base):
    """
    Ingenieurbauwerk gemäß ASB-ING (Brücken, Durchlässe, etc.)
    """
    __tablename__ = "ing_bauwerk"

    id         = Column(Integer, primary_key=True, index=True)
    netz_id    = Column(Integer, ForeignKey("netz.id", ondelete="CASCADE"), nullable=False, index=True)
    asb_id     = Column(String(50), unique=True, index=True) # Eindeutige Bauwerksnummer
    name       = Column(String(255), nullable=False)
    typ        = Column(String(100)) # Brücke, Durchlass, Stützwand, Lärmschutzwand
    bauart     = Column(String(100)) # Massivbau, Stahlbau, Verbundbau
    baujahr    = Column(Integer)
    geometrie  = Column(Geometry('POINTZ', srid=25832), nullable=True)
    gps_lat    = Column(Float, nullable=True) # WGS84 Breitengrad
    gps_lon    = Column(Float, nullable=True) # WGS84 Längengrad
    bemerkung  = Column(Text)

    erstellt_am  = Column(DateTime, server_default=func.now())
    geaendert_am = Column(DateTime, server_default=func.now(), onupdate=func.now())

    netz           = relationship("Netz")
    teilbauwerke   = relationship("IngTeilbauwerk", back_populates="bauwerk", cascade="all, delete-orphan")
    pruefungen     = relationship("IngPruefung", back_populates="bauwerk", cascade="all, delete-orphan")


class IngTeilbauwerk(Base):
    """
    Teilbauwerk (z.B. Überbau, Unterbau)
    """
    __tablename__ = "ing_teilbauwerk"

    id         = Column(Integer, primary_key=True)
    bauwerk_id = Column(Integer, ForeignKey("ing_bauwerk.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(255), nullable=False) # Überbau, Unterbau, Pfeilergruppe
    sort_order = Column(Integer, default=0)

    bauwerk    = relationship("IngBauwerk", back_populates="teilbauwerke")
    bauteile   = relationship("IngBauteil", back_populates="teilbauwerk", cascade="all, delete-orphan")


class IngBauteil(Base):
    """
    Konkretes Bauteil (z.B. Widerlager West, Lager 1)
    """
    __tablename__ = "ing_bauteil"

    id                = Column(Integer, primary_key=True)
    teilbauwerk_id    = Column(Integer, ForeignKey("ing_teilbauwerk.id", ondelete="CASCADE"), nullable=False)
    name              = Column(String(255), nullable=False)
    asb_bauteil_nr    = Column(String(50)) # ASB-Bauteilnummer
    material          = Column(String(100))
    menge             = Column(Float)
    einheit           = Column(String(20))

    teilbauwerk = relationship("IngTeilbauwerk", back_populates="bauteile")
    schaeden    = relationship("IngSchaden", back_populates="bauteil")


class IngPruefung(Base):
    """
    Bauwerksprüfung nach DIN 1076
    """
    __tablename__ = "ing_pruefung"

    id           = Column(Integer, primary_key=True)
    bauwerk_id   = Column(Integer, ForeignKey("ing_bauwerk.id", ondelete="CASCADE"), nullable=False)
    datum        = Column(Date, nullable=False)
    pruefart     = Column(String(50)) # Hauptprüfung (H1), Einfach (E1), Sonder
    pruefer      = Column(String(255))
    zustandsnote = Column(Float) # Gesamtergebnis 1.0 - 4.0
    bericht_pfad = Column(Text)

    bauwerk    = relationship("IngBauwerk", back_populates="pruefungen")
    schaeden   = relationship("IngSchaden", back_populates="pruefung", cascade="all, delete-orphan")


class IngSchaden(Base):
    """
    Einzelschaden gemäß RI-EBW-PRÜF
    """
    __tablename__ = "ing_schaden"

    id           = Column(Integer, primary_key=True)
    pruefung_id  = Column(Integer, ForeignKey("ing_pruefung.id", ondelete="CASCADE"), nullable=False)
    bauteil_id   = Column(Integer, ForeignKey("ing_bauteil.id"), nullable=False)
    code         = Column(String(50)) # Schadenscode aus RI-EBW-PRÜF
    beschreibung = Column(Text)
    bewertung_s  = Column(Integer) # Standsicherheit (0-4)
    bewertung_v  = Column(Integer) # Verkehrssicherheit (0-4)
    bewertung_d  = Column(Integer) # Dauerhaftigkeit (0-4)
    einzelnote   = Column(Float)
    skizze_json  = Column(JSONB, nullable=True) # Koordinaten der Markierung auf dem Foto
    
    erstellt_am  = Column(DateTime, server_default=func.now())

    pruefung   = relationship("IngPruefung", back_populates="schaeden")
    bauteil    = relationship("IngBauteil", back_populates="schaeden")
    fotos      = relationship("IngSchadensFoto", back_populates="schaden", cascade="all, delete-orphan")


class IngSchadensFoto(Base):
    """
    Foto eines Schadens am Ingenieurbauwerk
    """
    __tablename__ = "ing_schadens_foto"

    id          = Column(Integer, primary_key=True)
    schaden_id  = Column(Integer, ForeignKey("ing_schaden.id", ondelete="CASCADE"), nullable=False)
    dateipfad   = Column(Text, nullable=False)
    dateiname   = Column(String(255))
    aufnahme_ts = Column(DateTime)
    
    schaden     = relationship("IngSchaden", back_populates="fotos")
