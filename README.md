# Excel to DTICS - Data Extractor

Extracts project data from source Excel files in `Fuente_Datos/`, normalizes and formats every field, and writes it into a copy of the BD file (`BDVinculacionn 2024-2025.xlsx`) placed in the `output/` folder.

## Project Structure

```
Excel_to_dtics/
├── extract_data.py          # Main entry point (terminal menu + pipeline)
├── Programas.json           # Program codes (P1-P9) with name + coordinator
├── facultades.json          # Official faculty names (source of truth)
├── carreras.json            # Known career names (canonical spelling + combined careers)
├── utils/
│   ├── __init__.py
│   ├── column_mapper.py     # Source column mappings per period
│   ├── data_formatter.py    # Field formatting, date parsing, career logic
│   ├── file_reader.py       # Excel file reader
│   ├── facultad_matcher.py  # Faculty normalization (facultades.json + aliases)
│   └── proper_nouns.py      # Proper nouns, acronyms, accent fixes (Spanish)
├── docs/
│   ├── spanish-text-formatting.md   # Detailed rules of the text engine
│   └── career-normalization.md      # Career splitting + canonical naming rules
├── Fuente_Datos/            # Source Excel files (real ones gitignored)
│   ├── .gitkeep
│   ├── EJEMPLO PERIODO 21-22.xlsx   # Example with invented data (committed)
│   ├── EJEMPLO PERIODO 22-23.xlsx   # Example with invented data (committed)
│   └── EJEMPLO PERIODO 27-28.xlsx   # Example with invented data (committed)
├── scripts/
│   └── semver.py            # Next semantic version from conventional commits
├── tests/
│   ├── test_formatting.py   # Unit tests (dates, careers, faculties, fields)
│   └── test_integration.py  # End-to-end pipeline on example workbooks
├── .github/
│   └── workflows/
│       ├── ci.yml           # Validation + integration (dev/production environments)
│       └── release.yml      # Semver tagging on main
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
3. **Format** - `DataFormatter` normalizes every field: dates to `DD/MM/YYYY` (or kept as text when only month+year is given), uppercase fields, sentence case, proper nouns, tildes, plus career canonical naming and multi-career splitting.
4. **Enrich** - `FacultadMatcher` matches the source faculty to the official names in `facultades.json`. If `NombrePrograma`/`NombreCoordinador` are missing, `Programas.json` is queried using the program number extracted from `idCodigo` (e.g., `P3AGR18` -> `P3`). If the career maps to a definitive faculty (see `CARRERA_FACULTAD_OVERRIDE`), the faculty is set from the career.
5. **Write** - `write_to_output` writes into the existing period sheet (or creates it only if absent), sorts rows by `Facultad` then `NombreProyecto`, applies the base sheet formatting, colors rows, filters, and saves.

### Example files

`Fuente_Datos/` ships with three example workbooks (`EJEMPLO PERIODO 21-22.xlsx`, `EJEMPLO PERIODO 22-23.xlsx`, `EJEMPLO PERIODO 27-28.xlsx`) filled with **invented data**. They exist to show the exact input layout the program expects (title row, header row, data from row 3, `NRO` in column 1) and are safe to commit - they contain no real information. You can run any of them from the menu to test the tool without touching real data.

### Date parsing

`FechaInicio` and `FechaFin` are parsed robustly. A value is written as `DD/MM/YYYY` only when it is a real calendar date. Supported inputs include:

| Input | Output |
|-------|--------|
| Native Excel date | `01/04/2025` |
| `2025-04-01` / `2025-04-01 00:00:00` | `01/04/2025` |
| `01/04/2025`, `1-4-2025`, `2025.04.01` | `01/04/2025` |
| `12 Septiembre 2026`, `01 de febrero de 2025`, `1 de ABRIL DEL 2027` | `12/09/2026`, `01/02/2025`, `01/04/2027` |
| `Octubre 1/2024`, `Septiembre 30/2026`, `octubre 10,2023` | `01/10/2024`, `30/09/2026`, `10/10/2023` |
| US order `10/31/2026` (auto-detected when day > 12) | `31/10/2026` |
| Month + year only, e.g. `marzo de 2025`, `ABRIL DEL 2025` | *(original text kept, row marked RED)* |
| `FALTA`, `NO EXISTE`, `FECHA QUE INICIO EL PROYECTO`, `periodo 24-25` | *(blank)* |
| Invalid dates such as `31/02/2026` | *(blank)* |

Rules:

- A **complete** calendar date (day + month + year) becomes `DD/MM/YYYY`.
- A **partial** date with a month and a year but no day (`marzo de 2025`, `Septiembre del 2025`) is kept **as the original text** in the cell so the information is not lost, and the row is marked **red** because the exact date is still missing.
- Unparseable text (`periodo 24-25`, `FALTA`, etc.) leaves the cell **empty**; the row is marked red as missing that date.

### Link fields

Most link fields are always written as `N/A`. They are never searched, never validated, and never trigger a missing-data mark.

- `LinkPlanificacion` receives the URL from the source column `DISEÑO DEL PROYECTO` and is written as a **clickable hyperlink** (Aptos Narrow 10 pt, blue, underlined). Only valid Google Drive **file** links matching `https://drive.google.com/file/d/<id>...` are kept; all other values (empty, filenames like `PROYECTO.pdf`, `FALTA`, folder links, or any non-URL text) are written as `N/A`. This field never triggers a missing-data mark regardless of value. Every row in this column contains either a clickable URL or `N/A`; it is never left blank.
- `LinkLevantamientoBase`, `LinkJuridico`, `LinkConvenio`, `LinkAprobacion`, `LinkCronogramaActividades` are always `N/A`.

