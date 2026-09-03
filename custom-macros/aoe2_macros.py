#!/usr/bin/env python3
"""Linux hotkey daemon for the AoE2 DE one-hand layout."""

from __future__ import annotations

import argparse
import configparser
import ctypes
import ctypes.util
import os
from pathlib import Path
import select
import sys
import time


KEY_PRESS = 2
KEY_RELEASE = 3
EXPOSE = 12
EXPOSURE_MASK = 1 << 15
GRAB_MODE_ASYNC = 1
LOCK_MASK = 1 << 1
MOD2_MASK = 1 << 4
MODIFIER_KEYS = {
    "ctrl": "Control_L",
    "control": "Control_L",
    "shift": "Shift_L",
    "alt": "Alt_L",
}
MOUSE_BUTTONS = {"mouse_left": 1, "mouse_middle": 2, "mouse_right": 3}


class XKeyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("keycode", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("xkey", XKeyEvent), ("pad", ctypes.c_long * 24)]


class XFontStruct(ctypes.Structure):
    _fields_ = [("ext_data", ctypes.c_void_p), ("fid", ctypes.c_ulong)]


def load_library(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if not path:
        raise RuntimeError(f"Linux library lib{name} is not installed")
    return ctypes.CDLL(path)


def configure_x11() -> tuple[ctypes.CDLL, ctypes.CDLL]:
    x11 = load_library("X11")
    xtst = load_library("Xtst")

    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
    x11.XStringToKeysym.restype = ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XKeysymToKeycode.restype = ctypes.c_uint
    x11.XGrabKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ]
    x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
    x11.XPending.argtypes = [ctypes.c_void_p]
    x11.XPending.restype = ctypes.c_int
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XCreateSimpleWindow.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    x11.XCreateSimpleWindow.restype = ctypes.c_ulong
    x11.XCreateGC.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
    x11.XCreateGC.restype = ctypes.c_void_p
    x11.XSetForeground.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    x11.XLoadQueryFont.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    x11.XLoadQueryFont.restype = ctypes.POINTER(XFontStruct)
    x11.XSetFont.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    x11.XStoreName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_char_p]
    x11.XMapRaised.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XSelectInput.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long]
    x11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XClearWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XDrawString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XChangeProperty.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
    ]
    x11.XkbSetDetectableAutoRepeat.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
    ]
    xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeKeyEvent.restype = ctypes.c_int
    xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.restype = ctypes.c_int
    return x11, xtst


def read_config(
    path: Path,
) -> tuple[dict[str, dict[str, tuple[list[str], str]]], tuple[str, ...], str, int, bool, str]:
    config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    if not config.read(path):
        raise RuntimeError(f"Cannot read configuration: {path}")

    general = config["general"]
    modes = tuple(part.strip() for part in general.get("modes", "economy, military, groups").split(","))
    if not modes or any(not mode for mode in modes) or len(set(modes)) != len(modes):
        raise RuntimeError("general.modes must contain unique, comma-separated section names")

    bindings: dict[str, dict[str, tuple[list[str], str]]] = {}
    for mode in modes:
        if not config.has_section(mode):
            raise RuntimeError(f"Missing [{mode}] section in {path}")
        bindings[mode] = {}
        for trigger, value in config.items(mode):
            sequence_text, separator, label = value.partition("|")
            sequence = sequence_text.split()
            if not separator or not sequence or not label.strip():
                raise RuntimeError(f"Invalid {mode} binding for {trigger!r}")
            bindings[mode][trigger.strip()] = (sequence, label.strip())

    toggle = general.get("toggle", "grave").strip()
    delay_ms = general.getint("key_delay_ms", 35)
    overlay = general.getboolean("show_overlay", True)
    wayland_device = general.get("wayland_device", "").strip()
    if not 0 <= delay_ms <= 500:
        raise RuntimeError("key_delay_ms must be between 0 and 500")
    return bindings, modes, toggle, delay_ms, overlay, wayland_device


