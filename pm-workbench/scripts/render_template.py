#!/usr/bin/env python3
"""Render a markdown body into HTML or a .docx using the standard library.

Formatting of a branded Word file still comes from the template: when the
template is a .docx, its ``word/styles.xml`` is copied into the result.
Headings, paragraphs, bullets, tables, and links are written as
WordprocessingML. There is no pandoc and no python-docx.

HTML templates (``reference/templates/formatted/page.html``) are filled by
replacing ``{{title}}`` and ``{{content}}``. ``{{content}}`` is HTML this
script produced; ``{{title}}`` is escaped.

Usage:
  python3 scripts/render_template.py <template> <context.json> <output>

``context.json`` keys:
  markdown   source text (headings, paragraphs, bullets, tables, links)
  title      document title (optional; first heading is used otherwise)
  content    prebuilt HTML; when set, an HTML template skips markdown

.xlsx and .pptx are not rendered. Exit 1 and say so. Callers fall back to
markdown for those formats.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

SLACK_LIMIT = 5000

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def markdown_to_blocks(text: str) -> list[dict]:
    """Turn a small markdown subset into blocks.

    Each block is ``{"kind": ..., ...}``. Kinds: h1, h2, h3, p, bullet, table,
    code. Text fields are lists of inline spans: ``{"text", "bold", "italic",
    "code", "href"}``.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[dict] = []
    i = 0
    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            blocks.append({"kind": "p", "inlines": parse_inlines(" ".join(para))})
            para = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_para()
            lang_line = stripped[3:]
            buf: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            blocks.append({"kind": "code", "text": "\n".join(buf), "lang": lang_line.strip()})
            i += 1
            continue
        if not stripped:
            flush_para()
            i += 1
            continue
        if _is_table_start(lines, i):
            flush_para()
            rows, i = _consume_table(lines, i)
            blocks.append({"kind": "table", "rows": rows})
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            flush_para()
            level = len(heading.group(1))
            blocks.append({
                "kind": f"h{level}",
                "inlines": parse_inlines(heading.group(2).strip()),
            })
            i += 1
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_para()
            blocks.append({"kind": "bullet", "inlines": parse_inlines(bullet.group(1).strip())})
            i += 1
            continue
        numbered = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if numbered:
            flush_para()
            blocks.append({"kind": "bullet", "inlines": parse_inlines(numbered.group(1).strip())})
            i += 1
            continue
        para.append(stripped)
        i += 1
    flush_para()
    return blocks


def parse_inlines(text: str) -> list[dict]:
    spans: list[dict] = []
    pattern = re.compile(
        r"(\*\*[^*]+?\*\*|\*[^*]+?\*|_[^_]+?_|`[^`]+`|\[[^\]]+\]\([^)]+\))"
    )
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            spans.append(_span(text[pos:match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            spans.append(_span(token[2:-2], bold=True))
        elif token.startswith("`"):
            spans.append(_span(token[1:-1], code=True))
        elif token.startswith("["):
            label, href = token[1:].split("](", 1)
            spans.append(_span(label, href=href[:-1]))
        else:
            inner = token[1:-1]
            spans.append(_span(inner, italic=True))
        pos = match.end()
    if pos < len(text):
        spans.append(_span(text[pos:]))
    return [s for s in spans if s["text"]]


def _span(text: str, bold: bool = False, italic: bool = False, code: bool = False, href: str | None = None) -> dict:
    return {"text": text, "bold": bold, "italic": italic, "code": code, "href": href}


def _is_table_start(lines: list[str], i: int) -> bool:
    if i + 1 >= len(lines):
        return False
    if "|" not in lines[i]:
        return False
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1]))


def _consume_table(lines: list[str], i: int) -> tuple[list[list[list[dict]]], int]:
    rows: list[list[list[dict]]] = []
    while i < len(lines) and "|" in lines[i]:
        if re.match(r"^\s*\|?\s*:?-{3,}", lines[i]):
            i += 1
            continue
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        rows.append([parse_inlines(c) for c in cells])
        i += 1
    return rows, i


def plain_text(inlines: list[dict]) -> str:
    return "".join(span["text"] for span in inlines)


def blocks_to_html(blocks: list[dict]) -> str:
    return _html_from_blocks(blocks)


def _html_from_blocks(blocks: list[dict]) -> str:
    parts: list[str] = []
    list_open = False

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            parts.append("</ul>")
            list_open = False

    for block in blocks:
        kind = block["kind"]
        if kind == "bullet":
            if not list_open:
                parts.append("<ul>")
                list_open = True
            parts.append(f"<li>{_html_inlines(block['inlines'])}</li>")
            continue
        close_list()
        if kind in {"h1", "h2", "h3"}:
            parts.append(f"<{kind}>{_html_inlines(block['inlines'])}</{kind}>")
        elif kind == "p":
            parts.append(f"<p>{_html_inlines(block['inlines'])}</p>")
        elif kind == "table":
            parts.append(_html_table(block["rows"]))
        elif kind == "code":
            parts.append(f"<pre>{html.escape(block['text'])}</pre>")
    close_list()
    return "\n".join(parts)


