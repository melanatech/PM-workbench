#!/usr/bin/env python3
"""Publish a workspace draft as neutral, audience-aware files.

The internal draft stays untouched. Register ids, workspace paths, and
internal tags in that draft are rewritten into citations an outside reader
can recognize. A ``*.sources.md`` sidecar keeps the id-to-label map.

Workspace aliases are not a blanket ban. ``external_treatment`` on each row
of ``reference/context/workspace-aliases.md`` is ``internal_only`` (block),
``expand`` or ``neutralize`` (replace with ``external_value``), or
``preserve`` (leave the phrase). A missing or unknown treatment blocks
publishing and names the alias.

Citations are links only when ``reference/context/audiences.md`` says this
audience can open that system. A missing file, or one still marked
``status: template``, grants no links.

``[NEEDS INPUT]`` blocks publishing: nothing is written.
An id that is not in a register fails the command.

Formats: md, html, docx, confluence, slack. Confluence storage-format and
Slack mrkdwn are local drafts. This script never creates a wiki page and
never sends a chat message.

Usage:
  python3 scripts/publish.py <draft.md> --root <live>
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import render_template  # noqa: E402

HOOKS = KIT_ROOT / ".claude" / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))
import check_external_artifact as external_artifact  # noqa: E402

DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
REGISTER_RE = re.compile(r"\b((?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5})\b")
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d{1,6})\b")
REGISTER_KEY_RE = re.compile(r"^(?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5}$")
NEEDS_INPUT_RE = re.compile(r"\[NEEDS INPUT[^\]]*\]", re.I)
HYPOTHESIS_RE = re.compile(r"\[hypothesis(?::\s*([^\]]*))?\]", re.I)
TRAINING_RE = re.compile(r"\[external::training\]", re.I)
METRIC_RE = re.compile(r"\bmetric:([A-Za-z0-9][A-Za-z0-9_/-]{0,80})")
USERS_RE = re.compile(r"/Users/[A-Za-z0-9_./\-]+")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
_PATH_PREFIX = (
    r"(?:inbox|archive|outputs|registers|state|logs|learning|reference|"
    r"prototypes|drafts|repos|scripts|tools|fixtures|\.claude)/"
)
_PATH_EXT = r"(?:md|csv|txt|json|yml|yaml|html|htm|pdf|py|docx|pptx|xlsx|png)"
PATH_RE = re.compile(
    rf"(?<![\w./])({_PATH_PREFIX}"
    rf"(?:[A-Za-z0-9_.\-]+/)*"
    rf"[A-Za-z0-9_.\- ]*?\.{_PATH_EXT})"
)
PATH_PREFIXES = (
    "inbox/", "archive/", "outputs/", "registers/", "state/", "logs/",
    "learning/", "reference/", "prototypes/", "drafts/", "repos/",
    "scripts/", "tools/", "fixtures/", ".claude/",
)
MD_LINK_RE = re.compile(r"^\[([^\]]*)\]\(([^)]+)\)$")
UPLOAD_EXT = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx", ".key", ".png"}
FORMATS = ("md", "html", "docx", "confluence", "slack")
SYSTEM_WORDS = {
    "jira": "jira",
    "tracker": "jira",
    "ticket": "jira",
    "tickets": "jira",
    "confluence": "confluence",
    "wiki": "confluence",
    "slack": "slack",
    "chat": "slack",
    "dashboard": "dashboard",
    "dashboards": "dashboard",
}


class PublishError(Exception):
    """The draft cannot be published as written."""


class NeedsInputError(PublishError):
    """``[NEEDS INPUT]`` is still in the draft."""

    def __init__(self, placeholders: list[str]):
        self.placeholders = placeholders
        shown = "; ".join(placeholders)
        super().__init__(f"Publishing blocked until [NEEDS INPUT] is resolved: {shown}")


@dataclass
class Citation:
    text: str
    url: str | None = None

    def markdown(self) -> str:
        if self.url:
            return f"[{self.text}]({self.url})"
        return self.text

    @property
    def key(self) -> str:
        return f"{self.text}|{self.url or ''}"


@dataclass
class Access:
    jira: bool = False
    confluence: bool = False
    slack: bool = False
    dashboard: bool = False
    note: str = ""

    def allows(self, system: str) -> bool:
        return bool(getattr(self, system, False))


@dataclass
class Footnote:
    number: int
    citation: Citation
    labels: list[str] = field(default_factory=list)


@dataclass
class Published:
    body: str
    footnotes: list[Footnote]
    files: list[Path]
    access_note: str


def publish_file(
    draft: Path,
    root: Path,
    formats: list[str] | None = None,
    output_name: str | None = None,
) -> Published:
    """Neutralize ``draft`` and write the requested formats under outputs/external/."""
    draft = draft.resolve()
    root = root.resolve()
    raw = draft.read_text(encoding="utf-8")
    placeholders = NEEDS_INPUT_RE.findall(raw)
    if placeholders:
        raise NeedsInputError(placeholders)
    meta, body = _split_frontmatter(raw)
    aliases = external_artifact.load_aliases(root)
    alias_problems = external_artifact.alias_publish_problems(body, aliases)
    if alias_problems:
        raise PublishError("Publishing blocked: " + "; ".join(alias_problems))
    body = external_artifact.apply_alias_treatments(body, aliases)
    chosen = formats or _formats_from(meta.get("formats", ""))
    if not chosen:
        chosen = ["md"]
    unknown = [item for item in chosen if item not in FORMATS]
    if unknown:
        raise PublishError(f"Unknown format: {', '.join(unknown)}")
    name = output_name or _strip_placeholder(meta.get("output", ""))
    access = load_access(root / "reference" / "context" / "audiences.md", name)
    workspace = Workspace.load(root)
    published_body, footnotes = neutralize(body, workspace, access)
    alias_problems = external_artifact.alias_publish_problems(published_body, aliases)
    if alias_problems:
        raise PublishError("Publishing blocked: " + "; ".join(alias_problems))
    external = "\n".join([
        "---",
        "audience: external",
        "formats: [" + ", ".join(chosen) + "]",
        "---",
        "",
        published_body,
    ])
    banned = external_artifact.find_banned(
        published_body,
        external_artifact.load_alias_phrases(root),
    )
    if banned:
        raise PublishError(
            "Neutralized draft still has workspace-only labels: " + "; ".join(banned)
        )
    sidecar = draft.with_name(draft.stem + ".sources.md")
    out_dir = root / "outputs" / "external"
    stem = draft.stem
    written: list[Path] = []
    # Resolve every citation before creating files. neutralize already did.
    blocks = render_template.markdown_to_blocks(published_body)
    title = render_template.first_heading(blocks) or stem
    to_write: list[tuple[Path, str | None]] = []
    binary: list[tuple[Path, list]] = []
    if "md" in chosen:
        to_write.append((out_dir / f"{stem}.md", external))
    if "html" in chosen:
        template = _html_template(root)
        content = render_template.blocks_to_html(blocks)
        page = render_template.fill_html_template(
            template,
            title,
            "<!-- Local draft. Do not publish until the author explicitly approves (Tier 3). -->\n"
            + content,
        )
        to_write.append((out_dir / f"{stem}.html", page))
    if "confluence" in chosen:
        to_write.append((out_dir / f"{stem}.confluence.xml", render_template.blocks_to_confluence(blocks)))
    if "slack" in chosen:
        parts = render_template.blocks_to_slack(blocks)
        if len(parts) == 1:
            to_write.append((out_dir / f"{stem}.slack.md", parts[0]))
        else:
            for index, part in enumerate(parts, start=1):
                to_write.append((out_dir / f"{stem}.slack-{index}.md", part))
    if "docx" in chosen:
        binary.append((out_dir / f"{stem}.docx", blocks))
    sidecar_text = _sidecar(footnotes, access.note, draft, root)
    # Sidecar is internal. Write it beside the draft, not under outputs/external/.
    _write_text(sidecar, sidecar_text)
    written.append(sidecar)
    styles = _company_styles(root)
    for path, blocks_for_doc in binary:
        render_template.blocks_to_docx(blocks_for_doc, path, styles_docx=styles)
        written.append(path)
    for path, text in to_write:
        _write_text(path, text)
        written.append(path)
    return Published(body=published_body, footnotes=footnotes, files=written, access_note=access.note)


def neutralize(body: str, workspace: "Workspace", access: Access) -> tuple[str, list[Footnote]]:
    placeholders = NEEDS_INPUT_RE.findall(body)
    if placeholders:
        raise NeedsInputError(placeholders)
    hits = _collect_hits(body)
    footnotes: list[Footnote] = []
    by_key: dict[str, Footnote] = {}
    replacements: list[tuple[int, int, str]] = []
    for hit in hits:
        citation = _resolve_hit(hit, workspace, access)
        if hit.kind in {"hypothesis", "training"}:
            replacements.append((hit.start, hit.end, citation.text))
            continue
        note = by_key.get(citation.key)
        if note is None:
            note = Footnote(number=len(footnotes) + 1, citation=citation, labels=[])
            footnotes.append(note)
            by_key[citation.key] = note
        if hit.label not in note.labels:
            note.labels.append(hit.label)
        replacements.append((hit.start, hit.end, f"[^{note.number}]"))
    rendered = body
    for start, end, text in sorted(replacements, key=lambda item: item[0], reverse=True):
        rendered = rendered[:start] + text + rendered[end:]
    if footnotes:
        lines = ["", "## Sources", ""]
        for note in footnotes:
            lines.append(f"[^{note.number}]: {note.citation.markdown()}")
        rendered = rendered.rstrip() + "\n" + "\n".join(lines) + "\n"
    return rendered, footnotes


@dataclass
class Hit:
    start: int
    end: int
    kind: str
    label: str
    extra: str = ""


def _collect_hits(body: str) -> list[Hit]:
    found: list[Hit] = []
    for match in HYPOTHESIS_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "hypothesis", match.group(0), match.group(1) or ""))
    for match in TRAINING_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "training", match.group(0)))
    for match in REGISTER_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "register", match.group(1)))
    for match in METRIC_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "metric", match.group(0), match.group(1).strip()))
    for match in USERS_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "users", match.group(0)))
    for match in PATH_RE.finditer(body):
        found.append(Hit(match.start(), match.end(), "path", match.group(1)))
    for match in JIRA_KEY_RE.finditer(body):
        key = match.group(1)
        if REGISTER_KEY_RE.match(key):
            continue
        start = match.start(1)
        prefix = body[max(0, start - 5):start]
        if prefix.lower().endswith("jira "):
            start = start - 5
        found.append(Hit(start, match.end(1), "jira", key))
    return _drop_overlaps(found)


def _drop_overlaps(hits: list[Hit]) -> list[Hit]:
    ordered = sorted(hits, key=lambda hit: (hit.start, -(hit.end - hit.start)))
    kept: list[Hit] = []
    cursor = -1
    for hit in ordered:
        if hit.start < cursor:
            continue
        kept.append(hit)
        cursor = hit.end
    return kept


def _resolve_hit(hit: Hit, workspace: "Workspace", access: Access) -> Citation:
    if hit.kind == "hypothesis":
        phrase = (hit.extra or "").strip().strip("\"'")
        return Citation(phrase or "unverified")
    if hit.kind == "training":
        return Citation("unverified")
    if hit.kind == "register":
        return workspace.resolve_id(hit.label, access)
    if hit.kind == "metric":
        return workspace.resolve_metric(hit.extra, access)
    if hit.kind == "jira":
        return workspace.resolve_jira_key(hit.label, access)
    if hit.kind == "users":
        return classify_source(hit.label, "", "", workspace.root, access, workspace.metrics)
    if hit.kind == "path":
        return classify_source(hit.label, "", "", workspace.root, access, workspace.metrics)
    raise PublishError(f"Unresolvable label: {hit.label}")


def classify_source(
    source: str,
    source_app: str,
    date: str,
    root: Path,
    access: Access,
    metrics: list[dict],
) -> Citation:
    """Map one register source (or a raw path) to a neutral citation."""
    raw = unwrap_link(source).strip()
    app = (source_app or "").strip().lower()
    extracted = _extract_workspace_path(raw)
    target = extracted or raw
    if app == "slack" or target.lower().startswith("slack:") or "slack" in app:
        return _as_slack(target, date)
    if "/meetings/" in target.replace("\\", "/") or app == "meeting":
        return _as_meeting(target, date, root)
    if app == "confluence" or "confluence" in target.lower() or "/wiki/" in target.lower():
        return _as_confluence(target, access)
    if app in {"jira", "tracker"} or "/browse/" in target.lower():
        return _as_jira(target, access)
    if app in {"dashboard", "metric"} or "dashboard:" in target.lower() or "okr-history" in target:
        return _as_dashboard_source(target, date, access, metrics)
    if _is_upload(target, app):
        return _as_upload(target)
    if _looks_like_workspace_path(target) or target.startswith("/Users/"):
        return _as_file(target, root)
    key = _lone_jira_key(target)
    if key:
        return _as_jira(target, access)
    raise PublishError(f"Unresolvable source: {source}")


def _as_meeting(source: str, date: str, root: Path) -> Citation:
    path = _extract_workspace_path(source) or source
    title = _document_title(root, path) or _humanize_stem(path)
    found = DATE_RE.search(path) or DATE_RE.search(date or "") or DATE_RE.search(source)
    if not found:
        raise PublishError(f"Meeting source has no date: {source}")
    if not title:
        raise PublishError(f"Meeting source has no title: {source}")
    return Citation(f"{title}, {found.group(1)} (meeting notes)")


def _as_upload(source: str) -> Citation:
    name = Path(source.replace("\\", "/")).name
    if not name or name in {".", "/"}:
        raise PublishError(f"Uploaded document has no file name: {source}")
    return Citation(f"Uploaded document: {name}")


def _as_jira(source: str, access: Access) -> Citation:
    keys = [key for key in JIRA_KEY_RE.findall(source) if not REGISTER_KEY_RE.match(key)]
    if not keys:
        raise PublishError(f"Jira source has no issue key: {source}")
    key = keys[0]
    url = _http_url(source)
    if access.jira and url:
        return Citation(f"Jira {key}", url=url)
    return Citation(f"Jira {key}")


def _as_confluence(source: str, access: Access) -> Citation:
    title, url = _confluence_title_and_url(source)
    if not title:
        raise PublishError(f"Confluence source has no page title: {source}")
    if access.confluence and url:
        return Citation(f"Confluence: {title}", url=url)
    return Citation(f"Confluence: {title}")


def _as_slack(source: str, date: str) -> Citation:
    channel = re.search(r"#([A-Za-z0-9_-]+)", source)
    if not channel:
        raise PublishError(f"Slack source has no channel: {source}")
    found = DATE_RE.search(source) or DATE_RE.search(date or "")
    if not found:
        raise PublishError(f"Slack source has no date: {source}")
    return Citation(f"Slack #{channel.group(1)}, {found.group(1)}")


def _as_dashboard_source(source: str, date: str, access: Access, metrics: list[dict]) -> Citation:
    name = ""
    marker = re.search(r"dashboard:\s*([^|]+)", source, re.I)
    if marker:
        name = marker.group(1).strip()
    elif metrics:
        # A register row that points at the metric history names the metric in the path fragment.
        fragment = source.split("#")[-1].strip()
        if fragment and fragment != source:
            name = fragment
    if not name:
        raise PublishError(f"Dashboard source has no name: {source}")
    found = DATE_RE.search(source) or DATE_RE.search(date or "")
    as_of = found.group(1) if found else ""
    if not as_of:
        raise PublishError(f"Dashboard source has no as-of date: {source}")
    url = _http_url(source) if access.dashboard else None
    return Citation(f"Internal dashboard: {name}, as of {as_of}", url=url)


def _as_file(source: str, root: Path) -> Citation:
    path = source
    if path.startswith("/Users/"):
        name = Path(path).name
        if Path(name).suffix.lower() in UPLOAD_EXT:
            return Citation(f"Uploaded document: {name}")
        if not name:
            raise PublishError(f"Path has no file name: {source}")
        return Citation(name)
    title = _document_title(root, path) or Path(path.replace("\\", "/")).name
    if not title:
        raise PublishError(f"Workspace path has no file name: {source}")
    return Citation(title)


def _is_upload(source: str, app: str) -> bool:
    norm = source.replace("\\", "/")
    if "/meetings/" in norm:
        return False
    suffix = Path(norm).suffix.lower()
    if suffix in UPLOAD_EXT:
        return True
    if "inbox/documents/" in norm or "archive/documents/" in norm:
        return True
    return app in {"upload", "document", "deck"}


def _looks_like_workspace_path(source: str) -> bool:
    return _extract_workspace_path(source) is not None or source.startswith("/Users/")


def _extract_workspace_path(source: str) -> str | None:
    stripped = source.strip().rstrip(".,;:")
    if stripped.startswith(PATH_PREFIXES):
        return stripped
    match = PATH_RE.search(source)
    if not match:
        return None
    return match.group(1).rstrip(".,;:")


def _lone_jira_key(source: str) -> str | None:
    match = re.fullmatch(r"\s*([A-Z][A-Z0-9]{1,9}-\d{1,6})\s*", source)
    if not match or REGISTER_KEY_RE.match(match.group(1)):
        return None
    return match.group(1)


def _confluence_title_and_url(source: str) -> tuple[str, str | None]:
    url = _http_url(source)
    if "|" in source and not source.strip().startswith("http"):
        title = source.split("|", 1)[0].strip()
        return title, url
    if url:
        from urllib.parse import unquote, urlparse
        slug = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
        slug = slug.replace("+", " ").replace("-", " ").strip()
        if re.fullmatch(r"\d+", slug):
            slug = ""
        return slug, url
    text = source.strip()
    text = re.sub(r"(?i)^confluence:\s*", "", text)
    return text, None


def _http_url(source: str) -> str | None:
    match = re.search(r"https?://[^\s|>]+", source)
    return match.group(0).rstrip(".,)") if match else None


def _document_title(root: Path, rel: str) -> str | None:
    path = _safe_join(root, rel)
    if path is None or not path.is_file():
        return None
    if path.suffix.lower() not in {".md", ".txt", ".html"}:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return None


def _safe_join(root: Path, rel: str) -> Path | None:
    rel = rel.replace("\\", "/").lstrip("/")
    if rel.startswith("Users/"):
        return None
    try:
        path = (root / rel).resolve()
    except OSError:
        return None
    if not str(path).startswith(str(root.resolve())):
        return None
    return path


def _humanize_stem(path: str) -> str:
    stem = Path(path.replace("\\", "/")).stem
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    stem = stem.replace("-", " ").replace("_", " ").strip()
    if not stem:
        return ""
    return stem[:1].upper() + stem[1:]


def unwrap_link(source: str) -> str:
    match = MD_LINK_RE.match(source.strip())
    if match:
        return match.group(2).strip()
    return source.strip()


@dataclass
class Workspace:
    root: Path
    rows: dict[str, dict]
    metrics: list[dict]
    jira_urls: dict[str, str]

    @classmethod
    def load(cls, root: Path) -> "Workspace":
        registers = root / "registers"
        rows: dict[str, dict] = {}
        for name, key in (
            ("decisions.csv", "id"),
            ("commitments.csv", "id"),
            ("risks.csv", "id"),
            ("initiatives.csv", "id"),
            ("todos.csv", "id"),
            ("evidence.csv", "evidence_id"),
        ):
            for row in _read_csv(registers / name):
                ident = (row.get(key) or "").strip()
                if ident:
                    rows[ident] = row
        metrics = _read_csv(root / "state" / "okr-history.csv")
        jira_urls: dict[str, str] = {}
        for row in rows.values():
            blob = " ".join(row.values())
            url = _http_url(blob)
            if not url or "/browse/" not in url and "jira" not in url.lower():
                continue
            for key in JIRA_KEY_RE.findall(blob):
                if not REGISTER_KEY_RE.match(key):
                    jira_urls.setdefault(key, url)
        return cls(root=root, rows=rows, metrics=metrics, jira_urls=jira_urls)

    def resolve_id(self, ident: str, access: Access) -> Citation:
        row = self.rows.get(ident)
        if row is None:
            raise PublishError(f"Unresolvable register id {ident}: not in registers")
        source, app, date = _row_source(ident, row)
        if not source.strip():
            raise PublishError(f"Unresolvable register id {ident}: no source to cite")
        try:
            return classify_source(source, app, date, self.root, access, self.metrics)
        except PublishError as exc:
            raise PublishError(f"Unresolvable register id {ident}: {exc}") from exc

    def resolve_metric(self, name: str, access: Access) -> Citation:
        matches = [row for row in self.metrics if (row.get("metric") or "").strip() == name]
        if not matches:
            raise PublishError(f"Unresolvable metric: {name}")
        matches.sort(key=lambda row: row.get("as_of_date") or "")
        row = matches[-1]
        as_of = (row.get("as_of_date") or "").strip()
        if not DATE_RE.search(as_of):
            raise PublishError(f"Unresolvable metric: {name} has no as-of date")
        url = None
        source = (row.get("source") or "").strip()
        if access.dashboard:
            url = _http_url(source)
        return Citation(f"Internal dashboard: {name}, as of {as_of}", url=url)

    def resolve_jira_key(self, key: str, access: Access) -> Citation:
        url = self.jira_urls.get(key) if access.jira else None
        if access.jira and url:
            return Citation(f"Jira {key}", url=url)
        return Citation(f"Jira {key}")


def _row_source(ident: str, row: dict) -> tuple[str, str, str]:
    prefix = ident.split("-", 1)[0]
    if prefix == "DEC":
        return row.get("source_link") or "", "", row.get("date") or ""
    if prefix == "COM":
        return row.get("source") or "", "", row.get("last_updated") or row.get("due_date") or ""
    if prefix == "RISK":
        return row.get("source") or "", "", row.get("date_raised") or ""
    if prefix == "EV":
        return row.get("source_url") or "", row.get("source_app") or "", row.get("source_date") or row.get("capture_date") or ""
    if prefix == "TODO":
        return row.get("source") or "", "", row.get("last_updated") or row.get("created") or ""
    if prefix == "INIT":
        for column in ("prd", "launch", "prototype", "experiment"):
            value = (row.get(column) or "").strip()
            if value:
                return value, "file", row.get("last_updated") or ""
        return "", "", row.get("last_updated") or ""
    return "", "", ""


def load_access(path: Path, output_name: str) -> Access:
    if not path.is_file():
        return Access(note="audiences.md is missing; citations are plain text.")
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?m)^status:\s*template\s*$", text):
        return Access(note="audiences.md is still a template; citations are plain text.")
    if not output_name:
        return Access(note="No output name on the draft; citations are plain text.")
    wanted = output_name.casefold()
    for row in _markdown_rows(text):
        cells = row
        if len(cells) < 6:
            continue
        label = _strip_placeholder(cells[0]).casefold()
        if label != wanted:
            continue
        systems = cells[5]
        if systems.strip().startswith("["):
            return Access(note=f"Audience row '{output_name}' is still a placeholder; citations are plain text.")
        flags = _system_flags(systems)
        return Access(
            jira="jira" in flags,
            confluence="confluence" in flags,
            slack="slack" in flags,
            dashboard="dashboard" in flags,
            note=f"Audience row '{output_name}'. Link systems: {', '.join(sorted(flags)) or 'none'}.",
        )
    return Access(note=f"No audience row for '{output_name}'; citations are plain text.")


def _system_flags(cell: str) -> set[str]:
    flags: set[str] = set()
    for word in re.findall(r"[A-Za-z]+", cell.casefold()):
        mapped = SYSTEM_WORDS.get(word)
        if mapped:
            flags.add(mapped)
    return flags


def _markdown_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= set("-: "):
            continue
        if cells[0].casefold() == "output":
            continue
        rows.append(cells)
    return rows


def _strip_placeholder(value: str) -> str:
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    return text


def _formats_from(value: str) -> list[str]:
    inner = value.strip().strip("[]")
    if not inner:
        return []
    return [part.strip() for part in inner.split(",") if part.strip()]


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, text[match.end():]


def _sidecar(footnotes: list[Footnote], note: str, draft: Path, root: Path) -> str:
    lines = [
        "# Source map",
        "",
        "Internal mapping for the published draft. This file stays in the workspace.",
        "",
        note,
        "",
        "| Footnote | Internal label | Neutral citation |",
        "|---|---|---|",
    ]
    if not footnotes:
        lines.append("| | | No workspace labels to rewrite. |")
    for item in footnotes:
        for label in item.labels:
            lines.append(
                "| "
                + " | ".join([
                    str(item.number),
                    _sidecar_label(label, draft, root),
                    item.citation.text.replace("|", "/"),
                ])
                + " |"
            )
    lines.append("")
    return "\n".join(lines)


def _sidecar_label(label: str, draft: Path, root: Path) -> str:
    del draft  # the href is workspace-relative so the link check can see it
    path = _extract_workspace_path(label)
    if not path:
        return label.replace("|", "/")
    target = root / path
    if not target.exists():
        return path.replace("|", "/")
    return f"[{path}]({path})"


def _html_template(root: Path) -> str:
    live = root / "reference" / "templates" / "formatted" / "page.html"
    kit = KIT_ROOT / "reference" / "templates" / "formatted" / "page.html"
    path = live if live.is_file() else kit
    if not path.is_file():
        raise PublishError(f"HTML template not found: {kit}")
    return path.read_text(encoding="utf-8")


def _company_styles(root: Path) -> Path | None:
    folders = [
        root / "reference" / "templates" / "formatted",
        KIT_ROOT / "reference" / "templates" / "formatted",
    ]
    seen: set[Path] = set()
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.docx")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            return path
    return None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a draft with neutral citations. Local files only.")
    parser.add_argument("draft", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--formats", default="", help="Comma-separated: md,html,docx,confluence,slack")
    parser.add_argument("--output-name", default="", help="Audiences table row, first column")
    args = parser.parse_args(argv)
    formats = [part.strip() for part in args.formats.split(",") if part.strip()] or None
    try:
        result = publish_file(
            args.draft,
            args.root,
            formats=formats,
            output_name=args.output_name or None,
        )
    except NeedsInputError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except PublishError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    root = args.root.resolve()
    for path in result.files:
        try:
            print(path.resolve().relative_to(root))
        except ValueError:
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
