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
quirks=/etc/libinput/local-overrides.quirks
if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -L "$target" ] || [ ! -f "$target" ] || ! cmp -s diamond.conf "$target"; then
        echo "Review $target before removing it manually. It differs from the standalone config or is a link." >&2
        exit 1
    fi
    rm -- "$target"
    if systemctl is-active --quiet keyd.service; then
        systemctl try-restart keyd.service
    fi
    echo "Removed the diamond cursor config."
else
    echo "The standalone diamond cursor config is already absent."
fi

if [ ! -L "$quirks" ] && [ -f "$quirks" ] && cmp -s keyd.quirks "$quirks"; then
    rm -- "$quirks"
    echo "Removed the keyd touchpad pairing rule. Log out and back in, or reboot, to apply the change."
elif [ -e "$quirks" ] || [ -L "$quirks" ]; then
    echo "Keeping existing $quirks. See Manual removal in linux/README.md to remove a merged rule."
fi
