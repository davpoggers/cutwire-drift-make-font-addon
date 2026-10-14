#!/usr/bin/env python3
"""
make_font_addon.py - packs fonts (.ttf/.otf) into an addon for CutWire Drift (unofficial).

Examples:
    python make_font_addon.py Playtime.ttf --id fonts.playtime --name "Playtime" --author YourName
    python make_font_addon.py ./my-fonts --id fonts.myfonts --category playful --driftpkg

Produces <id>-<version>.zip (or .driftpkg) with manifest.json and fonts/ at the ROOT of the zip,
the layout Drift accepted in testing.
Requires: pip install fonttools
"""
import argparse, json, re, shutil, sys, tempfile, zipfile
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("Missing the fonttools library. Install it with:  pip install fonttools")

STYLE = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
         600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
CATEGORIES = ("impact", "editorial", "clean", "playful")   # the ones used by fonts.essentials
EXTS = {".ttf", ".otf"}


def get_name(font, nid):
    recs = font["name"].names
    for r in recs:                      # prefer Windows/Unicode
        if r.nameID == nid and r.platformID == 3:
            return r.toUnicode().strip()
    for r in recs:
        if r.nameID == nid:
            return r.toUnicode().strip()
    return ""


NAME_WEIGHT = [("extralight", 200), ("ultralight", 200), ("extrabold", 800), ("ultrabold", 800),
               ("semibold", 600), ("demibold", 600), ("thin", 100), ("hairline", 100), ("light", 300),
               ("medium", 500), ("black", 900), ("heavy", 900), ("bold", 700),
               ("regular", 400), ("normal", 400), ("book", 400)]


def detect_weight(font):
    """Weight 100-900. Uses the style name (e.g. 'ExtraLight') first and the OS/2 number only as a
    fallback, because some fonts (e.g. Thin/ExtraLight) share the same number (250)."""
    style = (get_name(font, 17) or get_name(font, 2)).lower().replace(" ", "").replace("-", "")
    for key, w in NAME_WEIGHT:
        if key in style:
            return w
    return min(900, max(100, int(font["OS/2"].usWeightClass / 100 + 0.5) * 100))


def slug(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def camel(s):
    return re.sub(r"[^A-Za-z0-9]", "", s)


def collect(inputs):
    files = []
    for i in inputs:
        p = Path(i)
        if p.is_dir():
            files += sorted(x for x in p.rglob("*") if x.suffix.lower() in EXTS)
        elif p.is_file():
            files.append(p)
        else:
            sys.exit(f"Not found: {p}")
    if not files:
        sys.exit("No fonts (.ttf/.otf) found.")
    return files


def main():
    ap = argparse.ArgumentParser(description="Creates a font addon for CutWire Drift (unofficial).")
    ap.add_argument("inputs", nargs="+", help=".ttf/.otf files or folders containing fonts")
    ap.add_argument("--id", required=True, help="addon id, e.g. fonts.myfonts (use the fonts.<name> pattern)")
    ap.add_argument("--name", help="name shown in the app (default: the family name)")
    ap.add_argument("--description", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--license", default="Freeware", help="e.g. OFL-1.1, Freeware, MIT")
    ap.add_argument("--license-file", help="license file (OFL.txt etc.) copied into each family folder")
    ap.add_argument("--category", default="playful", choices=CATEGORIES)
    ap.add_argument("--min-app-version", default="0.1.0")
    ap.add_argument("--out", default=".", help="output folder")
    ap.add_argument("--driftpkg", action="store_true", help="save with a .driftpkg extension instead of .zip")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_-]+)+", a.id):
        sys.exit("--id must be lowercase with a dot, e.g. fonts.myfonts")
    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version):
        sys.exit("--version must look like 1.0.0")

    # ---- read the fonts and group them by family
    fams = {}
    for p in collect(a.inputs):
        try:
            f = TTFont(p, lazy=True)
            fam = get_name(f, 16) or get_name(f, 1)
            os2 = f["OS/2"]
            fvar = "fvar" in f
        except Exception as e:
            sys.exit(f"Could not read {p.name}: {e}")
        if not fam:
            sys.exit(f"{p.name} has no internal family name.")
        if fvar:
            print(f"WARNING: {p.name} is a variable font; Drift may only use its default weight.")
        if os2.fsType & 0x0002:
            print(f"WARNING: {p.name} has restricted embedding (fsType={os2.fsType}); check its license.")
        w = detect_weight(f)
        it = bool(os2.fsSelection & 1) or bool(f["head"].macStyle & 2)
        fams.setdefault(fam, {})
        if (w, it) in fams[fam]:
            print(f"WARNING: {p.name} duplicates {fam} weight {w}{' italic' if it else ''}; skipping.")
            continue
        fams[fam][(w, it)] = p
        f.close()

    # ---- build a temporary folder
    tmp = Path(tempfile.mkdtemp(prefix="fontaddon_"))
    try:
        (tmp / "fonts").mkdir()
        total = 0
        for order, (fam, faces) in enumerate(sorted(fams.items()), 1):
            fid = slug(fam)
            d = tmp / "fonts" / fid
            d.mkdir()
            entries = []
            for (w, it), src in sorted(faces.items()):
                fn = f"{camel(fam)}-{w}{'italic' if it else ''}{src.suffix.lower()}"
                shutil.copy(src, d / fn)
                if it:
                    sn = {400: "Italic", 700: "Bold Italic"}.get(w, STYLE[w] + " Italic")
                else:
                    sn = STYLE[w]
                entries.append({"weight": w, "italic": it, "styleName": sn, "file": fn})
                total += 1
            meta = {"id": fid, "family": fam, "category": a.category,
                    "order": order * 10, "license": a.license}
            if a.license_file:
                lf = Path(a.license_file)
                shutil.copy(lf, d / lf.name)
                meta["licenseFile"] = lf.name
            meta["faces"] = entries
            (d / "family.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        default_name = a.name or (next(iter(fams)) if len(fams) == 1 else a.id)
        manifest = {
            "schema": 1, "id": a.id, "version": a.version, "name": default_name,
            "description": a.description or f"{len(fams)} font famil{'y' if len(fams)==1 else 'ies'}",
            "author": a.author, "license": a.license, "minAppVersion": a.min_app_version,
            "kind": "fonts", "provides": [{"kind": "fonts", "root": "fonts"}], "platforms": [],
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{a.id}-{a.version}{'.driftpkg' if a.driftpkg else '.zip'}"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp / "manifest.json", "manifest.json")          # manifest first, at the root
            for p in sorted((tmp / "fonts").rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(tmp).as_posix())         # always forward slashes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- verify the output
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "manifest.json" in names, "manifest.json missing"
        bad = [n for n in names if re.search(r"\.(json|ttf|otf)\.(json|ttf|otf)$", n)]
        assert not bad, f"duplicate extension: {bad}"
        json.loads(z.read("manifest.json"))
    print(f"OK: {out}  ({len(fams)} family/families, {total} style(s))")


if __name__ == "__main__":
    main()
