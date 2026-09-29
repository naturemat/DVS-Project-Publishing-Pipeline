class ColumnMapper:

    MAP_25_25 = {
        "Facultad": 2,
        "Carrera": 3,
        "NombreProyecto": 4,
        "TipoProyecto": 5,
        "NombrePrograma": 7,
        "NombreCoordinador": 8,
        "Territorio": 9,
        "FechaInicio": 10,
        "FechaFin": 11,
        "LinkLevantamientoBase": None,
        "LinkJuridico": 19,
        "LinkConvenio": 16,
        "LinkAprobacion": 13,
        "LinkPlanificacion": 20,
        "LinkCronogramaActividades": 22,
        "idCodigo": 6,
    }

    MAP_25_26 = {
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
        "LinkJuridico": 20,
        "LinkConvenio": 16,
        "LinkAprobacion": 13,
        "LinkPlanificacion": 22,
        "LinkCronogramaActividades": 24,
        "idCodigo": 6,
    }

    MAP_26_26 = {
        "Facultad": 4,
        "Carrera": 5,
        "NombreProyecto": 2,
        "TipoProyecto": 7,
        "NombrePrograma": 13,
        "NombreCoordinador": 14,
        "Territorio": 15,
        "FechaInicio": 8,
        "FechaFin": 9,
        "LinkLevantamientoBase": 10,
        "LinkJuridico": 12,
        "LinkConvenio": 11,
        "LinkAprobacion": 18,
        "LinkPlanificacion": 19,
        "LinkCronogramaActividades": 21,
        "idCodigo": 3,
    }

    PERIOD_SHEET_MAP = {
        "25-25": "2025-2025",
        "25-26": "2025-2026",
        "26-26": "2026-2026",
        "21-22": "2021-2022",
        "22-23": "2022-2023",
        "27-28": "2027-2028",
    }

    EXAMPLE_LAYOUT = {
        "Facultad": 2,
        "Carrera": 3,
        "NombreProyecto": 4,
        "TipoProyecto": 5,
        "idCodigo": 6,
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
    }

    OUTPUT_COLUMNS = [
        "idDocumento", "Facultad", "Carrera", "TipoProyecto", "NombreProyecto",
        "NombrePrograma", "NombreCoordinador", "Territorio", "FechaInicio",
        "FechaFin", "Anio", "LinkLevantamientoBase", "LinkJuridico",
        "LinkConvenio", "LinkAprobacion", "LinkPlanificacion",
        "LinkCronogramaActividades", "idCodigo"
    ]

    @classmethod
    def detect_period(cls, filename):
        fname = filename.upper()
        if "25-25" in fname:
            return "25-25"
        elif "25-26" in fname:
            return "25-26"
        elif "26-26" in fname:
            return "26-26"
        elif "21-22" in fname:
            return "21-22"
        elif "22-23" in fname:
            return "22-23"
        elif "27-28" in fname:
            return "27-28"
        return None

    @classmethod
    def get_column_map(cls, filename):
        period = cls.detect_period(filename)
        if period == "25-25":
            return cls.MAP_25_25
        elif period == "25-26":
            return cls.MAP_25_26
        elif period == "26-26":
            return cls.MAP_26_26
        elif period in ("21-22", "22-23", "27-28"):
            return cls.EXAMPLE_LAYOUT
        return None

    @classmethod
    def get_sheet_name(cls, period):
        return cls.PERIOD_SHEET_MAP.get(period)

    @classmethod
    def extract_year_from_period(cls, period):
        period_map = {
            "25-25": "2025",
            "25-26": "2026",
            "26-26": "2026",
            "21-22": "2022",
            "22-23": "2023",
            "27-28": "2028",
        }
        return period_map.get(period, None)
