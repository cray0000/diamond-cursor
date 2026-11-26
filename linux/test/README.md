# Testing the Linux diamond cursor

GitHub Actions runs the tests on Ubuntu for every push. To run them locally, start in the repository’s `linux/` directory. [Linux workflow](../../.github/workflows/linux-tests.yml)

**Installer tests** need Python 3 and Bubblewrap (`bubblewrap` on Ubuntu). They run the real scripts in a disposable filesystem with simulated APT and systemd commands.

```sh
python3 test/installer.py
```

**Extras tests** use the same sandbox with simulated GNOME settings and touchpads. They cover prior settings, edge widths, device selection, download verification, and removal after a failed start. The scroll-extra tests substitute a build fixture and exercise independent installation and removal in both orders, reuse of the shared library, upgrade fallback, and rollback after a failed install.

```sh
python3 -B test/extras.py
```

**Binding tests** need Python 3, a C compiler with Linux development headers (`build-essential` on Ubuntu), and the keyd v2.5.0 source. The suite compiles keyd’s remapping engine in a temporary directory and sends it synthetic key presses. It checks each binding, both Shift keys, modifier order, key release, and ordinary shortcuts.

```sh
git clone --depth 1 --branch v2.5.0 https://github.com/rvaiya/keyd.git /tmp/keyd-2.5.0
python3 test/bindings.py /tmp/keyd-2.5.0
```