def _html_inlines(inlines: list[dict]) -> str:
    out: list[str] = []
    for span in inlines:
        text = html.escape(span["text"])
        if span.get("code"):
            text = f"<code>{text}</code>"
        if span.get("bold"):
            text = f"<strong>{text}</strong>"
        if span.get("italic"):
            text = f"<em>{text}</em>"
        if span.get("href"):
            href = html.escape(span["href"], quote=True)
            text = f'<a href="{href}">{text}</a>'
        out.append(text)
    return "".join(out)


def _html_table(rows: list[list[list[dict]]]) -> str:
    body = ["<table>"]
    for index, row in enumerate(rows):
        tag = "th" if index == 0 else "td"
        cells = "".join(f"<{tag}>{_html_inlines(cell)}</{tag}>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    body.append("</table>")
    return "".join(body)


def fill_html_template(template: str, title: str, content: str) -> str:
    rendered = template.replace("{{title}}", html.escape(title))
    rendered = rendered.replace("{{content}}", content)
    return rendered


def first_heading(blocks: list[dict]) -> str:
    for block in blocks:
        if block["kind"] in {"h1", "h2", "h3"}:
            return plain_text(block["inlines"]).strip()
    return ""


def blocks_to_confluence(blocks: list[dict]) -> str:
    """Confluence storage-format fragment. Local draft only."""
    body = blocks_to_html(blocks)
    return (
        "<!-- Local draft. Do not publish until the author explicitly approves (Tier 3). -->\n"
        + body
        + "\n"
    )


def blocks_to_slack(blocks: list[dict], limit: int = SLACK_LIMIT) -> list[str]:
    """Slack mrkdwn parts, each within ``limit`` characters.

    Message tools that accept standard markdown convert on send. This file is
    a local draft in mrkdwn so it can be pasted after Tier 3 approval. Sending
    is not done here.
    """
    chunks: list[str] = []
    for block in blocks:
        kind = block["kind"]
        if kind in {"h1", "h2", "h3"}:
            chunks.append(f"*{_mrkdwn_inlines(block['inlines'])}*")
        elif kind == "p":
            chunks.append(_mrkdwn_inlines(block["inlines"]))
        elif kind == "bullet":
            chunks.append("• " + _mrkdwn_inlines(block["inlines"]))
        elif kind == "table":
            for row in block["rows"]:
                chunks.append(" | ".join(_mrkdwn_inlines(cell) for cell in row))
        elif kind == "code":
            chunks.append("```\n" + block["text"] + "\n```")
    packed = _pack_chunks(chunks, limit)
    return packed or [""]


def _mrkdwn_inlines(inlines: list[dict]) -> str:
    out: list[str] = []
    for span in inlines:
        text = span["text"]
        if span.get("code"):
            text = f"`{text}`"
        elif span.get("bold"):
            text = f"*{text}*"
        elif span.get("italic"):
            text = f"_{text}_"
        if span.get("href"):
            text = f"<{span['href']}|{span['text']}>"
        out.append(text)
    return "".join(out)


def _pack_chunks(chunks: list[str], limit: int) -> list[str]:
    parts: list[str] = []
    current = ""
    for chunk in chunks:
        piece = chunk.strip("\n")
        if not piece:
            continue
        while len(piece) > limit:
            parts.append(piece[:limit])
            piece = piece[limit:]
        candidate = piece if not current else current + "\n\n" + piece
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = piece
    if current:
        parts.append(current)
    return parts


def blocks_to_docx(blocks: list[dict], dest: Path, styles_docx: Path | None = None) -> None:
    """Write a .docx. Optionally replace styles.xml from ``styles_docx``."""
    body_xml: list[str] = []
    link_ids: dict[str, str] = {}

    def link_id(url: str) -> str:
        if url not in link_ids:
            link_ids[url] = f"rIdLink{len(link_ids) + 1}"
        return link_ids[url]

    for block in blocks:
        kind = block["kind"]
        if kind in {"h1", "h2", "h3", "p", "bullet"}:
            style = {"h1": "Heading1", "h2": "Heading2", "h3": "Heading3", "p": None, "bullet": None}[kind]
            body_xml.append(_docx_paragraph(block["inlines"], style=style, bullet=(kind == "bullet"), link_id=link_id))
        elif kind == "table":
            body_xml.append(_docx_table(block["rows"], link_id))
        elif kind == "code":
            body_xml.append(_docx_paragraph([_span(block["text"], code=True)], style=None, bullet=False, link_id=link_id))
    body_xml.append(
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
        f"<w:body>{''.join(body_xml)}</w:body></w:document>"
    )
    styles = _styles_xml(styles_docx)
    numbering = _numbering_xml()
    rel_xml = _document_rels(link_ids)
    content_types = _content_types()
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/numbering.xml", numbering)
        archive.writestr("word/_rels/document.xml.rels", rel_xml)


def _docx_paragraph(inlines: list[dict], style: str | None, bullet: bool, link_id) -> str:
    props: list[str] = []
    if style:
        props.append(f'<w:pStyle w:val="{style}"/>')
    if bullet:
        props.append("<w:numPr><w:ilvl w:val=\"0\"/><w:numId w:val=\"1\"/></w:numPr>")
    ppr = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    return f"<w:p>{ppr}{_docx_runs(inlines, link_id)}</w:p>"


def _docx_runs(inlines: list[dict], link_id) -> str:
    runs: list[str] = []
    for span in inlines:
        text = xml_escape(span["text"])
        rpr: list[str] = []
        if span.get("bold"):
            rpr.append("<w:b/>")
        if span.get("italic"):
            rpr.append("<w:i/>")
        if span.get("code"):
            rpr.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
        if span.get("href"):
            rpr.append('<w:rStyle w:val="Hyperlink"/>')
        rpr_xml = f"<w:rPr>{''.join(rpr)}</w:rPr>" if rpr else ""
        run = f'<w:r>{rpr_xml}<w:t xml:space="preserve">{text}</w:t></w:r>'
        if span.get("href"):
            rid = link_id(span["href"])
            run = f'<w:hyperlink r:id="{rid}">{run}</w:hyperlink>'
        runs.append(run)
    return "".join(runs) if runs else "<w:r><w:t></w:t></w:r>"


def _docx_table(rows: list[list[list[dict]]], link_id) -> str:
    trs: list[str] = []
    for row in rows:
        cells = []
        for cell in row:
            cells.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"0\" w:type=\"auto\"/></w:tcPr>"
                f"{_docx_paragraph(cell, style=None, bullet=False, link_id=link_id)}</w:tc>"
            )
        trs.append(f"<w:tr>{''.join(cells)}</w:tr>")
    borders = (
        '<w:tblBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        "</w:tblBorders>"
    )
    return (
        f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>{borders}</w:tblPr>"
        f"{''.join(trs)}</w:tbl>"
    )