class Overlay:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.x11 = None
        self.display = None
        self.window = 0
        self.gc = None
        self.lines: list[str] = []

    def connect(self, x11: ctypes.CDLL, display: int, root: int) -> None:
        if not self.enabled:
            return
        self.x11 = x11
        self.display = display
        self.window = x11.XCreateSimpleWindow(display, root, 16, 250, 650, 82, 0, 0, 0x20242B)
        self.gc = x11.XCreateGC(display, self.window, 0, None)
        x11.XSetForeground(display, self.gc, 0xFFFFFF)
        font = x11.XLoadQueryFont(display, b"10x20")
        if font:
            x11.XSetFont(display, self.gc, font.contents.fid)
        x11.XStoreName(display, self.window, b"AoE2 build macros")
        x11.XSelectInput(display, self.window, EXPOSURE_MASK)

        # Ask the window manager to keep this small reference above the game.
        atom = x11.XInternAtom(display, b"ATOM", False)
        state = x11.XInternAtom(display, b"_NET_WM_STATE", False)
        values = (ctypes.c_ulong * 2)(
            x11.XInternAtom(display, b"_NET_WM_STATE_ABOVE", False),
            x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_TASKBAR", False),
        )
        x11.XChangeProperty(
            display,
            self.window,
            state,
            atom,
            32,
            0,
            ctypes.cast(values, ctypes.POINTER(ctypes.c_ubyte)),
            2,
        )
        x11.XMapRaised(display, self.window)
        x11.XFlush(display)

    def update(self, mode: str, entries: dict[str, tuple[list[str], str]], action: str = "") -> None:
        if not self.window or self.x11 is None or self.display is None:
            return
        items = [f"{key} {label}" for key, (_, label) in entries.items()]
        midpoint = (len(items) + 1) // 2
        rows = ("   •   ".join(items[:midpoint]), "   •   ".join(items[midpoint:]))
        text = f"AoE2 — {mode.title()} mode"
        if action:
            text += f"  |  {action} selected"
        self.lines = [text, *(row for row in rows if row)]
        self.draw()

    def draw(self) -> None:
        if not self.window or self.x11 is None or self.display is None:
            return
        self.x11.XClearWindow(self.display, self.window)
        for index, line in enumerate(self.lines):
            # XDrawString uses the locale's single-byte encoding; all labels here
            # are ASCII after replacing the cosmetic punctuation.
            encoded = line.replace("—", "-").replace("•", "|").encode("ascii", "replace")
            self.x11.XDrawString(
                self.display,
                self.window,
                self.gc,
                12,
                20 + index * 24,
                encoded,
                len(encoded),
            )
        self.x11.XRaiseWindow(self.display, self.window)
        self.x11.XFlush(self.display)


