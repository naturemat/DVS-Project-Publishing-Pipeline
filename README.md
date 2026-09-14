# Excel to DTICS - Data Extractor

Extracts project data from source Excel files in `Fuente_Datos/`, normalizes and formats every field, and writes it into a copy of the BD file (`BDVinculacionn 2024-2025.xlsx`) placed in the `output/` folder.

## Project Structure

```
Excel_to_dtics/
├── extract_data.py          # Main entry point (terminal menu + pipeline)
├── Programas.json           # Program codes (P1-P9) with name + coordinator
├── facultades.json          # Official faculty names (source of truth)
├── utils/
│   ├── __init__.py
│   ├── column_mapper.py     # Source column mappings per period
│   ├── data_formatter.py    # Field formatting and validation rules
│   ├── file_reader.py       # Excel file reader
│   ├── facultad_matcher.py  # Faculty normalization (facultades.json + aliases)
│   └── proper_nouns.py      # Proper nouns, acronyms, accent fixes (Spanish)
├── docs/
│   └── spanish-text-formatting.md   # Detailed rules of the text engine
├── Fuente_Datos/            # Source Excel files (real ones gitignored)
│   ├── .gitkeep
│   ├── EJEMPLO PERIODO 21-22.xlsx   # Example with invented data (committed)
│   ├── EJEMPLO PERIODO 22-23.xlsx   # Example with invented data (committed)
│   └── EJEMPLO PERIODO 27-28.xlsx   # Example with invented data (committed)
└── output/                  # Generated output (gitignored)
    ├── BDVinculacionn.xlsx  # Copy of base BD + analyzed period sheet
    └── missing_data_report.md
```

## Requirements

- Python 3.10+
- openpyxl (`pip install openpyxl`)

## How to Run (from scratch)

```bash
cd D:\UCE\PPP\Unidad_Comunicación\Excel_to_dtics
python -m venv venv
venv\Scripts\activate
pip install openpyxl
python extract_data.py
```

Then:

1. Place your source files in `Fuente_Datos/` (e.g., `PERIODO 25-25.xlsx`, `PERIODO 25-26.xlsx`, `PERIODO 26-26.xlsx`).
2. Run `python extract_data.py`.
3. Select a file from the menu (type the number and press Enter).
4. The script ensures `output/BDVinculacionn.xlsx` exists (copies the base file the first time, keeps previous data afterwards).
5. It creates or replaces only the sheet for the analyzed period (e.g., `2026-2026` from `PERIODO 26-26.xlsx`). If the sheet already exists, its data is overwritten in place - no duplicate sheets are ever created.
6. Rows are sorted alphabetically: first by `Facultad`, then by `NombreProyecto` within each faculty. Names starting with a special character (quotes, brackets, etc.) come first.
7. A missing-data report is written to `output/missing_data_report.md`.

## How It Works

The pipeline runs in five stages:

1. **Read** - `FileExtractor` opens the selected file from `Fuente_Datos/` and reads all data rows.
2. **Map** - `ColumnMapper` detects the period from the filename (`25-25`, `25-26`, `26-26`) and selects the correct source column positions for that file layout.
3. **Format** - `DataFormatter` normalizes every field: dates to `DD/MM/YYYY`, uppercase fields, sentence case, proper nouns, tildes.
4. **Enrich** - `FacultadMatcher` matches the source faculty to the official names in `facultades.json`. If `NombrePrograma`/`NombreCoordinador` are missing, `Programas.json` is queried using the program number extracted from `idCodigo` (e.g., `P3AGR18` -> `P3`).
5. **Write** - `write_to_output` writes into the existing period sheet (or creates it only if absent), sorts rows by `Facultad` then `NombreProyecto`, applies the base sheet formatting, colors rows, filters, and saves.

### Example files

`Fuente_Datos/` ships with three example workbooks (`EJEMPLO PERIODO 21-22.xlsx`, `EJEMPLO PERIODO 22-23.xlsx`, `EJEMPLO PERIODO 27-28.xlsx`) filled with **invented data**. They exist to show the exact input layout the program expects (title row, header row, data from row 3, `NRO` in column 1) and are safe to commit - they contain no real information. You can run any of them from the menu to test the tool without touching real data.

### Date parsing

