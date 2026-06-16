# terratheme-sites — Site Theme Configs for Terra Theme Browser

Data-only repository hosting per-site CSS variable mappings for the
[Terra Theme Browser](https://github.com/terra-de/terratheme-browser) extension.

**No build step — no rebuild/re-sign required.** The extension fetches
configs from this repo at runtime. Updating a site's theme means pushing
a JSON change here — users get it within 24h (TTL) without any extension update.

## Structure

```
terratheme-sites/
├── registry.json        # Versioned index of all available sites
├── sites/
│   ├── github.json      # Per-site CSS variable mapping configs
│   ├── reddit.json
│   ├── youtube.json
│   ├── chatgpt.json
│   └── monkeytype.json
├── tools/
│   └── analyze_site.py  # Dev tool: extract CSS vars from a site
├── SPEC.md              # Config format specification
├── AGENTS.md
├── LICENSE
└── .github/workflows/
    └── validate.yml     # CI: validate all JSONs against schema
```

## Usage

The extension fetches `registry.json` from:
```
https://raw.githubusercontent.com/terra-de/terratheme-sites/main/registry.json
```

Users can override this URL in the extension popup (Advanced settings)
to use a fork or custom data source.

## Adding a new site (workflow)

1. Run `tools/analyze_site.py` to extract the site's CSS variables:
   ```bash
   uv run tools/analyze_site.py https://example.com
   ```
   This outputs a categorized variable listing, a skeleton config template
   with `var(--tt-????)` placeholders, and a suggested registry entry.

2. Feed the output to an LLM or manually map each site variable to the
   appropriate `--tt-*` token. See `SPEC.md` for the full token reference.

3. Create `sites/<id>.json` with the completed mapping.

4. Add an entry to `registry.json` under the `sites` array.

5. Commit and push.

Users see the new site config within 24h (or immediately if they click
"Refresh Site Configs" in the extension popup).

## Tools

### `tools/analyze_site.py`

Extracts all CSS custom properties from a website and produces structured
output for generating terratheme-site configs.

**Requires:** `uv` and Playwright (auto-installed by `uv run`).

```bash
# Full analysis (categorized vars + template + registry entry)
uv run tools/analyze_site.py https://example.com

# Skeleton config only (pipe to LLM)
uv run tools/analyze_site.py https://example.com --template

# Registry entry only
uv run tools/analyze_site.py https://example.com --registry

# Raw variables only (flat JSON)
uv run tools/analyze_site.py https://example.com --raw

# Write to file
uv run tools/analyze_site.py https://example.com -o /tmp/example.json
```

**First run** will download Playwright browser binaries (~300MB). Subsequent
runs are fast.
