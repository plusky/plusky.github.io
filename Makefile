HUGO ?= hugo
PYTHON ?= python3 -I
PORT ?= 8765
PAGE ?= /

POSTS = $(wildcard content/posts/*/index.md)
LEAK_PATHS = data content figures layouts assets static tools .github .githooks .gitignore README.md Makefile hugo.toml

.PHONY: all figures check check-svg check-facts check-leaks build serve preview-figures shots linkcheck linkcheck-internal fresh

all: figures check build linkcheck-internal
	$(PYTHON) tools/check_leaks.py public

figures:
	$(PYTHON) figures/build.py

check: check-svg check-facts check-leaks

check-svg:
	$(PYTHON) tools/check_svg.py content

check-facts:
	$(PYTHON) tools/check_facts.py $(POSTS)

check-leaks:
	$(PYTHON) tools/check_leaks.py $(LEAK_PATHS)

build:
	$(HUGO) --gc --minify --panicOnWarning --printPathWarnings --cleanDestinationDir $(HUGOFLAGS)

serve:
	$(HUGO) server -D --bind 127.0.0.1 --disableFastRender

preview-figures:
	$(PYTHON) tools/preview.py

# make shots PAGE=/posts/<post>/ ; builds first, drafts included, so the shots show the current tree.
shots: HUGOFLAGS = -D
shots: build
	tools/shots.sh -p $(PORT) $(PAGE)

linkcheck:
	$(PYTHON) tools/check_links.py --external public

linkcheck-internal:
	$(PYTHON) tools/check_links.py --internal public

# Checksums rather than git status, so this works on an uncommitted tree too.
fresh:
	@tmp=$$(mktemp -d) || exit 1; trap 'rm -rf "$$tmp"' EXIT; \
	find content -path '*/fig/*' -type f -exec sha256sum {} + | LC_ALL=C sort -k2 >"$$tmp/before"; \
	$(PYTHON) figures/build.py || exit 1; \
	find content -path '*/fig/*' -type f -exec sha256sum {} + | LC_ALL=C sort -k2 >"$$tmp/after"; \
	if ! cmp -s "$$tmp/before" "$$tmp/after"; then \
		echo "fresh: these figures changed when rebuilt; run 'make figures' and commit them:"; \
		diff "$$tmp/before" "$$tmp/after" | sed -n 's/^[<>] [0-9a-f]* *//p' | LC_ALL=C sort -u; \
		exit 1; \
	fi; \
	echo "fresh: figures are up to date"
