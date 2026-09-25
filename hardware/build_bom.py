from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

HERE = Path(__file__).resolve().parent
OUT = HERE / "v1-electronics-bom.pdf"

# Prices are extended cart line prices in USD, checked 2026-09-24.
rows = [
    ("Compute", "Pi Zero 2 W, soldered header", "1", 20.75, "https://www.pishop.us/product/raspberry-pi-zero-2w-with-headers/"),
    ("Compute", "2x20 female Pi socket", "1", 1.50, "https://www.adafruit.com/product/2222"),
    ("Compute", "32 GB microSD card", "1", 19.95, "https://www.pishop.us/product/raspberry-pi-sd-card-32gb/"),
    ("Audio", "SPH0645 I2S mic breakout", "1", 6.95, "https://www.adafruit.com/product/3421"),
    ("Audio", "MAX98357A I2S amp breakout", "1", 5.95, "https://www.adafruit.com/product/3006"),
    ("Audio", "8-ohm, 1 W mini speaker", "1", 1.95, "https://www.adafruit.com/product/3923"),
    ("Motion", "SG92R micro servo", "3", 17.85, "https://www.adafruit.com/product/169"),
    ("Controls", "16 mm momentary pushbutton", "2", 1.90, "https://www.adafruit.com/product/1504"),
    ("Power", "USB-C 5 V sink breakout, CC resistors", "1", 2.95, "https://www.sparkfun.com/usb-2-0-type-c-connector-breakout-board.html"),
    ("Power", "5.1 V, 3 A USB-C power supply", "1", 8.80, "https://www.pishop.us/product/raspberry-pi-15w-power-supply-us-black/"),
    ("Power", "2200 uF, 16 V bulk capacitor*", "1", 3.32, "https://www.digikey.com/en/products/detail/tdk/B41866C4228M000/5844971"),
    ("Build", "Half-size solderable Perma-Proto", "1", 4.50, "https://www.adafruit.com/product/1609"),
    ("Build", "40-pin breakaway male header", "1", 1.95, "https://www.sparkfun.com/straight-header-male-pth-0-1in-40-pin.html"),
    ("Build", "22 AWG stranded ribbon, 10 wires", "1 m", 4.25, "https://www.adafruit.com/product/6180"),
    ("Build", "26 AWG stranded ribbon, 10 wires", "1 m", 2.50, "https://www.adafruit.com/product/6182"),
    ("Build", "8 A, 2-pin screw terminal", "2", 2.20, "https://www.sparkfun.com/screw-terminals-5mm-pitch-2-pin.html"),
    ("Build", "M2.5 nylon standoff/screw kit", "1 kit", 14.95, "https://www.adafruit.com/product/3658"),
    ("Bench", "Pi micro-USB power supply", "1", 8.80, "https://www.pishop.us/product/raspberry-pi-12-5w-power-supply-us-white/"),
    ("Finish", "Panchroma Metallic Bronze PLA, 1.75 mm", "1 kg", 24.99, "https://www.gigaparts.com/polymaker-panchroma-metallic-pla-bronze-1-75mm-1kg-filament-spool.html"),
]

assert round(sum(r[3] for r in rows), 2) == 156.01

navy = colors.HexColor("#173348")
teal = colors.HexColor("#087C91")
gray = colors.HexColor("#4E626D")
pale = colors.HexColor("#EAF3F5")

styles = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=navy, spaceAfter=8),
    "deck": ParagraphStyle("deck", fontName="Helvetica", fontSize=9.2, leading=13.3, textColor=gray, spaceAfter=10),
    "head": ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=11.5, leading=16, textColor=teal, spaceBefore=13, spaceAfter=6),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=13, textColor=navy, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10.6, textColor=navy),
    "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=navy),
}

def P(s, kind="body"):
    return Paragraph(s, styles[kind])

story = [
    P("A1-4RD | V1 electronics shopping list", "title"),
    P("Rebuilt for what you already own or can access: soldering supplies, heat shrink, 1 k-ohm resistors, LEDs, "
      "jumper wires, a microSD reader, a multimeter, a breadboard, and white or black PLA for internal prints. "
      "This is the linked, priced shopping list for one Pi Zero 2 W prototype with two moving servos, I2S audio, "
      "a button, and a status LED. US list prices checked 24 Sep 2026; click part names for product pages.", "deck"),
]