class MacroDaemon:
    def __init__(
        self,
        bindings: dict[str, dict[str, tuple[list[str], str]]],
        modes: tuple[str, ...],
        toggle: str,
        delay_ms: int,
        overlay: Overlay,
    ) -> None:
        self.bindings = bindings
        self.modes = modes
        self.toggle = toggle
        self.delay = delay_ms / 1000
        self.overlay = overlay
        self.mode = modes[0]
        self.down: set[int] = set()
        self.x11, self.xtst = configure_x11()
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Cannot open the X11 display; check DISPLAY and XAUTHORITY")
        self.root = self.x11.XDefaultRootWindow(self.display)
        self.overlay.connect(self.x11, self.display, self.root)
        self.trigger_codes: dict[int, str] = {}

    def keycode(self, name: str) -> int:
        keysym = self.x11.XStringToKeysym(name.encode())
        code = self.x11.XKeysymToKeycode(self.display, keysym) if keysym else 0
        if not code:
            raise RuntimeError(f"Unknown X11 key name: {name!r}")
        return code

    def grab_keys(self) -> None:
        trigger_names = {self.toggle}
        for mode in self.modes:
            trigger_names.update(self.bindings[mode])
        for name in trigger_names:
            code = self.keycode(name)
            self.trigger_codes[code] = name
            # Preserve Ctrl/Alt/Shift combinations; account for Caps Lock and Num Lock.
            for modifiers in (0, LOCK_MASK, MOD2_MASK, LOCK_MASK | MOD2_MASK):
                self.x11.XGrabKey(
                    self.display,
                    code,
                    modifiers,
                    self.root,
                    False,
                    GRAB_MODE_ASYNC,
                    GRAB_MODE_ASYNC,
                )
        supported = ctypes.c_int()
        self.x11.XkbSetDetectableAutoRepeat(self.display, True, ctypes.byref(supported))
        self.x11.XFlush(self.display)

    def send_sequence(self, sequence: list[str]) -> None:
        for token in sequence:
            if token.lower() in MOUSE_BUTTONS:
                button = MOUSE_BUTTONS[token.lower()]
                self.xtst.XTestFakeButtonEvent(self.display, button, True, 0)
                self.xtst.XTestFakeButtonEvent(self.display, button, False, 0)
            else:
                parts = token.split("+")
                names = [MODIFIER_KEYS.get(part.lower(), part) for part in parts]
                codes = [self.keycode(name) for name in names]
                for code in codes:
                    self.xtst.XTestFakeKeyEvent(self.display, code, True, 0)
                for code in reversed(codes):
                    self.xtst.XTestFakeKeyEvent(self.display, code, False, 0)
            self.x11.XFlush(self.display)
            if self.delay:
                time.sleep(self.delay)

    def run(self) -> None:
        self.grab_keys()
        self.overlay.update(self.mode, self.bindings[self.mode])
        print("AoE2 DE controls running. Tilde changes mode; Ctrl+C exits.")
        print("Plain 1-6 use the current row; modified number keys remain available.")
        event = XEvent()
        try:
            while True:
                while not self.x11.XPending(self.display):
                    time.sleep(0.01)
                self.x11.XNextEvent(self.display, ctypes.byref(event))
                code = event.xkey.keycode
                if event.type == EXPOSE:
                    self.overlay.draw()
                    continue
                if event.type == KEY_RELEASE:
                    self.down.discard(code)
                    continue
                if event.type != KEY_PRESS or code in self.down:
                    continue
                self.down.add(code)
                trigger = self.trigger_codes.get(code)
                if trigger == self.toggle:
                    self.mode = self.modes[(self.modes.index(self.mode) + 1) % len(self.modes)]
                    self.overlay.update(self.mode, self.bindings[self.mode])
                    print(f"Mode: {self.mode}")
                    continue
                binding = self.bindings[self.mode].get(trigger or "")
                if binding:
                    sequence, label = binding
                    self.send_sequence(sequence)
                    self.overlay.update(self.mode, self.bindings[self.mode], label)
                    print(f"{trigger}: {label}")
        finally:
            self.x11.XCloseDisplay(self.display)


def load_evdev():
    try:
        import evdev

        return evdev
    except ImportError as error:
        raise RuntimeError(
            "Wayland needs python-evdev; install the 'python3-evdev' package"
        ) from error


def wayland_keycode(name: str, ecodes) -> int:
    aliases = {
        "control_l": "KEY_LEFTCTRL",
        "shift_l": "KEY_LEFTSHIFT",
        "alt_l": "KEY_LEFTALT",
        "grave": "KEY_GRAVE",
        "space": "KEY_SPACE",
        "delete": "KEY_DELETE",
        "tab": "KEY_TAB",
        "escape": "KEY_ESC",
        "esc": "KEY_ESC",
    }
    lowered = name.lower()
    code_name = aliases.get(lowered)
    if code_name is None and len(name) == 1 and name.isalnum():
        code_name = f"KEY_{name.upper()}"
    if code_name is None:
        code_name = f"KEY_{name.upper()}"
    code = getattr(ecodes, code_name, None)
    if code is None:
        raise RuntimeError(f"Unknown evdev key name: {name!r}")
    return code


