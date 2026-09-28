# linux-bluetooth-dongle-fix

**Pakai hanya dongle Bluetooth USB di Linux: matikan Bluetooth bawaan laptop, aktifkan Bluetooth Low Energy (BLE), dan perbaiki keyboard BLE yang tersambung tapi tidak bisa mengetik.**

English: [README.md](README.md)

Seharusnya jalan di Ubuntu, Debian, Linux Mint, Pop!_OS, Fedora, Arch, dan distro apa pun yang memakai **systemd + udev + BlueZ**.

## Cocok untukmu kalau...

- Bluetooth laptop **lag, patah-patah, atau sering putus** (audio tersendat, kursor mouse loncat, Wi-Fi melambat saat Bluetooth dipakai), lalu kamu membeli dongle Bluetooth USB.
- Sekarang ada **dua adapter Bluetooth** dan Linux malah memakai yang salah.
- **Keyboard/mouse BLE tidak muncul** saat scan, atau **tersambung tapi tidak bisa mengetik**.
- Kamu pernah mengikuti tutorial yang menyetel `ControllerMode = bredr` atau memasang skrip udev `btmgmt le on`, lalu Bluetooth jadi tidak stabil.
- Kamu mau setup Bluetooth bisa dipasang lagi **dengan satu perintah setelah install ulang Linux**.

## Mulai cepat

```bash
git clone https://github.com/khaichi11/linux-bluetooth-dongle-fix.git
cd linux-bluetooth-dongle-fix
sudo ./install.sh --dry-run   # lihat hasil deteksi, tidak mengubah apa pun
sudo ./install.sh             # terapkan
```

Colok dongle **sebelum** menjalankan installer. Yang dikerjakan installer:

1. Mencari chip Bluetooth bawaan secara otomatis (perangkat Bluetooth USB di port `fixed`, alias tersolder) lalu mematikannya lewat aturan udev. Chip itu tetap mati setiap kali boot.
2. Menyetel `ControllerMode = dual` di `/etc/bluetooth/main.conf` supaya Classic **dan** Low Energy sama-sama jalan.
3. Mempensiunkan hack udev lama yang menjalankan `btmgmt`/`hciconfig`, karena hack itu balapan dengan `bluetoothd`.
4. Memasang dua perintah bantu: `btinternal` dan `btpairing`.

Semua perubahan dibackup ke `/var/backups/bt-dongle-fix/`. Untuk membatalkan semuanya: `sudo ./uninstall.sh`.

Kalau deteksi otomatis tidak menemukan apa-apa (sebagian laptop melaporkan port sebagai `unknown`), pilih chipnya sendiri. `--dry-run` menampilkan semua perangkat Bluetooth lengkap dengan `VID:PID`-nya:

```bash
sudo ./install.sh --internal VID:PID
```

## Perintah

| Perintah | Fungsi |
|---|---|
| `btinternal status` | Status chip bawaan, apakah aturan udev terpasang, `ControllerMode`, dan controller yang terlihat oleh BlueZ |
| `sudo btinternal on` | Hidupkan lagi Bluetooth bawaan sampai reboot berikutnya |
| `sudo btinternal off` | Matikan lagi |
| `sudo btpairing backup [FILE]` | Simpan semua pairing (kunci) ke berkas `.tar.gz` privat |
| `sudo btpairing restore FILE` | Pulihkan pairing, misalnya setelah install ulang |

## Setelah install ulang Linux

Sebelum memformat, backup pairing supaya tidak perlu pairing ulang semua perangkat:

```bash
sudo btpairing backup ~/bt-pairing.tar.gz   # salin ke flashdisk atau penyimpanan pribadi
```

Setelah install baru:

```bash
git clone https://github.com/khaichi11/linux-bluetooth-dongle-fix.git
cd linux-bluetooth-dongle-fix
sudo ./install.sh
sudo btpairing restore ~/bt-pairing.tar.gz
```

Kunci pairing terikat ke MAC address dongle, jadi restore hanya berhasil kalau kamu memakai **dongle yang sama**.

