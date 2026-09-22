# Career Normalization

This document explains how the pipeline processes the `Carrera` (career) field: canonical spelling, keeping combined single careers whole, and splitting multi-career lists.

The logic lives in `DataFormatter` (`utils/data_formatter.py`), and the reference data lives in `carreras.json` at the project root.

## Why it exists

Source files write career names inconsistently:

- Same career with and without tildes: `AGRONOMIA` vs `AGRONOMÍA`
- Same career with different casing: `eEconomía`-style differences (`economía`), `Medicina Veterinaria y Zootecnia`
- One cell listing several careers at once, separated by ` - `, ` / `, ` / `+newline, commas, or the conjunction `Y`
- Combined programs whose full name contains a separator but is really ONE career: `MEDICINA VETERINARIA Y ZOOTECNIA`, `BIOQUÍMICA Y FARMACIA`, `INGENIERÍA EN DISEÑO INDUSTRIAL / DISEÑO INDUSTRIAL`

The code must produce a stable, canonical output and never split a career that is actually a single program.

## `carreras.json`

A JSON array of strings. Every entry is the **canonical accented UPPERCASE** form of a real career:

```json
[
  "AGRONOMÍA",
  "BIOQUÍMICA Y FARMACIA",
  "MEDICINA VETERINARIA Y ZOOTECNIA",
  "INGENIERÍA EN DISEÑO INDUSTRIAL / DISEÑO INDUSTRIAL"
]
```

Two kinds of entries exist:

1. Simple careers - `AGRONOMÍA`, `ECONOMÍA`, `TURISMO`.
2. Combined single careers - programs whose official name contains `Y`, ` - ` or ` / ` but is a single degree. Listing them here guarantees they are kept whole: `BIOQUÍMICA Y FARMACIA`, `PEDAGOGÍA DE LA ACTIVIDAD FÍSICA Y DEPORTE`, `COMPUTACIÓN / SISTEMAS DE INFORMACIÓN`.

Matching is **accent- and case-insensitive**: `BIOQUIMICA Y FARMACIA` matches the entry `BIOQUÍMICA Y FARMACIA`.

## Processing order

`DataFormatter.split_careers` runs on every `Carrera` value after uppercasing. It follows this order:

1. **Collapse whitespace** and UPPERCASE.
2. **Exact known-career lookup** (accent/case-insensitive) on the whole string. If it matches a `carreras.json` entry, the canonical form is returned - nothing else happens. This is what protects `MEDICINA VETERINARIA Y ZOOTECNIA` and `INGENIERÍA EN DISEÑO INDUSTRIAL / DISEÑO INDUSTRIAL` from being split.
3. **Normalize separators** (`/` -> `, ` unless date-like or `y/o`), collapse spaces.
4. **Known-career lookup again** on the normalized string.
5. **Career-chain matching** (`_find_career_chain`) - the main splitting engine. Its parts are prefixed with `•` and joined (e.g. `•QUÍMICA •BIOQUÍMICA Y FARMACIA`).
6. **Fallback** - if nothing above qualifies, the normalized source text is returned, bullet-prefixed per part when several parts are present.

### The chain matcher

`_find_career_chain` searches for every known career name *inside* the text (accent/case-insensitively), then looks for a non-overlapping sequence that:

- starts at position 0 and covers the whole string,
- contains **at least two** careers,
- leaves only separator characters (` `, `,`, `/`, `-`, `Y`) in the gaps between consecutive matches.

If such a chain exists, its careers are joined in order, each prefixed with `•`:

```
Input : QUIMICA Y BIOQUIMICA Y FARMACIA
Careers found in order: QUÍMICA, BIOQUÍMICA Y FARMACIA
Output: •QUÍMICA •BIOQUÍMICA Y FARMACIA
```

Greedy merging makes the multi-`Y` case correct: because `BIOQUÍMICA Y FARMACIA` is itself a known entry, it wins over splitting into `BIOQUÍMICA` + `FARMACIA` (which would be wrong).

## Worked examples

| Input | Output | Why |
|-------|--------|-----|
| `AGRONOMIA` | `AGRONOMÍA` | Canonical lookup (step 2) |
| `BIOQUIMICA Y FARMACIA` | `BIOQUÍMICA Y FARMACIA` | Known combined single (step 2) |
| `MEDICINA VETERINARIA Y ZOOTECNIA` | `MEDICINA VETERINARIA Y ZOOTECNIA` | Known combined single (step 2) |
| `INGENIERIA INFORMATICA / SISTEMAS DE INFORMACIÓN` | `INGENIERÍA INFORMÁTICA / SISTEMAS DE INFORMACIÓN` | Known combined single with `/` (step 2) |
| `TURISMO - INGENIERÍA AGRONÓMICA` | `•TURISMO •INGENIERÍA AGRONÓMICA` | Split: both parts known (step 5) |
| `ECONOMÍA Y ESTADISTICA` | `•ECONOMÍA •ESTADÍSTICA` | Split: both parts known (step 5) |
| `BIOQUIMICA Y FARMACIA / QUIMICA` | `•BIOQUÍMICA Y FARMACIA •QUÍMICA` | Split after `/` (step 3 + 5) |
| `CONTABILIDAD Y AUDITORIA/\nADMINISTRACIÓN PÚBLICA` | `•CONTABILIDAD Y AUDITORÍA •ADMINISTRACIÓN PÚBLICA` | Split after `/`+newline (steps 3-5) |
| `ECONOMIA/INGENIERIA EN ESTADÍSTICA/ IONEGENIERIA EN FINANZAS` | `•ECONOMIA •INGENIERIA EN ESTADÍSTICA •IONEGENIERIA EN FINANZAS` | `IONEGENIERIA` is a source typo, unknown -> each part falls back as source text |

## Unknown or ambiguous values

Values that do not decode into known careers are left as the normalized source text. Typed data containing typos (e.g. source `IONEGENIERIA EN FINANZAS`, `RADDIOLOGÍA E IMAGENOLOGÍA`) stays readable in the cell rather than being destroyed; when the fallback lists several parts they are separated with `•`. To fix such cases, add the correct name to `carreras.json`.

## How to add or change a career

1. Open `carreras.json`.
2. Add the canonical UPPERCASE (accented) name.
3. If it is a combined single (contains `Y`, ` - ` or ` / `), add it with its full name so it is never split.
4. Re-run any period to verify.