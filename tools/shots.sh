#!/bin/sh
# Full-page screenshots of one page at 400 and 1280 px, light and dark, into .preview/shots/,
# each also cut into <page>-<width>-<theme>-<nn>.png tiles of at most 1500 px height.
#
# Usage: tools/shots.sh [-p PORT] [-d DIR | -u BASE_URL] [PATH]
#   -d DIR       serve DIR (default: public) on 127.0.0.1:PORT for the run (default port 8765)
#   -u BASE_URL  use a server that is already running, e.g. http://127.0.0.1:1313
#   PATH         page path, default /
set -eu

port=8765
dir=public
base=
while getopts p:d:u:h opt; do
	case $opt in
	p) port=$OPTARG ;;
	d) dir=$OPTARG ;;
	u) base=${OPTARG%/} ;;
	*)
		sed -n '2,8s/^# \{0,1\}//p' "$0"
		exit 2
		;;
	esac
done
shift $((OPTIND - 1))
path=${1:-/}
case $path in /*) ;; *) path=/$path ;; esac

root=$(cd "$(dirname "$0")/.." && pwd)
preview=$root/.preview
out=$preview/shots
firefox=${FIREFOX:-firefox}
command -v "$firefox" >/dev/null || {
	echo "shots: $firefox not found" >&2
	exit 2
}

server_pid=
cleanup() {
	if [ -n "$server_pid" ]; then kill "$server_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

if [ -z "$base" ]; then
	[ -f "$dir/index.html" ] || {
		echo "shots: $dir/index.html not found; run 'make build' first or pass -u" >&2
		exit 2
	}
	python3 -I -m http.server --bind 127.0.0.1 --directory "$dir" "$port" >/dev/null 2>&1 &
	server_pid=$!
	base=http://127.0.0.1:$port
fi

python3 -I - "$base" <<'EOF'
import sys, time, urllib.request
for _ in range(100):
    try:
        urllib.request.urlopen(sys.argv[1] + "/", timeout=1).close()
        sys.exit(0)
    except Exception:
        time.sleep(0.1)
sys.exit(f"shots: no server answering at {sys.argv[1]}")
EOF

mkdir -p "$out"
slug=$(printf '%s' "$path" | tr -c 'A-Za-z0-9\n' '-' | sed 's/^-*//; s/-*$//')
[ -n "$slug" ] || slug=home

# A private HOME keeps Firefox away from the user's own profiles and settings.
fhome=$preview/ff-home
mkdir -p "$fhome"

for theme in light dark; do
	profile=$preview/ff-$theme
	rm -rf "$profile"
	mkdir -p "$profile"
	if [ "$theme" = dark ]; then scheme=0; else scheme=1; fi
	# Headless screenshots ignore the content override; the system theme pref is what takes effect.
	cat >"$profile/user.js" <<EOF
user_pref("layout.css.prefers-color-scheme.content-override", $scheme);
user_pref("browser.theme.content-theme", $scheme);
user_pref("ui.systemUsesDarkTheme", $((1 - scheme)));
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.startup.firstrunSkipsHomepage", true);
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("trailhead.firstrun.didSeeAboutWelcome", true);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.policy.firstRunURL", "");
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("app.normandy.enabled", false);
user_pref("app.update.auto", false);
user_pref("app.update.enabled", false);
user_pref("extensions.update.enabled", false);
user_pref("browser.newtabpage.enabled", false);
user_pref("browser.safebrowsing.malware.enabled", false);
user_pref("browser.safebrowsing.phishing.enabled", false);
user_pref("network.captive-portal-service.enabled", false);
user_pref("network.connectivity-service.enabled", false);
user_pref("toolkit.startup.max_resumed_crashes", -1);
EOF
	for width in 400 1280; do
		png=$out/$slug-$width-$theme.png
		rm -f "$png"
		HOME=$fhome MOZ_CRASHREPORTER_DISABLE=1 "$firefox" --headless --no-remote --profile "$profile" \
			--window-size="$width" --screenshot "$png" "$base$path" >/dev/null 2>&1 || true
		if [ ! -s "$png" ]; then
			echo "shots: no screenshot for $width $theme" >&2
			exit 1
		fi
		rm -f "$out/$slug-$width-$theme"-[0-9][0-9].png
		python3 -I "$root/tools/pngtiles.py" "$png" "$out/$slug-$width-$theme"
	done
done
