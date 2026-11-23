"""Check the chords against the keyd v2.5.0 parser and keyboard engine."""

import argparse
import ctypes
from itertools import permutations
import os
from pathlib import Path
import re
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
KEYS = {
    name: int(code)
    for name, code in re.findall(
        r"^#define\s+KEY_(\w+)\s+(\d+)\b",
        Path("/usr/include/linux/input-event-codes.h").read_text(),
        re.MULTILINE,
    )
}
MODIFIERS = {"LEFTALT", "RIGHTALT", "LEFTCTRL", "RIGHTCTRL", "LEFTSHIFT", "RIGHTSHIFT", "LEFTMETA", "RIGHTMETA"}
MODIFIER_NAMES = {KEYS[name]: name for name in MODIFIERS}
# keyd can emit either side for a Shift or Ctrl modifier.
MODIFIER_NAMES[KEYS["RIGHTSHIFT"]] = "LEFTSHIFT"
MODIFIER_NAMES[KEYS["RIGHTCTRL"]] = "LEFTCTRL"
CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_uint8, ctypes.c_uint8)


def load_engine(source, output):
    src = source / "src"
    units = "config ini keyboard keys log macro string unicode util".split()
    subprocess.run([
        os.environ.get("CC", "cc"), "-shared", "-fPIC", "-D_DEFAULT_SOURCE",
        '-DDATA_DIR="/usr/share/keyd"', "-iquote", str(src), "-o", str(output),
        HERE / "keyd_probe.c", *(src / f"{unit}.c" for unit in units),
    ], check=True)
    engine = ctypes.CDLL(str(output))
    engine.load_config.argtypes = [ctypes.c_char_p]
    engine.begin_case.argtypes = [CALLBACK]
    engine.send_event.argtypes = [ctypes.c_uint8, ctypes.c_uint8]
    if engine.load_config(os.fsencode(HERE.parent / "diamond.conf")):
        raise ValueError("keyd could not parse diamond.conf")
    return engine


def check(engine, modifiers, physical, expected, expected_modifiers, release_key_first=True):
    held = set()
    outputs = []

    @CALLBACK
    def record(code, pressed):
        if pressed:
            held.add(code)
            if code not in MODIFIER_NAMES:
                active = {MODIFIER_NAMES[k] for k in held if k in MODIFIER_NAMES}
                outputs.append((code, active))
        else:
            held.discard(code)

    engine.begin_case(record)
    for mod in modifiers:
        engine.send_event(KEYS[mod], 1)
    engine.send_event(KEYS[physical], 1)
    if release_key_first:
        engine.send_event(KEYS[physical], 0)
    for mod in reversed(modifiers):
        engine.send_event(KEYS[mod], 0)
    if not release_key_first:
        engine.send_event(KEYS[physical], 0)

    if outputs != [(KEYS[expected], set(expected_modifiers))] or held:
        raise AssertionError(f"{modifiers} + {physical}: got {outputs}, held {held}, expected {expected} {expected_modifiers}")


def check_bindings(engine):
    arrows = {"I": "UP", "J": "LEFT", "K": "DOWN", "L": "RIGHT"}
    navigation = dict(arrows, U="PAGEUP", M="PAGEDOWN", H="BACKSPACE", APOSTROPHE="DELETE", SEMICOLON="ESC")
    for mods, bindings in [(("LEFTALT",), navigation), (("LEFTALT", "LEFTCTRL"), {"J": "HOME", "L": "END"})]:
        for physical, expected in bindings.items():
            for shift in [(), ("LEFTSHIFT",), ("RIGHTSHIFT",)]:
                for order in permutations(mods + shift):
                    for release_key_first in (True, False):
                        check(engine, order, physical, expected, ("LEFTSHIFT",) if shift else (), release_key_first)

    for physical in navigation:
        check(engine, (), physical, physical, ())
        check(engine, ("RIGHTALT",), physical, physical, ("RIGHTALT",))
    for physical in ("J", "L"):
        check(engine, ("LEFTALT", "RIGHTCTRL"), physical, arrows[physical], ("LEFTCTRL",))
    for mods, key in [(("LEFTALT",), "TAB"), (("LEFTALT",), "F4"), (("LEFTCTRL",), "C"),
                      (("LEFTCTRL", "LEFTALT"), "F3"), (("LEFTMETA",), "SPACE")]:
        for order in permutations(mods):
            check(engine, order, key, key, mods)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="path to the upstream keyd v2.5.0 source tree")
    with tempfile.TemporaryDirectory() as tmp:
        check_bindings(load_engine(parser.parse_args().source, Path(tmp) / "keyd_probe.so"))
    print("Diamond cursor bindings passed.")
