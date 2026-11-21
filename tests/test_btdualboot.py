#!/usr/bin/env python3
"""Tests for bin/btdualboot using a synthetic registry hive and a fake
/var/lib/bluetooth. Run:  python3 tests/test_btdualboot.py"""

import glob
import importlib.machinery
import importlib.util
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "bin", "btdualboot")

_loader = importlib.machinery.SourceFileLoader("btdualboot", SCRIPT)
_spec = importlib.util.spec_from_loader("btdualboot", _loader)
bd = importlib.util.module_from_spec(_spec)
_loader.exec_module(bd)

ADAPTER = "00:1A:7D:DA:71:13"
CLASSIC_MAC = "AA:BB:CC:DD:EE:FF"
LE_WIN_MAC = "C2:9E:1D:E2:3D:A6"
LE_LINUX_MAC = "C2:9E:1D:E2:3D:A5"
CLASSIC_KEY = bytes(range(0x10, 0x20))
LTK = bytes.fromhex("FECC408F2B62AB18B9390543AF4CB409")
IRK = bytes.fromhex("00112233445566778899AABBCCDDEEFF")
ERAND = 0x1122334455667788
EDIV = 0xBEEF


class HiveBuilder:
    """Writes the subset of the regf format btdualboot reads."""

    def __init__(self):
        self.buf = bytearray(b"hbin" + b"\0" * 28)   # first hbin header

    def cell(self, data):
        size = (len(data) + 4 + 7) // 8 * 8
        off = len(self.buf)
        self.buf += struct.pack("<i", -size) + data + b"\0" * (size - 4 - len(data))
        return off

    def value(self, name, typ, data):
        if len(data) <= 4:
            d_size = 0x80000000 | len(data)
            d_off = struct.unpack("<I", data.ljust(4, b"\0"))[0]
        else:
            d_off, d_size = self.cell(data), len(data)
        nm = name.encode()
        return self.cell(b"vk" + struct.pack("<HIIIHH", len(nm), d_size, d_off, typ, 1, 0) + nm)

    def key(self, name, subs=(), vals=(), list_type="lf", utf16=False):
        sub_list = 0xFFFFFFFF
        if subs:
            if list_type == "lf":
                sub_list = self.cell(b"lf" + struct.pack("<H", len(subs)) +
                                     b"".join(struct.pack("<II", o, 0) for o in subs))
            elif list_type == "li":
                sub_list = self.cell(b"li" + struct.pack("<H", len(subs)) +
                                     b"".join(struct.pack("<I", o) for o in subs))
            else:  # ri -> li + lh
                a = self.cell(b"li" + struct.pack("<HI", 1, subs[0]))
                b = self.cell(b"lh" + struct.pack("<H", len(subs) - 1) +
                              b"".join(struct.pack("<II", o, 0) for o in subs[1:]))
                sub_list = self.cell(b"ri" + struct.pack("<HII", 2, a, b))
        val_list = self.cell(b"".join(struct.pack("<I", o) for o in vals)) if vals else 0xFFFFFFFF
        nm = name.encode("utf-16-le") if utf16 else name.encode()
        body = bytearray(0x4C)
        body[0:2] = b"nk"
        struct.pack_into("<H", body, 0x02, 0 if utf16 else 0x20)
        struct.pack_into("<II", body, 0x14, len(subs), 0)
        struct.pack_into("<II", body, 0x1C, sub_list, 0xFFFFFFFF)
        struct.pack_into("<II", body, 0x24, len(vals), val_list)
        struct.pack_into("<II", body, 0x2C, 0xFFFFFFFF, 0xFFFFFFFF)
        struct.pack_into("<H", body, 0x48, len(nm))
        return self.cell(bytes(body) + nm)

    def save(self, path, root, dirty=False):
        data = bytearray(self.buf)
        size = (len(data) + 4095) // 4096 * 4096
        data += b"\0" * (size - len(data))
        struct.pack_into("<II", data, 4, 0, size)
        hdr = bytearray(4096)
        hdr[0:4] = b"regf"
        struct.pack_into("<II", hdr, 4, 7, 6 if dirty else 7)
        struct.pack_into("<II", hdr, 0x24, root, size)
        with open(path, "wb") as f:
            f.write(bytes(hdr) + bytes(data))


def make_hive(path, dirty=False):
    b = HiveBuilder()
    le = b.key(LE_WIN_MAC.replace(":", "").lower(), vals=[
        b.value("LTK", 3, LTK),
        b.value("KeyLength", 4, struct.pack("<I", 16)),
        b.value("ERand", 11, struct.pack("<Q", ERAND)),
        b.value("EDIV", 4, struct.pack("<I", EDIV)),
        b.value("IRK", 3, IRK),
        b.value("AddressType", 4, struct.pack("<I", 1)),
    ])
    le_unpaired = b.key("d00000000001", vals=[b.value("LTK", 3, bytes(16))], utf16=True)
    adapter = b.key(ADAPTER.replace(":", "").lower(), subs=[le, le_unpaired], list_type="ri",
                    vals=[b.value(CLASSIC_MAC.replace(":", "").lower(), 3, CLASSIC_KEY),
                          b.value("MasterIRK", 3, bytes(16))])
    keys = b.key("Keys", [adapter], list_type="li")
    k = b.key("Parameters", [keys])
    k = b.key("BTHPORT", [k])
    k = b.key("Services", [k])
    cs = b.key("ControlSet001", [k])
    sel = b.key("Select", vals=[b.value("Current", 4, struct.pack("<I", 1))])
    b.save(path, b.key("ROOT", [cs, sel]), dirty)


