#!/bin/sh
set -eu

case "${1:-}" in
    install|uninstall) [ "$#" -eq 1 ] || exit 2 ;;
    *) echo "Usage: $0 install|uninstall" >&2; exit 2 ;;
esac
if [ "$(id -u)" -eq 0 ]; then
    echo "Run this in your GNOME desktop session as your own user, without sudo." >&2
    exit 1
fi

schema=org.gnome.desktop.peripherals.touchpad
key=disable-while-typing-timeout
state=${XDG_STATE_HOME:-"$HOME/.local/state"}/diamond-cursor
backup=$state/typing-delay.before
if [ "$1" = uninstall ] && [ ! -f "$backup" ]; then
    echo "No typing-delay change to undo."
    exit 0
fi
if [ "${GSETTINGS_BACKEND:-dconf}" != dconf ]; then
    echo "Run this in a GNOME session using the dconf settings backend." >&2
    exit 1
fi
if ! gsettings writable "$schema" "$key" 2>/dev/null | grep -qx true; then
    echo "This extra needs a writable GNOME disable-while-typing-timeout setting." >&2
    exit 1
fi
if ! command -v dconf >/dev/null; then
    echo "Install the dconf command (dconf-cli on Ubuntu) and try again." >&2
    exit 1
fi
umask 077
mkdir -p "$state"
exec 9<"$state"
flock -x 9
current=$(gsettings get "$schema" "$key")
if [ "$1" = install ]; then
    if [ "$current" != 'uint32 300' ]; then
        if [ ! -f "$backup" ]; then
            # An empty dconf value means uninstall should restore the default.
            before=$(dconf read "/org/gnome/desktop/peripherals/touchpad/$key")
            tmp=$(mktemp "$state/.typing-delay.XXXXXX")
            trap 'rm -f -- "$tmp"' EXIT
            printf '%s\n' "$before" > "$tmp"
            mv -- "$tmp" "$backup"
        fi
        gsettings set "$schema" "$key" 300
        [ "$(gsettings get "$schema" "$key")" = 'uint32 300' ]
    fi
    echo "Typing delay is 300 ms. It applies when disable-while-typing is enabled."
elif [ -f "$backup" ]; then
    if [ "$current" = 'uint32 300' ]; then
        before=$(cat "$backup")
        if [ -n "$before" ]; then
            gsettings set "$schema" "$key" "$before"
        else
            gsettings reset "$schema" "$key"
        fi
        [ "$(dconf read "/org/gnome/desktop/peripherals/touchpad/$key")" = "$before" ]
        echo "Restored the previous typing delay."
    else
        echo "Keeping the typing delay you selected after installation."
    fi
    rm -- "$backup"
fi
