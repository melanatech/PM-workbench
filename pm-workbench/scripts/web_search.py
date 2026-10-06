#!/usr/bin/env python3
"""Client-side web search (stdlib only).

Amazon Bedrock rejects Claude's native WebSearch tool
("Bedrock does not support the web_search tool"). This script searches from
the local machine so competitive-scan can discover official URLs without that
server tool.

Providers (tried in order until one returns hits):
  1. DuckDuckGo HTML POST
  2. Bing HTML (used when DDG serves an anomaly/captcha page)
  3. Optional: Serper.dev if SERPER_API_KEY is set
  4. Optional: Brave Search if BRAVE_API_KEY is set

Usage:
  python3 scripts/web_search.py "Square POS reporting help"
  python3 scripts/web_search.py --json --max 8 "Toast POS reports documentation"
  python3 scripts/web_search.py --urls-only "Clover reporting help"

Exit 0 with results, 1 on usage error, 2 on network/parse failure.
"""
from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DDG_HTML = "https://html.duckduckgo.com/html/"
BING_SEARCH = "https://www.bing.com/search"


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_url(url: str) -> str:
    url = html_lib.unescape(url.strip())
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    for noise in ("msockid", "utm_source", "utm_medium", "utm_campaign"):
        qs.pop(noise, None)
    query = urllib.parse.urlencode({k: v[0] for k, v in qs.items()}, doseq=False)
    return urllib.parse.urlunparse(parsed._replace(query=query))


def _unwrap_ddg_href(href: str) -> str:
    href = html_lib.unescape(href.strip())
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return _clean_url(urllib.parse.unquote(qs["uddg"][0]))
    return _clean_url(href)


def _decode_bing_u(value: str) -> str | None:
    raw = value[2:] if value.startswith("a1") else value
    raw += "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if decoded.startswith("http"):
        return _clean_url(decoded)
    return None


def _http(url: str, *, data: bytes | None = None) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"HTTP {err.code} from {urllib.parse.urlparse(url).netloc}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"network error: {err.reason}") from err


def _dedupe(results: list[dict], max_results: int) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for hit in results:
        url = hit.get("url") or ""
        if not url.startswith("http"):
            continue
        host = urllib.parse.urlparse(url).netloc.lower()
        if any(x in host for x in ("duckduckgo.com", "bing.com", "microsoft.com")):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(hit)
        if len(out) >= max_results:
            break
    return out


def search_duckduckgo(query: str, *, max_results: int) -> list[dict]:
    data = urllib.parse.urlencode({"q": query, "b": ""}).encode("utf-8")
    body = _http(DDG_HTML, data=data)
    if "anomaly" in body.lower() and "result__a" not in body:
        return []  # captcha / bot check — try next provider
    results: list[dict] = []
    for block in re.split(r'class="result__body"', body)[1:]:
        title_m = re.search(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            re.I | re.S,
        )
        if not title_m:
            continue
        url = _unwrap_ddg_href(title_m.group(1))
        snip_m = re.search(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
            block,
            re.I | re.S,
        )
        results.append(
            {
                "title": _strip_tags(title_m.group(2)),
                "url": url,
                "snippet": _strip_tags(snip_m.group(1)) if snip_m else "",
                "provider": "duckduckgo",
            }
        )
    if not results:
        for raw in re.findall(r'href="([^"]+)"', body):
            url = _unwrap_ddg_href(raw)
            results.append({"title": "", "url": url, "snippet": "", "provider": "duckduckgo"})
    return _dedupe(results, max_results)


def search_bing(query: str, *, max_results: int) -> list[dict]:
    url = BING_SEARCH + "?" + urllib.parse.urlencode({"q": query})
    body = _http(url)
    results: list[dict] = []
    for block in body.split('class="b_algo"')[1:]:
        href_m = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"', block, re.I)
        title_m = re.search(r"<h2[^>]*>\s*<a[^>]+>(.*?)</a>", block, re.I | re.S)
        if not href_m:
            continue
        href = html_lib.unescape(href_m.group(1))
        dest = href
        if "bing.com/ck/" in href:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if "u" in qs:
                decoded = _decode_bing_u(qs["u"][0])
                if decoded:
                    dest = decoded
        snip_m = re.search(r'class="b_caption"[^>]*>.*?<p>(.*?)</p>', block, re.I | re.S)
        results.append(
            {
                "title": _strip_tags(title_m.group(1)) if title_m else "",
                "url": _clean_url(dest),
                "snippet": _strip_tags(snip_m.group(1)) if snip_m else "",
                "provider": "bing",
            }
        )
    return _dedupe(results, max_results)


def search_serper(query: str, *, max_results: int, api_key: str) -> list[dict]:
    payload = json.dumps({"q": query, "num": max_results}).encode("utf-8")
    req = urllib.request.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    results = []
    for item in data.get("organic") or []:
        results.append(
            {
                "title": item.get("title") or "",
                "url": _clean_url(item.get("link") or ""),
                "snippet": item.get("snippet") or "",
                "provider": "serper",
            }
        )
    return _dedupe(results, max_results)


def search_brave(query: str, *, max_results: int, api_key: str) -> list[dict]:
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": max_results}
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    results = []
    for item in (data.get("web") or {}).get("results") or []:
        results.append(
            {
                "title": item.get("title") or "",
                "url": _clean_url(item.get("url") or ""),
                "snippet": item.get("description") or "",
                "provider": "brave",
            }
        )
    return _dedupe(results, max_results)


def search(query: str, *, max_results: int = 8) -> list[dict]:
    """Return list of {title, url, snippet, provider}."""
    errors: list[str] = []
    providers = [
        ("duckduckgo", lambda: search_duckduckgo(query, max_results=max_results)),
        ("bing", lambda: search_bing(query, max_results=max_results)),
    ]
    serper = os.environ.get("SERPER_API_KEY", "").strip()
    if serper:
        providers.append(
            ("serper", lambda: search_serper(query, max_results=max_results, api_key=serper))
        )
    brave = os.environ.get("BRAVE_API_KEY", "").strip()
    if brave:
        providers.append(
            ("brave", lambda: search_brave(query, max_results=max_results, api_key=brave))
        )

    for name, fn in providers:
        try:
            hits = fn()
        except Exception as err:  # noqa: BLE001 — try next provider
            errors.append(f"{name}: {err}")
            continue
        if hits:
            return hits
        errors.append(f"{name}: no results")
    raise RuntimeError("; ".join(errors) if errors else "no search providers")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="+", help="search query")
    parser.add_argument("--max", type=int, default=8, help="max results (default 8)")
    parser.add_argument(
        "--json",
        action="store_true",
        help="print JSON array of {title,url,snippet,provider}",
    )
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="print one URL per line",
    )
    args = parser.parse_args(argv)
    query = " ".join(args.query).strip()
    if not query:
        print("query required", file=sys.stderr)
        return 1
    try:
        hits = search(query, max_results=max(1, args.max))
    except RuntimeError as err:
        print(f"web_search failed: {err}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    elif args.urls_only:
        for hit in hits:
            print(hit["url"])
    else:
        for i, hit in enumerate(hits, 1):
            title = hit["title"] or hit["url"]
            print(f"{i}. {title}")
            print(f"   {hit['url']}")
            if hit.get("snippet"):
                print(f"   {hit['snippet']}")
            if hit.get("provider"):
                print(f"   [{hit['provider']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
