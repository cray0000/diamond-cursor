# Testing the Linux diamond cursor

Run the following from the repository’s `linux/` directory.

**Installer tests** need Python 3 and Bubblewrap (`bubblewrap` on Ubuntu). They run the real scripts in a disposable filesystem with simulated APT and systemd commands.

```sh
python3 test/installer.py
```

**Binding tests** need Python 3, a C compiler with Linux development headers (`build-essential` on Ubuntu), and the keyd v2.5.0 source. The suite compiles keyd’s remapping engine in a temporary directory and sends it synthetic key presses. It checks each binding, both Shift keys, modifier order, key release, and ordinary shortcuts.

```sh
git clone --depth 1 --branch v2.5.0 https://github.com/rvaiya/keyd.git /tmp/keyd-2.5.0
python3 test/bindings.py /tmp/keyd-2.5.0
```
