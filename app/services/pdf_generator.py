import io
import os
import tempfile
import urllib.request
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

logger = logging.getLogger(__name__)

# Blok inicjalizacji czcionki TrueType (wykonaj przed jakąkolwiek funkcją generującą PDF)
font_dir = '/tmp' if os.path.exists('/tmp') else '.'
font_path = os.path.join(font_dir, 'Roboto-Regular.ttf')
font_bold_path = os.path.join(font_dir, 'Roboto-Bold.ttf')

FONT_NAME = 'Roboto'
FONT_BOLD = 'Roboto-Bold'

# Pobieranie czcionek z oficjalnego repozytorium Google Fonts jeśli nie istnieją lokalnie
if not os.path.exists(font_path):
    try:
        logger.info(f"Pobieranie czcionki Roboto Regular do: {font_path}")
        urllib.request.urlretrieve('https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf', font_path)
    except Exception as e:
        logger.warning(f"Błąd pobierania z głównej gałęzi, próba zapasowego repozytorium: {e}")
        urllib.request.urlretrieve('https://raw.githubusercontent.com/googlefonts/roboto-2/main/src/hinted/Roboto-Regular.ttf', font_path)

if not os.path.exists(font_bold_path):
    try:
        logger.info(f"Pobieranie czcionki Roboto Bold do: {font_bold_path}")
        urllib.request.urlretrieve('https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf', font_bold_path)
    except Exception as e:
        logger.warning(f"Błąd pobierania z głównej gałęzi, próba zapasowego repozytorium: {e}")
        urllib.request.urlretrieve('https://raw.githubusercontent.com/googlefonts/roboto-2/main/src/hinted/Roboto-Bold.ttf', font_bold_path)

try:
    # Rejestracja czcionek w silniku ReportLab
    pdfmetrics.registerFont(TTFont('Roboto', font_path))
    pdfmetrics.registerFont(TTFont('Roboto-Bold', font_bold_path))
    registerFontFamily('Roboto', normal='Roboto', bold='Roboto-Bold')
    logger.info("Czcionki Roboto zostały pomyślnie zarejestrowane.")
except Exception as e:
    logger.error(f"Nie udało się wczytać czcionki Roboto, powrót do Roboto (ReportLab default name mapping): {e}")
    FONT_NAME = 'Roboto'
    FONT_BOLD = 'Roboto-Bold'

