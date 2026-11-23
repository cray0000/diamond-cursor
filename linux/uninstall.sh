#!/bin/sh
set -eu

if ! ( . /etc/os-release && [ "${ID:-}" = ubuntu ] ) 2>/dev/null; then
    echo "Quick uninstall is for Ubuntu. Follow Manual removal in linux/README.md and use your package manager to remove keyd if desired." >&2
    exit 1
fi

CDPATH='' cd -- "$(dirname -- "$0")"
if [ "$(id -u)" -ne 0 ]; then
    exec sudo -- ./uninstall.sh
fi

target=/etc/keyd/diamond.conf
if [ ! -e "$target" ] && [ ! -L "$target" ]; then
    echo "The standalone diamond cursor config is already absent."
    exit 0
fi
if [ -L "$target" ] || [ ! -f "$target" ] || ! cmp -s diamond.conf "$target"; then
    echo "Review $target before removing it manually. It differs from the standalone config or is a link." >&2
    exit 1
fi

rm -- "$target"
if systemctl is-active --quiet keyd.service; then
    systemctl try-restart keyd.service
fi
echo "Removed the diamond cursor config."
