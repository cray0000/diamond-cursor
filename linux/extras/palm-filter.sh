#!/bin/bash
set -euo pipefail
export LC_ALL=C

die() { echo "$*" >&2; exit 1; }
case "${1:-}" in
    install) (( $# <= 2 )) || die "Usage: $0 install [touchpad-event-device]" ;;
    uninstall) (( $# == 1 )) || die "Usage: $0 uninstall" ;;
    *) die "Usage: $0 install [touchpad-event-device] | uninstall" ;;
esac
cd -- "$(dirname -- "$0")"
[[ -d /run/systemd/system ]] || die "This extra requires systemd and udev."
if (( EUID != 0 )); then exec sudo -- ./palm-filter.sh "$@"; fi

bundle=/usr/local/lib/diamond-cursor-palm-filter
unit=diamond-cursor-palm-filter.service
rule=99-diamond-cursor-palm-filter.rules
unit_link=/etc/systemd/system/$unit
rule_link=/etc/udev/rules.d/$rule
alias_path=/dev/input/diamondpalm
exec 9>/run/diamond-cursor-palm-filter.lock
flock -x 9

# Only unlink configuration that points to this installation.
check_link() {
    if [[ -e $1 || -L $1 ]]; then
        [[ -L $1 && $(readlink -- "$1") == "$2" ]] || die "Another configuration owns $1."
    fi
}
check_link "$unit_link" "$bundle/$unit"
check_link "$rule_link" "$bundle/$rule"

remove_filter() {
    check_link "$unit_link" "$bundle/$unit"
    check_link "$rule_link" "$bundle/$rule"
    if [[ -L $unit_link ]] || systemctl is-enabled --quiet "$unit"; then
        systemctl disable --now "$unit" || return 1
    elif systemctl is-active --quiet "$unit"; then
        systemctl stop "$unit" || return 1
    fi
    rm -f -- "$unit_link" "$rule_link" || return 1
    systemctl daemon-reload && udevadm control --reload || return 1
    if [[ -e $device ]]; then udevadm trigger --action=change --settle "$device" || return 1; fi
    rm -- "$bundle/$unit" "$bundle/$rule" "$bundle/unpalm" "$bundle/device" "$bundle/files.sha256" && rmdir "$bundle"
}

has_bundle=false
if [[ -e $bundle || -L $bundle ]]; then
    if [[ -L $bundle || ! -d $bundle ]] || ! (cd "$bundle" && sha256sum --check --status files.sha256); then
        die "Review the existing or edited $bundle before continuing."
    fi
    device=$(cat "$bundle/device")
    has_bundle=true
fi
if [[ $1 == uninstall ]]; then
    if "$has_bundle"; then remove_filter; fi
    echo "The Diamond Cursor palm filter is uninstalled."
    exit
fi

filtered_pad_present() {
    grep -Fxql 'Filtered Touchpad' /sys/devices/virtual/input/input*/name 2>/dev/null
}

if systemctl is-enabled --quiet unpalm.service || systemctl is-active --quiet unpalm.service ||
   { filtered_pad_present && ! systemctl is-active --quiet "$unit"; }; then
    die "A separate unpalm installation already exists. Keep using it or remove it before installing this extra."
fi
if "$has_bundle"; then
    if [[ -n ${2:-} && ! $2 -ef $device ]]; then die "Uninstall first to select a different touchpad."; fi
else
    [[ ! -e $alias_path && ! -L $alias_path ]] || die "Another device owns $alias_path."

    candidates=(/dev/input/event*)
    if [[ -n ${2:-} ]]; then candidates=("$2"); fi
    declare -a pads=()
    for node in "${candidates[@]}"; do
        props=$(udevadm info -q property -n "$node" 2>/dev/null) || continue
        grep -qx 'ID_INPUT_TOUCHPAD=1' <<<"$props" || continue
        if grep -Eq '^(DEVPATH=/devices/virtual/|ID_INPUT_TOUCHSCREEN=1$|ID_(INPUT_TOUCHPAD_)?INTEGRATION=external$)' <<<"$props"; then
            continue
        fi
        if [[ -z ${2:-} ]] && ! grep -Eq '^(ID_(INPUT_TOUCHPAD_)?INTEGRATION=internal|ID_BUS=(i2c|i8042|spi|rmi))$|^ID_PATH=platform-i8042-' <<<"$props"; then
            continue
        fi
        pads+=("$node")
    done
    (( ${#pads[@]} == 1 )) || die "Could not select one built-in touchpad. Pass its /dev/input/eventN to install. Candidates: ${pads[*]:-none}"
    props=$(udevadm info -q property -n "${pads[0]}")
    width=$(sed -n 's/^ID_INPUT_WIDTH_MM=//p' <<<"$props")
    margin=$(awk -v w="$width" 'BEGIN { if (w !~ /^[0-9]+([.][0-9]+)?$/ || w <= 60) exit 1; printf "%.6f", 3000 / w }') ||
        die "The touchpad must report a width greater than 60 mm to leave room for two 30 mm margins."
    links=$(udevadm info -q symlink -n "${pads[0]}")
    device=
    for link in $links; do
        if [[ $link =~ ^input/by-path/[a-zA-Z0-9._:+-]+$ && /dev/$link -ef ${pads[0]} ]]; then
            device=/dev/$link
            break
        fi
    done
    [[ -n $device ]] || die "The selected touchpad needs a stable /dev/input/by-path link."

    mkdir -p /usr/local/lib
    stage=$(mktemp -d /usr/local/lib/.diamond-cursor-palm-filter.XXXXXX)
    fresh=false
    # shellcheck disable=SC2329 # Invoked by the EXIT trap.
    cleanup() {
        local rc=$?
        if (( rc != 0 )) && "$fresh"; then remove_filter || echo "Rollback needs attention. Run uninstall to retry." >&2; fi
        if [[ -d $stage ]]; then rm -r -- "$stage"; fi
    }
    trap cleanup EXIT
    if executable=$(type -P unpalm); then
        [[ $executable == /* ]] || die "Install unpalm on an absolute system PATH."
        ln -s -- "$executable" "$stage/unpalm"
    else
        [[ $(uname -m) == x86_64 ]] || die "Install unpalm from upstream for $(uname -m), then rerun this installer."
        curl --fail --location --proto '=https' --silent --show-error -o "$stage/unpalm" \
            https://github.com/rpodgorny/unpalm/releases/download/v0.2.2/unpalm-x86_64-linux
        printf '%s  %s\n' d9e6bca374c406b2805a5bbdc5a7ce24147c740628b4adf89e0c71998fe07ede "$stage/unpalm" | sha256sum --check --status ||
            die "The unpalm download failed checksum verification."
        chmod 0755 "$stage/unpalm"
    fi
    "$stage/unpalm" --help | grep -F -- '--block-taps' >/dev/null || die "unpalm must support --block-taps (tested with v0.2.2)."
    sed "s|@BY_PATH@|${device#/dev/}|g" palm-filter.rules > "$stage/$rule"
    sed "s/@MARGIN@/$margin/g" palm-filter.service > "$stage/$unit"
    printf '%s\n' "$device" > "$stage/device"
    (cd "$stage" && sha256sum "$unit" "$rule" device > files.sha256)
    chmod 0755 "$stage"
    chmod 0644 "$stage/$unit" "$stage/$rule"
    mv -T -- "$stage" "$bundle"
    fresh=true
    echo "Selected $device ($width mm wide). Each side margin is $margin%."
fi

[[ -e $device ]] || die "The selected touchpad is unavailable: $device"
mkdir -p /etc/udev/rules.d
[[ -L $unit_link ]] || ln -sT "$bundle/$unit" "$unit_link"
[[ -L $rule_link ]] || ln -sT "$bundle/$rule" "$rule_link"
systemctl daemon-reload
systemctl enable "$bundle/$unit"
udevadm control --reload
udevadm trigger --action=change --settle "$device"
[[ $alias_path -ef $device ]] || die "udev did not assign the selected touchpad to $alias_path."
systemctl start "$unit"
for _ in {1..50}; do
    if systemctl is-active --quiet "$unit" && filtered_pad_present; then
        echo "The 30 mm palm filter is active and enabled for future boots."
        exit 0
    fi
    sleep 0.1
done
die "The filtered touchpad did not appear. Inspect journalctl -u $unit -b."
