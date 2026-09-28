# linux-bluetooth-dongle-fix

**Use only a USB Bluetooth dongle on Linux: disable the built-in Bluetooth, enable Bluetooth Low Energy (BLE), and fix BLE keyboards that connect but don't type.**

Bahasa Indonesia: [README.id.md](README.id.md)

Should work on Ubuntu, Debian, Linux Mint, Pop!_OS, Fedora, Arch and any distro with **systemd + udev + BlueZ**.

## Is this for you?

- Bluetooth on your laptop **lags, stutters or drops** (audio skips, mouse jumps, Wi-Fi slows down while Bluetooth is on), so you bought a USB Bluetooth dongle.
- Now there are **two Bluetooth adapters** and Linux keeps using the wrong one.
- Your **BLE keyboard/mouse doesn't show up** when scanning, or it **connects but doesn't type**.
- You followed a tutorial that set `ControllerMode = bredr` or added a `btmgmt le on` udev script, and Bluetooth became flaky.
- You want your Bluetooth setup back in **one command after reinstalling Linux**.

## Quick start

```bash
git clone https://github.com/khaichi11/linux-bluetooth-dongle-fix.git
cd linux-bluetooth-dongle-fix
sudo ./install.sh --dry-run   # see what it detects, changes nothing
sudo ./install.sh             # apply
```

Plug in the dongle **before** installing. The installer:

1. Finds the built-in Bluetooth chip automatically (a USB Bluetooth device on a `fixed`, i.e. soldered, port) and disables it with a udev rule. It stays off after every reboot.
2. Sets `ControllerMode = dual` in `/etc/bluetooth/main.conf` so Classic **and** Low Energy both work.
3. Retires old udev hacks that run `btmgmt`/`hciconfig` (they race with `bluetoothd`).
4. Installs two helper commands: `btinternal` and `btpairing`.

Everything is backed up to `/var/backups/bt-dongle-fix/`. Undo it all with `sudo ./uninstall.sh`.

If auto-detection finds nothing (some laptops report ports as `unknown`), pick the chip yourself. `--dry-run` lists every Bluetooth device with its `VID:PID`:

```bash
sudo ./install.sh --internal VID:PID
```

## Commands

| Command | What it does |
|---|---|
| `btinternal status` | Built-in chip on/off, rule installed?, `ControllerMode`, controllers seen by BlueZ |
| `sudo btinternal on` | Turn built-in Bluetooth back on until the next reboot |
| `sudo btinternal off` | Turn it off again |
| `sudo btpairing backup [FILE]` | Save all pairings (keys) to a private `.tar.gz` |
| `sudo btpairing restore FILE` | Restore pairings, e.g. after reinstalling Linux |

## After reinstalling Linux

Before wiping, back up your pairings so you don't have to pair every device again:

```bash
sudo btpairing backup ~/bt-pairing.tar.gz   # copy it to a USB stick / private storage
```

After the fresh install:

```bash
git clone https://github.com/khaichi11/linux-bluetooth-dongle-fix.git
cd linux-bluetooth-dongle-fix
sudo ./install.sh
sudo btpairing restore ~/bt-pairing.tar.gz
```

Pairing keys are tied to the dongle's MAC address, so restoring works as long as you use the **same dongle**.

> **Warning:** The pairing archive contains encryption keys. Never commit it or upload it anywhere public. `.gitignore` already blocks `bt-pairing*.tar.gz`.

## Pairing a BLE keyboard properly

BLE keyboards need **bonding** (encrypted pairing). GUI tools like Blueman sometimes only "connect" without finishing it. The keyboard then shows as connected, but no keys arrive. Pair from the terminal instead:

```bash
bluetoothctl
```

Type these **one line at a time** (pasting several lines garbles them):

```
scan on
```

Put the keyboard in **pairing mode** (LED blinking fast, usually by holding `Fn` + a Bluetooth channel key). When `[NEW] Device XX:XX:XX:XX:XX:XX <name>` appears:

```
pair XX:XX:XX:XX:XX:XX
```

If a 6-digit passkey appears, **type it on the Bluetooth keyboard and press Enter on that keyboard**. Then:

```
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
scan off
quit
```

Check it with `bluetoothctl info XX:XX:XX:XX:XX:XX`. You want `Paired: yes`, `Bonded: yes`, `Trusted: yes`.

## How it works

The udev rule writes `0` to the chip's `authorized` attribute when it appears. The kernel then de-configures the USB device: `btusb` never binds and no `hciX` is created. The chip is still listed by `lsusb` but does nothing.

```
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="xxxx", ATTR{idProduct}=="yyyy", ATTR{removable}=="fixed", ATTR{authorized}="0"
```

Two safety checks keep your dongle from being hit: the rule matches only the chip's `VID:PID`, **and** only a `fixed` port. Anything plugged into an external port is `removable`, so it can never match. When the kernel reports `unknown`, the rule matches the exact internal port name instead.

Why not the usual alternatives?

| Approach | Problem |
|---|---|
| Blacklist `btusb` | Kills the dongle too, because it uses the same driver |
| `rfkill block hci0` | `hci` numbers change between boots, so you block the wrong one |
| `btmgmt le on` in a udev script | Races with `bluetoothd`, so it works only sometimes |
| `ControllerMode = bredr` | Turns Low Energy off completely, so BLE devices never appear |

## Problems this fixes, and how to diagnose them

See **[docs/troubleshooting.md](docs/troubleshooting.md)** for every problem with its symptom, cause, fix and the command that proves it.

## Should work with

- **Built-in chips:** any USB-attached Bluetooth, including Intel AX200/AX201/AX210/AX211, Realtek RTL8852/RTL8822/RTL8723 and MediaTek MT7921/MT7922 Wi-Fi+Bluetooth combo cards.
- **Dongles:** any BlueZ-supported USB dongle, e.g. Realtek RTL8761B-based ones (TP-Link UB400/UB500, ASUS USB-BT500, Orico, UGREEN).
- **Tested on:** Ubuntu 24.04, BlueZ 5.72.

Tested it on another distro or chip? Open an issue or PR to add it here.

## License

[MIT](LICENSE)

## Trademarks

Bluetooth is a registered trademark of Bluetooth SIG, Inc. Linux is a registered trademark of Linus Torvalds. Ubuntu is a registered trademark of Canonical Ltd. All other product and company names are trademarks of their respective owners and are used here only to describe compatibility. This project is not affiliated with or endorsed by any of them.
