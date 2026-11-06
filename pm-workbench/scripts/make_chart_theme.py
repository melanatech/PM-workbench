#!/usr/bin/env python3
"""Build an ECharts theme and an Altair theme from one chart token JSON file.

Usage (from the kit root):
  python3 scripts/make_chart_theme.py neutral
  python3 scripts/make_chart_theme.py assets/charts/themes/neutral.json
  python3 scripts/make_chart_theme.py /path/to/brand.json --out /path/to/generated

Checks, in order:
  1. Text on background, WCAG 2 relative luminance, ratio at least 4.5
     (the small-text threshold).
  2. The first four categorical colors are pairwise at least 80 apart in
     8-bit Euclidean RGB.

80 sits under the closest Okabe-Ito pair among that palette's first four
published colors (orange #E69F00 and yellow #F0E442, about 96 apart). Pairs
closer than 80 are treated as the same step, not two categories.

Exit 0 after writing both files. Exit 2 on a bad path, bad JSON, or a
failed check. A failed check writes nothing for that theme. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

RGB_DISTANCE_MIN = 80
CONTRAST_MIN = 4.5
ROLE_KEYS = (
    "primary",
    "comparison",
    "baseline",
    "highlight",
    "muted",
    "positive",
    "negative",
    "annotation",
)
HEX_KEYS = ("text", "muted", "gridline", "axis", "background", "surface")

KIT_ROOT = Path(__file__).resolve().parents[1]


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _parse_hex(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        _fail(f"{label} must be a #RRGGBB hex, got {value!r}")
    body = value[1:]
    if any(c not in "0123456789abcdefABCDEF" for c in body):
        _fail(f"{label} must be a #RRGGBB hex, got {value!r}")
    return "#" + body.upper()


def _rgb(hex_color: str) -> tuple[int, int, int]:
    body = hex_color[1:]
    return int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)


def _srgb_channel(channel: int) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _rgb(hex_color)
    return (
        0.2126 * _srgb_channel(r)
        + 0.7152 * _srgb_channel(g)
        + 0.0722 * _srgb_channel(b)
    )


def contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(relative_luminance(foreground), relative_luminance(background))
    darker = min(relative_luminance(foreground), relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def rgb_distance(a: str, b: str) -> float:
    ar, ag, ab = _rgb(a)
    br, bg, bb = _rgb(b)
    return math.sqrt((ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2)


def _hex_list(value: object, label: str, minimum: int) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(f"{label} must be a list of at least {minimum} hex colors")
    return [_parse_hex(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _check(theme: dict) -> None:
    ratio = contrast_ratio(theme["text"], theme["background"])
    if ratio < CONTRAST_MIN:
        _fail(
            f"contrast: text {theme['text']} on background {theme['background']} "
            f"is {ratio:.2f}, below {CONTRAST_MIN}"
        )
    colors = theme["categorical"][:4]
    for i in range(4):
        for j in range(i + 1, 4):
            distance = rgb_distance(colors[i], colors[j])
            if distance < RGB_DISTANCE_MIN:
                _fail(
                    f"distance: {colors[i]} and {colors[j]} are {distance:.1f} apart, "
                    f"below {RGB_DISTANCE_MIN}"
                )


def _load(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {path}: {exc}")
    if not isinstance(raw, dict):
        _fail(f"{path} must be a JSON object")
    name = raw.get("name")
    if (
        not isinstance(name, str)
        or not name
        or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name)
    ):
        _fail("name must be lowercase letters, digits, and hyphens")
    font = raw.get("font")
    if not isinstance(font, str) or not font.strip():
        _fail("font must be a non-empty string")
    loaded: dict = {"name": name, "font": font.strip()}
    for key in HEX_KEYS:
        loaded[key] = _parse_hex(raw.get(key), key)
    roles = raw.get("roles")
    if not isinstance(roles, dict):
        _fail("roles must be an object")
    missing = [key for key in ROLE_KEYS if key not in roles]
    if missing:
        _fail("roles missing: " + ", ".join(missing))
    loaded["roles"] = {key: _parse_hex(roles[key], f"roles.{key}") for key in ROLE_KEYS}
    loaded["categorical"] = _hex_list(raw.get("categorical"), "categorical", 4)
    loaded["sequential"] = _hex_list(raw.get("sequential"), "sequential", 2)
    loaded["diverging"] = _hex_list(raw.get("diverging"), "diverging", 2)
    notes = raw.get("notes")
    if notes is not None:
        if not isinstance(notes, str):
            _fail("notes must be a string")
        loaded["notes"] = notes
    return loaded


def _axis(theme: dict) -> dict:
    return {
        "axisLine": {"lineStyle": {"color": theme["axis"]}},
        "axisTick": {"lineStyle": {"color": theme["axis"]}},
        "axisLabel": {"color": theme["text"], "fontFamily": theme["font"]},
        "splitLine": {"lineStyle": {"color": theme["gridline"]}},
        "splitArea": {"areaStyle": {"color": [theme["background"], theme["surface"]]}},
        "nameTextStyle": {"color": theme["muted"], "fontFamily": theme["font"]},
    }


def _echarts_theme(theme: dict) -> dict:
    axis = _axis(theme)
    return {
        "color": theme["categorical"],
        "backgroundColor": theme["background"],
        "textStyle": {"color": theme["text"], "fontFamily": theme["font"]},
        "title": {
            "textStyle": {"color": theme["text"], "fontFamily": theme["font"]},
            "subtextStyle": {"color": theme["muted"], "fontFamily": theme["font"]},
        },
        "legend": {"textStyle": {"color": theme["text"], "fontFamily": theme["font"]}},
        "tooltip": {
            "backgroundColor": theme["surface"],
            "borderColor": theme["gridline"],
            "textStyle": {"color": theme["text"], "fontFamily": theme["font"]},
        },
        "categoryAxis": axis,
        "valueAxis": axis,
        "logAxis": axis,
        "timeAxis": axis,
        "visualMap": {
            "textStyle": {"color": theme["text"]},
            "color": theme["sequential"],
        },
        "toolbox": {"iconStyle": {"borderColor": theme["muted"]}},
        "graph": {"color": theme["categorical"]},
        "wb": {
            "name": theme["name"],
            "font": theme["font"],
            "text": theme["text"],
            "muted": theme["muted"],
            "gridline": theme["gridline"],
            "axis": theme["axis"],
            "background": theme["background"],
            "surface": theme["surface"],
            "roles": theme["roles"],
            "categorical": theme["categorical"],
            "sequential": theme["sequential"],
            "diverging": theme["diverging"],
            "notes": theme.get("notes", ""),
        },
    }


def _altair_config(theme: dict) -> dict:
    return {
        "config": {
            "background": theme["background"],
            "font": theme["font"],
            "view": {"stroke": "transparent"},
            "axis": {
                "labelColor": theme["text"],
                "titleColor": theme["text"],
                "labelFont": theme["font"],
                "titleFont": theme["font"],
                "gridColor": theme["gridline"],
                "domainColor": theme["axis"],
                "tickColor": theme["axis"],
            },
            "legend": {
                "labelColor": theme["text"],
                "titleColor": theme["text"],
                "labelFont": theme["font"],
                "titleFont": theme["font"],
            },
            "title": {
                "color": theme["text"],
                "subtitleColor": theme["muted"],
                "font": theme["font"],
                "subtitleFont": theme["font"],
            },
            "range": {
                "category": theme["categorical"],
                "heatmap": theme["sequential"],
                "diverging": theme["diverging"],
            },
        }
    }


def _write_echarts(path: Path, name: str, body: dict) -> None:
    payload = json.dumps(body, indent=2)
    name_js = json.dumps(name)
    text = (
        "/* Generated by scripts/make_chart_theme.py. Do not edit. */\n"
        "(function (root, factory) {\n"
        "    if (typeof define === \"function\" && define.amd) {\n"
        "        define([\"exports\", \"echarts\"], factory);\n"
        "    } else if (typeof exports === \"object\" && typeof exports.nodeName !== \"string\") {\n"
        "        factory(exports, require(\"echarts\"));\n"
        "    } else {\n"
        "        factory({}, root.echarts);\n"
        "    }\n"
        "})(typeof globalThis !== \"undefined\" ? globalThis : this, function (exports, echarts) {\n"
        f"    var theme = {payload};\n"
        "    var host = typeof globalThis !== \"undefined\" ? globalThis : window;\n"
        "    host.WB_THEMES = host.WB_THEMES || {};\n"
        f"    host.WB_THEMES[{name_js}] = theme;\n"
        "    if (!echarts) {\n"
        "        if (typeof console !== \"undefined\" && console.error) {\n"
        "            console.error(\"ECharts is not Loaded\");\n"
        "        }\n"
        "        return;\n"
        "    }\n"
        f"    echarts.registerTheme({name_js}, theme);\n"
        "});\n"
    )
    path.write_text(text, encoding="utf-8")


def _write_altair(path: Path, name: str, config: dict) -> None:
    literal = json.dumps(json.dumps(config))
    name_py = json.dumps(name)
    text = (
        f'"""Generated Altair theme register for {name}. Do not edit."""\n'
        "import json\n"
        "\n"
        f"_CONFIG = json.loads({literal})\n"
        "\n"
        "\n"
        "def config():\n"
        "    return _CONFIG\n"
        "\n"
        "\n"
        "def register():\n"
        "    import altair as alt\n"
        "\n"
        f"    alt.themes.register({name_py}, config)\n"
        "    return config\n"
    )
    path.write_text(text, encoding="utf-8")


def _resolve_theme(arg: str) -> Path:
    direct = Path(arg)
    if direct.is_file():
        return direct.resolve()
    name = arg if arg.endswith(".json") else arg + ".json"
    candidate = KIT_ROOT / "assets" / "charts" / "themes" / name
    if candidate.is_file():
        return candidate.resolve()
    _fail(f"Theme file not found: {arg}")
    raise AssertionError("unreachable")


def _output_dir(theme_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    try:
        theme_path.relative_to(KIT_ROOT)
    except ValueError:
        if theme_path.parent.name == "themes":
            return theme_path.parent.parent / "generated"
        return theme_path.parent / "generated"
    return KIT_ROOT / "assets" / "charts" / "generated"


def build(theme_path: Path, out_dir: Path) -> tuple[Path, Path]:
    theme = _load(theme_path)
    _check(theme)
    out_dir.mkdir(parents=True, exist_ok=True)
    js_path = out_dir / f"{theme['name']}.theme.js"
    py_path = out_dir / f"{theme['name']}.altair.py"
    _write_echarts(js_path, theme["name"], _echarts_theme(theme))
    _write_altair(py_path, theme["name"], _altair_config(theme))
    return js_path, py_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "themes",
        nargs="+",
        help="Theme name (for example neutral) or a path to a theme JSON file.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help=(
            "Directory for the generated files. "
            "Default is assets/charts/generated inside the kit when the theme "
            "file is in the kit. A theme file outside the kit writes to "
            "generated/ next to its themes/ folder."
        ),
    )
    args = parser.parse_args(argv)
    for arg in args.themes:
        theme_path = _resolve_theme(arg)
        out_dir = _output_dir(theme_path, args.out)
        js_path, py_path = build(theme_path, out_dir)
        print(js_path)
        print(py_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
