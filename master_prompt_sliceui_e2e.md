# Master Prompt: Membangun Paket NPM & Claude Code Skill `sliceui` (End-to-End)

Bangun repository paket NPM production-grade bernama `sliceui` dari nol sebagai Claude Code Agent Skill untuk mengeksekusi slicing desain `.figml` (Figma XML) menjadi kode UI secara end-to-end, presisi tinggi, hemat token/konteks, dan tervalidasi otomatis.

Jangan membuat versi MVP atau placeholder setengah jadi. Implementasikan seluruh file, logika CLI, parser `lxml`, kalkulator geometri, serta aturan referensi secara lengkap dan siap pakai sesuai spesifikasi teknis di bawah ini.

---

## 1. Arsitektur Direktori Paket NPM

Bangun struktur direktori berikut secara utuh:

    sliceui/
    ├── package.json
    ├── README.md
    ├── bin/
    │   └── cli.js
    └── skills/
        └── sliceui/
            ├── SKILL.md
            ├── scripts/
            │   └── sliceui.py
            └── references/
                ├── figml-schema-rules.md
                ├── charts-and-assets.md
                ├── mode-standalone.md
                ├── mode-codebase.md
                └── frameworks/
                    ├── README.md
                    ├── react-tailwind.md
                    └── laravel-blade.md

---

## 2. Spesifikasi `package.json` & `bin/cli.js` (Zero-Dependency Installer & Environment Manager)

### A. `package.json`
- `name`: `"sliceui"`
- `version`: `"1.0.0"`
- `description`: `"High-precision, context-efficient Figma XML (.figml) UI slicing skill and CLI engine for Claude Code"`
- `bin`: `{ "sliceui": "./bin/cli.js" }`
- `files`: `["bin/", "skills/", "README.md"]`
- `engines`: `{ "node": ">=18.0.0" }`
- Jangan gunakan dependency eksternal Node.js (`dependencies: {}`) agar instalasi via `npx` atau `npm i -g` berjalan instan.

### B. `bin/cli.js` (`#!/usr/bin/env node`)
Implementasikan CLI Node.js lintas platform (Linux, macOS, Windows) menggunakan modul bawaan (`fs`, `path`, `os`, `child_process`) dengan perintah berikut:

1. `sliceui init --global`
   - Menyalin folder `skills/sliceui/` secara rekursif ke `~/.claude/skills/sliceui/`.
   - Jika sudah ada instalasi sebelumnya, timpa file skill inti (`SKILL.md`, `scripts/`, `references/`) namun **pertahankan** `project-context.md` jika ada.
   - Otomatis menjalankan `doctor` untuk target direktori tersebut.
2. `sliceui init --project`
   - Menyalin folder `skills/sliceui/` secara rekursif ke `./.claude/skills/sliceui/` di direktori kerja saat ini (`process.cwd()`).
   - Otomatis menjalankan `doctor` untuk target direktori tersebut.
3. `sliceui init --context`
   - Membuat file `./.claude/skills/sliceui/project-context.md` di level proyek (jika belum ada; jika sudah ada, jangan ditimpa kecuali diberi flag `--force`).
   - Isi template terstruktur yang siap diisi developer: Tech Stack, Styling System, Design Tokens (Colors, Typography, Spacing), Reusable Components Mapping (`Button`, `Input`, `Select`, `Tabs`, `Card`, `Chart`), dan Folder Output konvensi proyek.
4. `sliceui doctor [--target <skill_dir>]`
   - Mengecek ketersediaan `python3` (atau `python` di Windows). Jika tidak ditemukan, tampilkan pesan error yang jelas dan exit code `1`.
   - Mengecek apakah `lxml` bisa di-import oleh Python global (`python3 -c "import lxml"`).
   - Jika `lxml` belum tersedia secara global, **buat virtual environment terisolasi** di `<skill_dir>/.venv` (`python3 -m venv <skill_dir>/.venv`) lalu install `lxml` ke dalamnya (`<venv_pip> install --quiet lxml`). Pendekatan ini wajib agar tidak gagal oleh aturan PEP 668 (`externally-managed-environment`) pada Ubuntu/macOS modern.
   - Pastikan `sliceui.py` otomatis mendeteksi dan me-reexec dirinya menggunakan `<skill_dir>/.venv/bin/python3` (atau `.venv\Scripts\python.exe`) jika `.venv` ada.
   - Jalankan smoke test `sliceui.py --help` untuk memastikan seluruh environment siap 100%.
