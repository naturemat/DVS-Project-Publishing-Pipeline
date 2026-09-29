import os
from openpyxl import load_workbook

from modules.date_comparison import rowstate
from utils.column_mapper import ColumnMapper

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "BDVinculacionn.xlsx")
REPORT_FILE = os.path.join(OUTPUT_DIR, "date_comparison_report.md")

CONSISTENCY_FIELDS = ("idCodigo", "LinkPlanificacion", "Carrera", "Facultad", "Territorio")


def _headers(ws):
    return {
        cell.value: idx
        for idx, cell in enumerate(ws[1], 1)
        if cell.value
    }


def _sheet_year(sheet_name):
    period = {v: k for k, v in ColumnMapper.PERIOD_SHEET_MAP.items()}.get(sheet_name)
    if not period:
        return 0
    year = ColumnMapper.extract_year_from_period(period)
    return int(year) if year else 0


def _sheet_order(sheet_names):
    return sorted(sheet_names, key=lambda s: (_sheet_year(s), s), reverse=True)


def _is_empty(value):
    if value is None:
        return True
    s = str(value).strip()
    return not s or s.upper() in {"N/A", "NA"}


def run(workbook_path=None, report_path=None):
    wb_path = workbook_path or OUTPUT_FILE
    rep_path = report_path or REPORT_FILE

    if not os.path.exists(wb_path):
        print("  CONSISTENCY: output workbook not found, skipping.", flush=True)
        return 0

    wb = load_workbook(wb_path)
    managed = set(ColumnMapper.PERIOD_SHEET_MAP.values())
    available = _sheet_order([s for s in wb.sheetnames if s in managed])

    groups = {}
    for sheet_name in available:
        ws = wb[sheet_name]
        headers = _headers(ws)
        name_col = headers.get("NombreProyecto")
        if not name_col:
            continue
        for r in range(2, ws.max_row + 1):
            name = ws.cell(r, name_col).value
            norm = rowstate.normalized(name)
            if not norm:
                continue
            entry = {
                "sheet": sheet_name,
                "row": r,
                "name": str(name or "")[:60],
                "values": {
                    f: ws.cell(r, headers[f]).value
                    for f in CONSISTENCY_FIELDS
                    if headers.get(f)
                },
            }
            groups.setdefault(norm, []).append(entry)

    conflicts = []
    for entries in groups.values():
        reference = {}
        for entry in entries:
            for field, value in entry["values"].items():
                if _is_empty(value):
                    continue
                if field not in reference:
                    reference[field] = str(value)
                    continue
                if rowstate.normalized(reference[field]) == rowstate.normalized(value):
                    continue
                conflicts.append({
                    "sheet": entry["sheet"],
                    "row": entry["row"],
                    "name": entry["name"],
                    "field": field,
                    "value": str(value),
                    "reference": reference[field],
                })

    per_sheet = {}
    for item in conflicts:
        ws = wb[item["sheet"]]
        rowstate.mark_yellow(ws, item["row"], ws.max_column)
        per_sheet.setdefault(item["sheet"], []).append(item)

    if conflicts:
        wb.save(wb_path)
    wb.close()

    _append_report(rep_path, conflicts)
    _print_summary(per_sheet, len(conflicts))
    return len(conflicts)


def _print_summary(per_sheet, total):
    print("\n  CONSISTENCY: same project compared across period sheets (VIGENTE/NUEVO), yellow = differs", flush=True)
    if not total:
        print("  No cross-sheet value differences found.", flush=True)
        return
    for sheet_name, items in per_sheet.items():
        print(f"    {sheet_name}: {len(items)} row(s) flagged yellow", flush=True)
    print(f"  Total rows flagged yellow: {total}", flush=True)


def _append_report(rep_path, conflicts):
    if not conflicts:
        return
    lines = ["", "## Consistency across period sheets (yellow)", ""]
    for item in conflicts:
        lines.append(
            f"- **{item['sheet']}** row {item['row']} - {item['name']}: "
            f"{item['field']} '{item['value']}' differs from '{item['reference']}'"
        )
    lines.append("")
    lines.append(f"**Total rows flagged yellow:** {len(conflicts)}")
    with open(rep_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))