> **Peringatan:** Berkas backup pairing berisi kunci enkripsi. Jangan di-commit dan jangan diunggah ke tempat publik. `.gitignore` sudah memblokir `bt-pairing*.tar.gz`.

## Cara pairing keyboard BLE yang benar

Keyboard BLE wajib **bonding** (pairing terenkripsi). Aplikasi GUI seperti Blueman kadang hanya menekan "connect" tanpa menuntaskan pairing. Akibatnya keyboard terlihat tersambung, tapi tidak ada tombol yang masuk. Lakukan pairing dari terminal:

```bash
bluetoothctl
```

Ketik perintah **satu baris per satu baris**, karena paste beberapa baris sekaligus akan membuat perintahnya rusak:

```
scan on
```

Masukkan keyboard ke **mode pairing** (LED berkedip cepat; biasanya tahan `Fn` + tombol channel Bluetooth). Setelah muncul `[NEW] Device XX:XX:XX:XX:XX:XX <nama>`:

```
pair XX:XX:XX:XX:XX:XX
```

Kalau muncul passkey 6 digit, **ketik angka itu di keyboard Bluetooth-nya lalu tekan Enter di keyboard itu**. Setelah itu:

```
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
scan off
quit
```

Cek hasilnya dengan `bluetoothctl info XX:XX:XX:XX:XX:XX`. Yang dicari: `Paired: yes`, `Bonded: yes`, `Trusted: yes`.

## Cara kerjanya

Saat chip bawaan muncul, aturan udev menulis `0` ke atribut `authorized` milik chip itu. Kernel lalu melepas konfigurasi perangkat USB tersebut: `btusb` tidak pernah terpasang dan `hciX` tidak pernah dibuat. Chip masih terlihat di `lsusb`, tetapi tidak berfungsi.

```
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="xxxx", ATTR{idProduct}=="yyyy", ATTR{removable}=="fixed", ATTR{authorized}="0"
```

Ada dua pengaman supaya dongle tidak ikut kena. Aturan ini hanya cocok dengan `VID:PID` chip bawaan, **dan** hanya di port `fixed`. Apa pun yang dicolok ke port luar berstatus `removable`, jadi tidak mungkin cocok. Kalau kernel melaporkan `unknown`, aturan mencocokkan nama port internal yang persis sebagai gantinya.

Kenapa tidak memakai cara yang biasa?

| Cara | Masalahnya |
|---|---|
| Blacklist `btusb` | Dongle ikut mati, karena memakai driver yang sama |
| `rfkill block hci0` | Nomor `hci` berubah-ubah tiap boot, jadi bisa salah blokir |
| `btmgmt le on` di skrip udev | Balapan dengan `bluetoothd`, jadi kadang jalan kadang tidak |
| `ControllerMode = bredr` | Low Energy mati total, sehingga perangkat BLE tidak pernah muncul |

## Masalah yang diperbaiki dan cara mendiagnosisnya

Lihat **[docs/troubleshooting.id.md](docs/troubleshooting.id.md)**. Setiap masalah dijelaskan lengkap dengan gejala, penyebab, solusi, dan perintah untuk membuktikannya.

## Seharusnya kompatibel dengan

- **Chip bawaan:** semua Bluetooth yang tersambung lewat USB, termasuk kartu kombo Wi-Fi+Bluetooth Intel AX200/AX201/AX210/AX211, Realtek RTL8852/RTL8822/RTL8723, dan MediaTek MT7921/MT7922.
- **Dongle:** semua dongle USB yang didukung BlueZ, misalnya yang berbasis Realtek RTL8761B (TP-Link UB400/UB500, ASUS USB-BT500, Orico, UGREEN).
- **Sudah diuji di:** Ubuntu 24.04, BlueZ 5.72.

Sudah mencobanya di distro atau chip lain? Buka issue atau PR untuk menambahkannya ke daftar ini.

## Lisensi

[MIT](LICENSE)
