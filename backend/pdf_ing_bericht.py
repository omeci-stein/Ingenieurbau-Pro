import datetime
import os
import json
from typing import Optional, List
from PySide6.QtCore import QMarginsF, QRectF, Qt, QPointF
from PySide6.QtGui import QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QPen, QPixmap, QBrush
from PySide6.QtPrintSupport import QPrinter

from backend import models

# Farben nach RI-EBW-PRÜF / DIN 1076 Standards
_COLOR_ZN_1 = QColor(76, 175, 80)   # Grün
_COLOR_ZN_2 = QColor(255, 193, 7)  # Gelb/Orange
_COLOR_ZN_3 = QColor(255, 152, 0)  # Dunkelorange
_COLOR_ZN_4 = QColor(244, 67, 54)   # Rot

_ACCENT = QColor(0, 102, 204)
_DARK   = QColor(33, 33, 33)
_GREY   = QColor(117, 117, 117)
_LINE   = QColor(224, 224, 224)

class IngPdfCreator:
    """
    Erzeugt DIN 1076 konforme Prüfberichte für Ingenieurbauwerke.
    Nutzt QPainter für maximale Präzision und Layout-Kontrolle.
    """
    def __init__(self, printer: QPrinter, bauwerk: models.IngBauwerk, projekt_name: str):
        self._printer = printer
        self._p = QPainter(printer)
        self._dpi = printer.logicalDpiX()
        self._mm = self._dpi / 25.4
        
        r = printer.pageRect(QPrinter.Unit.DevicePixel)
        inner = 15 * self._mm # Etwas breiterer Rand für Lochung
        self.x0 = r.x() + inner
        self.y0 = r.y() + inner
        self.x1 = r.x() + r.width() - 10 * self._mm
        self.y1 = r.y() + r.height() - 15 * self._mm
        self.w = self.x1 - self.x0
        
        self._y = self.y0
        self._page = 1
        self._bauwerk = bauwerk
        self._projekt_name = projekt_name
        self._generated = datetime.datetime.now().strftime("%d.%m.%Y")

    def _font(self, pt: float, bold: bool = False) -> QFont:
        f = QFont("Helvetica", pt)
        f.setBold(bold)
        return f

    def ensure(self, mm: float) -> None:
        if self._y + mm * self._mm > self.y1:
            self.new_page()

    def new_page(self):
        self._footer()
        self._printer.newPage()
        self._page += 1
        self._y = self.y0
        self._header()

    def _header(self):
        self._p.setFont(self._font(8))
        self._p.setPen(QPen(_GREY))
        self._p.drawText(QRectF(self.x0, self._y, self.w, 5 * self._mm), 
                         Qt.AlignLeft, f"DIN 1076 Prüfbericht: {self._bauwerk.name}")
        self._p.drawText(QRectF(self.x0, self._y, self.w, 5 * self._mm), 
                         Qt.AlignRight, f"{self._projekt_name} | {self._generated}")
        self._y += 6 * self._mm
        self._hline(_ACCENT, 0.5)
        self._y += 2 * self._mm

    def _footer(self):
        fy = self.y1 + 5 * self._mm
        self._p.setPen(QPen(_LINE, 0.2 * self._mm))
        self._p.drawLine(int(self.x0), int(fy), int(self.x1), int(fy))
        self._p.setFont(self._font(7))
        self._p.setPen(QPen(_GREY))
        self._p.drawText(QRectF(self.x0, fy + 1 * self._mm, self.w, 4 * self._mm), 
                         Qt.AlignCenter, f"Seite {self._page} - Generiert mit Ingenieurbau Pro")

    def _hline(self, color=None, width=0.2):
        self._p.setPen(QPen(color or _LINE, width * self._mm))
        self._p.drawLine(int(self.x0), int(self._y), int(self.x1), int(self._y))

    def create_report(self, pruefung: models.IngPruefung):
        self._header()
        
        # --- TITELBEREICH ---
        self._p.setFont(self._font(16, bold=True))
        self._p.setPen(QPen(_DARK))
        self._p.drawText(QRectF(self.x0, self._y, self.w, 10 * self._mm), 
                         Qt.AlignLeft, "Bauwerksprüfbericht nach DIN 1076")
        self._y += 12 * self._mm
        
        # --- STAMMDATEN ---
        self._draw_section_header("1. Stammdaten des Bauwerks")
        fields = [
            ("Bauwerksname:", self._bauwerk.name),
            ("ASB-Nummer:", self._bauwerk.asb_id),
            ("Bauwerksart:", self._bauwerk.typ),
            ("Bauweise:", self._bauwerk.bauart),
            ("Baujahr:", str(self._bauwerk.baujahr or "–")),
        ]
        self._draw_info_grid(fields)
        self._y += 5 * self._mm
        
        # --- PRÜFUNGSDATEN ---
        self._draw_section_header("2. Prüfungsdaten")
        p_fields = [
            ("Prüfungsdatum:", pruefung.datum.strftime("%d.%m.%Y")),
            ("Art der Prüfung:", pruefung.pruefart),
            ("Prüfender Ingenieur:", pruefung.pruefer),
        ]
        self._draw_info_grid(p_fields)
        self._y += 10 * self._mm
        
        # --- ZUSTANDSNOTE ---
        self._draw_zn_gauge(pruefung.zustandsnote)
        self._y += 15 * self._mm
        
        # --- SCHADENSLISTE ---
        self.ensure(40)
        self._draw_section_header("3. Schadensverzeichnis (RI-EBW-PRÜF)")
        self._draw_damage_table(pruefung.schaeden)
        
        # --- FOTOANHANG (SMART TAGGING) ---
        self.new_page()
        self._draw_section_header("4. Fotodokumentation & Schadensverortung")
        self._draw_photo_appendix(pruefung.schaeden)
        
        self._footer()
        self._p.end()

    def _draw_section_header(self, text):
        self._p.setFont(self._font(11, bold=True))
        self._p.setPen(QPen(_ACCENT))
        self._p.drawText(QRectF(self.x0, self._y, self.w, 6 * self._mm), Qt.AlignLeft, text)
        self._y += 7 * self._mm
        self._hline(_ACCENT, 0.4)
        self._y += 3 * self._mm

    def _draw_info_grid(self, fields):
        self._p.setFont(self._font(9))
        for label, val in fields:
            self._p.setPen(QPen(_GREY))
            self._p.drawText(QRectF(self.x0, self._y, 40 * self._mm, 5 * self._mm), Qt.AlignLeft, label)
            self._p.setPen(QPen(_DARK))
            self._p.drawText(QRectF(self.x0 + 42 * self._mm, self._y, self.w - 42 * self._mm, 5 * self._mm), Qt.AlignLeft, val)
            self._y += 5.5 * self._mm

    def _draw_zn_gauge(self, zn):
        self._p.save()
        gauge_w = 100 * self._mm
        gauge_h = 10 * self._mm
        gx = self.x0 + (self.w - gauge_w) / 2
        
        # Hintergrund-Balken (Verlauf)
        import PySide6.QtGui as QtGui
        grad = QtGui.QLinearGradient(gx, 0, gx + gauge_w, 0)
        grad.setColorAt(0.0, _COLOR_ZN_1)
        grad.setColorAt(0.33, _COLOR_ZN_2)
        grad.setColorAt(0.66, _COLOR_ZN_3)
        grad.setColorAt(1.0, _COLOR_ZN_4)
        
        self._p.fillRect(QRectF(gx, self._y, gauge_w, gauge_h), QBrush(grad))
        self._p.setPen(QPen(_DARK, 0.3 * self._mm))
        self._p.drawRect(QRectF(gx, self._y, gauge_w, gauge_h))
        
        # Zeiger
        pos = (zn - 1.0) / 3.0 * gauge_w
        self._p.setPen(QPen(Qt.black, 1 * self._mm))
        self._p.drawLine(int(gx + pos), int(self._y - 2 * self._mm), int(gx + pos), int(self._y + gauge_h + 2 * self._mm))
        
        # Text
        self._p.setFont(self._font(14, bold=True))
        self._p.drawText(QRectF(gx, self._y + gauge_h + 2 * self._mm, gauge_w, 10 * self._mm), 
                         Qt.AlignCenter, f"Zustandsnote: {zn:.1f}")
        self._p.restore()
        self._y += 25 * self._mm

    def _draw_damage_table(self, schaeden: List[models.IngSchaden]):
        headers = ["Pos", "Bauteil", "Schadensbeschreibung", "S", "V", "D", "Note"]
        widths = [10, 30, 80, 10, 10, 10, 15] # in mm
        
        # Header
        self._p.setFont(self._font(8, bold=True))
        self._p.fillRect(QRectF(self.x0, self._y, self.w, 6 * self._mm), QColor(240, 240, 240))
        cx = self.x0
        for i, h in enumerate(headers):
            self._p.drawText(QRectF(cx + 1 * self._mm, self._y, widths[i] * self._mm, 6 * self._mm), Qt.AlignVCenter, h)
            cx += widths[i] * self._mm
        self._y += 6 * self._mm
        self._hline()
        
        # Zeilen
        self._p.setFont(self._font(8))
        for i, s in enumerate(schaeden):
            self.ensure(10)
            cx = self.x0
            # Wrap description
            fm = self._p.fontMetrics()
            rect = fm.boundingRect(QRectF(0, 0, widths[2] * self._mm, 50 * self._mm).toRect(), Qt.TextWordWrap, s.beschreibung)
            h = max(6 * self._mm, rect.height() + 2 * self._mm)
            
            self._p.drawText(QRectF(cx + 1 * self._mm, self._y, widths[0] * self._mm, h), Qt.AlignVCenter, str(i+1))
            cx += widths[0] * self._mm
            self._p.drawText(QRectF(cx + 1 * self._mm, self._y, widths[1] * self._mm, h), Qt.AlignVCenter, s.bauteil.name)
            cx += widths[1] * self._mm
            self._p.drawText(QRectF(cx + 1 * self._mm, self._y, widths[2] * self._mm, h), Qt.AlignVCenter | Qt.TextWordWrap, s.beschreibung)
            cx += widths[2] * self._mm
            
            # SVD (Farblich markiert wenn > 0)
            for val, w in zip([s.bewertung_s, s.bewertung_v, s.bewertung_d], [widths[3], widths[4], widths[5]]):
                if val > 0:
                    self._p.setPen(QPen(_COLOR_ZN_3 if val < 3 else _COLOR_ZN_4, bold=True))
                self._p.drawText(QRectF(cx + 1 * self._mm, self._y, w * self._mm, h), Qt.AlignCenter, str(val))
                self._p.setPen(QPen(_DARK))
                cx += w * self._mm
            
            self._p.drawText(QRectF(cx + 1 * self._mm, self._y, widths[6] * self._mm, h), Qt.AlignCenter, f"{max(s.bewertung_s, s.bewertung_v, s.bewertung_d)}.0")
            
            self._y += h
            self._hline()

    def _draw_photo_appendix(self, schaeden: List[models.IngSchaden]):
        for s in schaeden:
            if not s.fotos: continue
            
            for f in s.fotos:
                self.ensure(80)
                self._p.setFont(self._font(9, bold=True))
                self._p.drawText(QRectF(self.x0, self._y, self.w, 5 * self._mm), Qt.AlignLeft, f"Foto: {s.bauteil.name} - {s.code}")
                self._y += 6 * self._mm
                
                # Bild zeichnen
                if os.path.exists(f.dateipfad):
                    img = QImage(f.dateipfad)
                    if not img.isNull():
                        # Bild skalieren (max 120mm breit)
                        max_w = 120 * self._mm
                        max_h = 80 * self._mm
                        scaled = img.scaled(int(max_w), int(max_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        # Bild zeichnen
                        self._p.drawImage(int(self.x0), int(self._y), scaled)
                        
                        # Markierungen (Smart Tagging) einzeichnen
                        if s.skizze_json:
                            self._draw_smart_tags(s.skizze_json, self.x0, self._y, scaled, img)
                        
                        self._y += scaled.height() + 5 * self._mm

    def _draw_smart_tags(self, json_str, x_px, y_px, scaled_img, orig_img):
        try:
            marks = json.loads(json_str)
            self._p.save()
            
            # Berechne Skalierungsfaktoren
            scale_x = scaled_img.width() / orig_img.width()
            scale_y = scaled_img.height() / orig_img.height()
            
            for m in marks:
                if m["type"] == "point":
                    # Punkte auf dem skalierten Bild einzeichnen
                    px = x_px + m["x"] * scale_x
                    py = y_px + m["y"] * scale_y
                    self._p.setPen(QPen(Qt.yellow, 0.5 * self._mm))
                    self._p.setBrush(QBrush(QColor(255, 255, 0, 150)))
                    self._p.drawEllipse(QPointF(px, py), 2 * self._mm, 2 * self._mm)
                elif m["type"] == "line":
                    p1x = x_px + m["x1"] * scale_x
                    p1y = y_px + m["y1"] * scale_y
                    p2x = x_px + m["x2"] * scale_x
                    p2y = y_px + m["y2"] * scale_y
                    self._p.setPen(QPen(Qt.red, 1 * self._mm))
                    self._p.drawLine(QPointF(p1x, p1y), QPointF(p2x, p2y))
            
            self._p.restore()
        except:
            pass

def erstelle_ing_bericht(db, bauwerk_id, pruefung_id, output_path, projekt_name):
    """Hauptfunktion zum Generieren des PDFs."""
    bauwerk = db.query(models.IngBauwerk).get(bauwerk_id)
    pruefung = db.query(models.IngPruefung).get(pruefung_id)
    
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(output_path)
    
    layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4),
                         QPageLayout.Orientation.Portrait,
                         QMarginsF(0, 0, 0, 0))
    printer.setPageLayout(layout)
    
    creator = IngPdfCreator(printer, bauwerk, projekt_name)
    creator.create_report(pruefung)
    return output_path