5. `sliceui --help` / `-h`
   - Menampilkan dokumentasi seluruh perintah di atas dengan rapi.

---

## 3. Spesifikasi `skills/sliceui/scripts/sliceui.py` (Deterministic `lxml` Engine)

Buat skrip Python CLI berbasis `lxml.etree` dan `math` dengan **auto-venv bootstrap** di bagian paling atas file (jika `import lxml` gagal di interpreter saat ini, otomatis cari `../.venv/bin/python3` atau `..\.venv\Scripts\python.exe` relatif terhadap lokasi `sliceui.py` dan `os.execv` ke interpreter `.venv` tersebut).

Implementasikan 5 sub-perintah CLI:

### 1. `compact <input.figml> [--out <output.xml>]`
Melakukan kompresi XML secara **lossless terhadap seluruh data visual & layout**, sambil membuang metadata internal Figma:
- **Hapus tag metadata non-visual:** `constraints`, `overrides`, `override`, `overriddenFields`, `overriddenField`, `mainComponent`, `componentProperties`, `variantProperties`, `layoutGrids`, `layoutGrid`, `exportSettings`, `filters`, `imageTransform`.
- **Hapus atribut noise:** `maskType`, `scaleFactor`, serta `blendMode` jika bernilai `"NORMAL"`.
- **Normalisasi angka floating-point:** Untuk atribut numerik (`x`, `y`, `width`, `height`, `strokeWeight`, `cornerRadius`, `opacity`, `startingAngle`, `endingAngle`, `innerRadius`, `rotation`, `itemSpacing`, `paddingLeft`, `paddingRight`, `paddingTop`, `paddingBottom`), ubah nilai dengan `abs(val) < 1e-6` menjadi `"0"`, bilangan bulat menjadi integer string (`"25"` bukan `"25.0"`), dan desimal menjadi maksimal 2 angka di belakang koma tanpa nol di belakang (`"93.09"`, `"0.5"`).
- **Lipat node tersembunyi (`visible="false"`):** Ganti seluruh subtree node yang memiliki `visible="false"` menjadi satu elemen ringkas `<HiddenNode id="..." name="..."/>` agar agent tahu elemen itu disembunyikan tanpa membuang token membaca anak-anaknya.
- **Deduplikasi pola dekoratif berulang:** Pada setiap tag `<children>` yang memiliki `>= 4` elemen anak dan **tidak mengandung** `<Text>` di dalamnya, cek apakah seluruh anak memiliki signature identik `(tag, name, width, height, jumlah_descendant)`. Jika identik, simpan hanya elemen anak pertama dengan tambahan atribut `repeatedCount="<jumlah>"` dan hapus duplikatnya.
- **Output:** Jika `--out` tidak diisi, simpan ke `<tempdir>/sliceui_<sha1_8char>_compact.xml` (gunakan `tempfile.gettempdir()` agar lintas OS). Cetak ke stdout path file hasil, perbandingan jumlah baris, jumlah karakter, estimasi token (`chars // 4`), dan persentase penghematan.

### 2. `outline <xml_file>`
Mencetak peta struktur hierarki yang cerdas agar LLM dapat merencanakan slicing per section tanpa melewatkan satu bagian pun:
- Tampilkan tiap node kontainer/komponen utama (lewati tag pembungkus teknis seperti `children`, `fills`, `strokes`, `effects`, `fontName`, `letterSpacing`, `lineHeight` dari tampilan tree agar ringkas).
- Format per baris:
  `[id] <Tag name="..."> WxH | layout=HORIZONTAL/VERTICAL/NONE | lines=N | flags=[...] | text="preview..."`
- **Flags otomatis yang wajib dideteksi dan ditampilkan pada outline:**
  - `IMAGE` jika subtree mengandung `<fill type="IMAGE">`
  - `ARC_CHART` jika subtree mengandung `<arcData>`
  - `VECTOR_CURVE` jika subtree mengandung `<Vector>` dengan `width > 20` dan `height > 20` (indikasi kurva line chart / ilustrasi non-garis lurus)
  - `REPEATED(xN)` jika ada atribut `repeatedCount`
  - `HIDDEN` untuk `<HiddenNode>`

