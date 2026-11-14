# PRN Melaka 2026 — Dashboard Auto-Sync MySPR Semak (v2.0)

Dashboard bebas (bukan laman rasmi SPR) untuk **28 DUN / 79 calon**. Fail asas berdasarkan prototaip v1.0. Versi ini menambah kutipan automatik keputusan daripada panggilan JSON yang digunakan oleh laman **MySPR Semak**, cache sahih dan paparan kemas kini berkala.

> **Penting:** Ini **bukan API terbuka rasmi yang didokumenkan/disokong oleh SPR**. Ia menggunakan endpoint dalaman laman rasmi SPR yang boleh berubah atau tidak tersedia. Kod dibekalkan dan diuji secara lokal, tetapi capaian sebenar ke pelayan SPR **belum dapat diuji** dalam persekitaran pembinaan ini. Jangan umumkan ia sebagai LIVE sehinggalah GitHub Actions berjaya dijalankan dan `data/results.json` mempunyai `syncedAt` serta rekod `official` yang benar.

## Senibina

`MySPR Semak (SPR) -> scripts/sync_spr.py (GitHub Actions) -> data/results.json (GitHub Pages) -> index.html (browser)`

- Python mengekstrak token CSRF sesi daripada laman awam, mengenal pasti pilihan raya **Melaka ke-16** (tidak mengambil 2021), mendapatkan senarai 28 DUN, dan membaca keputusan calon satu DUN pada satu masa.
- Keputusan hanya diterbitkan jika **semua undi calon dapat dipadankan** dan calon pemenang ditanda oleh SPR (`MNG`) dengan undi paling tinggi. Rekod yang belum lengkap tidak diterbitkan. Keputusan lama yang sah dikekalkan jika servis sementara gagal.
- Cache GitHub diperiksa oleh browser setiap **60 saat**. Pengumpulan ke SPR dijadual setiap **5 minit ketika waktu pengiraan undi**. GitHub Actions bukan servis masa nyata: job boleh tertunda. Jangan samakan kekerapan refresh browser dengan kekerapan data SPR.
- Terdapat mod operator asal sebagai sandaran; rekod automatik rasmi mengatasi rekod operator dan terkunci daripada disunting. Setiap rekod rasmi auto mempunyai `sourceType: spr_auto`.
- Untuk **peratus keluar mengundi (VTO)**, dashboard menyediakan pautan ke [dashboard rasmi SPR](https://dashboard.spr.gov.my/). Integrasi API VTO automatik tidak disertakan kerana endpoint yang selamat/stabil belum disahkan.

## Pasang ke GitHub Pages (paling ringkas)

1. Repository sedia ada: **matjeri99/PRNMelaka2026** (branch `main`).
2. Fail aplikasi, pengumpul SPR dan workflow telah dikemas kini ke repository ini melalui sambungan GitHub.
3. Di `Settings -> Pages -> Build and deployment`, pilih **Source: GitHub Actions** (BUKAN `Deploy from a branch`). Workflow akan membina dan menerbitkan laman setiap kali ia dijalankan.
4. Di tab `Actions`, pilih **PRN Melaka - semak SPR dan terbitkan dashboard**, tekan `Run workflow`. Ini menjalankan semakan sekali sekarang walaupun belum waktu pengiraan undi.
5. Pastikan di `Settings -> Actions -> General -> Workflow permissions` hak `Read and write permissions` dibenarkan, atau beri kebenaran untuk tindakan bot commit.
6. Semak `data/results.json`: jika `syncedAt` ada dan `officialCount` meningkat, sambungan telah berjaya. Jika belum ada keputusan, semak log Actions (mungkin SPR belum memaparkan Melaka ke-16 atau endpoint berubah). Jika collector gagal, deployment masih menerbitkan cache baik terakhir dan memberi amaran dalam log.
7. Buka URL GitHub Pages. Header akan menunjukkan status dan masa terakhir cache diselaraskan. Butang `Semak Data` hanya memuat semula cache dari GitHub Pages, **bukan** membuat panggilan baru ke SPR.

## Jadual automatik

Workflow `*/5 12-17 14 11 *` menggunakan UTC GitHub Actions (14 November setiap tahun; guard Python menghadkan kepada 2026 sahaja), tetapi skrip menyemak waktu Malaysia:
- 14 Nov 2026, jam **20:00–23:59 MYT**
- 15 Nov 2026, jam **00:00–01:59 MYT**

Di luar jendela ini, semakan berjadual tidak membuat permintaan SPR (untuk mengehadkan beban terhadap laman kerajaan). `Run workflow` (manual) boleh digunakan pada bila-bila masa. Setiap run juga menerbitkan semula GitHub Pages supaya pelawat melihat cache terkini. Apabila 28/28 keputusan telah disimpan, pengumpulan berhenti sendiri.

**Jika SPR mengumumkan keputusan lewat atau perlu memantau pada hari berikutnya:** gunakan `Run workflow` secara manual, atau panjangkan julat masa dalam `need_refresh_now()` dalam `scripts/sync_spr.py`.

## Status data & sempadan ketepatan

- `MENUNGGU`: cache belum dikemas kini; **bukan** bermaksud tiada pengundi / tiada keputusan SPR.
- `SPR AUTO`: keputusan berstruktur telah dipadankan dengan senarai pencalonan dan dikutip daripada laman keputusan SPR, kemudian disimpan di GitHub.
- `CACHE LAMA`: salinan yang berjaya lebih 30 minit lalu; semak log Actions dan portal SPR.
- `CACHE TERGANGGU`: browser tidak dapat mengakses fail JSON; jangan anggap keputusan yang dipaparkan adalah yang paling baru.
- `RASMI · OPERATOR`: keputusan dimasukkan manual dan perlu dipastikan terhadap dokumen rasmi, **tidak** diperoleh melalui kolektor automatik.

**Nota:** Tiada data kemenangan, bilangan undi, atau peratus VTO semasa direka untuk pratonton. `data/results.json` awal sengaja mengandungi kosong. Keputusan sebenar hanya muncul selepas pengumpulan berjaya.

## Struktur

- `index.html`: paparan responsif dan pemuatan cache automatik.
- `data/results.json`: cache keputusan; dikemas kini oleh GitHub Actions.
- `data/calon_2026.json`: penamaan calon (rujukan padanan).
- `scripts/sync_spr.py`: pengumpul dan penapis kesahihan.
- `.github/workflows/spr_sync.yml`: jadual dan commit automatik.
- `tests/test_sync.py`: ujian padanan nama, CSRF, kod DUN dan status pemenang.

## Uji lokal

```
python -m unittest discover -s tests -v
python -m http.server 8000
```

Kemudian lawati `http://localhost:8000`. Jangan buka `index.html` sebagai `file://` kerana `fetch('./data/results.json')` mungkin dihalang dasar keselamatan browser. Untuk menjalankan pengumpul sebenar secara manual, jalankan `FORCE_SPR_SYNC=1 python scripts/sync_spr.py` (macOS/Linux) atau set environment variable pada Windows.

Rujukan rasmi: [MySPR Semak](https://mysprsemak.spr.gov.my/semakan/keputusan/pru-dun), [Dashboard SPR / VTO](https://dashboard.spr.gov.my/). Corak endpoint diterangkan secara terbuka oleh [mfaizalzain/mygov — collect_election.py](https://github.com/mfaizalzain/mygov/blob/main/tools/collect_election.py); pengumpul ini ditulis khusus bagi Melaka ke-16.