#!/bin/bash
# Build one private Clutter library against Ubuntu's matching Mutter sources.
set -euo pipefail
export LC_ALL=C
output=$(realpath -- "$1")
here=$(dirname -- "$(realpath -- "$0")")
work=$(mktemp -d)
trap 'rm -r -- "$work"' EXIT
cd "$work"
lib=libmutter-clutter-51.so.0
installed=/usr/lib/x86_64-linux-gnu/mutter-51/$lib
sha256sum /usr/bin/gnome-shell "$(realpath "$installed")" /usr/lib/x86_64-linux-gnu/libmutter-51.so.0 > "$output/ubuntu.sha256"
mkdir -p debs/partial sysroot/usr
base=https://archive.ubuntu.com/ubuntu/pool/main/m/mutter
for archive in mutter_51.0.orig.tar.xz mutter_51.0-1ubuntu3.debian.tar.xz; do
    curl --fail --location --silent --show-error --retry 2 --proto '=https' "$base/$archive" -o "$archive"
done
sha256sum --check --status <<'SUMS'
5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3  mutter_51.0.orig.tar.xz
3ed4fd1f6cca56a9a6e62292382ae677500bb8b4f3807c9c5ebd71c34e0b1727  mutter_51.0-1ubuntu3.debian.tar.xz
SUMS
tar -xf mutter_51.0.orig.tar.xz
tar -xf mutter_51.0-1ubuntu3.debian.tar.xz
cp "$here/mutter-51.patch" diamond.patch

# Download missing build dependencies into this temporary tree. Installed
# dependencies are visible through the read-only /usr overlay below.
packages=(
    patch build-essential meson ninja-build pkgconf patchelf gettext xcvt systemd-dev
    bash-completion gnome-control-center-data gnome-settings-daemon-dev gsettings-desktop-schemas-dev
    libcairo2-dev libcanberra-gtk3-dev libcolord-dev libdisplay-info-dev libdrm-dev
    libegl1-mesa-dev libei-dev libeis-dev libfribidi-dev libgbm-dev libgl-dev
    libgles-dev libglib2.0-dev libgnome-desktop-4-dev libgraphene-1.0-dev
    libgtk-4-dev libgudev-1.0-dev libice-dev libinput-dev libjson-glib-dev
    liblcms2-dev libpam0g-dev libsoup-3.0-dev libpango1.0-dev libpipewire-0.3-dev libpixman-1-dev libsm-dev
    libstartup-notification0-dev libsysprof-6-dev libsysprof-capture-4-dev libsystemd-dev libudev-dev
    libumockdev-dev python3-argcomplete python3-dbusmock python3-docutils sysprof
    libwacom-dev libwayland-dev libx11-dev libx11-xcb-dev libxau-dev
    libxcb-res0-dev libxcomposite-dev libxcursor-dev libxdamage-dev libxext-dev
    libxfixes-dev libxi-dev libxinerama-dev libxkbcommon-dev libxkbregistry-dev
    libxrandr-dev libxrender-dev wayland-protocols xkb-data xwayland
)
apt-get -y --download-only --no-install-recommends -o Debug::NoLocking=1 \
    -o "Dir::Cache::archives=$work/debs" install "${packages[@]}"
shopt -s nullglob
for deb in debs/*.deb; do dpkg-deb -x "$deb" sysroot; done

bwrap --unshare-all --die-with-parent --ro-bind /etc /etc --symlink usr/bin /bin \
    --symlink usr/lib /lib --symlink usr/lib64 /lib64 --overlay-src /usr \
    --overlay-src "$work/sysroot/usr" --ro-overlay /usr --dev /dev --proc /proc \
    --tmpfs /tmp --bind "$work" /work --chdir /work --clearenv \
    --setenv PATH /usr/bin:/bin --setenv HOME /tmp --setenv LANG C.UTF-8 -- /bin/bash -eu <<'BUILD'
while read -r name _; do
    [[ -z $name || $name == '#'* ]] && continue
    patch --batch --fuzz=0 -d mutter-51.0 -p1 < "debian/patches/$name"
done < debian/patches/series
patch --batch --fuzz=0 -d mutter-51.0 -p1 < diamond.patch
meson setup build mutter-51.0 --prefix=/usr --libdir=lib/x86_64-linux-gnu \
    --buildtype=release -Db_ndebug=false -Dudev_dir=/usr/lib/udev -Dintrospection=false \
    -Dremote_desktop=true -Dtests=disabled -Dclutter_tests=false -Dcogl_tests=false \
    -Dmutter_tests=false -Ddocs=false
lib=libmutter-clutter-51.so.0
libdir=/usr/lib/x86_64-linux-gnu/mutter-51
jobs=$(nproc)
ninja -j"$((jobs < 8 ? jobs : 8))" -C build "clutter/clutter/$lib.0.0"
strip --strip-unneeded -o "$lib" "build/clutter/clutter/$lib.0.0"
patchelf --set-rpath "$libdir" "$lib"
# GNOME introspection opens this absolute name. Both loads must resolve to
# the same object or Clutter will try to register its GObject types twice.
patchelf --set-soname "$libdir/$lib" "$lib"
symbols() { nm -D --defined-only "$1" | awk '{print $3}' | sort; }
symbols "$libdir/$lib" > stock.symbols
symbols "./$lib" > build.symbols
cmp stock.symbols build.symbols
BUILD

# Resolve dependencies on the actual host after leaving the build overlay.
ldd -r "./$lib" > link-report 2>&1
if grep -E 'not found|undefined symbol' link-report; then exit 1; fi
install -D -m 0644 "$lib" "$output/lib/$lib"
