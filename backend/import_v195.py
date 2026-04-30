import os
import re
import datetime
from sqlalchemy.orm import Session
from backend import models

class V195Importer:
    """
    Importiert ASB-ING Daten aus dem .V195 Austauschformat.
    Unterstützt Kartenarten KA10, KA20, KA30, KA40.
    """
    def __init__(self, db: Session, netz_id: int):
        self.db = db
        self.netz_id = netz_id
        self.bauwerk_map = {} # asb_id -> IngBauwerk
        self.bauteil_map = {} # (asb_id, asb_bt_nr) -> IngBauteil
        
    def import_file(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
            
        # Typprüfung: CAB (MSCF) oder Text?
        with open(file_path, 'rb') as f:
            header = f.read(4)
            
        if header == b'MSCF':
            return self._import_cab_archive(file_path)
        else:
            return self._import_text_v195(file_path)

    def _import_cab_archive(self, file_path: str):
        import subprocess
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp(prefix="sib_import_")
        try:
            # Extrahieren mit Windows extrac32
            subprocess.run(["extrac32", "/e", "/l", temp_dir, file_path], check=True, capture_output=True)
            
            dbf_path = os.path.join(temp_dir, "ges_bw.dbf")
            if os.path.exists(dbf_path):
                return self._import_dbf(temp_dir)
            
            # Suche nach .v195 oder .txt im extrahierten Ordner
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.lower().endswith((".v195", ".v19", ".txt")):
                        content = open(os.path.join(root, f), "r", encoding="latin-1").read()
                        if "KA10" in content:
                            return self._import_text_v195(os.path.join(root, f))
            
            raise ValueError("Keine gültigen ASB-ING Daten im Archiv gefunden (DBF oder KA10).")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _import_dbf(self, base_path: str):
        count = 0
        bw_records = self._read_dbf_file(os.path.join(base_path, "ges_bw.dbf"))
        
        for r in bw_records:
            asb_id = r.get('BWNAME', '').strip()
            if not asb_id: continue
            
            bw = self.db.query(models.IngBauwerk).filter_by(asb_id=asb_id).first()
            if not bw:
                bw = models.IngBauwerk(
                    netz_id=self.netz_id,
                    asb_id=asb_id,
                    name=asb_id, # Fallback Name
                    typ="Importiert (SIB DBF)"
                )
                self.db.add(bw)
                self.db.flush()
            self.bauwerk_map[r.get('BWNR')] = bw
            count += 1
            
        # Prüfungen importieren
        pruf_path = os.path.join(base_path, "akt_pruf.dbf")
        if os.path.exists(pruf_path):
            p_records = self._read_dbf_file(pruf_path)
            for pr in p_records:
                bw = self.bauwerk_map.get(pr.get('BWNR'))
                if not bw: continue
                
                try:
                    # Datum parsen (oft YYYYMMDD in DBF)
                    d_str = pr.get('PRUFDAT1', '')
                    if len(d_str) == 8:
                        datum = datetime.date(int(d_str[:4]), int(d_str[4:6]), int(d_str[6:8]))
                    else:
                        datum = datetime.date.today()
                        
                    note_str = pr.get('ZN_BAUWERK', '').replace(',', '.')
                    note = float(note_str) if note_str else None
                    
                    new_pr = models.IngPruefung(
                        bauwerk_id=bw.id,
                        datum=datum,
                        pruefart=pr.get('PRUFART', 'Hauptprüfung'),
                        zustandsnote=note,
                        pruefer=pr.get('PRUEFER', '')
                    )
                    self.db.add(new_pr)
                except:
                    pass
                    
        self.db.commit()
        return count

    def _read_dbf_file(self, path):
        import struct
        with open(path, 'rb') as f:
            data = f.read()
            
        num_records = struct.unpack('<I', data[4:8])[0]
        header_len = struct.unpack('<H', data[8:10])[0]
        record_len = struct.unpack('<H', data[10:12])[0]
        
        fields = []
        for i in range(32, header_len - 1, 32):
            if data[i] == 0x0D: break
            field_name = data[i:i+11].split(b'\0')[0].decode('ascii', errors='ignore')
            field_len = data[i+16]
            fields.append((field_name, field_len))
            
        records = []
        for i in range(num_records):
            start = header_len + i * record_len
            if start + record_len > len(data): break
            record_data = data[start:start+record_len]
            if record_data[0] == 0x2A: continue # Gelöscht
            
            record = {}
            offset = 1
            for name, flen in fields:
                val = record_data[offset:offset+flen].decode('latin-1', errors='ignore').strip()
                record[name] = val
                offset += flen
            records.append(record)
        return records

    def _import_text_v195(self, file_path: str):
        with open(file_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()
        
        # 1. Durchlauf: Bauwerke anlegen (KA10)
        for line in lines:
            if line.startswith("KA10"):
                self._parse_ka10(line)
        self.db.flush()
        
        # 2. Durchlauf: Teilbauwerke & Bauteile (KA20)
        for line in lines:
            if line.startswith("KA20"):
                self._parse_ka20(line)
        self.db.flush()
        
        # 3. Durchlauf: Prüfungen (KA30)
        for line in lines:
            if line.startswith("KA30"):
                self._parse_ka30(line)
        self.db.flush()
        
        # 4. Durchlauf: Schäden (KA40)
        for line in lines:
            if line.startswith("KA40"):
                self._parse_ka40(line)
                
        self.db.commit()
        return len(self.bauwerk_map)

    def _parse_ka10(self, line):
        # KA10;Bauwerksnummer;Name;...
        parts = line.strip().split(';')
        if len(parts) < 3: return
        
        asb_id = parts[1]
        name = parts[2]
        
        # Prüfen ob Bauwerk schon existiert
        bw = self.db.query(models.IngBauwerk).filter_by(asb_id=asb_id).first()
        if not bw:
            bw = models.IngBauwerk(
                netz_id=self.netz_id,
                asb_id=asb_id,
                name=name,
                typ="Importiert (V195)"
            )
            self.db.add(bw)
        self.bauwerk_map[asb_id] = bw

    def _parse_ka20(self, line):
        # KA20;Bauwerksnummer;BauteilNr;Name;Material;...
        parts = line.strip().split(';')
        if len(parts) < 4: return
        
        asb_id = parts[1]
        bt_nr = parts[2]
        bt_name = parts[3]
        
        bw = self.bauwerk_map.get(asb_id)
        if not bw: return
        
        # Wir legen ein Standard-Teilbauwerk an, falls nicht vorhanden
        tbw = self.db.query(models.IngTeilbauwerk).filter_by(bauwerk_id=bw.id, name="Hauptbauwerk").first()
        if not tbw:
            tbw = models.IngTeilbauwerk(bauwerk_id=bw.id, name="Hauptbauwerk")
            self.db.add(tbw)
            self.db.flush()
            
        # Bauteil anlegen
        bt = self.db.query(models.IngBauteil).filter_by(teilbauwerk_id=tbw.id, asb_bauteil_nr=bt_nr).first()
        if not bt:
            bt = models.IngBauteil(
                teilbauwerk_id=tbw.id,
                asb_bauteil_nr=bt_nr,
                name=bt_name
            )
            self.db.add(bt)
        self.bauteil_map[(asb_id, bt_nr)] = bt

    def _parse_ka30(self, line):
        # KA30;Bauwerksnummer;Datum;Pruefart;Note;...
        parts = line.strip().split(';')
        if len(parts) < 5: return
        
        asb_id = parts[1]
        datum_str = parts[2] # Format oft DD.MM.YYYY
        art = parts[3]
        note_str = parts[4].replace(',', '.')
        
        bw = self.bauwerk_map.get(asb_id)
        if not bw: return
        
        try:
            datum = datetime.datetime.strptime(datum_str, "%d.%m.%Y").date()
            note = float(note_str) if note_str else None
            
            pruefung = models.IngPruefung(
                bauwerk_id=bw.id,
                datum=datum,
                pruefart=art,
                zustandsnote=note
            )
            self.db.add(pruefung)
        except:
            pass

    def _parse_ka40(self, line):
        # KA40;Bauwerksnummer;BauteilNr;SchadensNr;Code;S;V;D;...
        parts = line.strip().split(';')
        if len(parts) < 8: return
        
        asb_id = parts[1]
        bt_nr = parts[2]
        code = parts[4]
        s = parts[5]
        v = parts[6]
        d = parts[7]
        
        bt = self.bauteil_map.get((asb_id, bt_nr))
        if not bt: return
        
        # Wir brauchen die letzte Prüfung für dieses Bauwerk
        pruefung = self.db.query(models.IngPruefung).filter_by(bauwerk_id=bt.teilbauwerk.bauwerk_id).order_by(models.IngPruefung.datum.desc()).first()
        if not pruefung: return
        
        schaden = models.IngSchaden(
            pruefung_id=pruefung.id,
            bauteil_id=bt.id,
            code=code,
            bewertung_s=int(s) if s.isdigit() else 0,
            bewertung_v=int(v) if v.isdigit() else 0,
            bewertung_d=int(d) if d.isdigit() else 0
        )
        self.db.add(schaden)
