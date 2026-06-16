#!/usr/bin/env -S uv run python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///

"""
analyze_site.py — Extract CSS custom properties for terratheme-sites theming.

Launches a headless browser, navigates to a URL, extracts all CSS custom
properties (--* variables), categorizes them semantically, and outputs:

  1. A categorized variable listing with computed values
  2. A skeleton site config template (with var(--tt-????) placeholders)
  3. A suggested registry entry

Intended to be piped or pasted to an LLM — the human/LLM maps each site
variable to the appropriate --tt-* token to produce the final site config.

Usage:
    uv run tools/analyze_site.py https://example.com
    uv run tools/analyze_site.py https://example.com -o /tmp/example.json
    uv run tools/analyze_site.py https://example.com --template
    uv run tools/analyze_site.py https://example.com --registry
    uv run tools/analyze_site.py https://example.com --raw
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

TT_TOKENS = [
    ("bottom", "Deepest background"),
    ("low", "Low-elevation background"),
    ("base", "Main surface background"),
    ("high", "Elevated surface"),
    ("top", "Foremost surface"),
    ("standard", "Primary text/icon"),
    ("muted", "Secondary text/icon"),
    ("c0", "Accent 0 (darkest)"),
    ("c1", "Accent 1"),
    ("c2", "Accent 2"),
    ("c3", "Accent 3"),
    ("c4", "Accent 4 (loudest)"),
    ("on_c0", "Text on c0"),
    ("on_c1", "Text on c1"),
    ("on_c2", "Text on c2"),
    ("on_c3", "Text on c3"),
    ("on_c4", "Text on c4"),
    ("error", "Error color"),
    ("on_error", "Text on error"),
    ("outline", "Borders/outlines"),
]

TT_DERIVED = [
    ("outline-variant", "outline at 55% opacity"),
    ("scrim", "Overlay scrim"),
    ("inverse-base", "Opposite mode's base"),
    ("inverse-standard", "Opposite mode's standard"),
]


def is_color_value(value: str) -> bool:
    if not value:
        return False
    if value.startswith("#") and re.match(r"^#[0-9a-fA-F]{3,8}$", value):
        return True
    if value.startswith(("rgb(", "rgba(", "hsl(", "hsla(", "hwb(", "lch(", "lab(", "oklch(", "oklab(", "color(")):
        return True
    if value in ("transparent", "currentColor", "inherit", "initial", "unset"):
        return True
    if value.startswith("var(") or value.startswith("color-mix("):
        return True
    if value.startswith("[unresolved]"):
        return True
    return False


def categorize_var(name: str) -> str:
    name_lower = name.lower()
    if re.search(r"\b(bg|background|surface|canvas|base|card|tile|well|panel)\b", name_lower):
        return "background"
    if (
        re.search(r"\b(fg|foreground|text|color|heading|body|label|title|caption)\b", name_lower)
        and "border" not in name_lower
    ):
        return "foreground"
    if re.search(r"\b(border|outline|divider|separator|rule|stroke)\b", name_lower):
        return "border"
    if re.search(
        r"\b(button|btn|control|input|field|tab|chip|badge|switch|checkbox|radio|slider|track)\b",
        name_lower,
    ):
        return "control"
    if re.search(r"\b(shadow|elevation|depth|drop-shadow|box-shadow|inset-shadow)\b", name_lower):
        return "shadow"
    if re.search(r"\b(accent|focus|selection|highlight|caret|cursor|active|selected|link|visited)\b", name_lower):
        return "accent"
    if re.search(r"\b(icon|svg|logo)\b", name_lower):
        return "icon"
    if re.search(
        r"\b(danger|error|warning|success|info|done|sponsors|severe|critical)\b", name_lower
    ):
        return "semantic"
    if re.search(r"\b(overlay|modal|dialog|popover|popup|tooltip|toast|banner|menu|dropdown)\b", name_lower):
        return "overlay"
    if re.search(r"\b(code|pre|mono|font|syntax|token)\b", name_lower):
        return "code"
    return "other"


def extract_variables(page) -> dict[str, str]:
    script = """
    () => {
        const vars = {};

        // 1. getComputedStyle — resolved values
        const cs = getComputedStyle(document.documentElement);
        for (const prop of cs) {
            if (prop.startsWith('--')) {
                vars[prop] = cs.getPropertyValue(prop).trim();
            }
        }

        // 2. Same-origin stylesheet rules — raw var()/color-mix() expressions
        try {
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        if (rule.style) {
                            for (const prop of rule.style) {
                                if (prop.startsWith('--')) {
                                    const val = rule.style.getPropertyValue(prop).trim();
                                    if (val && !vars[prop]) {
                                        vars[prop] = val;
                                    }
                                }
                            }
                        }
                        if (rule.cssText) {
                            const matches = rule.cssText.matchAll(/--[a-zA-Z0-9_-]+/g);
                            for (const m of matches) {
                                const prop = m[0];
                                if (!vars[prop]) {
                                    vars[prop] = '[unresolved]';
                                }
                            }
                        }
                    }
                } catch (e) {}
            }
        } catch (e) {}

        // 3. Inline styles on html/body
        for (const el of [document.documentElement, document.body]) {
            if (el && el.style) {
                for (const prop of el.style) {
                    if (prop.startsWith('--') && !vars[prop]) {
                        vars[prop] = el.style.getPropertyValue(prop).trim();
                    }
                }
            }
        }

        return vars;
    }
    """
    try:
        raw = page.evaluate(script)
        if isinstance(raw, dict):
            return raw
    except Exception as e:
        print(f"Warning: could not extract variables: {e}", file=sys.stderr)
    return {}


def categorize_variables(raw: dict[str, str]) -> dict[str, dict[str, str]]:
    categories = {
        "background": {},
        "foreground": {},
        "border": {},
        "control": {},
        "shadow": {},
        "accent": {},
        "icon": {},
        "semantic": {},
        "overlay": {},
        "code": {},
        "other": {},
    }
    for name, value in raw.items():
        cat = categorize_var(name)
        categories[cat][name] = value
    return categories


def build_match_pattern(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    scheme = parsed.scheme or "https"
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return f"{scheme}://{hostname}/*"


def suggest_id_and_name(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    hostname = hostname.removeprefix("www.").removesuffix(".com").removesuffix(".org").removesuffix(".net").removesuffix(".io")
    parts = hostname.split(".")
    domain = parts[0] if parts else hostname
    name = domain.capitalize()
    return domain, name


def build_registry_entry(url: str) -> dict[str, Any]:
    site_id, name = suggest_id_and_name(url)
    return {
        "id": site_id,
        "name": name,
        "matches": [build_match_pattern(url)],
        "path": f"sites/{site_id}.json",
    }


def build_site_config_template(variables: dict[str, str], url: str) -> dict[str, Any]:
    cats = categorize_variables(variables)

    color_vars = {n: v for n, v in variables.items() if is_color_value(v)}

    category_hints = {
        "background": "/* Background: bottom (deepest) → low → base → high → top (foremost) */",
        "foreground": "/* Text: standard (primary) / muted (secondary) */",
        "border": "/* Border: outline / outline-variant (55% opacity) */",
        "control": "/* Controls: low/base for bg, standard/muted for text, outline for border */",
        "shadow": "/* Shadows: typically transparent or mix-in */",
        "accent": "/* Accent: c4 (primary), others for variants; on_c4 for text-on-accent */",
        "icon": "/* Icons: standard (active) / muted (inactive) */",
        "semantic": "/* Semantic: error/on_error (danger), c1 (warning), c2 (success) */",
        "overlay": "/* Overlays: high for background, scrim for backdrop */",
        "code": "/* Code: low for background, standard for text */",
        "other": "/* Uncategorized — review manually */",
    }

    color_cats = categorize_variables(color_vars)

    set_map: dict[str, str] = {}
    for cat in [
        "background",
        "foreground",
        "border",
        "control",
        "shadow",
        "accent",
        "icon",
        "semantic",
        "overlay",
        "code",
        "other",
    ]:
        cat_vars = color_cats.get(cat, {})
        if cat_vars:
            for var_name in cat_vars:
                set_map[var_name] = "var(--tt-????)"

    return {
        "version": 2,
        "match": [build_match_pattern(url)],
        "rules": [
            {
                "selector": ":root",
                "important": True,
                "set": set_map,
            }
        ],
    }


def generate_tt_reference() -> list[str]:
    lines = []
    lines.append("Available --tt-* tokens (injected by the content script):")
    for token, desc in TT_TOKENS:
        lines.append(f"  --tt-{token:<20} {desc}")
    lines.append("")
    lines.append("Derived tokens (computed from palette):")
    for token, desc in TT_DERIVED:
        lines.append(f"  --tt-{token:<20} {desc}")
    return lines


def format_friendly_output(analysis: dict[str, Any]) -> str:
    lines = []
    lines.append(f"URL: {analysis['url']}")
    lines.append(f"Match: {analysis['match_pattern']}")
    lines.append(f"Variables found: {analysis['total_variables']}")
    lines.append("")

    lines.append("Suggested registry entry:")
    lines.append(json.dumps(analysis["registry_entry"], indent=2))
    lines.append("")

    cats = analysis["categorized"]
    for cat in [
        "background", "foreground", "border", "control", "shadow",
        "accent", "icon", "semantic", "overlay", "code", "other"
    ]:
        entries = cats.get(cat, {})
        if not entries:
            continue
        lines.append(f"── {cat.upper()} ({len(entries)}) {'─' * max(0, 50 - len(cat) - 6)}")
        for name, value in entries.items():
            lines.append(f"  {name:{60}} {value}")
        lines.append("")

    lines.append("─── Template ───────────────────────────────────────")
    lines.append(json.dumps(analysis["template"], indent=2))
    lines.append("")

    lines.append("─── TT Token Reference ─────────────────────────────")
    lines.extend(analysis["tt_reference"])

    return "\n".join(lines)


def analyze_site(url: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "url": url,
        "match_pattern": build_match_pattern(url),
        "registry_entry": build_registry_entry(url),
        "total_variables": 0,
        "categorized": {},
        "variables": {},
        "template": {},
        "tt_reference": [],
        "error": None,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
        except Exception as e:
            result["error"] = f"Failed to load page: {e}"
            browser.close()
            result["tt_reference"] = generate_tt_reference()
            return result

        raw = extract_variables(page)
        browser.close()

    result["variables"] = raw
    result["total_variables"] = len(raw)
    result["categorized"] = categorize_variables(raw)
    result["template"] = build_site_config_template(raw, url)
    result["tt_reference"] = generate_tt_reference()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze CSS custom properties on a website for terratheme-sites theming."
    )
    parser.add_argument("url", help="URL of the page to analyze")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output file path")
    parser.add_argument(
        "--template", action="store_true", help="Output only the skeleton config JSON"
    )
    parser.add_argument(
        "--registry", action="store_true", help="Output only the registry entry JSON"
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True, help="Pretty-print JSON (default: True)"
    )
    parser.add_argument(
        "--raw", action="store_true", help="Output raw variables only (for LLM context)"
    )
    args = parser.parse_args()

    analysis = analyze_site(args.url)

    if analysis.get("error") and not args.template and not args.registry:
        print(f"Error: {analysis['error']}", file=sys.stderr)

    if args.template:
        indent = 2 if args.pretty else None
        sys.stdout.write(json.dumps(analysis["template"], indent=indent))
        sys.stdout.write("\n")
        return

    if args.registry:
        indent = 2 if args.pretty else None
        sys.stdout.write(json.dumps(analysis["registry_entry"], indent=indent))
        sys.stdout.write("\n")
        return

    if args.raw:
        indent = 2 if args.pretty else None
        sys.stdout.write(json.dumps(analysis["variables"], indent=indent))
        sys.stdout.write("\n")
        return

    if args.output:
        indent = 2 if args.pretty else None
        args.output.write_text(json.dumps(analysis, indent=indent), encoding="utf-8")
        print(f"Wrote {analysis['total_variables']} variables to {args.output}", file=sys.stderr)
    else:
        if args.pretty:
            sys.stdout.write(format_friendly_output(analysis))
            sys.stdout.write("\n")
        else:
            sys.stdout.write(json.dumps(analysis, indent=2))
            sys.stdout.write("\n")


if __name__ == "__main__":
    main()
