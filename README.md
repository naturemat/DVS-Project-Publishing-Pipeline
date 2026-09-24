# Excel to DTICS - Data Extractor

Extracts project data from source Excel files in `Fuente_Datos/`, normalizes and formats every field, and writes it into a copy of the BD file (`BDVinculacionn 2024-2025.xlsx`) placed in the `output/` folder.

## Project Structure

```
Excel_to_dtics/
├── extract_data.py          # Main entry point (terminal menu: option 1 pipeline, option 2 date comparison)
├── Programas.json           # Program codes (P1-P9) with name + coordinator
├── facultades.json          # Official faculty names (source of truth)
├── carreras.json            # Known career names (canonical spelling + combined careers)
├── requirements.txt         # Python dependencies
├── utils/
│   ├── __init__.py
│   ├── column_mapper.py     # Source column mappings per period
│   ├── data_formatter.py    # Field formatting, date parsing, career logic
│   ├── file_reader.py       # Excel file reader
│   ├── facultad_matcher.py  # Faculty normalization (facultades.json + aliases)
│   └── proper_nouns.py      # Proper nouns, acronyms, accent fixes (Spanish)
├── modules/
│   └── date_comparison/     # Module 2: PDF comparison + autofill + consistency
│       ├── pdf_reader.py    # Match URLs to local Planificaciones/<file_id>.pdf; scan by project code
│       ├── date_extractor.py # TIEMPOS DEL PROYECTO section → FechaInicio/FechaFin; project name + career
│       ├── rowstate.py      # Shared red/orange/yellow fills + required-field helpers
│       ├── comparator.py    # Compare codes/dates/name/career, red-or-orange marking, run autofill + consistency
│       ├── autofill.py      # Autofill missing fields of VIGENTE rows from other sheets
│       └── consistency.py   # Cross-period value differences → yellow
├── docs/
│   ├── spanish-text-formatting.md   # Detailed rules of the text engine
│   └── career-normalization.md      # Career splitting + canonical naming rules
├── Fuente_Datos/            # Source Excel files (real ones gitignored)
│   ├── EJEMPLO PERIODO 21-22.xlsx   # Example with invented data (committed)
│   ├── EJEMPLO PERIODO 22-23.xlsx   # Example with invented data (committed)
│   └── EJEMPLO PERIODO 27-28.xlsx   # Example with invented data (committed)
├── scripts/
│   └── semver.py            # Next semantic version from conventional commits
├── tests/
│   ├── test_formatting.py   # Unit tests (dates, careers, faculties, fields)
│   ├── test_autofill.py     # Unit tests (autofill + row colors)
│   ├── test_consistency.py  # Unit tests (cross-sheet consistency → yellow)
│   ├── test_file_reader.py  # Unit tests (hyperlink target reading)
│   ├── test_date_extractor_targets.py  # Unit tests (PDF project name/career extraction)
│   └── test_integration.py  # End-to-end pipeline on example workbooks
├── .github/
│   └── workflows/
│       ├── ci.yml           # Validation + integration (dev/production environments)
│       └── release.yml      # Semver tagging on main
├── Planificaciones/         # Manually placed planning PDFs (gitignored)
│   └── .gitkeep
└── output/                  # Generated output (gitignored)
    ├── BDVinculacionn.xlsx  # Copy of base BD + analyzed period sheets
    ├── missing_data_report.md
    └── date_comparison_report.md
```

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt` (openpyxl, pdfplumber, pypdf, Pillow)

## How to Run (from scratch)

```bash
cd D:\UCE\PPP\Unidad_Comunicación\Excel_to_dtics
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python extract_data.py
```

Then the main menu asks:

```
[1] Process data (extract Excel -> output workbook)
[2] Compare dates with documents (PDF)
[0] Exit
```

### Option 1 - Process data

1. Place your source files in `Fuente_Datos/` (e.g., `PERIODO 25-25.xlsx`, `PERIODO 25-26.xlsx`, `PERIODO 26-26.xlsx`).
2. Run `python extract_data.py` and choose option 1.
3. Select a file from the menu (type the number and press Enter).
4. The script ensures `output/BDVinculacionn.xlsx` exists (copies the base file the first time, keeps previous data afterwards).
5. It creates or replaces only the sheet for the analyzed period (e.g., `2026-2026` from `PERIODO 26-26.xlsx`). If the sheet already exists, its data is overwritten in place - no duplicate sheets are ever created.
6. Rows are sorted alphabetically: first by `Facultad`, then by `NombreProyecto` within each faculty. Names starting with a special character (quotes, brackets, etc.) come first.
7. A missing-data report is written to `output/missing_data_report.md`.

### Option 2 - Compare dates with documents

1. Run `python extract_data.py` and choose option 2 (after generating the output with option 1).
2. You will be asked **which period to compare** when the workbook holds several periods (e.g. `2025-2025`, `2025-2026`). Pick one period at a time, compare all at once, or go back with `0`. If only one period exists, it is compared directly without asking.
3. Rows whose `LinkPlanificacion` is not a valid Drive URL (`N/A`, blank) are skipped entirely - never changed, never colored.
4. For every row with a valid link, the tool searches `Planificaciones/` for the document. A file named with the Drive file id of its `LinkPlanificacion` URL (`Planificaciones/<file_id>.pdf`) is matched to the row that holds that URL.
5. If no `<file_id>.pdf` matches the URL, the tool scans the folder and matches a PDF by the project code printed inside it (e.g. `P1MED05`).
6. If still no document is found and the project is marked **`NUEVO`** in `TipoProyecto`, the tool **downloads** the planification from the Google Drive link into `Planificaciones/<file_id>.pdf` and compares against it. Exception: if a local file for that id already exists and is flagged invalid (`NO VALIDO`), the download is skipped and the flagged file is never overwritten. All non-`NUEVO` projects are never downloaded - you must place their PDFs manually.
7. The tool reads the project code from `Código del Proyecto:` in the `1.2 INFORMACIÓN DEL PROYECTO` section. If the document has no code (or it isn't in `P1MED05` format), the row is skipped entirely. On a mismatch with the Excel `idCodigo`, the code cell is overwritten with the document's code.
8. The tool also reads the **project name** (the text between `Código del Proyecto:` and `Nombre del proyecto:`) and the **career** (the value after `Carreras:`). On a mismatch they are overwritten with the document's value (formatted with the same rules as option 1) and the row is re-marked **red-or-orange**.
9. The tool reads the `1.4 TIEMPOS DEL PROYECTO` section (pages 2-3) and extracts `Fecha de inicio` / `Fecha de finalización`.
10. Each extracted date is compared with the `FechaInicio` / `FechaFin` columns of the output workbook. On a mismatch with a **full** document date, the Excel date is **replaced by the document date**. Partial document dates (`Abril 2026`) never overwrite - the Excel value is kept with no color. Any correction (code, full date, project name, career) re-marks the row via `mark_corrected`: **red** if a required field is still missing, **orange** otherwise (a completed row is never red).
11. If the document can't be found/read or no dates are extracted, the row is left untouched. Rows still missing a document are listed per sheet on the console and in the report (`output/date_comparison_report.md`) so you know which PDFs to place.
12. When the comparison pass finishes, option 2 **autofills** empty `VIGENTE` fields from other period sheets (same `NombreProyecto`) and then runs the **consistency** pass: the same project is compared across the period sheets (most recent period is the reference) and any differing value marks the row **yellow**.
13. A report of all corrections is written to `output/date_comparison_report.md`.

## How It Works

The pipeline runs in five stages:

1. **Read** - `FileExtractor` opens the selected file from `Fuente_Datos/` and reads all data rows.
2. **Map** - `ColumnMapper` detects the period from the filename (`25-25`, `25-26`, `26-26`) and selects the correct source column positions for that file layout.
3. **Format** - `DataFormatter` normalizes every field: dates to `DD/MM/YYYY` (month+year-only values are completed with the first day of the month), uppercase fields, sentence case, proper nouns, tildes, plus career canonical naming and multi-career splitting.
4. **Enrich** - `FacultadMatcher` matches the source faculty to the official names in `facultades.json`. If `NombrePrograma`/`NombreCoordinador` are missing, `Programas.json` is queried using the program number extracted from `idCodigo` (e.g., `P3AGR18` -> `P3`). If the career maps to a definitive faculty (see `carrera_facultad.json`), the faculty is set from the career.
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
| Month + year only, e.g. `marzo de 2025`, `ABRIL DEL 2025`, `Septiembre del 2025` | `01/03/2025`, `01/04/2025`, `01/09/2025` (first day of month, row marked ORANGE) |
| `FALTA`, `NO EXISTE`, `FECHA QUE INICIO EL PROYECTO`, `periodo 24-25` | *(blank)* |
| Invalid dates such as `31/02/2026` | *(blank)* |

Rules:

- A **complete** calendar date (day + month + year) becomes `DD/MM/YYYY`.
- A **partial** date with a month and a year but no day (`marzo de 2025`, `Septiembre del 2025`) is **completed with the first day of the month** (`01/09/2025`), and the row is marked **orange** so it can be reviewed later. The month and year are never lost.
- Unparseable text (`periodo 24-25`, `FALTA`, etc.) leaves the cell **empty**; the row is marked red as missing that date.

### Link fields

Most link fields are always written as `N/A`. They are never searched, never validated, and never trigger a missing-data mark.

- `LinkPlanificacion` receives the URL from the source column `DISEÑO DEL PROYECTO` and is written as a **clickable hyperlink** (Aptos Narrow 10 pt, blue, underlined). Only valid Google Drive **file** links matching `https://drive.google.com/file/d/<id>...` are kept; all other values (empty, filenames like `PROYECTO.pdf`, `FALTA`, folder links, or any non-URL text) are written as `N/A`. This field never triggers a missing-data mark regardless of value. Every row in this column contains either a clickable URL or `N/A`; it is never left blank. These URLs are also the input of **Module 2** (date comparison).
- In the 2026-2026 workbook the `LINK AL PDF` source cells store only a **display filename** while the real URL lives in the cell's hyperlink target. The reader reads the **hyperlink target** when it starts with `http`, so the full Drive URL is still captured and written as a clickable hyperlink.
- `LinkLevantamientoBase`, `LinkJuridico`, `LinkConvenio`, `LinkAprobacion`, `LinkCronogramaActividades` are always `N/A`.

