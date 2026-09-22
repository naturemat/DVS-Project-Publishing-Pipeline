import re
import json
import os
import unicodedata
from datetime import datetime, date
from .column_mapper import ColumnMapper
from .proper_nouns import PROPER_NOUNS, ACRONYMS, TITLE_PREFIXES, MINOR_WORDS
from .proper_nouns import ACCENT_FIX


SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y.%m.%d",
    "%d/%m/%y",
    "%d-%m-%y",
)

_CARRERA_SEPARATORS_RE = re.compile(r"\s+-\s+|\s*,\s*|\s+Y\s+")

_LINK_PLANIFICACION_RE = re.compile(r"^https://drive\.google\.com/file/d/[A-Za-z0-9_-]+")


class DataFormatter:

    _carrera_facultad_norm = None

    @classmethod
    def _load_carrera_facultad(cls):
        if cls._carrera_facultad_norm is not None:
            return
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "carrera_facultad.json",
        )
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        cls._carrera_facultad_norm = {
            cls._strip_accents(str(key).upper()): str(value)
            for key, value in raw.items()
        }

    @classmethod
    def carrera_facultad(cls, value):
        if not value:
            return None
        cls._load_carrera_facultad()
        return cls._carrera_facultad_norm.get(cls._strip_accents(str(value).upper()))

    _carreras_norm = None
    _carreras_canonical = None

    @classmethod
    def _load_carreras(cls):
        if cls._carreras_norm is not None:
            return
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "carreras.json",
        )
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        cls._carreras_norm = {
            cls._strip_accents(str(name).upper()): str(name).upper()
            for name in raw
        }
        cls._carreras_canonical = set(cls._carreras_norm.values())

    @classmethod
    def _canonical_career(cls, value):
        cls._load_carreras()
        return cls._carreras_norm.get(cls._strip_accents(str(value).upper()))

    @classmethod
    def _find_career_chain(cls, text):
        cls._load_carreras()
        norm_text = cls._strip_accents(text.upper())
        matches = []
        for canon in cls._carreras_canonical:
            norm_career = cls._strip_accents(canon)
            start = 0
            while True:
                idx = norm_text.find(norm_career, start)
                if idx == -1:
                    break
                matches.append((idx, idx + len(norm_career), canon))
                start = idx + 1
        if not matches:
            return None
        matches.sort()
        best = None
        for m in matches:
            chain = [m]
            end = m[1]
            for nxt in matches:
                if nxt[0] < end:
                    continue
                gap = norm_text[end:nxt[0]]
                if gap and not re.fullmatch(r"\s*Y\s*|\s*-\s*|[\s,/-]*", gap):
                    break
                chain.append(nxt)
                end = nxt[1]
            if len(chain) >= 2 and chain[0][0] == 0 and end == len(norm_text):
                if best is None or len(chain) > len(best):
                    best = chain
        if best is None:
            return None
        return [m[2] for m in best]

    @classmethod
    def split_careers(cls, value):
        if not value:
            return value
        s = str(value).strip().upper()
        s = " ".join(s.split())
        canonical = cls._canonical_career(s)
        if canonical:
            return canonical
        s = cls.normalize_separators(s)
        s = " ".join(s.split())
        canonical = cls._canonical_career(s)
        if canonical:
            return canonical
        chain = cls._find_career_chain(s)
        if chain:
            return " ".join("•" + c for c in chain)
        if ", " in s:
            return " ".join("•" + p.strip() for p in s.split(", "))
        return s

    @classmethod
    def parse_date(cls, value, preserve_text=False):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        s = str(value).strip()
        if not s or s.lower() == "none":
            return None
        dt = cls._try_parse_date(s)
        if dt is not None:
            return dt.strftime("%d/%m/%Y")
        if preserve_text and cls._is_month_year_text(s):
            return s
        return None

    @classmethod
    def _is_month_year_text(cls, text):
        lowered = cls._strip_accents(text.lower())
        for name in SPANISH_MONTHS:
            if re.search(r"\b" + name + r"\b", lowered):
                has_year = any(
                    num > 31 or (len(str(num)) == 4 and 1900 <= num <= 2100)
                    for num in (int(m.group()) for m in re.finditer(r"\d+", text))
                )
                return has_year
        return False

    @classmethod
    def _first_day_month_year(cls, text):
        if not text:
            return None
        s = str(text).strip()
        if not cls._is_month_year_text(s):
            return None
        lowered = cls._strip_accents(s.lower())
        month = None
        for name, num in SPANISH_MONTHS.items():
            if re.search(r"\b" + name + r"\b", lowered):
                month = num
                break
        year = None
        for m in re.finditer(r"\d+", s):
            num = int(m.group())
            if num > 31 or (len(str(num)) == 4 and 1900 <= num <= 2100):
                year = num
                break
        if month is None or year is None:
            return None
        return cls._safe_date(cls._full_year(year), month, 1).strftime("%d/%m/%Y")

    @staticmethod
    def _strip_accents(text):
        normalized = unicodedata.normalize("NFD", text)
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    @staticmethod
    def _safe_date(year, month, day):
        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _full_year(value):
        if value < 100:
            return value + 2000 if value < 50 else value + 1900
        return value

    @classmethod
    def _try_parse_date(cls, text):
        cleaned = re.sub(r"\s+", " ", text.strip())
        if not cleaned:
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        dt = cls._parse_text_month(cleaned)
        if dt is not None:
            return dt
        return cls._parse_numeric(cleaned)

    @classmethod
    def _parse_text_month(cls, text):
        lowered = cls._strip_accents(text.lower())
        month = None
        for name, num in SPANISH_MONTHS.items():
            if re.search(r"\b" + name + r"\b", lowered):
                month = num
                break
        if month is None:
            return None
        numbers = [int(m.group()) for m in re.finditer(r"\d+", text)]
        year = None
        day = None
        for num in numbers:
            if year is None and (num > 31 or (len(str(num)) == 4 and 1900 <= num <= 2100)):
                year = num
            elif day is None and 1 <= num <= 31:
                day = num
        if year is None or day is None:
            return None
        return cls._safe_date(cls._full_year(year), month, day)

    @classmethod
    def _parse_numeric(cls, text):
        cleaned = re.sub(r"\s*([/\-.])\s*", r"\1", text).replace(" ", "")
        compact = re.match(r"^(\d{1,2})/(\d{2})(\d{4})$", cleaned)
        if compact:
            day, month, year = (int(g) for g in compact.groups())
            return cls._safe_date(year, month, day)
        parts = re.split(r"[/\-.]", cleaned)
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            return None
        a, b, c = (int(p) for p in parts)
        if a > 31 or len(parts[0]) == 4:
            dt = cls._safe_date(cls._full_year(a), b, c)
            if dt is not None:
                return dt
            return cls._safe_date(cls._full_year(a), c, b)
        dt = cls._safe_date(cls._full_year(c), b, a)
        if dt is not None:
            return dt
        return cls._safe_date(cls._full_year(c), a, b)

    @classmethod
    def title_case(cls, value):
        if not value:
            return value
        s = str(value).strip()
        if not s:
            return s
        words = s.split()
        result = []
        for i, word in enumerate(words):
            word_fixed = ACCENT_FIX.get(word.upper(), word)
            word_lower = word_fixed.lower()
            if i == 0:
                result.append(word_lower.capitalize())
            elif word_lower in MINOR_WORDS:
                result.append(word_lower)
            else:
                result.append(word_lower.capitalize())
        return " ".join(result)

    @classmethod
    def proyecto_case(cls, value):
        if not value:
            return value
        s = str(value).strip()
        if not s:
            return s

        tokens = re.findall(r"\w+|[^\w]", s)
        out = []
        sentence_start = True
        n = len(tokens)

        def next_word_upper(idx):
            for j in range(idx + 1, n):
                if tokens[j] and re.search(r"\w", tokens[j]):
                    return tokens[j].upper()
            return None

        for i, tok in enumerate(tokens):
            if not tok:
                continue
            if not re.search(r"\w", tok):
                out.append(tok)
                if tok in ".!?":
                    sentence_start = True
                elif tok == "¿" or tok == "¡":
                    sentence_start = True
                continue

            upper = ACCENT_FIX.get(tok.upper(), tok.upper())
            lower = upper.lower()
            nxt = next_word_upper(i)

            if upper in ACRONYMS:
                out.append(upper)
            elif upper in PROPER_NOUNS:
                out.append(lower.capitalize())
            elif upper in TITLE_PREFIXES and nxt in PROPER_NOUNS:
                out.append(lower.capitalize())
            elif sentence_start:
                out.append(lower.capitalize())
            elif upper in {w.upper() for w in MINOR_WORDS}:
                out.append(lower)
            else:
                out.append(lower)
            sentence_start = False

        return "".join(out)

    @staticmethod
    def normalize_separators(value):
        if not value:
            return value
        s = str(value).strip()
        if not s:
            return s
        placeholders = []

        def keep(m):
            placeholders.append(m.group(0))
            return f"\x00{len(placeholders) - 1}\x00"

        s = re.sub(r"\by/o\b", keep, s, flags=re.IGNORECASE)
        s = re.sub(r"\b\d+\s*/\s*\d+(?:\s*/\s*\d+)?\b", keep, s)
        s = re.sub(r"\s*/\s*", ", ", s)
        for idx, val in enumerate(placeholders):
            s = s.replace(f"\x00{idx}\x00", val.lower())
        s = re.sub(r",\s*,", ",", s)
        s = re.sub(r"\s*,\s*", ", ", s)
        s = re.sub(r"\s{2,}", " ", s)
        s = re.sub(r",\s*$", "", s)
        return s.strip()

    @staticmethod
    def normalize_territorio_separators(value):
        if not value:
            return value
        s = str(value).strip()
        if not s:
            return s
        placeholders = []

        def keep(m):
            placeholders.append(m.group(0))
            return f"\x00{len(placeholders) - 1}\x00"

        s = re.sub(r"\by/o\b", keep, s, flags=re.IGNORECASE)
        s = re.sub(r"\b\d+\s*/\s*\d+(?:\s*/\s*\d+)?\b", keep, s)
        s = re.sub(r"(?<=\d)\s*[-]\s*(?=\d)", keep, s)
        s = re.sub(r"\s*/\s*", ", ", s)
        s = re.sub(r"\s*&\s*", ", ", s)
        s = re.sub(r"\s*-\s*", ", ", s)
        s = re.sub(r"\s+y\s+", ", ", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*y\s+", ", ", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+y\s*$", ", ", s, flags=re.IGNORECASE)
        for idx, val in enumerate(placeholders):
            s = s.replace(f"\x00{idx}\x00", val.lower())
        s = re.sub(r",\s*,", ",", s)
        s = re.sub(r"\s*,\s*", ", ", s)
        s = re.sub(r"\s{2,}", " ", s)
        s = re.sub(r",\s*$", "", s)
        return s.strip()

    @staticmethod
    def extract_program_number(codigo):
        if not codigo:
            return None
        codigo = str(codigo).strip()
        idx = 0
        while idx < len(codigo) and codigo[idx] == 'P':
            idx += 1
        if idx == 0:
            return None
        num_str = ""
        while idx < len(codigo) and codigo[idx].isdigit():
            num_str += codigo[idx]
            idx += 1
        if num_str:
            return f"P{num_str}"
        return None

    @classmethod
    def format_row(cls, raw_row, col_map, programas, period):
        out = {}
        for field, src_col in col_map.items():
            if src_col is None:
                out[field] = None
            else:
                out[field] = raw_row.get(src_col)

        if out.get("Facultad"):
            out["Facultad"] = out["Facultad"].strip().upper() if isinstance(out["Facultad"], str) else str(out["Facultad"]).strip().upper()

        if out.get("Carrera"):
            out["Carrera"] = out["Carrera"].strip().upper() if isinstance(out["Carrera"], str) else str(out["Carrera"]).strip().upper()
            out["Carrera"] = cls.split_careers(out["Carrera"])

        if out.get("TipoProyecto"):
            val = str(out["TipoProyecto"]).strip().upper()
            out["TipoProyecto"] = re.sub(r"^PROYECTO\s+", "", val)

        if out.get("idCodigo"):
            out["idCodigo"] = str(out["idCodigo"]).strip().upper()

        if out.get("NombreProyecto"):
            out["NombreProyecto"] = cls.proyecto_case(cls.normalize_separators(out["NombreProyecto"]))

        if out.get("NombrePrograma"):
            out["NombrePrograma"] = cls.title_case(out["NombrePrograma"])

        if out.get("NombreCoordinador"):
            out["NombreCoordinador"] = cls.title_case(out["NombreCoordinador"])

        if out.get("Territorio"):
            out["Territorio"] = cls.title_case(cls.normalize_territorio_separators(out["Territorio"]))

        date_autocompleted = False
        for date_field in ["FechaInicio", "FechaFin"]:
            raw = out.get(date_field)
            parsed = cls.parse_date(raw, preserve_text=True)
            if parsed and not re.match(r"^\d{2}/\d{2}/\d{4}$", parsed):
                first_day = cls._first_day_month_year(raw)
                if first_day:
                    parsed = first_day
                    date_autocompleted = True
            out[date_field] = parsed
        out["Anio"] = ColumnMapper.extract_year_from_period(period)

        for link_field in ["LinkLevantamientoBase", "LinkJuridico", "LinkConvenio",
                           "LinkAprobacion", "LinkCronogramaActividades"]:
            out[link_field] = "N/A"

        lp = out.get("LinkPlanificacion")
        if lp:
            lp = lp.strip() if isinstance(lp, str) else str(lp).strip()
        out["LinkPlanificacion"] = lp if _LINK_PLANIFICACION_RE.match(lp or "") else "N/A"

        program_info_found = False
        if not out.get("NombrePrograma") and out.get("idCodigo"):
            pnum = cls.extract_program_number(out["idCodigo"])
            if pnum:
                for p in programas:
                    if p["code"] == pnum:
                        out["NombrePrograma"] = cls.title_case(p["name"])
                        if not out.get("NombreCoordinador"):
                            out["NombreCoordinador"] = cls.title_case(p["coordinador"])
                        program_info_found = True
                        break

        missing = []
        required_fields = ["Facultad", "Carrera", "NombreProyecto", "NombrePrograma",
                           "NombreCoordinador", "Territorio", "FechaInicio", "FechaFin", "idCodigo"]
        for field in required_fields:
            if not out.get(field):
                missing.append(field)
        for date_field in ["FechaInicio", "FechaFin"]:
            val = out.get(date_field)
            if val and not re.match(r"^\d{2}/\d{2}/\d{4}$", val):
                missing.append(date_field)

        out["_missing"] = missing
        out["_program_info_found"] = program_info_found
        out["_date_autocompleted"] = date_autocompleted

        return out