### Location separators

When a field lists multiple locations separated by `/` (e.g., `Quito / Guaranda / Echeandía`), the slashes are replaced by commas so every location is listed separately: `Quito, Guaranda, Echeandía`. This applies to `Territorio` and `NombreProyecto`. The idiom `y/o` is preserved, and date-like patterns (`20/05/2025`) are never split.

### Career normalization

The `Carrera` field is written in UPPERCASE, but it is first normalized against the reference list in `carreras.json`:

1. **Canonical spelling** - source variants are rewritten to the canonical (accented) form. `AGRONOMIA` -> `AGRONOMÍA`, `BIOQUIMICA Y FARMACIA` -> `BIOQUÍMICA Y FARMACIA`.
2. **Combined careers that are a single program are kept whole** - `BIOQUÍMICA Y FARMACIA`, `MEDICINA VETERINARIA Y ZOOTECNIA`, `INGENIERÍA EN DISEÑO INDUSTRIAL / DISEÑO INDUSTRIAL`, etc. are stored as single entries.
3. **Multi-career lists are split and joined with `, `** - when a cell lists several distinguishable careers, each part is canonicalized and joined:

   | Input | Output |
   |-------|--------|
   | `TURISMO - INGENIERÍA AGRONÓMICA` | `TURISMO, INGENIERÍA AGRONÓMICA` |
   | `ECONOMÍA Y ESTADISTICA` | `ECONOMÍA, ESTADÍSTICA` |
   | `BIOQUIMICA Y FARMACIA / QUIMICA` | `BIOQUÍMICA Y FARMACIA, QUÍMICA` |
   | `CONTABILIDAD Y AUDITORIA/\nADMINISTRACIÓN PÚBLICA` | `CONTABILIDAD Y AUDITORÍA, ADMINISTRACIÓN PÚBLICA` |

   Splitting is validation-driven: a separator (` - `, ` / `, `, `, standalone ` Y `) only produces a split when **every part** matches a known career in `carreras.json` and the parts cover the whole string. Anything ambiguous is left as the source text.

> **Full rulebook:** see [`docs/career-normalization.md`](docs/career-normalization.md).

### Sheet formatting

