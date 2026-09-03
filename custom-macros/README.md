# AOE2 Helper

AOE2 Helper is a Linux-only tool for Age of Empires II: Definitive Edition running from
Steam. It turns the six number keys into one-press building shortcuts. Select
one or more villagers first, press a number, then place the building with the
mouse. Tilde cycles through economy buildings, military buildings, helpers, and
group assignment. The X11 overlay always shows the active row; on Wayland, the
same information is printed in the terminal instead.

| Key | Economy mode | Military mode |
| --- | --- | --- |
| `1` | House | Barracks |
| `2` | Farm | Archery Range |
| `3` | Lumber Camp | Stable |
| `4` | Mill | Siege Workshop |
| `5` | Mining Camp | Castle |
| `6` | Dock | Watch Tower |

The fourth mode assigns the selected units or villagers to a control group:

| Key | Group command |
| --- | --- |
| `1` | Replace group 1 |
| `2` | Replace group 2 |
| `3` | Replace group 3 |
| `4` | Replace group 4 |
| `5` | Replace group 5 |

Configure AoE2's **Select Group 1--5** commands as `F1`--`F5`. The workflow is:
select some units or villagers, switch the overlay to Groups and press `1`--`5`
to assign them; later press the corresponding `F1`--`F5` to recall them.

The layout deliberately avoids `W`, `A`, `S`, and `D`, leaving them available
for camera movement. Modified number keys are not captured, so `Ctrl+1` and
`Shift+1` can still be used for control groups.

## One-time AoE2 hotkey setup

In **Options > Hotkeys**, assign these keys. Clear any conflicting assignment
in the same command context if the game reports one.

| AoE2 command | Key |
| --- | --- |
| Economy Buildings menu | `Q` |
| Military Buildings menu | `E` |
| House / Barracks | `Q` |
| Farm / Archery Range | `E` |
| Lumber Camp / Stable | `R` |
| Mill / Siege Workshop | `T` |
| Mining Camp / Castle | `F` |
| Dock / Watch Tower | `G` |

The same target key can be reused because economy and military buildings are in
different menus. Keep your camera assignments on `W/A/S/D`.

## Run

From this directory:

```bash
chmod +x run-linux.sh aoe2_macros.py
./run-linux.sh
```

Leave the terminal open while playing. Press `Ctrl+C` in it to stop. The small
overlay shows the current mode and all six mappings, so it doubles as the only
reference card you need. Run `./run-linux.sh --list` to check the layout without
capturing any keys.

The default backend is X11 and uses libraries already supplied by Ubuntu. It
does not need `sudo` or extra Python packages.

## Wayland

Wayland blocks the global hotkey method used by X11. The Wayland backend instead
reads only the selected one-hand keyboard through Linux `evdev`, grabs that device, and
re-emits ordinary keys through `uinput`. Install its dependency first:

On Debian or Ubuntu:

```bash
sudo apt install python3-evdev
```

List the keyboard devices your account can access:

```bash
./run-linux.sh --backend wayland --list-devices
```

Then run using either the event path or a unique part of its displayed name:

```bash
./run-linux.sh --backend wayland --device "Corne Keyboard"
```

To avoid typing `--device` again, put that path or name after
`wayland_device =` in `keybindings.ini`. Your account needs read access to the
keyboard's `/dev/input/event*` node and write access to `/dev/uinput`. On most
distributions this means adding your account to the `input` group and then
logging out and back in:

```bash
sudo usermod -aG input "$USER"
```

Distribution security policies vary, so check the device permissions if it is
still absent from `--list-devices`. Do not run the whole macro program with
`sudo`. Membership in `input` grants broad access to input devices; a device-
specific udev rule is safer on a shared machine. Wayland mode prints the active
row and mappings in the terminal because the small X11 overlay is unavailable.

If no accessible devices are listed, inspect permissions and current groups:

```bash
ls -l /dev/input/event* /dev/uinput
id -nG
getent group input
```

If `input` is missing from `id -nG`, add it and then fully log out of the desktop
session and back in (opening a new terminal is not sufficient):

```bash
sudo usermod -aG input "$USER"
```

