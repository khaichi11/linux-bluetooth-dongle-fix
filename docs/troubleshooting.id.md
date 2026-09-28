# Troubleshooting: dongle Bluetooth di Linux

English version: [troubleshooting.md](troubleshooting.md)

Urutan masalah di bawah ini mengikuti urutan yang biasanya dialami. Setiap masalah dijelaskan dengan gejala, penyebab, solusi, dan perintah untuk mengeceknya.

---

## 1. Bluetooth lag atau patah-patah di laptop dengan kartu kombo Wi-Fi + Bluetooth

**Gejala:** Audio Bluetooth tersendat, kursor mouse loncat, ketikan telat masuk, atau Wi-Fi melambat saat Bluetooth dipakai.

**Penyebab:** Kebanyakan laptop menaruh Wi-Fi dan Bluetooth di **satu kartu kombo** (Intel AX2xx, Realtek RTL88xx, MediaTek MT79xx). Keduanya berbagi radio dan antena 2,4 GHz yang sama, lalu bergantian memakainya ("coexistence"). Di Linux pembagian waktu ini sering lebih buruk daripada di Windows, apalagi kalau Wi-Fi tersambung di 2,4 GHz.

**Solusi:** Pakai dongle Bluetooth USB terpisah supaya Bluetooth punya radio sendiri, lalu matikan Bluetooth bawaan (masalah berikutnya). Dua hal lain yang juga membantu:
- Sambungkan Wi-Fi ke **5 GHz** kalau router mendukung.
- Colok dongle ke **port USB 2.0**, atau pakai kabel ekstensi USB pendek. Port dan kabel USB 3.0 memancarkan derau ke pita 2,4 GHz.

---

## 2. Ada dua adapter Bluetooth dan Linux memakai yang salah

**Gejala:** Setelah dongle dicolok, `bluetoothctl list` menampilkan dua controller. Perangkat ter-pair ke adapter bawaan, adapter "default" berganti-ganti tiap boot, dan menu pengaturan menampilkan dua tombol Bluetooth.

**Penyebab:** BlueZ memakai semua adapter yang ditemukannya. Nomor `hci0`/`hci1` dibagikan sesuai urutan chip mana yang siap lebih dulu, jadi urutannya tidak tetap.

**Solusi:** `sudo ./install.sh` mematikan chip bawaan di level USB lewat udev, sehingga BlueZ hanya melihat dongle.

**Cek:**
```bash
bluetoothctl list        # harus tepat satu controller
btinternal status        # bawaan: OFF
lsusb                    # chip bawaan tetap terdaftar, dan itu normal
```

---

## 3. Keyboard/mouse BLE tidak pernah muncul saat scan

**Gejala:** Perangkat Classic (headset lama) bisa dipakai, tetapi perangkat Bluetooth Low Energy (kebanyakan keyboard, mouse, earbuds, dan smartband modern) tidak pernah muncul.

**Penyebab:** `/etc/bluetooth/main.conf` berisi `ControllerMode = bredr`. Sebagian tutorial menyarankan setelan ini untuk masalah dongle, padahal setelan ini **mematikan Low Energy sepenuhnya**.

**Solusi:** Setel `ControllerMode = dual` (sudah dikerjakan oleh `install.sh`), lalu restart Bluetooth:
```bash
sudo systemctl restart bluetooth
```

**Cek:** `le` harus ada di current settings:
```bash
sudo btmgmt info | grep 'current settings'
# current settings: powered ssp br/edr le secure-conn   # ada "le"
```

---

## 4. Skrip udev "btmgmt le on" membuat Bluetooth tidak stabil

**Gejala:** LE kadang jalan kadang tidak, atau adapter mati-hidup sendiri tepat setelah muncul.

**Penyebab:** Tambalan yang populer memasang aturan udev yang menjalankan `btmgmt power off; btmgmt le on; btmgmt power on` setiap kali dongle muncul. Skrip ini berebut dengan `bluetoothd`, yang sedang mengonfigurasi adapter di saat yang sama, sehingga hasilnya tergantung siapa yang selesai terakhir. Kalau digabung dengan `ControllerMode = bredr`, kedua setelan itu saling membatalkan.

**Solusi:** Hapus hack itu dan pakai `ControllerMode = dual`. `install.sh` mengganti nama semua aturan udev yang menjalankan `btmgmt`/`hciconfig` menjadi `*.disabled`.

**Cek:**
```bash
grep -lE 'btmgmt|hciconfig' /etc/udev/rules.d/*.rules   # harus kosong
```

---

## 5. Keyboard BLE tersambung tapi tidak bisa mengetik

**Gejala:** Keyboard terlihat **Connected** di Blueman atau Pengaturan GNOME, tetapi tidak ada tombol yang masuk.