def make_bt_dir(root):
    a = os.path.join(root, ADAPTER)
    os.makedirs(os.path.join(a, CLASSIC_MAC))
    os.makedirs(os.path.join(a, LE_LINUX_MAC))
    os.makedirs(os.path.join(a, "cache"))
    with open(os.path.join(a, CLASSIC_MAC, "info"), "w") as f:
        f.write("[General]\nName=Test Keyboard\nServices=0000110e-0000-1000-8000-00805f9b34fb;\n\n"
                "[LinkKey]\nKey=00000000000000000000000000000000\nType=4\nPINLength=0\n")
    with open(os.path.join(a, LE_LINUX_MAC, "info"), "w") as f:
        f.write("[General]\nName=Test Mouse\nAddressType=static\n\n"
                "[IdentityResolvingKey]\nKey=FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\n\n"
                "[LongTermKey]\nKey=11111111111111111111111111111111\nAuthenticated=0\n"
                "EncSize=16\nEDiv=1\nRand=2\n")
    with open(os.path.join(a, "cache", LE_LINUX_MAC), "w") as f:
        f.write("[General]\nName=Test Mouse\n")


class BtDualbootTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.hive = os.path.join(self.tmp, "SYSTEM")
        self.bt = os.path.join(self.tmp, "bluetooth")
        self.backups = os.path.join(self.tmp, "backups")
        make_hive(self.hive)
        make_bt_dir(self.bt)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, *args):
        cmd = [sys.executable, SCRIPT, "--bt-dir", self.bt, "--backup-dir", self.backups,
               "--no-restart", "--no-automount"] + list(args)
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True)

    def info(self, mac):
        return bd.load_info(os.path.join(self.bt, ADAPTER, mac, "info"))

    def test_parse_hive(self):
        hive = bd.Hive(self.hive)
        self.assertFalse(hive.dirty)
        _, win = bd.read_windows_keys(hive)
        self.assertEqual(win[ADAPTER]["classic"], {CLASSIC_MAC: CLASSIC_KEY})
        self.assertIn(LE_WIN_MAC, win[ADAPTER]["le"])
        self.assertIn("D0:00:00:00:00:01", win[ADAPTER]["le"])   # UTF-16 key name

    def test_le_mapping(self):
        _, win = bd.read_windows_keys(bd.Hive(self.hive))
        upd = bd.le_updates(win[ADAPTER]["le"][LE_WIN_MAC], reverse_irk=False)
        self.assertEqual(upd["LongTermKey"], {"Key": LTK.hex().upper(), "EncSize": "16",
                                              "EDiv": str(EDIV), "Rand": str(ERAND)})
        self.assertEqual(upd["IdentityResolvingKey"]["Key"], IRK.hex().upper())
        rev = bd.le_updates(win[ADAPTER]["le"][LE_WIN_MAC], reverse_irk=True)
        self.assertEqual(rev["IdentityResolvingKey"]["Key"], IRK[::-1].hex().upper())

    def test_preview_changes_nothing(self):
        path = os.path.join(self.bt, ADAPTER, CLASSIC_MAC, "info")
        with open(path) as f:
            before = f.read()
        out = self.run_cli("--hive", self.hive).stdout
        self.assertIn("WILL UPDATE", out)
        self.assertIn("--map %s=%s" % (LE_WIN_MAC, LE_LINUX_MAC), out)
        self.assertNotIn(CLASSIC_KEY.hex().upper(), out)          # keys masked
        with open(path) as f:
            self.assertEqual(before, f.read())
        self.assertFalse(os.path.exists(self.backups))

    def test_apply_restore(self):
        r = self.run_cli("--hive", self.hive, "--apply", "--map",
                         "%s=%s" % (LE_WIN_MAC, LE_LINUX_MAC.replace(":", "").lower()))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.info(CLASSIC_MAC).get("LinkKey", "Key"), CLASSIC_KEY.hex().upper())
        self.assertEqual(self.info(CLASSIC_MAC).get("LinkKey", "Type"), "4")      # kept
        mouse = self.info(LE_WIN_MAC)
        self.assertEqual(mouse.get("LongTermKey", "Key"), LTK.hex().upper())
        self.assertEqual(mouse.get("LongTermKey", "Rand"), str(ERAND))
        self.assertEqual(mouse.get("General", "Name"), "Test Mouse")
        self.assertFalse(os.path.exists(os.path.join(self.bt, ADAPTER, LE_LINUX_MAC)))
        self.assertTrue(os.path.exists(os.path.join(self.bt, ADAPTER, "cache", LE_WIN_MAC)))

        self.assertIn("Nothing to change", self.run_cli("--hive", self.hive).stdout)

        backup = glob.glob(os.path.join(self.backups, "*.tar.gz"))
        self.assertEqual(len(backup), 1)
        self.assertEqual(oct(os.stat(backup[0]).st_mode & 0o777), "0o600")
        r = self.run_cli("--restore", backup[0])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.info(CLASSIC_MAC).get("LinkKey", "Key"), "0" * 32)
        self.assertTrue(os.path.exists(os.path.join(self.bt, ADAPTER, LE_LINUX_MAC)))

    def test_dirty_hive_blocks_apply(self):
        make_hive(self.hive, dirty=True)
        r = self.run_cli("--hive", self.hive, "--apply")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not flushed", r.stdout)
        self.assertEqual(self.info(CLASSIC_MAC).get("LinkKey", "Key"), "0" * 32)
        r = self.run_cli("--hive", self.hive, "--apply", "--force")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_bad_input(self):
        self.assertIn("not a registry hive", self.run_cli("--hive", SCRIPT).stdout)
        self.assertIn("Bad --map", self.run_cli("--hive", self.hive, "--map", "xx").stdout)


if __name__ == "__main__":
    unittest.main()
