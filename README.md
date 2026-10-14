# CutWire Drift - MakeFontAddon

I had the idea for this after many failed attempts at importing custom fonts into CutWire Drift (thank you, Claude, for helping me find my mistakes). This script aims to make creating and importing addons with custom fonts easy.

> **Unofficial.** This is a community project and is not affiliated with CutWire. The addon format was worked out by studying the official addons, so it may change in future Drift versions.

## Usage

```bash
pip install fonttools

# a single font
python make_font_addon.py MyFont.ttf --id fonts.myfont --author YourName

# a folder with several fonts/weights
python make_font_addon.py ./my-fonts --id fonts.myfonts --category clean --license OFL-1.1 --license-file OFL.txt
```

This creates `fonts.myfont-1.0.0.zip`. Import it in Drift. If the app only accepts the official extension, add `--driftpkg` (untested).

## Options

| Option | What it does |
|---|---|
| `--id` | Addon id, use the `fonts.<name>` pattern (lowercase, with a dot) |
| `--name` | Name shown in the app (default: the family name) |
| `--category` | `impact`, `editorial`, `clean` or `playful` |
| `--license`, `--license-file` | Font license, and the license file (copied into each family folder) |
| `--version`, `--author`, `--description` | Metadata |
| `--driftpkg` | Save as `.driftpkg` instead of `.zip` |

Weight (100-900) and italic are read from the font itself. Fonts are grouped into families automatically.

## Generated structure

```
manifest.json
fonts/
  <family>/
    family.json
    <Family>-400.ttf
```

`manifest.json` and `fonts/` sit directly at the **root** of the zip (no wrapper folder).

## Common errors

- `manifest.json.json` / `.ttf.ttf`: Windows hides known file extensions, so a second one gets added. Turn on *View > File name extensions* in File Explorer.
- `no manifest .json`: the manifest is not at the root of the zip.
- `unsupported metadata schema`: the manifest needs `"schema": 1`.

Check the license of your fonts before sharing an addon. Do not redistribute fonts you are not allowed to.