### 3. `cut <xml_file> --id <node_id> [--id <node_id_2> ...]`
- Mendukung ekstraksi **satu atau beberapa ID sekaligus** dalam satu pemanggilan perintah untuk meminimalkan round-trip tool call.
- Untuk setiap ID, cetak header komentar konteks induknya:
  `<!-- SECTION_START id="..." parent_id="..." parent_name="..." parent_size="WxH" parent_layout="..." parent_itemSpacing="..." -->`
  diikuti XML subtree verbatim, lalu `<!-- SECTION_END id="..." -->`.
- Jika ukuran subtree satu ID melebihi `900` baris, cetak peringatan di header beserta daftar `id` dan `name` dari child langsungnya agar agent tahu cara memecahnya lebih lanjut bila perlu.

### 4. `arc --width <W> --height <H> --start <rad> --end <rad> [--inner <ratio>]`
- Kalkulator geometri deterministik untuk mengubah atribut `<arcData startingAngle="..." endingAngle="..." innerRadius="..."/>` milik Figma menjadi atribut SVG `<path d="..."/>` yang 100% presisi.
- Perhatikan sistem koordinat sudut Figma: `0` radian berada di arah jam 3 (sumbu +X) dan bertambah searah jarum jam (*clockwise*) dalam koordinat layar SVG (`x = cx + r * cos(theta)`, `y = cy + r * sin(theta)`).
- Jika `inner > 0` (Donut), hasilkan path cincin tertutup (busur luar searah jarum jam + garis ke radius dalam + busur dalam berlawanan jarum jam + `Z`). Jika `inner == 0` (Pie), hasilkan path juring tertutup (`M cx cy L x1 y1 A ... Z`). Tangani juga kasus busur penuh (`abs(end - start) >= 2 * pi - 1e-4`).

### 5. `verify <xml_file> <output_file_1> [output_file_2 ...]`
Audit kelengkapan konten dan warna lintas banyak file output (misalnya `dashboard.html` + `dashboard.css`):
- Ekstrak semua atribut `characters` dari tag `<Text>` yang berada di luar `<HiddenNode>`. Normalisasi karakter pemisah baris Unicode Figma (`\u2028`, `\u2029`, `\r\n`, `\n`) menjadi spasi tunggal saat membandingkan agar teks multi-baris di HTML tidak menghasilkan *false negative*.
- Ekstrak semua nilai kode warna hex (`#rrggbb`) dari tag `<fill>` dan `<stroke>` yang visible (normalisasi ke lowercase).
- Gabungkan teks dari seluruh file output yang diberikan, lakukan pengecekan keberadaan setiap string teks dan kode warna hex.
- Cetak laporan terstruktur:
  - `TEXT COVERAGE: matched/total (XX.X%)` + daftar eksplisit teks yang `MISSING` (jika ada).
  - `COLOR COVERAGE: matched/total (XX.X%)` + daftar eksplisit hex yang `MISSING` (jika ada).
  - Exit code `0` jika `TEXT COVERAGE == 100%`, atau exit code `2` jika masih ada teks visible yang hilang agar agent wajib memperbaikinya sebelum selesai.

---

## 4. Spesifikasi `skills/sliceui/SKILL.md` (Orkestrator E2E)

Jaga agar `SKILL.md` tetap padat, tegas, dan **di bawah 180 baris** dengan YAML frontmatter valid (`name: sliceui`, `description: ...`):

1. **Resolution & Context Priority:**
   - Cek apakah terdapat `./.claude/skills/sliceui/project-context.md` di workspace proyek saat ini. Jika ada, prioritaskan konvensi di dalamnya (meskipun skill berjalan dari `~/.claude/skills/sliceui/`).
2. **Mode Routing:**
   - **Mode Standalone (Default / Fase 1):** Jika user meminta slicing `.figml` menjadi HTML/CSS/Bootstrap standalone atau tidak menyebut integrasi codebase proyek -> baca `references/mode-standalone.md`.
   - **Mode Codebase (Fase 2):** Jika user meminta integrasi ke proyek/framework yang ada -> baca `references/mode-codebase.md` serta file framework yang relevan di `references/frameworks/`.
