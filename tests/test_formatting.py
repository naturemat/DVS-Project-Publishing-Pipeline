import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_formatter import DataFormatter
from utils.facultad_matcher import FacultadMatcher


class DateParsingTests(unittest.TestCase):

    def test_native_excel_date(self):
        self.assertEqual(DataFormatter.parse_date(datetime(2026, 4, 1)), "01/04/2026")

    def test_iso_date(self):
        self.assertEqual(DataFormatter.parse_date("2025-04-01"), "01/04/2025")

    def test_slash_date(self):
        self.assertEqual(DataFormatter.parse_date("01/04/2025"), "01/04/2025")

    def test_spanish_text_date(self):
        self.assertEqual(DataFormatter.parse_date("12 Septiembre 2026"), "12/09/2026")

    def test_invalid_date_is_blank(self):
        self.assertIsNone(DataFormatter.parse_date("FALTA"))

    def test_unparseable_text_is_blank(self):
        self.assertIsNone(DataFormatter.parse_date("periodo 24-25"))


class CareerTests(unittest.TestCase):

    def test_canonical_accent(self):
        self.assertEqual(DataFormatter.split_careers("AGRONOMIA"), "AGRONOMÍA")

    def test_combined_single_kept_whole(self):
        self.assertEqual(DataFormatter.split_careers("BIOQUIMICA Y FARMACIA"), "BIOQUÍMICA Y FARMACIA")

    def test_multi_career_keeps_every_part(self):
        result = DataFormatter.split_careers("TURISMO - INGENIERÍA AGRONÓMICA")
        self.assertIn("TURISMO", result)
        self.assertIn("INGENIERÍA AGRONÓMICA", result)


class FacultyTests(unittest.TestCase):

    def setUp(self):
        self.matcher = FacultadMatcher()

    def test_alias(self):
        self.assertEqual(self.matcher.normalize("ADMINISTRACION"), "CIENCIAS ADMINISTRATIVAS")

    def test_accent_insensitive_match(self):
        self.assertEqual(self.matcher.normalize("CIENCIAS AGRICOLAS"), "CIENCIAS AGRÍCOLAS")

    def test_unknown_keeps_source(self):
        self.assertEqual(self.matcher.normalize("INVENTADA"), "INVENTADA")

    def test_new_discapacidad_faculty_matches(self):
        self.assertEqual(
            self.matcher.normalize("CIENCIAS DE LA DISCAPACIDAD, ATENCION PREHOSPITALARIA Y DESASTRES"),
            "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        )

    def test_discapacidad_faculty_alias(self):
        self.assertEqual(
            self.matcher.normalize("DISCAPACIDAD"),
            "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES",
        )


class CareerToFacultyOverrideTests(unittest.TestCase):

    def test_discapacidad_careers_map_to_faculty(self):
        faculty = "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES"
        for career in ["ATENCIÓN PREHOSPITALARIA", "FISIOTERAPIA", "FONOAUDIOLOGÍA", "TERAPIA OCUPACIONAL"]:
            self.assertEqual(DataFormatter.carrera_facultad(career), faculty)
        self.assertEqual(DataFormatter.carrera_facultad("fisioterapia"), faculty)

    def test_variant_with_space_in_prehospitalaria(self):
        faculty = "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES"
        self.assertEqual(DataFormatter.carrera_facultad("ATENCION PRE HOSPITALARIA"), faculty)
        self.assertEqual(DataFormatter.carrera_facultad("ATENCIÓN PREHOSPITALARIA Y DESASTRES"), faculty)

    def test_multi_career_resolves_when_all_same_faculty(self):
        faculty = "CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES"
        multi = DataFormatter.split_careers("FISIOTERAPIA Y TERAPIA OCUPACIONAL")
        self.assertEqual(DataFormatter.carrera_facultad(multi), faculty)

    def test_mixed_faculties_do_not_collapse(self):
        multi = DataFormatter.split_careers("AGRONOMÍA Y FISIOTERAPIA")
        self.assertIsNone(DataFormatter.carrera_facultad(multi))


class FieldFormattingTests(unittest.TestCase):

    def setUp(self):
        self.col_map = {
            "Facultad": 2,
            "Carrera": 3,
            "NombreProyecto": 4,
            "TipoProyecto": 5,
            "NombrePrograma": 7,
            "NombreCoordinador": 8,
            "Territorio": 9,
            "FechaInicio": 10,
            "FechaFin": 11,
            "LinkLevantamientoBase": 12,
            "LinkJuridico": 13,
            "LinkConvenio": 14,
            "LinkAprobacion": 15,
            "LinkPlanificacion": 16,
            "LinkCronogramaActividades": 17,
            "idCodigo": 6,
        }

    def _raw_row(self):
        values = {
            "Facultad": "CIENCIAS AGRICOLAS",
            "Carrera": "AGRONOMIA",
            "NombreProyecto": "PRIMERA VIVIENDA ECOLOGICA EN LA ESPERANZA",
            "TipoProyecto": "NUEVO",
            "idCodigo": "p3agr18",
            "NombrePrograma": "",
            "NombreCoordinador": "",
            "Territorio": "QUITO / GUARANDA",
            "FechaInicio": "01/04/2025",
            "FechaFin": "01/04/2026",
            "LinkPlanificacion": "https://drive.google.com/file/d/abc123/view",
            "LinkLevantamientoBase": "",
            "LinkJuridico": "",
            "LinkConvenio": "",
            "LinkAprobacion": "",
            "LinkCronogramaActividades": "",
        }
        row = {self.col_map[field]: value for field, value in values.items()}
        row["_row_idx"] = 3
        return row

    def _format(self):
        row = self._raw_row()
        return DataFormatter.format_row(row, self.col_map, [], "25-25")

    def test_id_codigo_uppercased(self):
        self.assertEqual(self._format()["idCodigo"], "P3AGR18")

    def test_carrera_canonicalized(self):
        self.assertEqual(self._format()["Carrera"], "AGRONOMÍA")

    def test_dates_normalized(self):
        out = self._format()
        self.assertEqual(out["FechaInicio"], "01/04/2025")
        self.assertEqual(out["FechaFin"], "01/04/2026")

    def test_anio_derived_from_fecha_fin(self):
        out = self._format()
        self.assertEqual(out["Anio"], "2026")

    def test_anio_falls_back_to_period_when_no_fecha_fin(self):
        row = self._raw_row()
        row[self.col_map["FechaFin"]] = "N/A"
        out = DataFormatter.format_row(row, self.col_map, [], "25-25")
        self.assertEqual(out["Anio"], "2025")

    def test_valid_link_kept(self):
        self.assertEqual(self._format()["LinkPlanificacion"], "https://drive.google.com/file/d/abc123/view")

    def test_invalid_link_becomes_na(self):
        row = self._raw_row()
        row[self.col_map["LinkPlanificacion"]] = "PROYECTO.pdf"
        self.assertEqual(DataFormatter.format_row(row, self.col_map, [], "25-25")["LinkPlanificacion"], "N/A")

    def test_other_links_always_na(self):
        out = self._format()
        for field in ["LinkLevantamientoBase", "LinkJuridico", "LinkConvenio",
                      "LinkAprobacion", "LinkCronogramaActividades"]:
            self.assertEqual(out[field], "N/A")


if __name__ == "__main__":
    unittest.main()