`FechaInicio` and `FechaFin` are parsed robustly. A value is written as `DD/MM/YYYY` only when it is a real calendar date; anything else is left blank (and the row is reported as missing that date). Supported inputs include:

| Input | Output |
|-------|--------|
| Native Excel date | `01/04/2025` |
| `2025-04-01` / `2025-04-01 00:00:00` | `01/04/2025` |
| `01/04/2025`, `1-4-2025`, `2025.04.01` | `01/04/2025` |
| `12 Septiembre 2026`, `01 de febrero de 2025`, `1 de ABRIL DEL 2027` | `12/09/2026`, `01/02/2025`, `01/04/2027` |
| `Octubre 1/2024`, `Septiembre 30/2026`, `octubre 10,2023` | `01/10/2024`, `30/09/2026`, `10/10/2023` |
| US order `10/31/2026` (auto-detected when day > 12) | `31/10/2026` |
| `FALTA`, `NO EXISTE`, `FECHA QUE INICIO EL PROYECTO`, `periodo 24-25` | *(blank)* |
| Invalid dates such as `31/02/2026` | *(blank)* |
| Partial dates without a day, e.g. `marzo de 2025` | *(blank)* |

Invalid or incomplete dates are never copied as text. They leave the cell empty, which correctly marks the row as missing that date.

### Link fields

All link fields (`LinkLevantamientoBase`, `LinkJuridico`, `LinkConvenio`, `LinkAprobacion`, `LinkPlanificacion`, `LinkCronogramaActividades`) are always written as `N/A`. They are never searched, never validated, and never trigger a missing-data mark.

### Location separators

When a field lists multiple locations separated by `/` (e.g., `Quito / Guaranda / Echeandía`), the slashes are replaced by commas so every location is listed separately: `Quito, Guaranda, Echeandía`. This applies to `Territorio` and `NombreProyecto`. The idiom `y/o` is preserved, and date-like patterns (`20/05/2025`) are never split.

### Sheet formatting

Every generated period sheet replicates the base BD format exactly:

- Font: Aptos Narrow 10 pt (header bold, 10 pt)
- Borders: thin black line on every cell, identical to the `2024-2025` sheet
- Freeze panes `A2`, autofilter `A1:R1`, column widths and row heights copied from the base sheet

## Output Format

| Field | Format | Example |
|-------|--------|---------|
| idDocumento | Sequential number | 1 |
| Facultad | UPPERCASE (matched to facultades.json) | CIENCIAS AGRÍCOLAS |
| Carrera | UPPERCASE | AGRONOMÍA |
| TipoProyecto | UPPERCASE | VIGENTE |
| idCodigo | UPPERCASE | P3AGR18 |
| NombreProyecto | Sentence case (proper nouns preserved) | Primera vivienda ecológica en la parroquia La Esperanza para un número limitado de habitantes |
| NombrePrograma | Title case | P3. Hábitat, Desarrollo Local |
| NombreCoordinador | Title case | Jorge Antonio Piedra Rosales |
| Territorio | Title case, locations separated by commas | Quito, Guaranda, Echeandía |
| FechaInicio | DD/MM/YYYY | 01/04/2025 |
| FechaFin | DD/MM/YYYY | 01/04/2026 |
| Anio | Year derived from the period | 2025 |
| Link* | Always N/A | N/A |

## Spanish Text Formatting Engine

The most delicate part of the pipeline is producing correct Spanish text. `NombreProyecto` must NOT be all-caps. It is written in **sentence case**:

> `PRIMERA VIVIENDA ECOLÓGICA EN LA PARROQUIA LA ESPERANZA PARA UN NUMERO LIMITADO DE HABITANTES`

becomes

> `Primera vivienda ecológica en la parroquia La Esperanza para un número limitado de habitantes`

The engine decides case per word using four lists defined in `utils/proper_nouns.py`:

| List | Purpose | Example |
|------|---------|---------|
| `PROPER_NOUNS` | Proper nouns that stay capitalized in the middle of a sentence | `QUITO` -> `Quito`, `ATUCUCHO` -> `Atucucho` |
| `ACRONYMS` | Abbreviations that stay fully uppercase everywhere | `DM` -> `DM`, `UCE`, `CHQ` |
| `TITLE_PREFIXES` | Articles that are capitalized when they start a proper phrase (lookahead to `PROPER_NOUNS`) | `LA ESPERANZA` -> `La Esperanza`, `SAN PEDRO` -> `San Pedro` |
| `MINOR_WORDS` | Function words always written lowercase | `de`, `del`, `la`, `y`, `para` |