### Location separators

When a field lists multiple locations separated by `/` (e.g., `Quito / Guaranda / Echeandía`), the slashes are replaced by commas so every location is listed separately: `Quito, Guaranda, Echeandía`. This applies to `Territorio` and `NombreProyecto`. The idiom `y/o` is preserved, and date-like patterns (`20/05/2025`) are never split.

In `Territorio` the separator set is wider: `y`, `&`, `/`, and `-` (dash) are all replaced by `, `; for example `Angamarca - Cotopaxi` becomes `Angamarca, Cotopaxi` and `PUJILÍ Y SANTA CLARA` becomes `Pujilí, Santa Clara`. Date-like dash patterns (e.g. `20-05-2025`) are protected. `NombreProyecto` continues to use only `/`.

### Career normalization

The `Carrera` field is written in UPPERCASE, but it is first normalized against the reference list in `carreras.json`:

1. **Canonical spelling** - source variants are rewritten to the canonical (accented) form. `AGRONOMIA` -> `AGRONOMÍA`, `BIOQUIMICA Y FARMACIA` -> `BIOQUÍMICA Y FARMACIA`.
2. **Combined careers that are a single program are kept whole** - `BIOQUÍMICA Y FARMACIA`, `MEDICINA VETERINARIA Y ZOOTECNIA`, `INGENIERÍA EN DISEÑO INDUSTRIAL / DISEÑO INDUSTRIAL`, etc. are stored as single entries.
3. **Multi-career lists are split and joined with `•`** - when a cell lists several distinguishable careers, each part is canonicalized and prefixed with a bullet:

   | Input | Output |
   |-------|--------|
   | `TURISMO - INGENIERÍA AGRONÓMICA` | `•TURISMO •INGENIERÍA AGRONÓMICA` |
   | `ECONOMÍA Y ESTADISTICA` | `•ECONOMÍA •ESTADÍSTICA` |
   | `BIOQUIMICA Y FARMACIA / QUIMICA` | `•BIOQUÍMICA Y FARMACIA •QUÍMICA` |
   | `CONTABILIDAD Y AUDITORIA/\nADMINISTRACIÓN PÚBLICA` | `•CONTABILIDAD Y AUDITORÍA •ADMINISTRACIÓN PÚBLICA` |

   Splitting is validation-driven: a separator (` - `, ` / `, `, `, standalone ` Y `) only produces a split when **every part** matches a known career in `carreras.json` and the parts cover the whole string. Values that do not decode into known careers keep their normalized source text, bullet-prefixed per part when several parts are present.

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
| Carrera | UPPERCASE, canonical accents; multi-career lists "•"-prefixed per career | •TURISMO •INGENIERÍA AGRONÓMICA |
| TipoProyecto | UPPERCASE, "PROYECTO " prefix removed | VIGENTE, NUEVO |
| idCodigo | UPPERCASE | P3AGR18 |
| NombreProyecto | Sentence case (proper nouns preserved) | Primera vivienda ecológica en la parroquia La Esperanza para un número limitado de habitantes |
| NombrePrograma | Title case | P3. Hábitat, Desarrollo Local |
| NombreCoordinador | Title case | Jorge Antonio Piedra Rosales |
| Territorio | Title case, locations separated by commas | Quito, Guaranda, Echeandía |
| FechaInicio | DD/MM/YYYY | 01/04/2025 |
| FechaFin | DD/MM/YYYY | 01/04/2026 |
| Anio | Year derived from FechaFin (fallback: the period) | 2026 |
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

