import re
from datetime import datetime
import pdfplumber
from utils.data_formatter import DataFormatter, SPANISH_MONTHS

_TIEMPOS_RE = re.compile(r"TIEMPOS\s+DEL\s+PROYECTO", re.IGNORECASE)

_DATE_TOKEN_RE = re.compile(
    r"(?:\d{1,2}\s+de\s+(?:del\s+|el\s+|de\s+)?)?[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}\s+(?:del\s+|de\s+)?\d{4}",
    re.IGNORECASE,
)


def _parse_month_year_text(value):
    lowered = DataFormatter._strip_accents(value.lower())
    month = None
    for name, num in SPANISH_MONTHS.items():
        if re.search(r"\b" + name + r"\b", lowered):
            month = num
            break
    year = None
    for m in re.finditer(r"\d+", value):
        num = int(m.group())
        if num > 31 or (len(str(num)) == 4 and 1900 <= num <= 2100):
            year = num
            break
    if month is None or year is None:
        return None
    return f"{year:04d}-{month:02d}"


def normalize_for_compare(value):
    if not value:
        return ("empty", "")
    s = str(value).strip()
    full = DataFormatter.parse_date(s)
    if full:
        return ("full", full)
    month_year = _parse_month_year_text(s)
    if month_year:
        return ("monthyear", month_year)
    return ("other", DataFormatter._strip_accents(s.casefold()))


def _sort_key(value):
    full = DataFormatter.parse_date(value)
    if full:
        return datetime.strptime(full, "%d/%m/%Y")
    month_year = _parse_month_year_text(value)
    if month_year:
        return datetime.strptime(month_year + "-01", "%Y-%m-%d")
    return None


def _locate_section(text):
    m = _TIEMPOS_RE.search(text)
    if not m:
        return None
    start = m.start()
    end = text.find("\n1.5", start)
    if end == -1:
        end = min(len(text), start + 2000)
    return text[start:end]


def _read_pages(pdf_path, max_pages=6):
    with pdfplumber.open(pdf_path) as pdf:
        texts = []
        for page in pdf.pages[:max_pages]:
            texts.append(page.extract_text() or "")
            joined = "\n".join(texts)
            marker = _TIEMPOS_RE.search(joined)
            if marker and "\n1.5" in joined[marker.start():]:
                break
    return "\n".join(texts)


def extract_project_dates(pdf_path):
    text = _read_pages(pdf_path)
    section = _locate_section(text) or text[:8000]

    seen = {}
    for m in _DATE_TOKEN_RE.finditer(section):
        raw = re.sub(r"\s+", " ", m.group(0)).strip()
        key = _sort_key(raw)
        if key is not None:
            seen.setdefault(key, raw)

    if len(seen) < 2:
        return None

    items = sorted(seen.items())
    inicio_raw = items[0][1]
    fin_raw = items[-1][1]

    formatted = {
        "FechaInicio": DataFormatter.parse_date(inicio_raw, preserve_text=True),
        "FechaFin": DataFormatter.parse_date(fin_raw, preserve_text=True),
    }
    if not formatted["FechaInicio"] and not formatted["FechaFin"]:
        return None
    return formatted


def extract_project_code(pdf_path):
    code_re = re.compile(r"\b(P\d{1,2}[A-Z]+\d+)\b")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:4]:
            m = code_re.search(page.extract_text() or "")
            if m:
                return m.group(1)
    return None