def generate_quotation_pdf(query_id: str, sender_email: str, recipient_email: str, parsed_data: dict, price: float, created_at: datetime) -> io.BytesIO:
    """
    Generuje wycenę transportu w formacie PDF w pamięci przy użyciu ReportLab.
    Wspiera polskie znaki dzięki czcionce Roboto i pełnej konfiguracji stylów tabel.
    """
    buffer = io.BytesIO()
    
    # Helper do jawnego rzutowania na string UTF-8
    def to_utf8(val) -> str:
        if val is None:
            return ""
        if isinstance(val, bytes):
            return val.decode("utf-8")
        return str(val)

    # Utworzenie dokumentu PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Przypisanie 'Roboto' jako domyślnego fontName dla standardowych stylów
    styles['Normal'].fontName = 'Roboto'
    styles['BodyText'].fontName = 'Roboto'
    styles['Heading1'].fontName = 'Roboto'
    styles['Heading2'].fontName = 'Roboto'
    styles['Heading3'].fontName = 'Roboto'
    
    # Definicja stylów i kolorów (paleta premium: indigo / slate / warm-white)
    PRIMARY_COLOR = colors.HexColor("#1e293b")  # Slate 800
    SECONDARY_COLOR = colors.HexColor("#4f46e5") # Indigo 600
    TEXT_COLOR = colors.HexColor("#334155")      # Slate 700
    LIGHT_BG = colors.HexColor("#f8fafc")        # Slate 50
    
    # Własne style tekstu oparte na czcionce Roboto
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=PRIMARY_COLOR
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=14,
        leading=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=TEXT_COLOR
    )
    
    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName=FONT_BOLD
    )
    
    # Styl specjalnie dla nagłówków tabel z białym tekstem
    header_style = ParagraphStyle(
        'DocHeaderStyle',
        parent=body_bold,
        textColor=colors.white,
        fontSize=9,
        leading=13
    )
    
    price_style = ParagraphStyle(
        'DocPrice',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=SECONDARY_COLOR
    )

    story = []
    
    # 1. Nagłówek dokumentu
    story.append(Paragraph(to_utf8("LOJIPARSE LOGISTICS"), title_style))
    story.append(Paragraph(to_utf8(f"Wycena zapytania transportowego nr: {query_id}"), subtitle_style))
    story.append(Paragraph(to_utf8(f"Data wygenerowania: {created_at.strftime('%Y-%m-%d %H:%M:%S')}"), subtitle_style))
    story.append(Spacer(1, 15))
    
    # 2. Informacje o stronach (tabela)
    info_data = [
        [Paragraph(to_utf8("<b>Nadawca zapytania:</b>"), body_style), Paragraph(to_utf8(sender_email), body_style)],
        [Paragraph(to_utf8("<b>Skrzynka docelowa:</b>"), body_style), Paragraph(to_utf8(recipient_email), body_style)],
    ]
    info_table = Table(info_data, colWidths=[150, 380])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),  # Zapewnienie czcionki dla tabeli
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # 3. Szczegóły trasy
    story.append(Paragraph(to_utf8("Szczegóły Trasy"), section_heading))
    origin = to_utf8(parsed_data.get('origin_city', 'N/A'))
    if parsed_data.get('origin_postcode'):
        origin += to_utf8(f" ({parsed_data.get('origin_postcode')})")
        
    destination = to_utf8(parsed_data.get('destination_city', 'N/A'))
    if parsed_data.get('destination_postcode'):
        destination += to_utf8(f" ({parsed_data.get('destination_postcode')})")
        
    distance = to_utf8(f"{parsed_data.get('estimated_distance_km', 'N/A')} km" if parsed_data.get('estimated_distance_km') else "N/A")
    
    route_data = [
        [Paragraph(to_utf8("<b>Miejsce załadunku (Origin):</b>"), body_style), Paragraph(origin, body_style)],
        [Paragraph(to_utf8("<b>Miejsce rozładunku (Destination):</b>"), body_style), Paragraph(destination, body_style)],
        [Paragraph(to_utf8("<b>Szacowany dystans:</b>"), body_style), Paragraph(distance, body_style)]
    ]
    route_table = Table(route_data, colWidths=[180, 350])
    route_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    story.append(route_table)
    story.append(Spacer(1, 20))
    
    # 4. Szczegóły Ładunku
    story.append(Paragraph(to_utf8("Specyfikacja ładunku"), section_heading))
    
    cargo_items = parsed_data.get("cargo_items", [])
    if cargo_items:
        # Tabela ładunków z wrapowaniem tekstu w Paragraph
        cargo_headers = [
            Paragraph(to_utf8("<b>Opis towaru</b>"), header_style),
            Paragraph(to_utf8("<b>Ilość</b>"), header_style),
            Paragraph(to_utf8("<b>Waga (kg)</b>"), header_style),
            Paragraph(to_utf8("<b>Wymiary (cm)</b>"), header_style)
        ]
        table_rows = [cargo_headers]
        
        for item in cargo_items:
            desc = to_utf8(item.get("description", "Cargo"))
            pcs = to_utf8(item.get("pieces", "-"))
            weight = to_utf8(f"{item.get('weight_kg', '-')} kg" if item.get('weight_kg') else "-")
            
            dims = "-"
            if item.get("length_cm") and item.get("width_cm") and item.get("height_cm"):
                dims = to_utf8(f"{item.get('length_cm')}x{item.get('width_cm')}x{item.get('height_cm')}")
                
            table_rows.append([
                Paragraph(desc, body_style),
                Paragraph(pcs, body_style),
                Paragraph(weight, body_style),
                Paragraph(dims, body_style)
            ])
            
        cargo_table = Table(table_rows, colWidths=[200, 70, 100, 160])
        cargo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(cargo_table)
    else:
        # Uproszczony opis ładunku
        total_weight = to_utf8(parsed_data.get('total_weight_kg', 'N/A'))
        total_volume = to_utf8(parsed_data.get('total_volume_cbm', 'N/A'))
        
        simple_cargo = [
            [Paragraph(to_utf8("<b>Waga całkowita:</b>"), body_style), Paragraph(f"{total_weight} kg", body_style)],
            [Paragraph(to_utf8("<b>Objętość całkowita:</b>"), body_style), Paragraph(f"{total_volume} CBM", body_style)]
        ]
        simple_cargo_table = Table(simple_cargo, colWidths=[150, 380])
        simple_cargo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ]))
        story.append(simple_cargo_table)
        
    story.append(Spacer(1, 15))
    
    # 5. Instrukcje obsługi / uwagi
    instructions = parsed_data.get("handling_instructions")
    if instructions:
        story.append(Paragraph(to_utf8("<b>Instrukcje specjalne:</b>"), body_style))
        story.append(Paragraph(to_utf8(instructions), body_style))
        story.append(Spacer(1, 20))
        
    # 6. Podsumowanie Wyceny (Cena)
    story.append(Paragraph(to_utf8("Wycena Szacunkowa"), section_heading))
    
    price_display = to_utf8(f"{price:.2f} EUR" if price else "Do kalkulacji indywidualnej")
    
    price_data = [
        [
            Paragraph(to_utf8("Sugerowana stawka netto za transport (EUR):"), body_bold),
            Paragraph(price_display, price_style)
        ]
    ]
    price_table = Table(price_data, colWidths=[330, 200])
    price_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_BOLD),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#e0e7ff")), # Light indigo
        ('PADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, SECONDARY_COLOR),
    ]))
    story.append(price_table)
    
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        to_utf8("<i>Wycena ma charakter poglądowy i została wygenerowana automatycznie przez system LojiParse na podstawie treści zapytania e-mail.</i>"),
        subtitle_style
    ))
    
    # Budowanie dokumentu
    doc.build(story)
    
    buffer.seek(0)
    return buffer
