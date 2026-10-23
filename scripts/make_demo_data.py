"""Generate the demo data (fictional pharmacy inventories and DEMO label images).

    python scripts/make_demo_data.py

Everything here is FICTIONAL except the alert batches it deliberately mixes in,
which are real rows from CDSCO's published alerts (so the demo shows real hits).
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "demo"
LABELS = DEMO / "labels"
random.seed(2026)

# --- real alert rows (CDSCO, Mar-Jul 2026 = live at demo start) ---
LIVE_FLAGGED = [
    ("Cefixime Tablets IP 200 mg", "25460922", "Alkem Health Science"),
    ("Pantoprazole Gastro-resistant Tablets IP 40 mg", "KT25028", "Keron Lifesciences Pvt. Ltd."),
    ("Paracetamol Tablets IP 500 mg", "PAK-825", "Healer's Lab"),
    ("Telmisartan Tablets IP 40 mg", "BPLT-25104", "Bennet Pharmaceuticals Limited"),
    ("Amoxycillin & Potassium Clavulanate Tablets IP", "VT251183", "VADSP Pharmaceuticals"),
    ("Diclofenac Sodium Tablets IP 50 mg", "SP250935", "Sharun Pharmaceuticals Pvt. Ltd."),
    ("Azithromycin Tablets IP 250 mg", "HAZT-2501", "Heal (India) Laboratories Pvt. Ltd."),
    ("Telmisartan & Amlodipine Tablets IP", "25440443", "Alkem Health Science"),
]
# real rows that only appear in the AUGUST 2026 alerts (data/inbox) -> flagged after admin approval
AUGUST_ONLY = [
    ("Paracetamol Tablets IP 650 mg", "T60093", "Zenith Drugs Limited"),
    ("Amoxicillin and Potassium Clavulanate Tablets IP", "GBR1240", "Brooks Laboratories Ltd."),
    ("Telmisartan Tablets IP 40 mg", "TM5145", "Kerala State Drugs and Pharmaceuticals Ltd."),
]
# POSSIBLE cases: an OCR-style misread, and a real batch code on an unrelated product
POSSIBLE = [
    ("Pantoprazole & Domperidone Tablets", "BCV4OO1DZ", "VPAM Healthcare Pvt. Ltd."),   # O instead of 0
    ("Vitamin C Chewable Tablets 500 mg", "STS-122", "Demo Nutrition Labs"),            # same code, other product
]

GENERICS = [
    "Paracetamol Tablets IP 500 mg", "Paracetamol Tablets IP 650 mg", "Cetirizine Tablets IP 10 mg",
    "Amoxycillin Capsules IP 500 mg", "Azithromycin Tablets IP 500 mg", "Metformin Tablets IP 500 mg",
    "Amlodipine Tablets IP 5 mg", "Atorvastatin Tablets IP 10 mg", "Pantoprazole Tablets IP 40 mg",
    "Ibuprofen Tablets IP 400 mg", "Omeprazole Capsules IP 20 mg", "ORS Powder IP", "Vitamin D3 Capsules",
    "Montelukast & Levocetirizine Tablets", "Losartan Tablets IP 50 mg", "Domperidone Tablets IP 10 mg",
    "Ondansetron Tablets IP 4 mg", "Cough Syrup (Dextromethorphan)", "Calcium & Vitamin D3 Tablets",
    "Iron & Folic Acid Tablets", "Glimepiride Tablets IP 2 mg", "Aceclofenac & Paracetamol Tablets",
    "Ciprofloxacin Tablets IP 500 mg", "Ranitidine Tablets IP 150 mg", "Salbutamol Inhaler",
]
MAKERS = ["Demo Pharma Labs", "Example Healthcare Pvt. Ltd.", "Sample Remedies", "Testwell Formulations",
          "Placeholder Biotech", "Mockup Lifesciences"]
SUPPLIERS = [("Northgate Distributors (Demo)", "orders@northgate.example.com"),
             ("Riverside Medical Supply (Demo)", "returns@riverside.example.com"),
             ("Lakeview Pharma Wholesale (Demo)", "qa@lakeview.example.com")]


def rand_batch():
    style = random.choice(["AAA9999", "AA99999A", "99A999", "AAA-99999"])
    out = ""
    for ch in style:
        out += random.choice("ABCDEFGHJKMNPRTUVWXY") if ch == "A" else (random.choice("0123456789") if ch == "9" else ch)
    return out


def inventory(n_clean, specials, name):
    rows = []
    for i in range(n_clean):
        sup = random.choice(SUPPLIERS)
        rows.append([f"SKU{1000+i}", random.choice(GENERICS), rand_batch(), random.choice(MAKERS),
                     random.randint(5, 300), sup[0], sup[1]])
    for product, batch, maker in specials:
        sup = random.choice(SUPPLIERS)
        rows.append([f"SKU{2000+len(rows)}", product, batch, maker, random.randint(10, 120), sup[0], sup[1]])
    random.shuffle(rows)
    import csv
    with open(DEMO / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku", "product", "batch", "manufacturer", "qty", "supplier", "supplier_email"])
        w.writerows(rows)
    return len(rows)


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for base in ["/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", ""]:
        try:
            return ImageFont.truetype(base + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def label(fname, brand, generic, maker, batch, mfg, exp, blur=False):
    W, H = 1200, 560
    img = Image.new("RGB", (W, H), (214, 218, 222))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 6):  # foil texture
        d.line([(x, 0), (x + 200, H)], fill=(205 + (x // 6) % 12, 209 + (x // 6) % 12, 214), width=3)
    d.rectangle([30, 30, W - 30, H - 30], outline=(120, 125, 130), width=3)
    d.text((70, 60), brand, font=font(64, True), fill=(30, 60, 120))
    d.text((70, 145), generic, font=font(30), fill=(40, 40, 40))
    d.text((70, 200), f"Mfd. by: {maker}", font=font(26), fill=(40, 40, 40))
    d.text((70, 290), f"B.No.: {batch}", font=font(40, True), fill=(20, 20, 20))
    d.text((70, 350), f"Mfg. Dt.: {mfg}     Exp. Dt.: {exp}", font=font(30), fill=(20, 20, 20))
    d.text((70, 420), "Store below 25°C. Keep out of reach of children.", font=font(22), fill=(70, 70, 70))
    banner = Image.new("RGBA", (W, 70), (0, 0, 0, 0))
    ImageDraw.Draw(banner).rectangle([0, 0, W, 70], fill=(181, 82, 59, 200))
    ImageDraw.Draw(banner).text((W // 2 - 330, 14), "DEMO SAMPLE – NOT A REAL PACK", font=font(36, True), fill="white")
    img.paste(banner.rotate(-8, expand=False), (0, 470), banner.rotate(-8, expand=False))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(9))
    img.save(LABELS / fname, quality=92)


def main():
    DEMO.mkdir(parents=True, exist_ok=True)
    LABELS.mkdir(parents=True, exist_ok=True)
    n1 = inventory(187, LIVE_FLAGGED + AUGUST_ONLY + POSSIBLE, "inventory_sunrise_pharmacy_demo.csv")
    n2 = inventory(58, [LIVE_FLAGGED[2], LIVE_FLAGGED[6]], "inventory_careplus_hospital_demo.csv")
    print(f"inventories: {n1} and {n2} lines")

    # labels.json: 'printed' = ground truth; 'offline_read' = what the no-API fallback returns,
    # simulating a realistic read (incl. an OCR slip) so the human confirmation gate can be demoed.
    labels = {
        "1_cefixime_flagged.jpg": dict(brand="CEFIXIME-200", generic="Cefixime Tablets IP 200 mg",
            maker="Alkem Health Science", batch="25460922", mfg="Jul-2025", exp="Jun-2027"),
        "2_paracetamol_clear.jpg": dict(brand="FEVRA-500", generic="Paracetamol Tablets IP 500 mg",
            maker="Demo Pharma Labs", batch="DPL24A117", mfg="Mar-2026", exp="Feb-2028"),
        "3_pantoprazole_ocr_slip.jpg": dict(brand="PANTODOM", generic="Pantoprazole & Domperidone Tablets",
            maker="VPAM Healthcare Pvt. Ltd.", batch="BCV4001DZ", mfg="Jul-2024", exp="Jun-2026",
            offline_batch="BCV4OO1DZ", offline_conf=0.62),
        "4_telmisartan_august.jpg": dict(brand="TELMI-40", generic="Telmisartan Tablets IP 40 mg",
            maker="Kerala State Drugs and Pharmaceuticals Ltd.", batch="TM5145", mfg="Sep-2025", exp="Aug-2027"),
        "5_cefixime_blurry.jpg": dict(brand="CEFIXIME-200", generic="Cefixime Tablets IP 200 mg",
            maker="Alkem Health Science", batch="25460922", mfg="Jul-2025", exp="Jun-2027", blur=True),
    }
    meta = {}
    for fname, L in labels.items():
        label(fname, L["brand"], L["generic"], L["maker"], L["batch"], L["mfg"], L["exp"], blur=L.get("blur", False))
        blurred = L.get("blur", False)
        meta[fname] = {
            "printed": {"brand_name": L["brand"], "generic_name": L["generic"], "manufacturer": L["maker"],
                        "batch_number": L["batch"], "expiry_date": L["exp"]},
            "offline_read": {
                "fields": {"brand_name": None if blurred else L["brand"],
                           "generic_name": None if blurred else L["generic"],
                           "manufacturer": None if blurred else L["maker"],
                           "batch_number": None if blurred else L.get("offline_batch", L["batch"]),
                           "expiry_date": None if blurred else L["exp"]},
                "confidence": {"brand_name": 0 if blurred else 0.95, "generic_name": 0 if blurred else 0.93,
                               "manufacturer": 0 if blurred else 0.9,
                               "batch_number": 0 if blurred else L.get("offline_conf", 0.94),
                               "expiry_date": 0 if blurred else 0.92}},
        }
    with open(LABELS / "labels.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"labels: {len(meta)} images + labels.json")


if __name__ == "__main__":
    sys.exit(main())
