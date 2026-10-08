"""Kopiert die Windows-Spotlight-Bilder aus dem ContentDeliveryManager-Assets-Ordner
nach C:\\Users\\offic\\Claude\\Asset_Images. Die Kopien heißen
Asset_Image_<Kopierdatum YYYY-MM-DD>_<Nr>.<passende Bild-Extension>.

Kopiert werden nur Bilder im Querformat mit mindestens MIN_WIDTH Pixel Breite, und nur,
wenn im Zielordner (inkl. Unterordnern) noch keine Datei mit gleichem Inhalt existiert.
Der Vergleich erfolgt per SHA-256-Prüfsumme, umbenannte Dateien werden also erkannt.
Bildtyp und Größe ermittelt Pillow; beschädigte Bilder werden übersprungen.
Alle Meldungen werden in copy_assets.log neben diesem Skript protokolliert;
Einträge älter als LOG_RETENTION_DAYS Tage werden beim Start entfernt.
"""

import hashlib
import logging
import shutil
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:  # wird in main() gemeldet, damit der Fehler im Log landet
    Image = None

SOURCE_DIR = Path(r"C:\Users\offic\AppData\Local\Packages"
                  r"\Microsoft.Windows.ContentDeliveryManager_cw5n1h2txyewy\LocalState\Assets")
TARGET_DIR = Path(r"C:\Users\offic\Claude\Asset_Images")
LOG_FILE = Path(__file__).with_suffix(".log")
LOG_RETENTION_DAYS = 60
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_WIDTH = 1920
NAME_PREFIX = "Asset_Image_"

# Pillow-Format -> Dateiendung (andere Formate: Formatname in Kleinbuchstaben)
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "BMP": ".bmp", "WEBP": ".webp"}
EXIF_ORIENTATION = 0x0112
ROTATED_ORIENTATIONS = {5, 6, 7, 8}  # Bild wird um 90° bzw. 270° gedreht angezeigt


def prune_log() -> None:
    """Entfernt Einträge aus der Logdatei, die älter als LOG_RETENTION_DAYS sind.

    Zeilen ohne Zeitstempel (z. B. Tracebacks) gehören zum vorherigen Eintrag.
    """
    if not LOG_FILE.exists():
        return
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    kept, keep = [], True
    for line in lines:
        try:
            keep = datetime.strptime(line[:19], LOG_DATE_FORMAT) >= cutoff
        except ValueError:
            pass  # Folgezeile: gleiche Entscheidung wie für den Eintrag davor
        if keep:
            kept.append(line)
    if len(kept) < len(lines):
        LOG_FILE.write_text("".join(kept), encoding="utf-8")


def setup_logging() -> None:
    """Schreibt Meldungen in die Logdatei und zusätzlich auf die Konsole."""
    prune_log()
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", LOG_DATE_FORMAT)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])


def image_info(data: bytes) -> tuple[str, int, int]:
    """Ermittelt Dateiendung und angezeigte Größe (Breite, Höhe) eines Bildes.

    Das Bild wird vollständig dekodiert, damit unvollständige oder beschädigte
    Dateien auffallen. Eine EXIF-Drehung um 90°/270° wird bei der Größe berücksichtigt.
    Wirft UnidentifiedImageError, wenn die Datei kein Bild ist, und OSError bei
    beschädigten Bildern.
    """
    with Image.open(BytesIO(data)) as im:
        im.load()
        width, height = im.size
        if im.getexif().get(EXIF_ORIENTATION) in ROTATED_ORIENTATIONS:
            width, height = height, width
        ext = EXTENSIONS.get(im.format, f".{im.format.lower()}")
    return ext, width, height


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def known_hashes(folder: Path) -> set[str]:
    """Prüfsummen aller Dateien im Zielordner inkl. Unterordnern, unabhängig vom Dateinamen."""
    return {file_hash(p.read_bytes()) for p in folder.rglob("*") if p.is_file()}


def next_target_path(ext: str) -> Path:
    """Liefert den nächsten freien Namen Asset_Image_YYYY-MM-DD_NN<ext> für heute.

    Die Nummerierung setzt bei der höchsten heute schon vergebenen Nummer fort,
    unabhängig von der Dateiendung.
    """
    prefix = f"{NAME_PREFIX}{datetime.now():%Y-%m-%d}_"
    numbers = [int(p.stem[len(prefix):]) for p in TARGET_DIR.glob(f"{prefix}*")
               if p.stem[len(prefix):].isdigit()]
    return TARGET_DIR / f"{prefix}{max(numbers, default=0) + 1:02d}{ext}"


def main() -> None:
    if Image is None:
        raise RuntimeError("Pillow ist nicht installiert. Abhilfe: pip install pillow")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    existing = known_hashes(TARGET_DIR)
    copied = skipped = filtered = not_image = damaged = 0

    for src in SOURCE_DIR.iterdir():
        if not src.is_file():
            continue

        data = src.read_bytes()
        try:
            ext, width, height = image_info(data)
        except UnidentifiedImageError:
            not_image += 1
            logging.warning("Kein Bild, übersprungen: %s", src.name)
            continue
        except (OSError, SyntaxError, ValueError) as e:
            damaged += 1
            logging.warning("Bild beschädigt oder unvollständig, übersprungen: %s (%s)", src.name, e)
            continue

        if width <= height or width < MIN_WIDTH:
            filtered += 1
            continue

        digest = file_hash(data)
        if digest in existing:
            skipped += 1
            continue

        dest = next_target_path(ext)
        shutil.copy2(src, dest)
        existing.add(digest)
        copied += 1
        logging.info("Kopiert: %s -> %s (%dx%d)", src.name, dest.name, width, height)

    logging.info("Fertig: %d kopiert, %d bereits vorhanden, %d nicht Querformat/zu klein, "
                 "%d beschädigt, %d keine Bilder.", copied, skipped, filtered, damaged, not_image)


if __name__ == "__main__":
    setup_logging()
    try:
        main()
    except Exception:
        logging.exception("Fehler beim Kopieren")
        raise
