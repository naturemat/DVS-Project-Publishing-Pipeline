import json
import os
import re


class FacultadMatcher:

    ALIAS_MAP = {
        "ADMINISTRACION": "CIENCIAS ADMINISTRATIVAS",
        "ADMINISTACION": "CIENCIAS ADMINISTRATIVAS",
        "CIENCIAS ADMINISTRATIVAS": "CIENCIAS ADMINISTRATIVAS",
        "AGRICOLA": "CIENCIAS AGRÍCOLAS",
        "AGRICOLAS": "CIENCIAS AGRÍCOLAS",
        "CIENCIAS AGRICOLAS": "CIENCIAS AGRÍCOLAS",
        "BIOLOGIA": "CIENCIAS BIOLÓGICAS",
        "BIOLOGICAS": "CIENCIAS BIOLÓGICAS",
        "CIENCIAS BIOLOGICAS": "CIENCIAS BIOLÓGICAS",
        "ECONOMIA": "CIENCIAS ECONÓMICAS",
        "ECONOMICAS": "CIENCIAS ECONÓMICAS",
        "CIENCIAS ECONOMICAS": "CIENCIAS ECONÓMICAS",
        "MEDICINA": "CIENCIAS MEDICAS",
        "CIENCIAS MEDICAS": "CIENCIAS MEDICAS",
        "PSICOLOGIA": "CIENCIAS PSICOLÓGICAS",
        "PSICOLOGICAS": "CIENCIAS PSICOLÓGICAS",
        "CIENCIAS PSICOLOGICAS": "CIENCIAS PSICOLÓGICAS",
        "QUIMICA": "CIENCIAS QUÍMICAS",
        "QUIMICAS": "CIENCIAS QUÍMICAS",
        "CIENCIAS QUIMICAS": "CIENCIAS QUÍMICAS",
        "SOCIALES": "CIENCIAS SOCIALES Y HUMANAS",
        "CIENCIAS SOCIALES": "CIENCIAS SOCIALES Y HUMANAS",
        "COMUNICACION": "COMUNICACIÓN SOCIAL",
        "COMUNICACION SOCIAL": "COMUNICACIÓN SOCIAL",
        "CULTURA FISICA": "CULTURA FÍSICA",
        "FISICA": "CULTURA FÍSICA",
        "FILOSOFIA": "FILOSOFÍA, LETRAS Y CIENCIAS DE LA EDUCACIÓN",
        "EDUCACION": "FILOSOFÍA, LETRAS Y CIENCIAS DE LA EDUCACIÓN",
        "GEOLOGIA": "INGENIERÍA EN GEOLOGÍA, MINAS PETRÓLEOS Y AMBIENTAL",
        "GEOLOGIA MINAS": "INGENIERÍA EN GEOLOGÍA, MINAS PETRÓLEOS Y AMBIENTAL",
        "INGENIERIA QUIMICA": "INGENIERÍA QUÍMICA",
        "QUIMICA INGENIERIA": "INGENIERÍA QUÍMICA",
        "INGENIERIA APLICADAS": "INGENIERÍA Y CIENCIAS APLICADAS",
        "JURISPRUDENCIA": "JURISPRUDENCIA, CIENCIAS POLÍTICAS Y SOCIALES",
        "DERECHO": "JURISPRUDENCIA, CIENCIAS POLÍTICAS Y SOCIALES",
        "VETERINARIA": "MEDICINA VETERINARIA Y ZOOTECNIA",
        "ZOOTECNIA": "MEDICINA VETERINARIA Y ZOOTECNIA",
        "ODONTOLOGIA": "ODONTOLOGÍA",
        "FIGEMPA": "INGENIERÍA EN GEOLOGÍA, MINAS PETRÓLEOS Y AMBIENTAL",
        "FACSO": "COMUNICACIÓN SOCIAL",
        "DISCAPACIDAD": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        "CIENCIAS DE LA DISCAPACIDAD": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        "ATENCION PREHOSPITALARIA": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        "ATENCION PREHOSPITALARIA Y DESASTRES": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        "CIENCIAS DE LA DISCAPACIDAD, ATENCION PREHOSPITALARIA Y DESASTRES": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        "CIENCIAS DE LA DISCAPACIDAD, ATENCION PRE HOSPITALARIA Y DESASTRES": "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
    }

    def __init__(self, json_path=None):
        if json_path is None:
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "facultades.json"
            )
        self.valid_facultades = self._load_facultades(json_path)

    def _load_facultades(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [item["facultad"].upper() for item in data]

    def normalize(self, raw_facultad):
        if not raw_facultad:
            return None
        cleaned = raw_facultad.strip().upper()
        cleaned = " ".join(cleaned.split())
        cleaned = re.sub(r"^\W+|\W+$", "", cleaned)

        if cleaned in self.ALIAS_MAP:
            return self.ALIAS_MAP[cleaned]

        for valid in self.valid_facultades:
            if cleaned == valid:
                return valid

        for valid in self.valid_facultades:
            if self._match_exact_length(cleaned, valid):
                return valid

        for valid in self.valid_facultades:
            if self._match_partial(cleaned, valid):
                return valid

        return cleaned

    def _remove_accents(self, text):
        accent_map = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'Ñ': 'N', 'Ü': 'U',
        }
        for k, v in accent_map.items():
            text = text.replace(k, v)
        return text

    def _match_exact_length(self, cleaned, valid):
        clean_no_accents = self._remove_accents(cleaned)
        valid_no_accents = self._remove_accents(valid)
        return clean_no_accents == valid_no_accents

    def _match_partial(self, cleaned, valid):
        clean_no_accents = self._remove_accents(cleaned)
        valid_no_accents = self._remove_accents(valid)
        if len(clean_no_accents) < 4:
            return False
        return clean_no_accents in valid_no_accents or valid_no_accents in clean_no_accents
