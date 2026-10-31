"""Draws the three synthetic sample deeds in deed/samples/ (run by hand: python -m deed.make_samples).

Every name, number and plate is made up; the national IDs only pass the checksum. The files are committed, so the
server never runs this (drawing Persian text needs Pillow with libraqm, which a server may not have).
1. clean.png        a clean single-owner deed, one page
2. shared.pdf       two pages: three owners with shares, the transfer history, and an area that disagrees
                    between the two pages (for the reviewer to settle)
3. unclear.png      a poor scan: turned on its side, blurred, the deed number smudged, no issue date or book/page
"""
import os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "frontend", "public", "fonts")
OUT = os.path.join(HERE, "samples")
W, H, MARGIN = 1240, 1754, 110   # A4 at 150 dpi

def font(size, bold=False):
    return ImageFont.truetype(os.path.join(FONTS, f"Vazirmatn-{'Bold' if bold else 'Regular'}.woff2"), size)

def page(lines, seed):
    """lines: [(text, size, bold, centred)]. A paper-coloured page with a frame and the text right to left."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), (246, 241, 228))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, W - 60, H - 60], outline=(120, 100, 70), width=3)
    d.rectangle([72, 72, W - 72, H - 72], outline=(160, 140, 105), width=1)
    y = 120
    for text, size, bold, centred in lines:
        if text:
            f = font(size, bold)
            if centred:
                d.text((W // 2, y), text, font=f, fill=(35, 30, 25), direction="rtl", anchor="ma")
            else:
                d.text((W - MARGIN, y), text, font=f, fill=(35, 30, 25), direction="rtl", anchor="ra")
        y += int(size * 1.9)
    # a faint round stamp and a little paper grain
    d.ellipse([140, H - 360, 380, H - 120], outline=(110, 90, 170), width=4)
    d.text((260, H - 250), "مهر اداره ثبت", font=font(24), fill=(110, 90, 170), direction="rtl", anchor="mm")
    px = img.load()
    for _ in range(9000):
        x, yy = rnd.randrange(W), rnd.randrange(H)
        c = px[x, yy]
        px[x, yy] = tuple(max(0, v - rnd.randint(10, 40)) for v in c)
    return img

def L(text, size=30, bold=False, centred=False):
    return (text, size, bold, centred)

HEAD = [L("جمهوری اسلامی ایران", 30, True, True), L("سازمان ثبت اسناد و املاک کشور", 34, True, True),
        L("سند مالکیت (نمونه‌ی ساختگی)", 30, False, True), L("")]

def clean():
    return page(HEAD + [
        L("شماره سند: 482913"),
        L("دفتر شماره 312 صفحه 47"),
        L("تاریخ صدور: 1384/06/15"),
        L(""),
        L("ششدانگ یک باب خانه به مساحت 245.50 مترمربع"),
        L("پلاک شماره 1520 فرعی از 87 اصلی واقع در بخش 11 تهران"),
        L(""),
        L("مالک: آقای کامران نیک‌سرشت فرزند جهانگیر"),
        L("به شماره ملی 5260181591 نسبت به شش دانگ"),
        L(""),
        L("حدود اربعه:", 30, True),
        L("شمالاً به طول 12 متر دیوار به دیوار پلاک 1519 فرعی"),
        L("شرقاً به طول 20.5 متر درب و دیواری است به کوچه"),
        L("جنوباً به طول 12 متر دیوار به دیوار پلاک 1521 فرعی"),
        L("غرباً به طول 20.5 متر دیوار به دیوار پلاک 1530 فرعی"),
    ], seed=1)

def shared():
    first = page(HEAD + [
        L("شماره سند: 731045"),
        L("دفتر شماره 98 صفحه 211"),
        L("تاریخ صدور: 1391/02/20"),
        L(""),
        L("ششدانگ یک قطعه زمین به مساحت 180 مترمربع"),
        L("پلاک شماره 2245 فرعی از 112 اصلی واقع در بخش 4 اصفهان"),
        L(""),
        L("مالکین:", 30, True),
        L("خانم مهسا رادمنش فرزند فرهاد به شماره ملی 0830166130 نسبت به سه دانگ"),
        L("آقای بهراد رادمنش فرزند فرهاد به شماره ملی 1860913903 نسبت به یک و نیم دانگ"),
        L("آقای سپهر رادمنش فرزند فرهاد به شماره ملی 9960308243 نسبت به یک و نیم دانگ"),
        L(""),
        L("حدود اربعه:", 30, True),
        L("شمالاً به طول 10 متر به خیابان بیست متری"),
        L("شرقاً به طول 18 متر به پلاک 2246 فرعی"),
        L("جنوباً به طول 10 متر به پلاک 2260 فرعی"),
        L("غرباً به طول 18 متر به پلاک 2244 فرعی"),
    ], seed=2)
    second = page([L("ادامه‌ی سند شماره 731045", 30, True, True), L(""),
        L("نقل و انتقالات:", 30, True),
        L("به موجب سند انتقال شماره 15422 مورخ 1392/11/03 دفترخانه 48"),
        L("سه دانگ از آقای فرهاد رادمنش به خانم مهسا رادمنش منتقل شد"),
        L(""),
        L("به موجب سند انتقال شماره 16870 مورخ 1395/04/12 دفترخانه 48"),
        L("سه دانگ از آقای فرهاد رادمنش به آقای بهراد رادمنش و آقای سپهر رادمنش منتقل شد"),
        L(""),
        L("ملاحظات:", 30, True),
        L("به مساحت 186 مترمربع طبق صورتمجلس تفکیکی"),
    ], seed=3)
    return first, second

def unclear():
    img = page(HEAD + [
        L("شماره سند: 556207"),
        L(""),
        L("ششدانگ یک باب مغازه به مساحت 42 مترمربع"),
        L("پلاک شماره 318 فرعی از 1290 اصلی واقع در بخش 2 مشهد"),
        L(""),
        L("مالک: خانم نرگس کیانی فرزند احمد"),
        L("به شماره ملی 6281948211 نسبت به شش دانگ"),
        L(""),
        L("حدود اربعه:", 30, True),
        L("شمالاً به طول 6 متر به راهرو"),
        L("جنوباً به طول 6 متر به خیابان"),
    ], seed=4)
    d = ImageDraw.Draw(img)
    d.ellipse([W - 470, 330, W - 300, 400], fill=(150, 135, 110))   # a smudge over the deed number
    img = img.filter(ImageFilter.GaussianBlur(1.3)).rotate(90, expand=True, fillcolor=(230, 225, 210))
    return img.resize((img.width * 3 // 4, img.height * 3 // 4))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    clean().save(os.path.join(OUT, "clean.png"), optimize=True)
    a, b = shared()
    a.save(os.path.join(OUT, "shared.pdf"), save_all=True, append_images=[b], resolution=150)
    unclear().convert("L").save(os.path.join(OUT, "unclear.png"), optimize=True)
    print("written to", OUT)
