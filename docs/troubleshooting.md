# Troubleshooting: Bluetooth dongle on Linux

Bahasa Indonesia: [troubleshooting.id.md](troubleshooting.id.md)

The problems below are in the order you usually hit them. Each one has the symptom, the cause, the fix, and a command to check it.

---

## 1. Bluetooth lags or stutters on a laptop with a Wi-Fi + Bluetooth combo card

**Symptom:** Bluetooth audio skips, the mouse cursor jumps, keystrokes arrive late, or Wi-Fi gets slow while Bluetooth is in use.

**Cause:** Most laptops put Wi-Fi and Bluetooth on **one combo card** (Intel AX2xx, Realtek RTL88xx, MediaTek MT79xx). They share the same 2.4 GHz radio and antenna and take turns using it ("coexistence"). On Linux that time-sharing is often worse than on Windows, especially when Wi-Fi is on 2.4 GHz.

**Fix:** Use a separate USB Bluetooth dongle so Bluetooth gets its own radio, then disable the built-in one (next problem). It also helps to:
- Put Wi-Fi on **5 GHz** when your router supports it.
- Plug the dongle into a **USB 2.0 port** or use a short USB extension cable. USB 3.0 ports and cables leak noise into the 2.4 GHz band.

---

## 2. Two Bluetooth adapters: Linux uses the wrong one

**Symptom:** After plugging in the dongle, `bluetoothctl list` shows two controllers. Devices pair to the built-in one, the "default" adapter changes between boots, and settings show two Bluetooth toggles.

**Cause:** BlueZ uses every adapter it finds. `hci0`/`hci1` are assigned in whatever order the chips come up, so the numbering is not stable.

**Fix:** `sudo ./install.sh` disables the built-in chip at the USB level via udev, so BlueZ only sees the dongle.

**Check:**
```bash
bluetoothctl list        # should show exactly one controller
btinternal status        # built-in: OFF
lsusb                    # the built-in chip is still listed, which is expected
```

---

## 3. BLE keyboard/mouse never shows up when scanning

**Symptom:** Classic devices (older headsets) work, but Bluetooth Low Energy devices (most modern keyboards, mice, earbuds, fitness bands) never appear.

**Cause:** `/etc/bluetooth/main.conf` contains `ControllerMode = bredr`. Some tutorials suggest it for dongle problems, but it turns Low Energy **off completely**.

**Fix:** Set `ControllerMode = dual`, which `install.sh` does for you, then restart Bluetooth:
```bash
sudo systemctl restart bluetooth
```

**Check:** `le` must be in the current settings:
```bash
sudo btmgmt info | grep 'current settings'
# current settings: powered ssp br/edr le secure-conn   # "le" present
```

---

## 4. A "btmgmt le on" udev script makes Bluetooth flaky

**Symptom:** LE works sometimes and not other times, or the adapter turns off and on by itself right after it appears.

**Cause:** A common workaround adds a udev rule that runs a script doing `btmgmt power off; btmgmt le on; btmgmt power on` whenever the dongle appears. It fights `bluetoothd`, which is configuring the adapter at the same moment, so whichever finishes last wins. Combined with `ControllerMode = bredr`, the two settings keep undoing each other.

**Fix:** Remove the hack and use `ControllerMode = dual` instead. `install.sh` renames any udev rule that runs `btmgmt`/`hciconfig` to `*.disabled`.

**Check:**
```bash
grep -lE 'btmgmt|hciconfig' /etc/udev/rules.d/*.rules   # should print nothing
```

---

## 5. BLE keyboard connects but doesn't type

**Symptom:** The keyboard shows as **Connected** in Blueman/GNOME Settings, but no keys arrive.

**Cause:** It was connected without being **bonded**. BLE keyboards (HID over GATT) only send keystrokes over an encrypted, bonded link. GUI tools sometimes press "Connect" and never finish pairing, or skip the passkey step.

**Check:**
```bash
bluetoothctl info XX:XX:XX:XX:XX:XX
#   Paired: no     # the problem
#   Bonded: no     # the problem
#   UUID: Human Interface Device (00001812-...)   # confirms it is a BLE keyboard
```

**Fix:** Delete the half-finished record, then pair from the terminal:
```bash
bluetoothctl remove XX:XX:XX:XX:XX:XX
```
Then follow [Pairing a BLE keyboard properly](../README.md#pairing-a-ble-keyboard-properly). The 6-digit passkey must be **typed on the Bluetooth keyboard itself**, not on the laptop.

When it works, the kernel log shows the keyboard as an input device:
```bash
sudo dmesg | grep -i 'bluetooth hid'
# hid-generic ...: BLUETOOTH HID v0.01 Keyboard [<name>] on <dongle-mac>
```

---

## 6. Commands pasted into bluetoothctl get mangled

**Symptom:** You paste several commands at once and get things like `agent KeyboardDisplayKeyboardDisplay` or a MAC address with extra bytes.

**Cause:** `bluetoothctl`'s prompt does not handle multi-line paste.

**Fix:** Type or paste **one command at a time**. The agent is registered automatically, so you can skip `agent ...` and `default-agent`.

---

## 7. Blueman still says LE is off after fixing the config

**Cause:** Blueman reads the adapter's capabilities when it starts and caches them.

**Fix:** Quit Blueman completely (tray icon -> Exit) and start it again after `systemctl restart bluetooth`.

---

## 8. The device doesn't appear even with LE on

**Cause:** BLE keyboards and mice advertise **only in pairing mode**. Being turned on is not enough.

**Fix:** Enter pairing mode (LED blinking fast; usually hold `Fn` + a Bluetooth channel key for about 3 seconds), then scan. If you're unsure whether it's advertising, `bluetoothctl` -> `scan on` shows every device it hears, including ones Blueman hides.

---

## 9. All pairings are gone after reinstalling Linux

**Cause:** Pairing keys are stored in `/var/lib/bluetooth/<adapter-mac>/<device-mac>/` and are wiped with the system.

**Fix:** Back them up with `sudo btpairing backup` before reinstalling and run `sudo btpairing restore FILE` afterwards. This only works with the same dongle, because the keys are tied to its MAC. Keep the archive private: it contains the encryption keys.

---

## 10. The dongle isn't detected at all

**Check the firmware:**
```bash
sudo dmesg | grep -iE 'bluetooth|rtl_bt|firmware' | tail -20
```
- `firmware file rtl_bt/rtl8761bu_fw.bin not found`: install or update `linux-firmware` (Ubuntu/Debian: `sudo apt install --reinstall linux-firmware`), then replug.
- No `hci` line at all: try another USB port and check that `lsusb` lists the dongle.
- Very old kernels (before 5.x) may not support newer Realtek dongles.

**Check the service:**
```bash
systemctl status bluetooth
rfkill list bluetooth     # "Soft blocked: yes" -> rfkill unblock bluetooth
```

---

## Useful commands

| Command | Shows |
|---|---|
| `bluetoothctl list` | Controllers BlueZ can use |
| `bluetoothctl show` | Default controller details (powered, discoverable...) |
| `sudo btmgmt info` | Supported vs. current settings (`le`, `br/edr`) |
| `bluetoothctl devices Paired` | Paired devices |
| `bluetoothctl info MAC` | Paired / Bonded / Trusted / Connected for one device |
| `lsusb` + `btinternal status` | Which chip is which, and whether the built-in one is off |
| `journalctl -u bluetooth -b` | `bluetoothd` log for this boot |
