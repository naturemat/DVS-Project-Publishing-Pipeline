import re
import unittest

from modules.date_comparison.date_extractor import extract_project_career, extract_project_name

_INFO_SECTION = """1.2 INFORMACIÓN DEL PROYECTO
UNIDAD ACADEMICA EJECUTORA UCE
Facultades:
CIENCIAS AGRÍCOLAS
Carreras:
AGRONOMÍA
1ro Año
2. Correo electrónico de contacto:
Nombre del programa:
Fortalecimiento Integral
Coordinador del programa:
Ana López
Código del Proyecto:
P3AGR18
Construcción de un modelo de simulación
agroclimático para los cantones Cayambe
Pedro Moncayo.
Nombre del proyecto:
Fortalecimiento agrícola integral
"""


class DateExtractorTargetsTests(unittest.TestCase):

    def test_project_name_between_code_and_name_labels(self):
        name = extract_project_name("/does/not/exist.pdf", text=_INFO_SECTION)
        self.assertEqual(
            name,
            "Construcción de un modelo de simulación agroclimático para los cantones Cayambe Pedro Moncayo",
        )

    def test_project_career_after_carreras_label(self):
        career = extract_project_career("/does/not/exist.pdf", text=_INFO_SECTION)
        self.assertEqual(career, "AGRONOMÍA")

    def test_no_project_name_section(self):
        self.assertIsNone(extract_project_name("/does/not/exist.pdf", text="TIEMPOS DEL PROYECTO"))

    def test_no_career_section(self):
        self.assertIsNone(extract_project_career("/does/not/exist.pdf", text="1.2 INFORMACIÓN"))

    def test_career_carriage_returns_collapsed(self):
        text = _INFO_SECTION.replace("\n", "\r\n")
        self.assertEqual(
            extract_project_career("/does/not/exist.pdf", text=text), "AGRONOMÍA"
        )

    def test_name_with_values_before_labels(self):
        text = (
            "Nombre del programa:\n"
            "Fortalecimiento Integral\n"
            "P3AGR18\n"
            "Código del Proyecto:\n"
            "Construcción de un modelo de simulación agroclimático\n"
            "para los cantones Cayambe Pedro Moncayo.\n"
            "Nombre del proyecto:\n"
            "Objetivo general:\n"
        )
        self.assertEqual(
            extract_project_name("/does/not/exist.pdf", text=text),
            "Construcción de un modelo de simulación agroclimático para los cantones Cayambe Pedro Moncayo",
        )

    def test_career_nearest_to_row_code(self):
        multi = (
            "1.2 INFORMACIÓN DEL PROYECTO\n"
            "Código del Proyecto:\n"
            "P3ARQ01\n"
            "Primer proyecto\n"
            "Nombre del proyecto:\n"
            "Carreras:\n"
            "ARQUITECTURA\n"
            "1.2 INFORMACIÓN DEL PROYECTO\n"
            "Código del Proyecto:\n"
            "P3AGR41\n"
            "Segundo proyecto\n"
            "Nombre del proyecto:\n"
            "Carreras:\n"
            "AGRONOMÍA\n"
        )
        self.assertEqual(
            extract_project_career("/does/not/exist.pdf", text=multi, code="P3AGR41"),
            "AGRONOMÍA",
        )


if __name__ == "__main__":
    unittest.main()