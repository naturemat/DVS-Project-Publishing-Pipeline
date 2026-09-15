# Spanish Text Formatting Engine

This document explains how the pipeline turns messy, often all-caps Spanish text into correctly punctuated Spanish, and how it decides which words are proper nouns (like `Quito`) that must stay capitalized.

The engine lives in `utils/data_formatter.py` (`DataFormatter`) and its vocabulary lives in `utils/proper_nouns.py`.

## Why it exists

Source files in `Fuente_Datos/` contain project names in all caps and without tildes:

```
PRIMERA VIVIENDA ECOLÓGICA EN LA PARROQUIA LA ESPERANZA PARA UN NUMERO LIMITADO DE HABITANTES
```

The requirement is that `NombreProyecto` uses **sentence case**:

```
Primera vivienda ecológica en la parroquia La Esperanza para un número limitado de habitantes
```

Only the first letter of each sentence is uppercase; every other ordinary word is lowercase. The only exceptions are:

- proper nouns (names of people and places): `Quito`, `Atucucho`, `Rumiñahui`
- abbreviations: `DM`, `UCE`, `CHQ`
- words the RAE approves as capitalized titles/phrases: `La Esperanza`, `San Pedro`

## The vocabulary lists

All four lists are in `utils/proper_nouns.py`.

### `PROPER_NOUNS`

Uppercase words that must be written capitalized when they appear in the middle of a sentence.

```python
PROPER_NOUNS = {
    "QUITO", "ECUADOR", "PICHINCHA", "CAYAMBE", "ATUCUCHO",
    "RUMIPAMBA", "MALCHINGUI", "TOCACHI", ...
}
```

Rule applied: `word -> word_capitalized` (`QUITO` -> `Quito`).

### `ACRONYMS`

Abbreviations that must always stay fully uppercase, punctuation or not.

```python
ACRONYMS = {"DM", "DMQ", "UCE", "GAD", "PUAM", "CACS", "FAU", "CHQ", ...}
```

Rule applied: `word -> word` (unchanged, all caps). This is why `DM. Quito` stays `DM. Quito` and not `dm. quito`.

### `TITLE_PREFIXES`

Short words that are only capitalized when they are the start of a proper phrase, detected by looking at the NEXT word.

```python
TITLE_PREFIXES = {"LA", "LAS", "EL", "LOS", "SAN", "SANTA", "DON", "DOÑA", ...}
```

When `LA` is followed by a proper noun (`ESPERANZA`), both are capitalized: `La Esperanza`. But a `la` not followed by a proper noun stays lowercase, as in `en la parroquia La Esperanza` (the first `la` is ordinary).

### `MINOR_WORDS`

Function words (articles, prepositions, conjunctions) that are always lowercase mid-sentence.

```python
MINOR_WORDS = {"a", "al", "de", "del", "en", "la", "las", "los", "y", "para", ...}
```

### `ACCENT_FIX`

Restores tildes on common words that the source wrote without them. Keys are uppercase, values are the correctly accented uppercase form.

```python
ACCENT_FIX = {
    "NUMERO": "NÚMERO",
    "GESTION": "GESTIÓN",
    "AGRICOLA": "AGRÍCOLA",
    "TURISTICO": "TURÍSTICO",
    "CLIMATICO": "CLIMÁTICO",
    ...
}
```

Accents are restored BEFORE deciding case, so `NUMERO` becomes `NÚMERO` and finally `número` (or `Número` if it starts a sentence).

## How a word is decided (decision order)

For every token in the text, `DataFormatter.proyecto_case` applies the first matching rule:

| Priority | Condition | Result | Example in |
|----------|-----------|--------|-------------|
| 1 | Word is in `ACRONYMS` | Keep uppercase | `DM` -> `DM` |
| 2 | Word is in `PROPER_NOUNS` | First letter uppercase, rest lowercase | `QUITO` -> `Quito` |
| 3 | Word is in `TITLE_PREFIXES` AND next word is in `PROPER_NOUNS` | First letter uppercase | `LA` (before `ESPERANZA`) -> `La` |
| 4 | Word starts a sentence | First letter uppercase, rest lowercase | `PRIMERA` -> `Primera` |
| 5 | Word is in `MINOR_WORDS` | Lowercase | `PARA` -> `para` |
| 6 | Anything else | Lowercase | `VIVIENDA` -> `vivienda` |

Sentence start is tracked with a flag that is set to `True` at the beginning of the text and after `.`, `!`, `?`, `¿`, `¡` punctuation tokens.

## Worked examples

### The user-facing example