Some careers always belong to one specific faculty. The mapping lives in **`carrera_facultad.json`** (in the repo root - the file you review and edit). When the formatted career matches one of the keys below, the faculty is set unconditionally - this fixes wrong or missing faculties:

| Career | Faculty |
|--------|---------|
| `AGRONOMÍA` | `CIENCIAS AGRÍCOLAS` |
| `INGENIERÍA AGRONÓMICA` | `CIENCIAS AGRÍCOLAS` |
| `CIENCIAS AGRÍCOLAS` | `CIENCIAS AGRÍCOLAS` |
| `TURISMO` | `CIENCIAS AGRÍCOLAS` |
| `DERECHO` | `JURISPRUDENCIA, CIENCIAS POLÍTICAS Y SOCIALES` |
| `BIOLOGÍA` | `CIENCIAS BIOLÓGICAS` |
| `INGENIERÍA EN RECURSOS NATURALES RENOVABLES` | `CIENCIAS BIOLÓGICAS` |
| `ATENCIÓN PREHOSPITALARIA` | `CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES` |
| `FISIOTERAPIA` | `CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES` |
| `FONOAUDIOLOGÍA` | `CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES` |
| `TERAPIA OCUPACIONAL` | `CIENCIAS DE LA DISCAPACIDAD, ATENCIÓN PRE HOSPITALARIA Y DESASTRES` |

