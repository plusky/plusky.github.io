#!/bin/sh
# Fetch the variable fonts, cut them to weights 400-700 and the Latin ranges
# the site uses, and write woff2 files plus licences to static/fonts/.
# Needs curl and fontTools with brotli (pyftsubset).
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
cache="$root/.cache/fonts"
out="$root/static/fonts"
base=https://raw.githubusercontent.com/google/fonts/main/ofl
pyftsubset=${PYFTSUBSET:-pyftsubset}

unicodes="U+0020-007E,U+00A0-00FF,U+0100-017F,U+2000-206F,U+2212,U+00D7,U+00B1,U+2264,U+2265,U+2248,U+2190-2193,U+2026,U+00B7"
features="kern,liga,tnum,lnum,onum,case,frac"

mkdir -p "$cache" "$out"

fetch() { # family, encoded file name, local file name
	[ -s "$cache/$3" ] || curl -fsSL -o "$cache/$3" "$base/$1/$2"
}

fetch sourceserif4 'SourceSerif4%5Bopsz%2Cwght%5D.ttf' 'SourceSerif4[opsz,wght].ttf'
fetch sourceserif4 'SourceSerif4-Italic%5Bopsz%2Cwght%5D.ttf' 'SourceSerif4-Italic[opsz,wght].ttf'
fetch sourceserif4 OFL.txt OFL-SourceSerif4.txt
fetch sourcesans3 'SourceSans3%5Bwght%5D.ttf' 'SourceSans3[wght].ttf'
fetch sourcesans3 'SourceSans3-Italic%5Bwght%5D.ttf' 'SourceSans3-Italic[wght].ttf'
fetch sourcesans3 OFL.txt OFL-SourceSans3.txt
fetch jetbrainsmono 'JetBrainsMono%5Bwght%5D.ttf' 'JetBrainsMono[wght].ttf'
fetch jetbrainsmono OFL.txt OFL-JetBrainsMono.txt

build() { # source ttf, output name, instancer axis limits
	src=$1 name=$2
	shift 2
	tmp="$cache/$name.ttf"
	python3 -m fontTools.varLib.instancer "$cache/$src" "$@" -o "$tmp"
	"$pyftsubset" "$tmp" \
		--unicodes="$unicodes" \
		--layout-features="$features" \
		--no-hinting --desubroutinize \
		--name-IDs='*' --name-languages=0x409 \
		--flavor=woff2 \
		--output-file="$out/$name.woff2"
	rm -f "$tmp"
}

# The OFL forbids a Modified Version from using a Reserved Font Name, so the
# subset gets a new family name; copyright and licence records stay as they are.
rename() { # woff2 file, old family, new family
	python3 - "$@" <<'EOF'
import sys
from fontTools.ttLib import TTFont

path, old, new = sys.argv[1:]
ps_old, ps_new = old.replace(" ", ""), new.replace(" ", "")
font = TTFont(path)
name = font["name"]
ids = (1, 3, 4, 6, 16, 17, 21, 22, 25)
for rec in name.names:
    if rec.nameID in ids:
        rec.string = rec.toUnicode().replace(old, new).replace(ps_old, ps_new)
for rec in name.names:
    if rec.nameID == 3:
        rec.string = f"{font['head'].fontRevision:.3f};{name.getDebugName(6)}"
for rec in name.names:
    s = rec.toUnicode().lower()
    if rec.nameID in ids and ("source" in s or "adobe" in s):
        sys.exit(f"{path}: name ID {rec.nameID} still reads {rec.toUnicode()!r}")
font.save(path)
EOF
}

# Optical size pinned at text size: one master instead of a second axis.
build 'SourceSerif4[opsz,wght].ttf' plain-serif wght=400:700 opsz=18
build 'SourceSerif4-Italic[opsz,wght].ttf' plain-serif-italic wght=400:700 opsz=18
rename "$out/plain-serif.woff2" 'Source Serif 4' 'Plain Serif'
rename "$out/plain-serif-italic.woff2" 'Source Serif 4' 'Plain Serif'
build 'SourceSans3[wght].ttf' plain-sans wght=400:700
build 'SourceSans3-Italic[wght].ttf' plain-sans-italic wght=400:700
rename "$out/plain-sans.woff2" 'Source Sans 3' 'Plain Sans'
rename "$out/plain-sans-italic.woff2" 'Source Sans 3' 'Plain Sans'
build 'JetBrainsMono[wght].ttf' jetbrains-mono wght=400:700

cp "$cache/OFL-SourceSerif4.txt" "$cache/OFL-SourceSans3.txt" "$cache/OFL-JetBrainsMono.txt" "$out/"
ls -l "$out"