Every generated period sheet replicates the base BD format exactly:

- Font: Aptos Narrow 10 pt (header bold, 10 pt)
- `LinkPlanificacion` cells that hold a URL are clickable hyperlinks (Aptos Narrow 10 pt, blue `0563C1`, single underline)
- Borders: thin black line on every cell, identical to the `2024-2025` sheet
- Freeze panes `A2`, autofilter `A1:R1`, column widths and row heights copied from the base sheet

## Output Format

| Field | Format | Example |
|-------|--------|---------|
| idDocumento | Sequential number | 1 |
| Facultad | UPPERCASE (matched to facultades.json) | CIENCIAS AGRÍCOLAS |
| Carrera | UPPERCASE, canonical accents; multi-career lists joined with ", " | AGRONOMÍA / TURISMO, INGENIERÍA AGRONÓMICA |
| TipoProyecto | UPPERCASE | VIGENTE |
| idCodigo | UPPERCASE | P3AGR18 |
| NombreProyecto | Sentence case (proper nouns preserved) | Primera vivienda ecológica en la parroquia La Esperanza para un número limitado de habitantes |
| NombrePrograma | Title case | P3. Hábitat, Desarrollo Local |
| NombreCoordinador | Title case | Jorge Antonio Piedra Rosales |
| Territorio | Title case, locations separated by commas | Quito, Guaranda, Echeandía |
| FechaInicio | DD/MM/YYYY | 01/04/2025 |
| FechaFin | DD/MM/YYYY | 01/04/2026 |
| Anio | Year derived from the period | 2025 |
| LinkPlanificacion | Valid Google Drive file URL → clickable hyperlink; everything else → `N/A` | https://drive.google.com/file/d/... |
| Link* (others) | Always N/A | N/A |

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
2. Alias map (`utils/facultad_matcher.py` -> `ALIAS_MAP`) - `ADMINISTRACION` -> `CIENCIAS ADMINISTRATIVAS`, `AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`, `FIGEMPA` -> `INGENIERÍA EN GEOLOGÍA, MINAS PETRÓLEOS Y AMBIENTAL`, `FACSO` -> `COMUNICACIÓN SOCIAL`.
3. Accent-insensitive exact match - `CIENCIAS AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`.
4. Partial match - `AGRICOLAS` -> `CIENCIAS AGRÍCOLAS`.

If no match is found the source value is kept as-is (and the row is reported as missing `Facultad`).

### Career to faculty overrides

Some careers always belong to one specific faculty. When the career matches one of the keys below (`CARRERA_FACULTAD_OVERRIDE` in `utils/data_formatter.py`), the faculty is set unconditionally - this fixes wrong or missing faculties:

| Career | Faculty |
|--------|---------|
| `DERECHO` | `JURISPRUDENCIA, CIENCIAS POLÍTICAS Y SOCIALES` |
| `BIOLOGÍA` | `CIENCIAS BIOLÓGICAS` |
| `INGENIERÍA EN RECURSOS NATURALES RENOVABLES` | `CIENCIAS BIOLÓGICAS` |

This runs after the faculty matcher, so an override always wins.

## Programas.json Lookup

When `NombrePrograma` (and optionally `NombreCoordinador`) is missing and `idCodigo` is present, the program number is extracted from the code prefix (`P3AGR18` -> `P3`) and searched in `Programas.json`:

```json
{ "code": "P3", "name": "Desarrollo Sostenible...", "coordinador": "Jorge Antonio Piedra Rosales" }
```

Rows completed this way are marked **orange**.

## Color Coding

- **Red** - the row is missing one or more required fields (`Facultad`, `Carrera`, `NombreProyecto`, `NombrePrograma`, `NombreCoordinador`, `Territorio`, `FechaInicio`, `FechaFin`, `idCodigo`). Missing URLs never cause a red mark. A month+year date kept as text (`marzo de 2025`) also produces a red mark because the full date is still unknown.
- **Orange** - the row was completed using the `Programas.json` lookup.