Keys are matched accent/case-insensitively, so `AGRONOMIA` or `ingenieria agronomica` still match. This runs after the faculty matcher, so an override always wins. Note also that the faculty matcher strips trailing punctuation (`CIENCIAS AGRICOLAS.` -> `CIENCIAS AGRÍCOLAS`).

## Programas.json Lookup

When `NombrePrograma` (and optionally `NombreCoordinador`) is missing and `idCodigo` is present, the program number is extracted from the code prefix (`P3AGR18` -> `P3`) and searched in `Programas.json`:

```json
{ "code": "P3", "name": "Desarrollo Sostenible...", "coordinador": "Jorge Antonio Piedra Rosales" }
```

Rows completed this way are marked **orange**.

## Date Comparison Module (Module 2)

Module 2 (menu option 2) cross-checks the dates stored in the output workbook against the dates written inside each project's planification PDF. It only inspects sheets generated by the pipeline (`PERIOD_SHEET_MAP`).

### How the document is located

Only rows whose `LinkPlanificacion` holds a valid Drive URL are inspected. Rows whose link is `N/A` (or empty) are skipped completely - they are never matched against `Planificaciones/`, never changed, and never colored.

1. The row's `LinkPlanificacion` URL is parsed. If a file named `Planificaciones/<file_id>.pdf` (the Drive file id from that URL) exists, it is used.
2. If the row has a valid URL but no `<file_id>.pdf` was found, `Planificaciones/` is scanned (only on demand) and PDFs are matched to the row by the project code extracted from the document itself (regex like `P1MED05`, `P3AGR01` found on page 1 under "Código del Proyecto").
3. If still nothing is found and the project's `TipoProyecto` is **`NUEVO`**, the planification is **downloaded from its Google Drive file link** into `Planificaciones/<file_id>.pdf` and the comparison proceeds. The download uses the Drive `uc?export=download` endpoint (the large-file virus-scan `confirm` token is handled automatically).

