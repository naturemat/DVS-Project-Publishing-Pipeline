import re
from datetime import datetime
from .column_mapper import ColumnMapper
from .proper_nouns import PROPER_NOUNS, ACRONYMS, TITLE_PREFIXES, MINOR_WORDS
from .proper_nouns import ACCENT_FIX


class DataFormatter:

    @staticmethod
    def parse_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        s = str(value).strip()
        if not s or s == "None":
            return None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y.%m.%d"]:
            try:
                dt = datetime.strptime(s.split()[0] if " " in s else s, fmt.split()[0])
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue
        return s

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