def accessible_input_devices(evdev) -> list[tuple[str, str]]:
    devices: list[tuple[str, str]] = []
    # Calling without newer optional arguments also supports python-evdev 1.6,
    # which ships with Ubuntu 22.04.
    for path in evdev.list_devices():
        device = evdev.InputDevice(path)
        try:
            keys = device.capabilities().get(evdev.ecodes.EV_KEY, [])
            if evdev.ecodes.KEY_1 in keys and evdev.ecodes.KEY_GRAVE in keys:
                devices.append((path, device.name))
        finally:
            device.close()
    return devices


def print_input_devices() -> None:
    evdev = load_evdev()
    devices = accessible_input_devices(evdev)
    if not devices:
        print("No accessible keyboard devices found.")
        print("Check membership of the input group and log out/in after changing it.")
        return
    for path, name in devices:
        print(f"{path}: {name}")


def choose_input_device(evdev, device_spec: str):
    if not device_spec:
        raise RuntimeError(
            "Wayland needs --device PATH_OR_NAME (use --list-devices first), "
            "or set general.wayland_device in keybindings.ini"
        )
    if Path(device_spec).exists():
        return evdev.InputDevice(device_spec)

    matches = [item for item in accessible_input_devices(evdev) if device_spec.lower() in item[1].lower()]
    if len(matches) == 1:
        return evdev.InputDevice(matches[0][0])
    if not matches:
        raise RuntimeError(f"No accessible input device matches {device_spec!r}")
    names = ", ".join(f"{path} ({name})" for path, name in matches)
    raise RuntimeError(f"Device name is ambiguous; use a path instead: {names}")


class WaylandDaemon:
    def __init__(
        self,
        bindings: dict[str, dict[str, tuple[list[str], str]]],
        modes: tuple[str, ...],
        toggle: str,
        delay_ms: int,
        device_spec: str,
    ) -> None:
        self.evdev = load_evdev()
        self.ecodes = self.evdev.ecodes
        self.bindings = bindings
        self.modes = modes
        self.mode = modes[0]
        self.toggle = toggle
        self.delay = delay_ms / 1000
        self.device = choose_input_device(self.evdev, device_spec)
        self.output = None
        self.trigger_codes: dict[int, str] = {}
        trigger_names = {toggle}
        for mode in modes:
            trigger_names.update(bindings[mode])
        for name in trigger_names:
            self.trigger_codes[wayland_keycode(name, self.ecodes)] = name
        self.modifier_codes = {
            self.ecodes.KEY_LEFTCTRL,
            self.ecodes.KEY_RIGHTCTRL,
            self.ecodes.KEY_LEFTSHIFT,
            self.ecodes.KEY_RIGHTSHIFT,
            self.ecodes.KEY_LEFTALT,
            self.ecodes.KEY_RIGHTALT,
            self.ecodes.KEY_LEFTMETA,
            self.ecodes.KEY_RIGHTMETA,
        }
        self.modifiers_down: set[int] = set()
        self.captured_down: set[int] = set()

    def emit_key(self, code: int, value: int) -> None:
        self.output.write(self.ecodes.EV_KEY, code, value)

    def send_sequence(self, sequence: list[str]) -> None:
        for token in sequence:
            lowered = token.lower()
            if lowered in MOUSE_BUTTONS:
                buttons = {
                    "mouse_left": self.ecodes.BTN_LEFT,
                    "mouse_middle": self.ecodes.BTN_MIDDLE,
                    "mouse_right": self.ecodes.BTN_RIGHT,
                }
                code = buttons[lowered]
                self.emit_key(code, 1)
                self.emit_key(code, 0)
            else:
                parts = token.split("+")
                names = [MODIFIER_KEYS.get(part.lower(), part) for part in parts]
                codes = [wayland_keycode(name, self.ecodes) for name in names]
                for code in codes:
                    self.emit_key(code, 1)
                for code in reversed(codes):
                    self.emit_key(code, 0)
            self.output.syn()
            if self.delay:
                time.sleep(self.delay)

    def show_mode(self, action: str = "") -> None:
        suffix = f" | {action}" if action else ""
        entries = " | ".join(
            f"{key} {label}" for key, (_, label) in self.bindings[self.mode].items()
        )
        print(f"Mode: {self.mode}{suffix}")
        print(entries)

    def pass_event(self, event) -> None:
        if event.type == self.ecodes.EV_KEY:
            self.output.write(event.type, event.code, event.value)
            self.output.syn()

    def handle_key(self, event) -> None:
        code = event.code
        if code in self.modifier_codes:
            if event.value == 1:
                self.modifiers_down.add(code)
            elif event.value == 0:
                self.modifiers_down.discard(code)
            self.pass_event(event)
            return

        if code in self.captured_down:
            if event.value == 0:
                self.captured_down.discard(code)
            return

        trigger = self.trigger_codes.get(code)
        if trigger is None or self.modifiers_down or event.value != 1:
            self.pass_event(event)
            return

        self.captured_down.add(code)
        if trigger == self.toggle:
            self.mode = self.modes[(self.modes.index(self.mode) + 1) % len(self.modes)]
            self.show_mode()
            return
        binding = self.bindings[self.mode].get(trigger)
        if binding:
            sequence, label = binding
            self.send_sequence(sequence)
            self.show_mode(label)

    def run(self) -> None:
        # With no explicit capabilities UInput supports all KEY_* and BTN_* codes,
        # which covers both keyboard passthrough and cursor clicks.
        self.output = self.evdev.UInput(name="AoE2 One-Hand Virtual Keyboard")
        try:
            self.device.grab()
            print(f"Wayland device: {self.device.path} ({self.device.name})")
            print("AoE2 DE controls running. Tilde changes mode; Ctrl+C exits.")
            self.show_mode()
            while True:
                ready, _, _ = select.select([self.device.fd], [], [], 0.05)
                if not ready:
                    continue
                for event in self.device.read():
                    if event.type == self.ecodes.EV_KEY:
                        self.handle_key(event)
        finally:
            try:
                self.device.ungrab()
            except OSError:
                pass
            self.device.close()
            self.output.close()