> **Downloads:** only projects marked `NUEVO` are ever downloaded, and only when no matching document is already in `Planificaciones/`. A download is skipped when `Planificaciones/<file_id>.pdf` already exists and is flagged invalid (see below) - a `NO VALIDO` file is never overwritten. For **every other project** (`VIGENTE`, `RESTRUCTURADO`, or `N/A`) you must place the planification PDF in `Planificaciones/` manually (named by Drive file id, by project code, or in any shape - they only have to contain the planification text).

> **Performance:** the code scan of `Planificaciones/` runs only when the folder changes. The result is cached in `Planificaciones/.pdf_index.json` (gitignored), so the first run takes a minute or two and every later run starts in under a second. Progress lines are printed while option 2 works (`Indexed N project codes...`, `2025-2025: checked 100 rows...`).

> **Flagging invalid documents:** sometimes a file in `Planificaciones/` turns out to be a different document (wrong format/content, e.g. a municipal resolution that got linked to a project). To keep it from ever being used, rename or copy it to `NO VALIDO.pdf` (any spacing/underscore between `NO` and `VALIDO`). The module excludes flagged files **and** any other file with byte-identical content (e.g. the same document still stored under its `<file_id>.pdf` name) from both the URL lookup and the local scan. Every other file is treated as valid.

### How the dates are extracted

The tool reads the `1.4 TIEMPOS DEL PROYECTO` section on pages 2-3 and collects every date-like token (`1 de junio 2024`, `Abril 2025`, `agosto 2021`). The earliest token becomes `FechaInicio` and the latest becomes `FechaFin` - this is robust against the PDF's two-column layout where a value may appear before or after its label.

### How the project code, name and career are extracted

Besides the dates, module 2 reads three more fields from the planification PDF:

- **Project code** - `Código del Proyecto:` inside the `1.2 INFORMACIÓN DEL PROYECTO` section. It must match the `P\d{1,2}[A-Z]+\d+` format (e.g. `P1MED05`), otherwise the row is skipped entirely.
- **Project name** - the text between the `Código del Proyecto:` and `Nombre del proyecto:` labels. The PDF uses a value-before-label layout, so this block starts with the project code (which is stripped). The value is run through the option-1 formatting (`proyecto_case` + `normalize_separators`).
- **Career** - the value after `Carreras:`. It is uppercased and canonicalized via the `carreras.json` engine (`split_careers`).