3. **Mandatory Reference Loading:**
   - Sebelum menulis satu baris kode pun, wajib baca `references/figml-schema-rules.md` dan `references/charts-and-assets.md`.
4. **Protokol Eksekusi `.figml` (Anti-Hallucination & Context-Safe):**
   - **Langkah 1 — Kompresi & Pemetaan:** Jalankan `python3 <skill_dir>/scripts/sliceui.py compact <file.figml>` lalu `outline <compact.xml>` (untuk file `< 500` baris tetap boleh menjalankan `outline` agar flag `IMAGE`/`ARC_CHART`/`VECTOR_CURVE` terlihat jelas).
   - **Langkah 2 — Slicing Bertahap Per Section:** Kelompokkan ID section utama dari hasil `outline` dari atas ke bawah. Panggil `cut` secara bertahap (1–3 section per batch agar tetap hemat konteks) untuk **SELURUH section yang visible**. **LARANGAN KERAS:** Dilarang melewati section bagian bawah halaman, dilarang menyalin struktur satu grafik ke grafik lain tanpa memotong XML-nya, dan dilarang mengarang judul, label, angka, atau warna.
   - **Langkah 3 — Tulis File Output Secara Terpisah:** Ikuti urutan penulisan file sesuai mode aktif (misalnya tulis `.css` lebih dulu baru `.html` pada Mode Standalone).
   - **Langkah 4 — Audit & Perbaikan Mandiri:** Jalankan `python3 <skill_dir>/scripts/sliceui.py verify <compact.xml> <output_files...>`. Jika ada teks atau warna hex penting yang terlewat, lakukan perbaikan terarah sampai `verify` lulus 100%.

---

## 5. Spesifikasi Lengkap File Referensi (`skills/sliceui/references/*.md`)

### A. `references/figml-schema-rules.md`
Dokumentasikan pemetaan deterministik seluruh tag dan atribut FigML ke CSS/HTML:
- **Layout & Flexbox:**
  - `layoutMode="HORIZONTAL"` -> `display: flex; flex-direction: row;`
  - `layoutMode="VERTICAL"` -> `display: flex; flex-direction: column;`
  - `layoutWrap="WRAP"` -> `flex-wrap: wrap;`
  - `primaryAxisAlignItems`: `MIN` -> `flex-start`, `CENTER` -> `center`, `MAX` -> `flex-end`, `SPACE_BETWEEN` -> `space-between`.
  - `counterAxisAlignItems`: `MIN` -> `flex-start`, `CENTER` -> `center`, `MAX` -> `flex-end`, `BASELINE` -> `baseline`.
  - `itemSpacing` -> `gap: <N>px;`
  - `paddingLeft`, `paddingRight`, `paddingTop`, `paddingBottom` -> `padding: <T>px <R>px <B>px <L>px;`
  - `layoutSizingHorizontal="FILL"` / `layoutGrow="1"` -> `flex: 1 1 0%; width: 100%;` (sesuaikan dengan arah parent).
  - `layoutPositioning="ABSOLUTE"` -> `position: absolute; left: <x>px; top: <y>px;` (pastikan parent terdekat memiliki `position: relative`).
  - `clipsContent="true"` -> `overflow: hidden;`
- **Visual Styles:**
  - `<fill type="SOLID" color="#hex" opacity="0.1"/>` -> gunakan `rgba(r, g, b, opacity)` jika `opacity < 1`, atau `#hex` jika opacity tidak ada / `1`.
  - `<fill type="GRADIENT_LINEAR">` + `<gradientStops>` -> konversi ke `linear-gradient(...)` sesuai urutan `position` dan `color`/`opacity` pada `<gradientStop>`.
  - `<stroke color="#hex" opacity="..."/>` + `strokeWeight` + `<dashPattern>` -> `border: <strokeWeight>px <solid|dashed> <color>;` (untuk `<Line>` horizontal/vertical `height="0"` atau `width="0"`, gunakan `border-top` / `border-left` atau SVG `<line stroke-dasharray="...">`).
  - `<effect type="DROP_SHADOW">` (`<offset x y>`, `radius`, `color`, `opacity`) -> `box-shadow: <x>px <y>px <radius>px rgba(...);`.
  - `cornerRadius` -> `border-radius: <N>px;`.
