# PRN MELAKA 2026 — Election Intelligence Dashboard v1.0

**Versi prototaip statik**, dibangunkan pada 14 November 2026 untuk 28 DUN dan 79 calon. Tiada keputusan PRN 2026 dipraisi.

## Kandungan
- `index.html` — dashboard interaktif responsif, boleh dibuka terus dalam pelayar dan sesuai GitHub Pages.
- `calon_2026.csv` — dataset senarai 79 calon / 28 DUN untuk audit.
- `calon_2026.json` — dataset 79 calon berstruktur.

## Penggunaan
1. Buka `index.html` dalam Chrome, Edge atau Firefox. Untuk terbitkan, muat naik `index.html` ke root repo GitHub Pages dan aktifkan Pages pada Settings > Pages.
2. Gunakan carian dan penapis untuk melihat 28 kawasan dan 79 calon.
3. Pilih **Mod Operator**; tekan **Kemas Kini** pada kerusi DUN; masukkan undi SEMUA calon, status, sumber, dan nota. Klik Simpan.
4. Status `RASMI SPR` memerlukan tandakan perakuan semakan rasmi dan nyatakan sumber. `TIDAK RASMI` ialah input operator, **bukan pengumuman SPR**.
5. **Eksport JSON** untuk salinan data penuh dan import pada browser lain; **CSV** untuk analisis.

## Perhatian penting
- Semua rekod keputusan disimpan dalam `localStorage` peranti/pelayar masing-masing. **Ia tidak diselaraskan automatik antara pengguna.** Untuk siaran keputusan benar-benar live kepada semua orang, perlukan backend berpusat (contoh Worker + Sheets/Supabase) dan proses kelulusan sebelum diterbitkan.
- Sumber calon / data pemilih: https://election.bernama.com/prn/melaka/2026/penamaan/?detail=seats, https://election.bernama.com/prn/melaka/2026/, https://pilihanraya.my/melaka/prn16-2026/calon, https://spr.gov.my/prudunmelaka16/
- Pilihan raya 2021: BN 21 kerusi, PH 5, PN 2. 2026 bermula 0 keputusan secara sengaja.
- Tidak ada `apiKey`, token, maklumat peribadi atau credential di dalam frontend.
- Semakan silang nama penuh calon disarankan sebelum penggunaan rasmi bagi variasi gelaran/ejaan sumber media.

## UAT dicadangkan
- Semak jumlah 28 DUN / 79 calon dan pecahan BN23, PH24, Bersama16, Bersatu7, PN5, Bebas3, Putra1.
- Cari kawasan / nama / parti, uji filter status dan 2/3/4 penjuru.
- Masukkan undi satu DUN sebagai TIDAK RASMI dan pastikan statistik berubah.
- Tukar ke RASMI SPR hanya apabila sumber rasmi disahkan.
- Tutup/buka pelayar, semak localStorage, eksport/import JSON, CSV, kemudian reset.