def _styles_xml(styles_docx: Path | None) -> str:
    borrowed = _zip_part(styles_docx, "word/styles.xml") if styles_docx else None
    if borrowed:
        return borrowed.decode("utf-8")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:outlineLvl w:val="2"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="character" w:styleId="Hyperlink">
    <w:name w:val="Hyperlink"/>
    <w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr>
  </w:style>
</w:styles>
"""


def _numbering_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{W_NS}">
  <w:abstractNum w:abstractNumId="0">
    <w:multiLevelType w:val="hybridMultilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="bullet"/>
      <w:lvlText w:val="•"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1">
    <w:abstractNumId w:val="0"/>
  </w:num>
</w:numbering>
"""


def _document_rels(link_ids: dict[str, str]) -> str:
    rows = [
        '<Relationship Id="rIdStyles" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>',
        '<Relationship Id="rIdNumbering" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" '
        'Target="numbering.xml"/>',
    ]
    for url, rid in link_ids.items():
        rows.append(
            f'<Relationship Id="{xml_escape(rid)}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            f'Target="{xml_escape(url)}" TargetMode="External"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_NS}">{"".join(rows)}</Relationships>'
    )


def _content_types() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{CT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>
"""


def _zip_part(docx: Path | None, name: str) -> bytes | None:
    if docx is None or not docx.is_file():
        return None
    try:
        with zipfile.ZipFile(docx) as archive:
            return archive.read(name)
    except (KeyError, zipfile.BadZipFile):
        return None


def render(template: Path, context: dict, output: Path) -> None:
    suffix = template.suffix.lower()
    out_suffix = output.suffix.lower()
    if suffix in {".xlsx", ".pptx"} or out_suffix in {".xlsx", ".pptx"}:
        raise SystemExit(
            "render_template.py renders .docx and .html only. "
            "For spreadsheets and slides, keep the markdown draft."
        )
    markdown = context.get("markdown") or ""
    title = (context.get("title") or "").strip()
    if out_suffix == ".html" or suffix == ".html":
        if context.get("content"):
            content = context["content"]
        else:
            blocks = markdown_to_blocks(markdown)
            if not title:
                title = first_heading(blocks) or output.stem
            content = blocks_to_html(blocks)
        if not title:
            title = output.stem
        template_text = template.read_text(encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(fill_html_template(template_text, title, content), encoding="utf-8")
        return
    if out_suffix == ".docx" or suffix == ".docx":
        blocks = markdown_to_blocks(markdown)
        styles = template if suffix == ".docx" else None
        blocks_to_docx(blocks, output, styles_docx=styles)
        return
    raise SystemExit(
        f"render_template.py does not render {suffix or out_suffix}. "
        "Use .docx or .html, or keep the markdown draft."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fill an HTML page or write a .docx from markdown.")
    parser.add_argument("template", type=Path)
    parser.add_argument("context_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if not args.template.is_file():
        print(f"Template not found: {args.template}", file=sys.stderr)
        return 1
    try:
        context = json.loads(args.context_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Context JSON is not valid: {exc}", file=sys.stderr)
        return 1
    if not isinstance(context, dict):
        print("Context JSON must be an object.", file=sys.stderr)
        return 1
    try:
        render(args.template, context, args.output)
    except SystemExit as exc:
        code = exc.code
        if code in (0, None):
            return 0
        if isinstance(code, str):
            print(code, file=sys.stderr)
            return 1
        return int(code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