```
Input : “transfórmate Mujer”. Promoviendo Estilos de Vida Saludables en Mujeres Adultas Media en Atucucho
Output: “Transfórmate mujer”. Promoviendo estilos de vida saludables en mujeres adultas media en Atucucho
```

- `transfórmate` is the first word (after the opening quote) -> `Transfórmate`
- `Mujer` is not a proper noun and does not start a sentence -> `mujer`
- `.` ends the sentence -> next word is capitalized
- `Promoviendo` starts the new sentence -> `Promoviendo`
- `Estilos`, `Vida`, `Saludables`, `Mujeres`, `Adultas`, `Media` -> lowercase
- `Atucucho` is in `PROPER_NOUNS` -> `Atucucho`

### Place name with article

```
Input : EN LA PARROQUIA LA ESPERANZA
Output: en la parroquia La Esperanza
```

- first `LA` -> followed by `PARROQUIA` (not a proper noun) -> lowercase `la`
- `PARROQUIA` -> `parroquia`
- second `LA` -> followed by `ESPERANZA` (a proper noun) -> `La`
- `ESPERANZA` -> `Esperanza`

### Acronym + proper noun

```
Input : DEL DM. QUITO
Output: del DM. Quito
```

- `DEL` minor word -> `del`
- `DM` acronym -> `DM`
- `QUITO` proper noun -> `Quito`

## Restoring tildes

The accent map is applied before capitalization in both `proyecto_case` and `title_case`. This means:

```
Input : UN NUMERO LIMITADO DE HABITANTES
Output: un número limitado de habitantes
```

`NUMERO` is not in `MINOR_WORDS`, so its base form is taken from `ACCENT_FIX` (`NÚMERO`), lowercased to `número`. Words with tildes already present (`ECOLÓGICA`, `ATENCIÓN`) pass through unchanged.

> Note - `ACCENT_FIX` corrects only common, unambiguous words. It is not a full grammar engine. If a new word appears frequently without its tilde, add it to the dictionary.

## Separators (multiple locations)

Fields such as `Territorio` and `NombreProyecto` often list several locations separated by `/`. The engine calls `normalize_separators` BEFORE applying case rules, so:

```
Input : QUITO / GUARANDA / ECHEANDÍA / CHIMBO / CHILLANES
Step 1: QUITO, GUARANDA, ECHEANDÍA, CHIMBO, CHILLANES
Output: Quito, Guaranda, Echeandía, Chimbo, Chillanes
```

Rules of `normalize_separators`:

- Any `/` between parts is replaced by `, ` (comma + space).
- Multiple commas are collapsed; trailing commas are removed; double spaces are removed.
- The conjunction `y/o` ("and/or") is protected and never split.
- Numeric date-like patterns such as `20/05/2025` are protected and kept as-is.

This ordering matters: normalizing before `title_case`/`proyecto_case` prevents a glued token like `DMQ/PUERTO QUITO` from being treated as a single (wrongly cased) word.

## How to add a proper noun

Look for the word in `utils/proper_nouns.py`, `PROPER_NOUNS`, and add the UPPERCASE form:

```python
"NUEVOPLACENAME",
```

## How to add a tilde fix

In `utils/proper_nouns.py`:

```python
"NUMERO": "NÚMERO",
```

The key is the word WITHOUT tilde in uppercase; the value is the WITH tilde in uppercase.

## Where the rest of the fields are formatted

- `Facultad`, `TipoProyecto`, `idCodigo` - forced to UPPERCASE (see `utils/data_formatter.py`).
- `Carrera` - UPPERCASE, then normalized through `split_careers` (canonical accents from `carreras.json`, combined singles kept whole, multi-career lists split and joined with `, `). See [`career-normalization.md`](career-normalization.md).
- `NombrePrograma`, `NombreCoordinador`, `Territorio` - use `DataFormatter.title_case` (first letter of every word uppercase, accents restored, minor words lowercase).
- Dates - normalized to `DD/MM/YYYY` by `parse_date`. Month+year-only values are kept as their original text (see README).
- `LinkPlanificacion` - validated against the Google Drive file-link format `https://drive.google.com/file/d/<id>...`. Matches are kept as the original URL and rendered as a clickable hyperlink (blue `0563C1`, Aptos Narrow 10 pt, single underline). All other values — blank, filename text (`PROYECTO.pdf`), `FALTA`, folder links (`/drive/folders/...`), or any non-URL text — are written as `N/A`. This field is **never flagged as missing**; every row contains either a URL or `N/A`, never blank. All other `Link*` fields are forced to `N/A`.