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
- Kamu **dual boot Windows dan Linux**, dan harus pairing ulang keyboard/mouse setiap kali pindah OS.

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
4. Memasang tiga perintah bantu: `btinternal`, `btpairing`, dan `btdualboot`.

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
| `sudo btdualboot` | Pratinjau penyalinan kunci pairing dari Windows (dual boot); tidak mengubah apa pun |
| `sudo btdualboot --apply` | Salin kuncinya, supaya perangkat jalan di Windows dan Linux tanpa pairing ulang |
| `sudo btdualboot --restore FILE` | Batalkan `--apply` dari backup otomatisnya |

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

## Dual boot dengan Windows: pairing sekali, jalan di keduanya

Perangkat Bluetooth hanya menyimpan **satu** kunci pairing per komputer. Windows dan Linux di laptop yang sama terlihat seperti satu komputer (dongle sama, MAC sama), tapi masing-masing membuat kuncinya sendiri. Akibatnya, pairing di satu OS membuat perangkat tidak nyambung di OS lainnya. `btdualboot` menyalin kunci buatan Windows ke Linux, supaya kedua OS memakai kunci yang sama.

Registry Windows hanya **dibaca** (partisi Windows boleh tetap read-only). Yang diubah hanya file pairing di `/var/lib/bluetooth`, dan file itu di-backup dulu.

1. **Linux:** pairing perangkat seperti biasa. Jangan dihapus setelahnya, karena `btdualboot` memperbarui data ini.
2. **Windows:** pairing ulang perangkat yang sama (hapus dulu entri lamanya). Lalu matikan Windows sepenuhnya: matikan Fast Startup (*Control Panel > Power Options > Choose what the power buttons do*), atau tahan **Shift** sambil klik **Shut down**.
3. **Linux:** perangkat belum akan nyambung, dan itu normal. Jalankan:

```bash
sudo btdualboot            # pratinjau: daftar perangkat dan apa yang akan berubah
sudo btdualboot --apply    # terapkan (backup dulu, lalu restart bluetooth)
```

Belum dipasang lewat `install.sh`? Jalankan langsung dari folder repo: `sudo ./bin/btdualboot`. Cukup butuh Python 3.

Partisi Windows dicari otomatis, dan di-mount read-only kalau perlu. Kalau tidak ketemu, pakai `--hive /path/ke/Windows/System32/config/SYSTEM`.

**Mouse/keyboard BLE sering ganti alamat setiap pairing.** Pratinjau lalu menampilkan `NOT PAIRED IN LINUX` dan menyarankan entri Linux yang cocok:

```
[BLE] AA:BB:CC:DD:EE:02  (adapter 11:22:33:44:55:66)  ->  NOT PAIRED IN LINUX
    Probably the same device in Linux: AA:BB:CC:DD:EE:01 "My Mouse"
    -> run again with:  --map AA:BB:CC:DD:EE:02=AA:BB:CC:DD:EE:01
```

Tambahkan `--map` itu ke perintah `--apply`. Kalau satu perangkat muncul beberapa kali, berarti Windows masih menyimpan pairing lama: hapus perangkat itu di Windows, pairing sekali, lalu jalankan pratinjau lagi.

Pakai **dongle yang sama** di kedua OS. Kunci terikat ke MAC adapter, jadi perangkat yang di-pairing ke Bluetooth bawaan di Windows tidak bisa dipindah ke dongle di Linux. Nanti pairing ulang di salah satu OS? Ulangi langkah 2-3.

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

## Merek dagang

Bluetooth adalah merek dagang terdaftar milik Bluetooth SIG, Inc. Linux adalah merek dagang terdaftar milik Linus Torvalds. Ubuntu adalah merek dagang terdaftar milik Canonical Ltd. Nama produk dan perusahaan lain adalah merek dagang milik pemiliknya masing-masing dan disebut di sini hanya untuk menjelaskan kompatibilitas. Proyek ini tidak berafiliasi dengan maupun didukung oleh pihak-pihak tersebut.