**Penyebab:** Keyboard tersambung tanpa **bonding**. Keyboard BLE (HID over GATT) hanya mengirim ketikan lewat koneksi yang terenkripsi dan sudah di-bond. Aplikasi GUI kadang menekan "Connect" tanpa pernah menuntaskan pairing, atau melewatkan langkah passkey.

**Cek:**
```bash
bluetoothctl info XX:XX:XX:XX:XX:XX
#   Paired: no     # ini masalahnya
#   Bonded: no     # ini masalahnya
#   UUID: Human Interface Device (00001812-...)   # memastikan ini keyboard BLE
```

**Solusi:** Hapus data pairing yang setengah jadi, lalu pairing ulang dari terminal:
```bash
bluetoothctl remove XX:XX:XX:XX:XX:XX
```
Ikuti langkah di [Cara pairing keyboard BLE yang benar](../README.id.md#cara-pairing-keyboard-ble-yang-benar). Passkey 6 digit harus **diketik di keyboard Bluetooth-nya**, bukan di keyboard laptop.

Kalau berhasil, log kernel akan menampilkan keyboard sebagai perangkat input:
```bash
sudo dmesg | grep -i 'bluetooth hid'
# hid-generic ...: BLUETOOTH HID v0.01 Keyboard [<nama>] on <mac-dongle>
```

---

## 6. Perintah yang di-paste ke bluetoothctl jadi kacau

**Gejala:** Setelah paste beberapa perintah sekaligus, muncul hal aneh seperti `agent KeyboardDisplayKeyboardDisplay` atau MAC address yang kelebihan byte.

**Penyebab:** Prompt `bluetoothctl` tidak bisa menangani paste beberapa baris.

**Solusi:** Ketik atau paste **satu perintah per satu perintah**. Agent sudah terdaftar otomatis, jadi `agent ...` dan `default-agent` boleh dilewati.

---

## 7. Blueman masih menganggap LE mati setelah config diperbaiki

**Penyebab:** Blueman membaca kemampuan adapter saat baru dibuka, lalu menyimpannya di cache.

**Solusi:** Tutup Blueman sepenuhnya (ikon tray -> Exit), lalu buka lagi setelah `systemctl restart bluetooth`.

---

## 8. Perangkat tidak muncul walaupun LE sudah aktif

**Penyebab:** Keyboard dan mouse BLE **hanya mengiklankan diri saat mode pairing**. Sekadar dinyalakan belum cukup.

**Solusi:** Masuk ke mode pairing (LED berkedip cepat; biasanya tahan `Fn` + tombol channel Bluetooth sekitar 3 detik), lalu scan. Kalau ragu perangkatnya sedang mengiklan atau tidak, jalankan `bluetoothctl` -> `scan on`. Perintah ini menampilkan semua perangkat yang terdengar, termasuk yang disembunyikan Blueman.

---

## 9. Semua pairing hilang setelah install ulang Linux

**Penyebab:** Kunci pairing disimpan di `/var/lib/bluetooth/<mac-adapter>/<mac-perangkat>/`, dan ikut terhapus saat sistem diinstal ulang.

**Solusi:** Jalankan `sudo btpairing backup` sebelum install ulang, lalu `sudo btpairing restore FILE` sesudahnya. Cara ini hanya berlaku untuk dongle yang sama, karena kuncinya terikat ke MAC dongle. Simpan berkas backup secara privat, karena isinya kunci enkripsi.

---

## 10. Dongle sama sekali tidak terdeteksi

**Cek firmware:**
```bash
sudo dmesg | grep -iE 'bluetooth|rtl_bt|firmware' | tail -20
```
- `firmware file rtl_bt/rtl8761bu_fw.bin not found`: pasang atau perbarui `linux-firmware` (Ubuntu/Debian: `sudo apt install --reinstall linux-firmware`), lalu cabut-colok dongle.
- Tidak ada baris `hci` sama sekali: coba port USB lain, dan pastikan `lsusb` menampilkan dongle.
- Kernel yang sangat lama (sebelum 5.x) mungkin belum mendukung dongle Realtek yang lebih baru.

**Cek service:**
```bash
systemctl status bluetooth
rfkill list bluetooth     # "Soft blocked: yes" -> rfkill unblock bluetooth
```

---

## Perintah yang berguna

| Perintah | Menampilkan |
|---|---|
| `bluetoothctl list` | Controller yang bisa dipakai BlueZ |
| `bluetoothctl show` | Detail controller default (powered, discoverable, dst.) |
| `sudo btmgmt info` | Setelan yang didukung vs. yang aktif (`le`, `br/edr`) |
| `bluetoothctl devices Paired` | Perangkat yang sudah di-pair |
| `bluetoothctl info MAC` | Status Paired / Bonded / Trusted / Connected untuk satu perangkat |
| `lsusb` + `btinternal status` | Chip mana yang mana, dan apakah chip bawaan sudah mati |
| `journalctl -u bluetooth -b` | Log `bluetoothd` sejak boot terakhir |
