import os
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from modules.date_comparison import pdf_reader
from modules.date_comparison.date_extractor import extract_project_dates, normalize_for_compare
from utils.column_mapper import ColumnMapper

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "BDVinculacionn.xlsx")
REPORT_FILE = os.path.join(OUTPUT_DIR, "date_comparison_report.md")

ORANGE_FILL = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
RED_RGB = ("FFFF0000", "00FF0000")


def _is_red(cell):
    rgb = getattr(cell.fill.start_color, "rgb", None)
    return rgb in RED_RGB


def _set_orange(row_cells):
    for cell in row_cells:
        if not _is_red(cell):
            cell.fill = ORANGE_FILL


def _headers(ws):
    return {
        cell.value: idx
        for idx, cell in enumerate(ws[1], 1)
        if cell.value
    }


def _row_cells(ws, r, num_cols):
    return [ws.cell(r, c) for c in range(1, num_cols + 1)]


def run():
    pdf_reader.ensure_planificaciones_dir()

    if not os.path.exists(OUTPUT_FILE):
        print("  [ERROR] Output file not found. Run option 1 first.", flush=True)
        return False

    print("  Scanning Planificaciones/ for project documents...", flush=True)
    local_index = pdf_reader.index_local_pdfs()
    print(f"  Indexed {len(local_index)} project codes from local documents.", flush=True)

    wb = load_workbook(OUTPUT_FILE)

    total_rows = 0
    checked = 0
    corrected = 0
    no_doc = 0
    report = []
    dates_cache = {}

    managed_sheets = set(ColumnMapper.PERIOD_SHEET_MAP.values())

    for sheet_name in wb.sheetnames:
        if sheet_name not in managed_sheets:
            continue
        ws = wb[sheet_name]
        headers = _headers(ws)
        if not headers.get("LinkPlanificacion"):
            continue

        num_cols = ws.max_column
        link_col = headers["LinkPlanificacion"]
        inicio_col = headers.get("FechaInicio")
        fin_col = headers.get("FechaFin")
        codigo_col = headers.get("idCodigo")
        if not (inicio_col and fin_col and codigo_col):
            continue

        per_sheet = 0
        for r in range(2, ws.max_row + 1):
            total_rows += 1
            row_cell = ws.cell(r, codigo_col)
            if not row_cell.value:
                continue

            checked += 1
            if checked % 25 == 0:
                print(f"    {sheet_name}: checked {checked} rows...", flush=True)
            link_value = ws.cell(r, link_col).value

            pdf_path = None
            if isinstance(link_value, str) and link_value.startswith("http"):
                pdf_path = pdf_reader.local_pdf_for_url(link_value)
            if not pdf_path:
                code = str(row_cell.value).strip()
                matches = local_index.get(code) or []
                if matches:
                    pdf_path = matches[0]

            if not pdf_path:
                no_doc += 1
                continue

            if pdf_path in dates_cache:
                doc_dates = dates_cache[pdf_path]
            else:
                doc_dates = extract_project_dates(pdf_path)
                dates_cache[pdf_path] = doc_dates
            if not doc_dates:
                no_doc += 1
                continue

            changes = []
            for col_key, col in (("FechaInicio", inicio_col), ("FechaFin", fin_col)):
                if col_key not in doc_dates:
                    continue
                cell = ws.cell(r, col)
                old = cell.value
                new = doc_dates[col_key]
                if new and normalize_for_compare(old) != normalize_for_compare(new):
                    changes.append((col_key, old, new))
                    cell.value = new

            if changes:
                corrected += 1
                per_sheet += 1
                _set_orange(_row_cells(ws, r, num_cols))
                report.append({
                    "sheet": sheet_name,
                    "row": r,
                    "codigo": row_cell.value,
                    "nombre": ws.cell(r, headers.get("NombreProyecto", 1)).value,
                    "changes": changes,
                })

        print(f"  {sheet_name}: checked {ws.max_row - 1} rows, {per_sheet} corrected", flush=True)

    wb.save(OUTPUT_FILE)
    wb.close()

    _write_report(report)

    print("\n  COMPARISON SUMMARY", flush=True)
    print(f"  Rows found: {total_rows}", flush=True)
    print(f"  Rows checked (with idCodigo): {checked}", flush=True)
    print(f"  Rows corrected: {corrected}", flush=True)
    print(f"  Rows without document: {no_doc}", flush=True)
    print(f"  Report: {REPORT_FILE}", flush=True)
    return True


def _changelog_line(change):
    if change is None:
        return None
    key, old, new = change
    label = "Fecha de inicio" if key == "FechaInicio" else "Fecha de finalización"
    return f"\n      - {label}: '{old}' -> '{new}'"


def _write_report(report):
    lines = [
        "# Date Comparison Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Corrections",
        "",
    ]
    if not report:
        lines.append("No date mismatches found.")
    for item in report:
        changes_txt = "".join(_changelog_line(c) for c in item["changes"])
        lines.append(
            f"- **{item['sheet']}** row {item['row']} - {item['codigo']} - "
            f"{str(item['nombre'] or '')[:60]}{changes_txt}"
        )
    lines.append("")
    lines.append(f"**Total rows corrected:** {len(report)}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))