table_data = [[P("Group", "th"), P("Buy", "th"), P("Qty", "th"), P("Cost", "th")]]
for group, name, qty, price, url in rows:
    label = f'<link href="{escape(url)}" color="#087C91"><u>{escape(name)}</u></link>'
    table_data.append([P(group, "cell"), P(label, "cell"), P(qty, "cell"), P(f"${price:.2f}", "cell")])
table_data.append([P("", "th"), P("Order-now subtotal", "th"), P("", "th"), P("$156.01", "th")])
t = Table(table_data, colWidths=[55, 335, 55, 75], repeatRows=1, hAlign="LEFT")
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), pale),
    ("BACKGROUND", (0, -1), (-1, -1), pale),
    ("LINEBELOW", (0, 0), (-1, 0), .6, teal),
    ("LINEABOVE", (0, -1), (-1, -1), .6, teal),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
]))
story += [t, Spacer(1, 5)]
story += [
    P("Cost and scope", "head"),
    P("<b>Buy now:</b> $156.01 before shipping and tax, including one bronze PLA spool for visible prints. "
      "Three servos means two installed and one spare; "
      "two buttons means one installed and one spare. Packs leave extras. Allow another <b>$20-$35</b> for "
      "the final input/servo protection, small decoupling parts, enclosure fasteners, and cable strain relief "
      "after measurements and CAD. That puts the purchased electronics and filament at roughly <b>$176-$191</b> "
      "before shipping/tax, or about <b>$200-$240 at checkout</b> across five vendors. "
      "These are planning estimates, not quotes."),
    P("<b>Already owned, so excluded:</b> soldering supplies, heat shrink, 1 k-ohm resistors, LEDs, jumper wires, "
      "microSD reader, multimeter, breadboard, and white or black PLA for internal prints. "
      "No custom PCB is ordered for this first build; the solderable protoboard carries the initial circuit."),
    KeepTogether([
        P("Selection gates", "head"),
        P("<b>Audio:</b> the SPH0645 mic and MAX98357A amp are test candidates. Verify simultaneous capture and "
          "playback on the Pi's shared I2S controller before committing to the enclosure or a PCB."),
    ]),
    P("<b>Power:</b> the 5.1 V / 3 A supply is a test candidate for the assembled unit. Measure Pi voltage "
      "while both servos start/reverse and audio plays. The listed USB-C sink breakout has the required "
      "5.1 k-ohm CC pull-down resistors; the earlier breakout did not."),
    P("<b>*Bulk capacitor:</b> buy it for power experiments, but do not put 2200 uF directly on USB-C VBUS. "
      "Decide its placement and the attach/inrush protection after measuring the load."),
    P("<b>Mechanical:</b> confirm SG92R torque and the jaw/neck envelope. The small speaker is a fit candidate; "
      "limit amplifier output to its 1 W rating. Final M3 enclosure hardware depends on the printed design."),
    P("<b>Filament:</b> Panchroma Metallic Bronze is a bronze-colored PLA, not a metal-filled filament. "
      "Use it for visible parts and accessible white/black PLA for internal parts. Confirm your printer takes "
      "1.75 mm filament and has a 0.4 mm or larger nozzle."),
    P("Test equipment", "head"),
    P("Use a current-limited 5 V bench supply and an oscilloscope for current and voltage-transient measurements; "
      "borrow lab equipment if available. Neither instrument is included in the electronics checkout estimate. "
      "The listed Pi micro-USB supply powers the Pi alone during bring-up."),
]

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D5E1E4"))
    canvas.line(46, 40, letter[0]-46, 40)
    canvas.setFillColor(gray)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(46, 28, "A1-4RD  |  24 Sep 2026  |  prices subject to change")
    canvas.drawRightString(letter[0]-46, 28, f"{doc.page}")
    canvas.restoreState()

OUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=46, rightMargin=46,
                        topMargin=42, bottomMargin=54)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