### Comparison rules

- The PDF code is compared with the Excel `idCodigo`. On a **mismatch** the Excel code is **overwritten** with the document's code.
- The PDF project name and career are compared with `NombreProyecto` and `Carrera`. On a mismatch they are **overwritten** with the document's formatted value. Comparisons are accent/case/whitespace-insensitive (so formatting-only differences and spelling variants never trigger a rewrite).
- Both dates are normalized before comparing: full dates become `DD/MM/YYYY`; month+year-only values (`Abril 2025`) are compared by the underlying month+year, so `marzo de 2025` and `01/03/2025` do NOT count as equal (different information), while `Abril 2025` and `abril 2025` do.
- On a mismatch with a **full** document date (`DD/MM/YYYY`), the Excel cell is **overwritten** with the document's date.
- Any correction (code, project name, career, or a full date) re-marks the row with `rowstate.mark_corrected`: **red** when a required field is still missing, **orange** when the row is otherwise complete (red rows never become orange, and a completed row is never marked red).
- **Incomplete document dates are never applied.** A date without a day (month+year only, e.g. `Abril 2026`, or year only) found in the PDF never overwrites the Excel column: the cell keeps its current value and no color is applied. Only full dates (`DD/MM/YYYY`) from the document can correct a row.
- **Rows without a link are never touched.** If `LinkPlanificacion` is not a valid Drive URL (`N/A`, blank, etc.), the row is skipped - no document lookup, no changes, no orange marking.
- Rows whose document cannot be found or whose dates cannot be parsed are left unchanged. Hyperlinks and formatting survive the update.
- A summary of every correction is written to `output/date_comparison_report.md`.

### Autofill missing fields (last step of option 2)

When the comparison pass finishes, option 2 makes one more attempt to complete rows that still have empty fields, reusing information already present elsewhere in the workbook:

- Every managed period sheet is scanned and rows are grouped by `NombreProyecto` (**accent/case/whitespace-insensitive** match, so `Fortalecimiento agrícola` and `FORTALECIMIENTO AGRICOLA` count as the same project).
- Only rows whose `TipoProyecto` is **`VIGENTE`** can be filled. `NUEVO` (and any other type) rows are skipped.
- Fillable fields (when empty or `N/A`): `idCodigo`, `LinkPlanificacion`, `Facultad`, `Carrera`, `NombrePrograma`, `NombreCoordinador`, `Territorio`, `FechaInicio`, `FechaFin`. Dates are copied only when the source holds a **full `DD/MM/YYYY`** value; `N/A`, blanks and month+year-only text are never used.
- The source is the first non-empty cell of the same project found anywhere in the workbook (any sheet, including other periods). If a `VIGENTE` project continues from a `NUEVO` period, the previous sheet's data is reused.
- Filled `LinkPlanificacion` cells become clickable hyperlinks (Aptos Narrow 10pt, blue `0563C1`, single underline), like option 1.
- **Every filled row is re-marked** with `mark_corrected`: **red** if it still misses a required field, **orange** if it is complete. Rows that receive no fill keep their previous color.
- Every filled cell is logged to the console and appended to `output/date_comparison_report.md` under `## Autofill (same NombreProyecto across sheets, VIGENTE only)`.

### Consistency across period sheets (last step of option 2)

The final pass groups every row by normalized `NombreProyecto` and compares the **identity** fields `idCodigo`, `LinkPlanificacion`, `Carrera`, `Facultad` and `Territorio` across the period sheets:

- Sheets are processed **most-recent-first** (by period year descending); the first non-empty value seen per field is the **reference**.
- Any other **non-empty** value for the same project that differs (accent/case/whitespace-insensitive) marks the row **yellow** (never over a red cell) and is appended to the report under `## Consistency across period sheets (yellow)`.
- Projects that appear only once never flag. Empty cells never flag - consistency only compares values that are actually present.

## Color Coding

- **Red** - the row is missing one or more required fields (`Facultad`, `Carrera`, `NombreProyecto`, `NombrePrograma`, `NombreCoordinador`, `Territorio`, `FechaInicio`, `FechaFin`, `idCodigo`; dates only count when full `DD/MM/YYYY`). Missing URLs never cause a red mark. Red always wins over yellow and orange.
- **Orange** - the row was completed using the `Programas.json` lookup (module 1), had a month+year date autocompleted to `01/<month>/<year>` (module 1), had a code/date/name/career corrected from the PDF document (module 2), or received autofilled cells (module 2).
- **Yellow** - the same project has a differing identity value across the period sheets (module 2 consistency pass). Never painted over a red cell.

## Reports

- `output/missing_data_report.md` lists every row with missing data: source row number, code, project name, and the list of missing fields. The report is only generated when at least one row is missing data.
- `output/date_comparison_report.md` lists every correction applied by module 2: sheet, row, project code, and the old -> new changes (code, dates, project name, career). When option 2 finishes, the autofill step appends the cells it completed under its own `## Autofill` section, and the consistency pass appends its flagged rows under `## Consistency across period sheets (yellow)`.

## Config Files Reference

| File | Purpose |
|------|---------|
| `Programas.json` | Program codes P1-P9 with official name and coordinator |
| `facultades.json` | Official list of university faculties |
| `carrera_facultad.json` | Career -> faculty overrides (applied unconditionally after the matcher) |
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
| `ci.yml` | PR opened/updated to `main` or `dev`; push to `main` or `dev` | 1. **Validation**: syntax check (`compileall`), import smoke test, unit tests (`tests/test_formatting.py`, `tests/test_autofill.py`, `tests/test_consistency.py`, `tests/test_file_reader.py`, `tests/test_date_extractor_targets.py`). 2. **Integration**: runs `tests/test_integration.py`, which formats every `EJEMPLO PERIODO *.xlsx` and writes a real period sheet into `output/`, using the base BD workbook (created on demand in CI). |
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
venv\Scripts\python.exe -m unittest discover -s tests -p "test_autofill.py" -v
venv\Scripts\python.exe -m unittest discover -s tests -p "test_consistency.py" -v
venv\Scripts\python.exe -m unittest discover -s tests -p "test_file_reader.py" -v
venv\Scripts\python.exe -m unittest discover -s tests -p "test_date_extractor_targets.py" -v
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
- **Career to faculty override** - add the career -> faculty mapping to `carrera_facultad.json` (repo root). Keys are matched accent/case-insensitively against the formatted career.
- **New date format** - add the pattern to `DATE_FORMATS` or the month/numeric helpers in `utils/data_formatter.py`.
- **New date pattern in PDFs** - adjust the regexes in `modules/date_comparison/date_extractor.py` (`_DATE_TOKEN_RE`, `_TIEMPOS_RE`).
- **New PDF-sourced comparison target** (name, career, etc.) - add a helper in `modules/date_comparison/date_extractor.py` (each `extract_project_*` accepts an optional `text=` for unit tests) and a comparison block in `comparator.py`.
- **New document location** - extend `modules/date_comparison/pdf_reader.py` (`local_pdf_for_url`, `index_local_pdfs`).
- **New autofill-able field** - add it to `FILLABLE_FIELDS` in `modules/date_comparison/autofill.py` (matching a column in `OUTPUT_COLUMNS`).
- **New consistency-checked field** - add it to `CONSISTENCY_FIELDS` in `modules/date_comparison/consistency.py`.
- **New required field for red/orange marking** - add it to `REQUIRED_FIELDS` in `modules/date_comparison/rowstate.py`.