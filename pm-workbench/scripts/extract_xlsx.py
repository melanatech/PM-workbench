#!/usr/bin/env python3
"""Extract plain text from .xlsx / .xlsm into a UTF-8 text file.

Stdlib only (zipfile + xml). No openpyxl. Macros in .xlsm are ignored;
cell values and shared strings are extracted sheet-by-sheet as TSV-ish rows.

Optional --formulas appends a Formulas section with cell refs, formula text,
and cached calculated values (Excel does not recalculate here).

Usage:
  extract_xlsx.py <workbook.xlsx|xlsm> <output.txt>
  extract_xlsx.py <workbook.xlsx|xlsm> <output.txt> --formulas
Exit: 0 success, 2 empty/unsupported structure, 3 corrupt/unreadable.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _cell_ref_col_row(ref: str) -> tuple[int, int]:
    m = re.match(r"^([A-Z]+)(\d+)$", ref.upper())
    if not m:
        return 0, 0
    col_letters, row_s = m.group(1), m.group(2)
    col = 0
    for ch in col_letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col - 1, int(row_s) - 1


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in zf.namelist():
        return []
    root = ET.fromstring(zf.read(name))
    out: list[str] = []
    for si in root.findall("m:si", NS):
        parts = [t.text or "" for t in si.iter() if _local(t.tag) == "t"]
        out.append("".join(parts))
    return out


def _sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return [(sheet_name, zip_path), ...] in workbook order."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_path = "xl/_rels/workbook.xml.rels"
    rid_to_target: dict[str, str] = {}
    if rels_path in zf.namelist():
        rels = ET.fromstring(zf.read(rels_path))
        for rel in rels:
            if _local(rel.tag) != "Relationship":
                continue
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if rid and target:
                if target.startswith("/"):
                    zip_name = target.lstrip("/")
                else:
                    zip_name = "xl/" + target.lstrip("./")
                rid_to_target[rid] = zip_name

    sheets: list[tuple[str, str]] = []
    for sh in wb.findall("m:sheets/m:sheet", NS):
        name = sh.attrib.get("name") or "Sheet"
        rid = sh.attrib.get(f"{{{NS['r']}}}id") or sh.attrib.get("id")
        target = rid_to_target.get(rid or "", "")
        if not target:
            sid = sh.attrib.get("sheetId") or str(len(sheets) + 1)
            target = f"xl/worksheets/sheet{sid}.xml"
        if target in zf.namelist():
            sheets.append((name, target))
    return sheets


def _cell_display_value(c: ET.Element, shared: list[str]) -> str | None:
    ctype = c.attrib.get("t")
    v_el = None
    for child in c:
        if _local(child.tag) == "v":
            v_el = child
            break
    if ctype == "inlineStr":
        texts = [t.text or "" for t in c.iter() if _local(t.tag) == "t"]
        return "".join(texts)
    if v_el is None or v_el.text is None:
        return None
    if ctype == "s":
        try:
            return shared[int(v_el.text)]
        except (ValueError, IndexError):
            return v_el.text
    return v_el.text


def _normalize_cell(val: str) -> str:
    return val.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")


def _sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(zf.read(sheet_path))
    grid: dict[tuple[int, int], str] = {}
    max_r, max_c = -1, -1

    for c in root.iter():
        if _local(c.tag) != "c":
            continue
        ref = c.attrib.get("r")
        if not ref:
            continue
        col, row = _cell_ref_col_row(ref)
        val = _cell_display_value(c, shared)
        if val is None:
            continue
        val = _normalize_cell(val)
        grid[(row, col)] = val
        max_r = max(max_r, row)
        max_c = max(max_c, col)

    if max_r < 0:
        return []
    rows: list[list[str]] = []
    for r in range(max_r + 1):
        row_vals = [grid.get((r, c), "") for c in range(max_c + 1)]
        if any(cell.strip() for cell in row_vals):
            rows.append(row_vals)
    return rows


def _formula_text(f_el: ET.Element) -> str:
    """Turn an <f> element into readable formula text (leading =)."""
    body = "".join(f_el.itertext()).strip()
    ftype = f_el.attrib.get("t", "")
    ref = f_el.attrib.get("ref", "")
    si = f_el.attrib.get("si", "")
    if body:
        formula = body if body.startswith("=") else f"={body}"
    elif ftype == "shared" and si != "":
        # Continuation of a shared formula — master is elsewhere
        formula = f"=(shared si={si})"
    else:
        formula = "=(formula)"
    notes = []
    if ftype:
        notes.append(f"t={ftype}")
    if ref:
        notes.append(f"ref={ref}")
    if notes and (ftype or not body):
        formula = f"{formula}  [{', '.join(notes)}]"
    return formula


def _sheet_formulas(
    zf: zipfile.ZipFile, sheet_path: str, shared: list[str]
) -> list[tuple[str, str, str]]:
    """Return [(A1, '=B1+C1', 'cached'), ...] sorted by row/col."""
    root = ET.fromstring(zf.read(sheet_path))
    found: list[tuple[int, int, str, str, str]] = []
    for c in root.iter():
        if _local(c.tag) != "c":
            continue
        ref = c.attrib.get("r")
        if not ref:
            continue
        f_el = None
        for child in c:
            if _local(child.tag) == "f":
                f_el = child
                break
        if f_el is None:
            continue
        col, row = _cell_ref_col_row(ref)
        formula = _formula_text(f_el)
        cached = _cell_display_value(c, shared)
        cached_s = _normalize_cell(cached) if cached is not None else ""
        found.append((row, col, ref.upper(), formula, cached_s))
    found.sort(key=lambda t: (t[0], t[1]))
    return [(ref, formula, cached) for _, _, ref, formula, cached in found]


def extract_xlsx(src: Path, dest: Path, *, formulas: bool = False) -> int:
    try:
        with zipfile.ZipFile(src, "r") as zf:
            names = set(zf.namelist())
            if "xl/workbook.xml" not in names:
                print(
                    f"Not a readable Office Open XML workbook: {src}",
                    file=sys.stderr,
                )
                return 2
            shared = _load_shared_strings(zf)
            sheets = _sheet_targets(zf)
            if not sheets:
                print(f"No worksheets found in {src}", file=sys.stderr)
                return 2

            chunks: list[str] = []
            cell_count = 0
            formula_blocks: list[str] = []
            formula_count = 0

            for sheet_name, path in sheets:
                rows = _sheet_rows(zf, path, shared)
                chunks.append(f"### Sheet: {sheet_name}")
                if not rows:
                    chunks.append("(empty)")
                else:
                    for row in rows:
                        cell_count += sum(1 for c in row if c.strip())
                        chunks.append("\t".join(row))
                chunks.append("")

                if formulas:
                    flist = _sheet_formulas(zf, path, shared)
                    formula_blocks.append(f"### Sheet: {sheet_name}")
                    if not flist:
                        formula_blocks.append("(no formulas)")
                    else:
                        formula_count += len(flist)
                        for ref, formula, cached in flist:
                            if cached:
                                formula_blocks.append(f"{ref}\t{formula}\t[cached: {cached}]")
                            else:
                                formula_blocks.append(f"{ref}\t{formula}")
                    formula_blocks.append("")

            if cell_count == 0 and formula_count == 0:
                print(
                    f"Workbook has no cell text: {src}. "
                    "Re-export as .csv/.pdf or paste.",
                    file=sys.stderr,
                )
                return 2

            if formulas:
                chunks.append("## Formulas")
                chunks.append(
                    "_Formula text from the workbook XML; cached values are "
                    "Excel's last-saved results (not recalculated here). "
                    "Shared-formula continuations show `(shared si=N)` — "
                    "see the master cell with the same si._"
                )
                chunks.append("")
                chunks.extend(formula_blocks)
                chunks.append(f"_Formulas found: {formula_count}_")

            dest.write_text("\n".join(chunks).strip() + "\n", encoding="utf-8")
            return 0
    except zipfile.BadZipFile:
        print(
            f"Corrupt or encrypted workbook (not a zip): {src}. "
            "Re-export as .csv/.pdf without protection, or paste.",
            file=sys.stderr,
        )
        return 3
    except ET.ParseError as e:
        print(f"XML parse failed for {src}: {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"Failed to read {src}: {e}", file=sys.stderr)
        return 3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path, help="Workbook .xlsx or .xlsm")
    ap.add_argument("dest", type=Path, help="Output .txt path")
    ap.add_argument(
        "--formulas",
        action="store_true",
        help="Append a Formulas section (cell ref, formula, cached value)",
    )
    args = ap.parse_args(argv)
    if not args.src.is_file():
        print(f"Not a file: {args.src}", file=sys.stderr)
        return 1
    return extract_xlsx(args.src, args.dest, formulas=args.formulas)


if __name__ == "__main__":
    raise SystemExit(main())
