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

## Adding a new site

1. Create `sites/<id>.json` following the schema in `SPEC.md`
2. Add an entry to `registry.json` under the `sites` array
3. Commit and push

That's it. Users will see the new site config within 24h (or immediately
if they click the "Refresh Site Configs" button in the popup).
