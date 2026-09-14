import re
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


class DataFormatter:

    @classmethod
    def parse_date(cls, value):
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
        if dt is None:
            return None
        return dt.strftime("%d/%m/%Y")

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

        if out.get("TipoProyecto"):
            val = str(out["TipoProyecto"]).strip().upper()
            out["TipoProyecto"] = val

        if out.get("idCodigo"):
            out["idCodigo"] = str(out["idCodigo"]).strip().upper()

        if out.get("NombreProyecto"):
            out["NombreProyecto"] = cls.proyecto_case(cls.normalize_separators(out["NombreProyecto"]))

        if out.get("NombrePrograma"):
            out["NombrePrograma"] = cls.title_case(out["NombrePrograma"])

        if out.get("NombreCoordinador"):
            out["NombreCoordinador"] = cls.title_case(out["NombreCoordinador"])

        if out.get("Territorio"):
            out["Territorio"] = cls.title_case(cls.normalize_separators(out["Territorio"]))

        out["FechaInicio"] = cls.parse_date(out.get("FechaInicio"))
        out["FechaFin"] = cls.parse_date(out.get("FechaFin"))
        out["Anio"] = ColumnMapper.extract_year_from_period(period)

        for link_field in ["LinkLevantamientoBase", "LinkJuridico", "LinkConvenio",
                           "LinkAprobacion", "LinkPlanificacion", "LinkCronogramaActividades"]:
            out[link_field] = "N/A"

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

        out["_missing"] = missing
        out["_program_info_found"] = program_info_found

        return out