- **Typography (`<Text>`):**
  - Petakan `fontName` (`family`, `style`), `fontSize`, `fontWeight`, `<lineHeight value unit>`, `<letterSpacing value unit>`, `textAlignHorizontal` (`LEFT`/`CENTER`/`RIGHT`/`JUSTIFIED`), dan karakter `\u2028` (ubah menjadi `<br>`).
- **Pemetaan Custom Tag Komponen Figma:**
  - Tag seperti `<Icon_Font_Awesome_I_info-circle>`, `<Icon_Font_Awesome_Free_Solid_C_caret-down>` -> ekstrak nama ikon setelah prefix (`info-circle` -> `<i class="fa-solid fa-circle-info"></i>`, `caret-down` -> `<i class="fa-solid fa-caret-down"></i>`).
  - Tag seperti `<Tab_basic>`, `<Field_FNC>`, `<Button_FNC>` -> render sebagai elemen HTML semantik (`<button role="tab">`, `<select class="form-select">`, `<button class="btn">`) dengan styling persis dari child node di dalamnya.

### B. `references/charts-and-assets.md`
Aturan ketat untuk menutup celah visual pada grafik, gambar, dan dekorasi:
1. **Node `<fill type="IMAGE">` (Flag `IMAGE`):**
   - **Dilarang keras** membiarkan area gambar kosong atau putih polos.
   - Render kontainer berdimensi persis (`width` x `height`, `border-radius` dari `cornerRadius`).
   - Buat ilustrasi placeholder SVG inline yang bersih, proporsional, dan kontekstual dengan label teks di sebelahnya (misalnya jika berada di kartu identitas/profil mahasiswa atau karyawan, render siluet/avatar portrait modern dalam frame berwarna lembut; jika thumbnail produk/berita, render placeholder kartu media).
2. **Donut & Pie Chart (`<Ellipse>` + `<arcData>`, Flag `ARC_CHART`):**
   - Wajib memanggil `python3 <skill_dir>/scripts/sliceui.py arc --width <W> --height <H> --start <startingAngle> --end <endingAngle> --inner <innerRadius>` untuk setiap slice `<Ellipse>` yang memiliki `<arcData>`.
   - Susun seluruh `<path>` hasil kalkulasi di dalam satu `<svg viewBox="0 0 W H">` dengan `fill` (`color` + `opacity`), `stroke`, dan `stroke-width` sesuai XML.
   - Pastikan label tengah donat (seperti angka total di tengah lingkaran) diposisikan tepat di pusat lingkaran (`position: absolute; inset: 0; display: flex; align-items: center; justify-content: center`).
3. **Bar Chart (`<Rectangle>` series):**
   - Periksa **setiap** frame kolom/grup kategori satu per satu. Jangan pernah mengasumsikan semua bulan/kategori memiliki jumlah batang yang sama (jika kategori A punya 3 `<Rectangle>`, kategori B punya 2 `<Rectangle>`, dan kategori C punya 1 `<Rectangle>`, render persis sejumlah itu).
   - Hitung tinggi tiap batang secara proporsional terhadap tinggi area plot sumbu Y (`height_px / plot_height_px * 100%`), pertahankan `width`, `cornerRadius` (misal rounded top `border-radius: 8px 8px 0 0` atau penuh sesuai desain), dan warna `color` dari XML.
   - Jika terdapat kartu tooltip mengambang di dalam chart (seperti kotak detail angka & panah kecil), posisikan dengan `position: absolute` mengikuti koordinat `(x, y)` dari XML.
4. **Line Chart / Kurva Vektor Bebas (`<Vector>` besar tanpa `<arcData>`, Flag `VECTOR_CURVE`):**
   - FigML tidak mengekspor koordinat titik kurva pada `<Vector>` bebas, hanya bounding box `(x, y, width, height)` dan `stroke`.
   - Render seluruh elemen terukur secara 100% akurat: header kartu, legenda, label sumbu Y, label sumbu X, garis grid horizontal, dan garis batas putus-putus (`dashPattern`).
   - Pada area bounding box kurva, render kurva `<svg>` placeholder yang halus menggunakan warna `stroke` dan `strokeWeight` asli dari XML, serta wajib sertakan komentar eksplisit: `<!-- TODO: bind dynamic line series data (XML Vector lacks path vertices) -->`.
