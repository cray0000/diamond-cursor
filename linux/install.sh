#!/bin/sh
set -eu

if ! ( . /etc/os-release && [ "${ID:-}" = ubuntu ] ) 2>/dev/null; then
    echo "Quick install is for Ubuntu. Install keyd with your package manager and follow Manual install in linux/README.md." >&2
    exit 1
fi

CDPATH='' cd -- "$(dirname -- "$0")"
if [ "$(id -u)" -ne 0 ]; then
    exec sudo -- ./install.sh
fi

target=/etc/keyd/diamond.conf
quirks=/etc/libinput/local-overrides.quirks
if [ ! -r diamond.conf ] || [ ! -r keyd.quirks ] || [ ! -d /run/systemd/system ]; then
    echo "The installer needs diamond.conf and keyd.quirks next to install.sh and a running systemd." >&2
    exit 1
fi

if [ -e "$target" ] || [ -L "$target" ]; then
    if [ -L "$target" ] || [ ! -f "$target" ] || ! cmp -s diamond.conf "$target"; then
        echo "$target already exists and differs from the standalone config or is a link. See Manual install to merge your bindings." >&2
        exit 1
    fi
fi

for config in /etc/keyd/*.conf; do
    if [ ! -f "$config" ] || [ "$config" = "$target" ]; then
        continue
    fi
    if grep -Eq '^[[:space:]]*\*[[:space:]]*$' "$config"; then
        echo "$config already has a wildcard keyboard match. Merge the bindings there using Manual install." >&2
        exit 1
    fi
done

if [ "$(dpkg-query -W -f='${db:Status-Status}' keyd 2>/dev/null || true)" != installed ] &&
    ! systemctl cat keyd.service >/dev/null 2>&1; then
    apt-get update
    if ! apt-get install -y keyd; then
        echo "If your Ubuntu release does not package keyd, see the upstream instructions in linux/README.md." >&2
        exit 1
    fi
fi

install -C -D -m 0644 diamond.conf "$target"
if [ ! -e "$quirks" ] && [ ! -L "$quirks" ]; then
    mkdir -p /etc/libinput
    # Publish a complete file only if the overrides path is still available.
    staged=$(mktemp /etc/libinput/.diamond-cursor.XXXXXX)
    trap 'rm -f -- "$staged"' EXIT
    install -m 0644 keyd.quirks "$staged"
    ln -T -- "$staged" "$quirks"
    echo "Installed the keyd touchpad pairing rule. Log out and back in, or reboot, to apply it."
elif [ -L "$quirks" ] || [ ! -f "$quirks" ] || ! cmp -s keyd.quirks "$quirks"; then
    echo "Keeping existing $quirks. See Touchpad pairing in linux/README.md to check or merge the keyd rule."
fi
systemctl enable keyd.service
systemctl restart keyd.service
echo "Diamond cursor is active. Try Left Alt + J in a text editor."