## Report

`output/missing_data_report.md` lists every row with missing data: source row number, code, project name, and the list of missing fields. The report is only generated when at least one row is missing data.

## Config Files Reference

| File | Purpose |
|------|---------|
| `Programas.json` | Program codes P1-P9 with official name and coordinator |
| `facultades.json` | Official list of university faculties |
| `carreras.json` | Known career names: canonical spelling plus combined single careers (used for canonical naming and safe splitting) |
| `utils/proper_nouns.py` | Spanish proper nouns, acronyms, minor words, accent fixes |

## CI/CD

GitHub Actions validates every change and releases `main` with semantic version tags.

### Branch strategy and environments

Two long-lived branches, each mapped to a GitHub Actions **environment**:

| Branch | Environment | Purpose |
|--------|-------------|---------|
| `dev` | `dev` | Integration branch. PRs from feature branches target `dev`; pushes to `dev` run the CI pipeline against the `dev` environment. |
| `main` | `production` | Release branch. After `dev` is validated, `main` is updated and the **release workflow** tags it with the next semantic version. Merges to `main` run CI against the `production` environment. |

Feature branches are deleted automatically after their merge by enabling the GitHub repository setting **Settings > General > Automatically delete head branches**.

### Workflows

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | PR opened/updated to `main` or `dev`; push to `main` or `dev` | 1. **Validation**: syntax check (`compileall`), import smoke test, unit tests (`tests/test_formatting.py`). 2. **Integration**: runs `tests/test_integration.py`, which formats every `EJEMPLO PERIODO *.xlsx` and writes a real period sheet into `output/`, using the base BD workbook (created on demand in CI). |
| `release.yml` | push to `main` | Computes the next version with `scripts/semver.py` and creates + pushes an annotated `vX.Y.Z` tag. Requires the `production` environment. |

### Semver rules

`scripts/semver.py` derives the next `vX.Y.Z` from **conventional commits** between the last `v*` tag and `HEAD`:

| Change | Bump |
|--------|------|
| Breaking change (`!` in the type or `BREAKING CHANGE:` in the message) | Major (`X+1.0.0`) |
| `feat(...)` | Minor (`Y+1.0`) |
| Everything else (`fix`, `docs`, `ci`, etc.) | Patch (`Z+1`) |

Merge-commit subjects are ignored. With no previous tag, the version starts at `v0.1.0` and keeps bumping from there.

### Local test commands

```bash
venv\Scripts\python.exe -m unittest discover -s tests -p "test_formatting.py" -v
venv\Scripts\python.exe -m unittest discover -s tests -p "test_integration.py" -v
venv\Scripts\python.exe scripts\semver.py
```

> The integration tests write to `output/BDVinculacionn.xlsx`; close the file in Excel before running (`Stop-Process -Name EXCEL -Force` if it is locked).

## Extending

- **New period** - add a column map in `utils/column_mapper.py` (`MAP_XX_XX`), a `PERIOD_SHEET_MAP` entry, a `detect_period` branch, a `get_column_map` branch, and a `extract_year_from_period` entry. The example periods `21-22`, `22-23`, `27-28` use the shared `EXAMPLE_LAYOUT`.
- **New proper noun** - add the uppercase word to `PROPER_NOUNS` in `utils/proper_nouns.py`.
- **Missing accent fix** - add the word to `ACCENT_FIX` in `utils/proper_nouns.py`.
- **New faculty alias** - add it to `ALIAS_MAP` in `utils/facultad_matcher.py`.
- **New career / combined career** - add the canonical name to `carreras.json`. Careers listed there are kept whole and get canonical accents; multi-career lists split only when every part is present in this file.
- **Career to faculty override** - add the career -> faculty mapping to `CARRERA_FACULTAD_OVERRIDE` in `utils/data_formatter.py`.
- **New date format** - add the pattern to `DATE_FORMATS` or the month/numeric helpers in `utils/data_formatter.py`.