Rules applied in order per word:

1. If the word is an acronym -> keep uppercase.
2. If the word is a proper noun -> capitalize the first letter only (`QUITO` -> `Quito`).
3. If the word is a title prefix and the NEXT word is a proper noun -> capitalize it (`LA` before `ESPERANZA`).
4. If the word starts a sentence (or the whole text) -> capitalize the first letter; everything else lowercase.
5. If the word is a minor word -> lowercase.
6. Otherwise -> lowercase.

Sentence boundaries are detected after `.`, `!`, `?`, so the text after a period is capitalized again even mid-string.

### Accents (tildes)

Source files frequently omit tildes (`NUMERO`, `GESTION`, `EDUCACION`). The `ACCENT_FIX` dictionary in `utils/proper_nouns.py` restores the correct accent for the most common words before case is applied, following RAE rules:

| Without accent | With accent |
|----------------|-------------|
| NUMERO | NÚMERO |
| GESTION | GESTIÓN |
| AGRICOLA | AGRÍCOLA |
| TURISTICO | TURÍSTICO |
| CLIMATICO | CLIMÁTICO |

Accents already present in the source (`ECOLÓGICA`, `CATÁN`, `RUMIÑAHUI`) are preserved automatically because only case is changed, never the base letters.

> **Full rulebook:** see [`docs/spanish-text-formatting.md`](docs/spanish-text-formatting.md).

## Faculty Matching

The field `Facultad` must always match one of the official names in `facultades.json`. The matcher works in this order:

1. Exact match (after uppercasing and collapsing spaces) - `ARQUITECTURA Y URBANISMO`.
2. Alias map (`utils/facultad_matcher.py` -> `ALIAS_MAP`) - `ADMINISTRACION` -> `CIENCIAS ADMINISTRATIVAS`, `AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`.
3. Accent-insensitive exact match - `CIENCIAS AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`.
4. Partial match - `AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`.

If no match is found the source value is kept as-is (and the row is reported as missing `Facultad`).

## Programas.json Lookup

When `NombrePrograma` (and optionally `NombreCoordinador`) is missing and `idCodigo` is present, the program number is extracted from the code prefix (`P3AGR18` -> `P3`) and searched in `Programas.json`:

```json
{ "code": "P3", "name": "Desarrollo Sostenible...", "coordinador": "Jorge Antonio Piedra Rosales" }
```

Rows completed this way are marked **orange**.

## Color Coding

- **Red** - the row is missing one or more required fields (`Facultad`, `Carrera`, `NombreProyecto`, `NombrePrograma`, `NombreCoordinador`, `Territorio`, `FechaInicio`, `FechaFin`, `idCodigo`). Missing URLs never cause a red mark.
- **Orange** - the row was completed using the `Programas.json` lookup.

## Report

`output/missing_data_report.md` lists every row with missing data: source row number, code, project name, and the list of missing fields. The report is only generated when at least one row is missing data.

## Config Files Reference

| File | Purpose |
|------|---------|
| `Programas.json` | Program codes P1-P9 with official name and coordinator |
| `facultades.json` | Official list of university faculties |
| `utils/proper_nouns.py` | Spanish proper nouns, acronyms, minor words, accent fixes |

## Extending

- **New period** - add a column map in `utils/column_mapper.py` (`MAP_XX_XX`), a `PERIOD_SHEET_MAP` entry, a `detect_period` branch, a `get_column_map` branch, and a `extract_year_from_period` entry. The example periods `21-22`, `22-23`, `27-28` use the shared `EXAMPLE_LAYOUT`.
- **New proper noun** - add the uppercase word to `PROPER_NOUNS` in `utils/proper_nouns.py`.
- **Missing accent fix** - add the word to `ACCENT_FIX` in `utils/proper_nouns.py`.
- **New faculty alias** - add it to `ALIAS_MAP` in `utils/facultad_matcher.py`.
- **New date format** - add the pattern to `DATE_FORMATS` or the month/numeric helpers in `utils/data_formatter.py`.