If `/dev/uinput` does not exist, load its kernel module once with
`sudo modprobe uinput`. Persistent module loading and device permissions depend
on the Linux distribution.

Edit `keybindings.ini` to change labels, triggers, or sent keys. Its entry format
is `trigger = keys_to_send | Action name`.
`key_hold_ms` controls how long each generated key stays pressed; increase it if
AoE2 misses inputs on a low-frame-rate system.

## Troubleshooting input

If an overlay appears, the X11 backend is running. An X11 overlay can itself
appear through XWayland even when the desktop session is Wayland; that does not
mean its synthetic X11 keys will reach a Proton game. Use `--backend wayland` on
a Wayland session.

To distinguish backend trouble from an AoE2 hotkey mismatch, start on the
Economy row, focus a text editor, and press `1` once. It should type `qq`:

- Nothing appears: the selected backend is not injecting input correctly.
- `qq` appears: injection works; check that AoE2's Economy Buildings menu and
  House hotkeys are both configured as `Q`.

Generated keys are held for `key_hold_ms` rather than pressed and released in
the same instant. The default of 40 ms should be visible to a 60 FPS game.

## Suggested remaining one-hand bindings

Set these directly inside AoE2; the macro does not capture them:

- `F1` to `F5`: recall control groups 1 to 5
- `Space`: select/centre town centre
- `Tab`: next idle villager
- `Shift+Tab`: all idle villagers
- `W/A/S/D`: camera movement
- `Esc`: cancel

Start with these few bindings and add more only when a repeated action is
actually slowing you down.

## Unit controls and new scripts

Prefer AoE2 DE's own **Options > Hotkeys** screen for unit controls. This gives
one physical key one game action, works correctly through Steam/Proton, and is
appropriate for multiplayer. A suggested one-hand starting layout is:

| Key | Selected-unit command |
| --- | --- |
| `Q` | Attack move |
| `E` | Stop |
| `R` | Patrol |
| `T` | Garrison / unload |
| `F` | Follow |
| `G` | Guard |
| `Z` | Aggressive stance |
| `X` | Defensive stance |
| `C` | Stand-ground stance |
| `V` | Pack / unpack |
| `B` | Attack ground |

These commands are contextual, so reusing keys that are also building commands
is normally fine. `W/A/S/D` remain reserved for the camera.

To add or change a binding, edit the appropriate section in `keybindings.ini`.
The part before `|` is the key or chord sent to AoE2, and the part after it is
the overlay label.

For example:

```ini
[groups]
1 = ctrl+1 | Set Group 1
```

## Helpers

The Helpers row is part of the normal `./run-linux.sh` launcher:

| Key | Helper action |
| --- | --- |
| `1` | Select all TCs, queue a villager, send villagers back to work |
| `2` | Select one idle villager and place one farm under the cursor |
| `3` | Send all idle villagers to nearby shelters |
| `4` | Garrison selected villagers into the building under the cursor |
| `5` | Move all idle military units to the cursor |

Seek Shelter chooses nearby garrisonable buildings; AoE2 DE does not guarantee
that every villager will choose a Town Centre. Helper `4` is the precise option:
select the nearby villagers yourself and place the cursor over the particular
building before pressing it. The movement action selects all idle **military
units** because AoE2 DE exposes that selection hotkey; it cannot reliably select
only infantry without screen reading or game-state automation.

For farm placement, keep the mouse stationary and move the camera to put the
desired tile underneath it. Press `2` once per farm—holding it does not repeat.

The Helpers row assumes the hotkeys documented above plus:

- Select all town centres: `Shift+Space`
- Next idle villager: `Tab`
- Select all idle villagers: `Shift+Tab`
- Select all idle military: `Shift+grave`
- Seek Shelter: `G`
- Garrison: `T`
- Move command: right-click

The existing building feature sends two game inputs from one physical input.
Use that, or any longer sequence such as selecting units and then issuing an
order, only where the rules of your match explicitly allow macros. Do not build
screen-reading, auto-queue, repeated monk micro, or timed command automation for
ranked or tournament play. The current official tournament handbook explicitly
prohibits external software that turns one input into multiple inputs:
https://www.ageofempires.com/news/tournament_handbook_ageiide/