def print_bindings(bindings: dict[str, dict[str, tuple[list[str], str]]]) -> None:
    for mode, entries in bindings.items():
        print(f"{mode.title()} mode")
        for trigger, (sequence, label) in entries.items():
            print(f"  {trigger}: {label:<16} -> {' '.join(sequence).upper()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("keybindings.ini"),
        help="configuration file (default: beside this script)",
    )
    parser.add_argument("--list", action="store_true", help="print bindings without grabbing keys")
    parser.add_argument(
        "--backend",
        choices=("x11", "wayland"),
        default="x11",
        help="input backend (default: x11)",
    )
    parser.add_argument(
        "--device",
        help="Wayland input device path or unique name fragment",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="list keyboards accessible to the Wayland backend",
    )
    parser.add_argument("--no-overlay", action="store_true", help="disable the X11 status window")
    args = parser.parse_args()

    try:
        if args.list_devices:
            print_input_devices()
            return 0
        bindings, modes, toggle, delay_ms, show_overlay, configured_device = read_config(args.config)
        if args.list:
            print_bindings(bindings)
            return 0
        if args.backend == "wayland":
            daemon = WaylandDaemon(
                bindings,
                modes,
                toggle,
                delay_ms,
                args.device or configured_device,
            )
        else:
            if os.environ.get("XDG_SESSION_TYPE", "x11").lower() == "wayland":
                raise RuntimeError(
                    "X11 is the default backend; run with --backend wayland on this session"
                )
            daemon = MacroDaemon(
                bindings,
                modes,
                toggle,
                delay_ms,
                Overlay(show_overlay and not args.no_overlay),
            )
        daemon.run()
        return 0
    except KeyboardInterrupt:
        print("\nAoE2 macros stopped.")
        return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
