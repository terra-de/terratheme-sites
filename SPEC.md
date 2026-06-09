# terratheme-sites Config Format

## registry.json

The registry is the entry point — the extension fetches this first to
discover available sites.

```json
{
  "version": 1,
  "updated": "2026-06-09T00:00:00Z",
  "sites": [
    {
      "id": "github",
      "name": "GitHub",
      "matches": ["*://github.com/*"],
      "path": "sites/github.json"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Schema version (increment on breaking changes) |
| `updated` | ISO 8601 | Last update timestamp |
| `sites` | array | List of available site configs |

### Site Entry

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, matches filename without extension |
| `name` | string | Human-readable site name |
| `matches` | string[] | URL match patterns (same syntax as manifest.json content_scripts) |
| `path` | string | Path relative to repo root |

## Site Config JSON

Each site config uses the same schema as the individual JSON files in the
extension. Rules reference `--tt-*` CSS variables that are injected onto
`:root` by the extension's content script.

```json
{
  "version": 2,
  "match": ["*://github.com/*"],
  "rules": [
    {
      "selector": ":root",
      "important": true,
      "set": {
        "--bgColor-default": "var(--tt-base)",
        "--fgColor-default": "var(--tt-standard)"
      }
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Schema version (should match what the extension expects) |
| `match` | string[] | URL match patterns (used for verification, extension uses registry matches) |
| `rules` | array[] | CSS variable mapping rules |

### Rule

| Field | Type | Description |
|-------|------|-------------|
| `selector` | string | CSS selector to target |
| `important` | bool (opt) | Append `!important` to all values |
| `set` | object | CSS property → value mappings |

Values can be:
- `var(--tt-<token>)` — Terra DE palette variable (injected by content script)
- `color-mix(in srgb, var(--tt-<token>) <percent>, <color>)` — CSS color mixing
- Any static CSS value

### Available --tt-* Variables

| CSS Variable | Source | Description |
|-------------|--------|-------------|
| `--tt-bottom` | palette | Deepest background layer |
| `--tt-low` | palette | Low-elevation background |
| `--tt-base` | palette | Main surface background |
| `--tt-high` | palette | Elevated surface |
| `--tt-top` | palette | Foremost surface |
| `--tt-standard` | palette | Primary text/icon |
| `--tt-muted` | palette | Secondary text/icon |
| `--tt-c0`..`--tt-c4` | palette | Accent colors |
| `--tt-on-c0`..`--tt-on-c4` | palette | Text on accent |
| `--tt-error` | palette | Error color |
| `--tt-on-error` | palette | Text on error |
| `--tt-outline` | palette | Borders/outlines |
| `--tt-outline-variant` | derived | outline at 55% opacity |
| `--tt-scrim` | derived | Overlay scrim |
| `--tt-inverse-base` | derived | Opposite mode's base |
| `--tt-inverse-standard` | derived | Opposite mode's standard |
