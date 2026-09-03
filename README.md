# AOE2 Helper

Since the default keyboard shortcuts are either hard to remember or too far to press, I rearranged some hotkeys based on the locations and names. The key idea is to make the frequently-used hotkeys easily reachable with the left hand or use the initial letter of the name. Further, I include some strategies (build orders) to help beginners get a quick and well-organized start.

## Linux one-hand controls

`custom-macros` contains **AOE2 Helper**, a Linux-only tool for Age of Empires II: Definitive
Edition running through Steam/Proton. It is designed around a one-hand keyboard
with `1`--`6`, tilde, `F1`--`F5`, and the left-hand letter keys while preserving
`W/A/S/D` for camera movement.

Tilde cycles through four rows whose mappings are shown while the program runs:

- Economy buildings
- Military buildings
- Economy and positioning helpers
- Control-group assignment

The multi-action helpers are intended for single-player/offline games, not
ranked multiplayer or tournaments.

Run with the default X11 backend:

```bash
cd custom-macros
./run-linux.sh
```

X11 displays a solid dark status box measuring 650 by 82 pixels near the left
edge of the screen. It is not transparent and does not cover the whole screen.

For Wayland on Debian or Ubuntu, install `python-evdev`, list accessible input
devices, and select the one-hand keyboard:

```bash
sudo apt install python3-evdev
./run-linux.sh --backend wayland --list-devices
./run-linux.sh --backend wayland --device "HCT USB Entry Keyboard"
```

Wayland does not display the X11 status box; it prints the active row in the
terminal. It also requires access to the selected `/dev/input/event*` device and
`/dev/uinput`.

See [the complete setup and AoE2 hotkey assignments](custom-macros/README.md).

## Note

The document should be built with `PdfLaTeX`.

## Inspiration
Modified [AOE2-CheatSheet](https://github.com/YizeWang/Age-of-Empires-2-Cheat-Sheet/tree/master), to fit my usecase.

## Reference

- Keyboard Shortcuts by Meng: https://www.bilibili.com/video/av22359198

- Build Orders by Cicero: https://www.aoezone.net/threads/interactive-build-order-guide.150157

- St4rk Tutorials: https://www.youtube.com/channel/UCoX5HqFM4qEGJYfj0TEOIpg

- Build Order Reference: https://buildorderreference.com/

- Hera Build Orders: https://www.patreon.com/heraaoe2/posts