5. **Pola Dekoratif Berulang (`repeatedCount`, Flag `REPEATED`):**
   - Konversi geometri 1 tile contoh menjadi `<svg><defs><pattern id="..." width="..." height="..." patternUnits="userSpaceOnUse">...</pattern></defs><rect width="100%" height="100%" fill="url(#...)"/></svg>` dengan `opacity` asli dari XML.

### C. `references/mode-standalone.md` (Aktif Fase 1 — Separated Output)
- **Aturan Pemisahan File (Wajib):** Selalu hasilkan minimal **2 file terpisah** di direktori output yang diminta user (atau direktori kerja saat ini):
  1. `<nama-halaman>.css` — ditulis **pertama kali**.
  2. `<nama-halaman>.html` — ditulis **kedua**, memuat `<nama-halaman>.css` via `<link rel="stylesheet" href="./<nama-halaman>.css">`.
- **Stack Standalone:**
  - Bootstrap 5.3 CSS & JS Bundle via CDN.
  - Font Awesome 6 Free CSS via CDN (jika ditemukan ikon Font Awesome di XML).
  - Google Fonts sesuai seluruh `fontName` yang terdeteksi di XML.
- **Standar Kualitas CSS & HTML:**
  - Definisikan CSS Custom Properties (`:root`) untuk seluruh palet warna utama, warna netral, border, dan font family dari XML.
  - Gunakan Bootstrap grid (`container-fluid` / `container`, `row`, `col-lg-*`) untuk struktur makro halaman, dan CSS Flexbox/Grid presisi untuk komponen internal kartu dan grafik agar tidak pecah di layar desktop maupun tablet/mobile.
  - Pastikan halaman dapat langsung dibuka di browser (`file://` maupun local server) tanpa build step tambahan.

### D. `references/mode-codebase.md` & `references/frameworks/*.md` (Siap Fase 2)
- **`mode-codebase.md`:** Jelaskan alur kerja saat skill dijalankan di dalam proyek nyata:
  1. Baca `.claude/skills/sliceui/project-context.md` (jika ada).
  2. Inspeksi `package.json` / `composer.json` dan 2–3 komponen UI contoh di repo untuk mencocokkan konvensi penamaan, styling, dan komponen reusable (`Button`, `Input`, `Tabs`, `Card`, library chart jika terpasang).
  3. Muat panduan framework yang sesuai dari `references/frameworks/<framework>.md`.
  4. Petakan elemen `.figml` ke komponen proyek yang sudah ada sebelum membuat komponen baru, lalu jalankan `sliceui.py verify` terhadap seluruh file komponen yang dihasilkan.
- **`references/frameworks/README.md`:** Panduan cara menambahkan file knowledge framework baru (misal `vue-tailwind.md`, `nextjs-shadcn.md`) ke folder ini.
- **`references/frameworks/react-tailwind.md` & `laravel-blade.md`:** Buat template pengetahuan framework yang rapi dan terstruktur (konvensi komponen, mapping props/slots, styling tokens, dan integrasi chart) agar siap diperkaya pada Fase 2.

### E. `README.md`
- Dokumentasi lengkap cara instalasi (`npx sliceui init --global`, `npx sliceui init --project`, `npx sliceui init --context`), arsitektur 2-space, contoh prompt penggunaan di Claude Code untuk Mode Standalone maupun Mode Codebase, serta penjelasan perintah CLI `sliceui.py`.

---

## 6. Verifikasi Teknis Wajib Setelah Semua File Dibuat

Setelah selesai menulis seluruh file, jalankan rangkaian verifikasi berikut secara berurutan dan pastikan semuanya lulus tanpa error:
1. `chmod +x bin/cli.js skills/sliceui/scripts/sliceui.py`
2. `node --check bin/cli.js`
3. `python3 -m py_compile skills/sliceui/scripts/sliceui.py`
4. Uji `node ./bin/cli.js --help` dan `python3 skills/sliceui/scripts/sliceui.py --help`
5. Uji kalkulasi geometri `python3 skills/sliceui/scripts/sliceui.py arc --width 191 --height 191 --start 4.7124 --end 9.5497 --inner 0.5265` untuk memverifikasi output `<path d="..."/>` valid.