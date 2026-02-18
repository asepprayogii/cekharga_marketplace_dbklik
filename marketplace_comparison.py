import streamlit as st
import pandas as pd
import numpy as np
from difflib import SequenceMatcher
import io

st.set_page_config(page_title="Price Comparator", page_icon="💹", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
    background: #0a0a0f; color: #e8e8f0; font-family: 'DM Mono', monospace;
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 10%, #1a0a2e 0%, #0a0a0f 50%, #0d1a0a 100%);
    min-height: 100vh;
}
[data-testid="stSidebar"] { display: none; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
.hero { text-align: center; padding: 3rem 1rem 2rem; border-bottom: 1px solid #ffffff10; margin-bottom: 2.5rem; }
.hero h1 {
    font-family: 'Syne', sans-serif; font-size: clamp(2.2rem, 5vw, 4rem); font-weight: 800;
    background: linear-gradient(135deg, #a8ff78, #78ffd6, #a8c0ff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin: 0 0 0.5rem; letter-spacing: -1px;
}
.hero p { color: #888; font-size: 0.9rem; letter-spacing: 0.05em; margin: 0; }
.label-tag {
    display: inline-block; background: linear-gradient(135deg, #a8ff7820, #78ffd620);
    border: 1px solid #a8ff7840; color: #a8ff78; font-family: 'Syne', sans-serif;
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.15em;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 0.75rem; text-transform: uppercase;
}
.stat-card {
    background: #ffffff06; border: 1px solid #ffffff10; border-radius: 12px;
    padding: 1.25rem 1.5rem; text-align: center;
}
.stat-card .val { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 0.25rem; }
.stat-card .lbl { font-size: 0.72rem; color: #888; letter-spacing: 0.1em; text-transform: uppercase; }
.green { color: #a8ff78; } .red { color: #ff7878; } .blue { color: #78c8ff; }
.section-title {
    font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #e8e8f0;
    letter-spacing: 0.05em; margin: 0 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #ffffff10;
}
.info-box {
    background: #78ffd608; border: 1px solid #78ffd620; border-radius: 8px;
    padding: 0.75rem 1rem; font-size: 0.8rem; color: #78ffd6; margin-bottom: 1rem;
}
.warn-box {
    background: #ffd87808; border: 1px solid #ffd87820; border-radius: 8px;
    padding: 0.75rem 1rem; font-size: 0.8rem; color: #ffd878; margin-bottom: 1rem;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #a8ff78, #78ffd6) !important; color: #0a0a0f !important;
    border: none !important; font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Helpers ───────────────────────────────────────────────────────────────────
PRICE_KEYWORDS = ["harga","price","amount","cost","nilai","rate","web","shopee","tokped","tiktok","tokopedia"]
ID_KEYWORDS    = ["id","sku","kode","code","barcode","produk","artikel","no","nomor","number","ref","item"]

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def auto_detect(df, kind="price"):
    keywords = PRICE_KEYWORDS if kind == "price" else ID_KEYWORDS
    scored = sorted(df.columns, key=lambda c: max(similarity(c.lower(), k) for k in keywords), reverse=True)
    return scored[:5]

def load_file(uploaded):
    if uploaded is None:
        return None
    try:
        if uploaded.name.lower().endswith(".csv"):
            return pd.read_csv(uploaded)
        else:
            return pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

def clean_price(series):
    s = series.astype(str).str.replace(r"[Rp\s,]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")

def compute_status(price_a, price_b):
    """Selalu return pandas Series — tidak ada numpy array.
    Data Kosong = salah satu atau keduanya tidak ada harga.
    """
    diff = price_a - price_b
    out = []
    for a, b, d in zip(price_a, price_b, diff):
        if pd.isna(a) and pd.isna(b):
            out.append("Data Kosong (A & B kosong)")
        elif pd.isna(a):
            out.append("Data Kosong (A kosong, B ada)")
        elif pd.isna(b):
            out.append("Data Kosong (B kosong, A ada)")
        elif d == 0:
            out.append("Sama")
        elif d > 0:
            out.append(f"Tidak Sama (A lebih mahal, selisih Rp{abs(d):,.0f})")
        else:
            out.append(f"Tidak Sama (B lebih mahal, selisih Rp{abs(d):,.0f})")
    return pd.Series(out, index=price_a.index)

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>💹 Price Comparator</h1>
  <p>Upload 2 file → pilih kolom → bandingkan harga antar marketplace</p>
</div>
""", unsafe_allow_html=True)

# ─── Upload ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown('<div class="label-tag">File A — Portal / File Pertama</div>', unsafe_allow_html=True)
    file_a = st.file_uploader("Upload File A", type=["xlsx","xls","csv"], key="fa", label_visibility="collapsed")
with c2:
    st.markdown('<div class="label-tag">File B — Omni / File Kedua</div>', unsafe_allow_html=True)
    file_b = st.file_uploader("Upload File B", type=["xlsx","xls","csv"], key="fb", label_visibility="collapsed")

if not file_a or not file_b:
    st.markdown('<div class="warn-box">⬆️ Upload kedua file untuk mulai analisis.</div>', unsafe_allow_html=True)
    st.stop()

df_a = load_file(file_a)
df_b = load_file(file_b)
if df_a is None or df_b is None:
    st.stop()

st.success(f"✅ File A: **{len(df_a):,} baris**, {len(df_a.columns)} kolom  |  File B: **{len(df_b):,} baris**, {len(df_b.columns)} kolom")
st.markdown("---")

# ─── Konfigurasi Kolom ─────────────────────────────────────────────────────────
st.markdown('<p class="section-title">⚙️ Konfigurasi Kolom</p>', unsafe_allow_html=True)

all_cols_a = df_a.columns.tolist()
all_cols_b = df_b.columns.tolist()

ci1, ci2 = st.columns(2, gap="large")
with ci1:
    id_hint_a = auto_detect(df_a, "id")
    id_col_a  = st.selectbox("Kolom ID/SKU — File A", all_cols_a,
                              index=all_cols_a.index(id_hint_a[0]) if id_hint_a else 0)
with ci2:
    id_hint_b = auto_detect(df_b, "id")
    id_col_b  = st.selectbox("Kolom ID/SKU — File B", all_cols_b,
                              index=all_cols_b.index(id_hint_b[0]) if id_hint_b else 0)

hint_a = auto_detect(df_a, "price")
hint_b = auto_detect(df_b, "price")
st.markdown(f'<div class="info-box">💡 <b>Saran kolom harga File A:</b> {", ".join(hint_a)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="info-box">💡 <b>Saran kolom harga File B:</b> {", ".join(hint_b)}</div>', unsafe_allow_html=True)

cp1, cp2 = st.columns(2, gap="large")
with cp1:
    price_cols_a = st.multiselect("Kolom Harga — File A (bisa lebih dari 1)",
                                   all_cols_a, default=[],
                                   help="Semua kolom tersedia")
with cp2:
    price_cols_b = st.multiselect("Kolom Harga — File B (bisa lebih dari 1)",
                                   all_cols_b, default=[],
                                   help="Semua kolom tersedia")

if not price_cols_a or not price_cols_b:
    st.markdown('<div class="warn-box">⚠️ Pilih minimal 1 kolom harga dari masing-masing file.</div>', unsafe_allow_html=True)
    st.stop()

# ─── Pasangkan Kolom ───────────────────────────────────────────────────────────
st.markdown("##### 🔗 Pasangkan Kolom Harga (File A ↔ File B)")
st.markdown('<div class="info-box">💡 Contoh: Shopee Portal (A) ↔ Shopee Omni (B)</div>', unsafe_allow_html=True)

num_pairs = st.number_input("Jumlah pasangan kolom", min_value=1,
                             max_value=max(len(price_cols_a), len(price_cols_b)),
                             value=min(len(price_cols_a), len(price_cols_b)))
pairs = []
for i in range(int(num_pairs)):
    pc1, pc2, pc3 = st.columns([2, 2, 1])
    with pc1:
        col_a = st.selectbox(f"Kolom File A #{i+1}", price_cols_a,
                              index=min(i, len(price_cols_a)-1), key=f"pa_{i}")
    with pc2:
        col_b = st.selectbox(f"Kolom File B #{i+1}", price_cols_b,
                              index=min(i, len(price_cols_b)-1), key=f"pb_{i}")
    with pc3:
        label = st.text_input("Label", value=f"Pair {i+1}", key=f"lbl_{i}")
    pairs.append((col_a, col_b, label))

st.markdown("---")
run = st.button("🚀 Jalankan Analisis", type="primary", use_container_width=True)
# Jika belum menekan tombol dan belum ada hasil tersimpan, hentikan.
if not run and 'results' not in st.session_state:
    st.stop()

# ─── Merge ─────────────────────────────────────────────────────────────────────
if run:
    with st.spinner("Memproses data..."):
        try:
            used_a  = list(dict.fromkeys([p[0] for p in pairs]))
            used_b  = list(dict.fromkeys([p[1] for p in pairs]))
            cols_a  = list(dict.fromkeys([id_col_a] + used_a))
            cols_b  = list(dict.fromkeys([id_col_b] + used_b))

            df_a_sel = df_a[cols_a].copy()
            df_b_sel = df_b[cols_b].copy()
            df_a_sel[id_col_a] = df_a_sel[id_col_a].astype(str).str.strip()
            df_b_sel[id_col_b] = df_b_sel[id_col_b].astype(str).str.strip()

            merged = pd.merge(df_a_sel, df_b_sel,
                              left_on=id_col_a, right_on=id_col_b,
                              how="inner", suffixes=("_A", "_B"))

            if merged.empty:
                st.error("❌ Tidak ada baris yang cocok. Cek kolom ID yang dipilih.")
                st.stop()

            # simpan hasil merge untuk interaksi selanjutnya
            st.session_state['merged'] = merged
            st.session_state['df_a_sel'] = df_a_sel
            st.session_state['df_b_sel'] = df_b_sel
        except Exception as e:
            st.error(f"Error saat merge: {e}")
            st.stop()
else:
    # ambil dari session_state jika tersedia
    merged = st.session_state.get('merged')
    df_a_sel = st.session_state.get('df_a_sel')
    df_b_sel = st.session_state.get('df_b_sel')
    if merged is None:
        st.error("Silakan jalankan analisis terlebih dahulu.")
        st.stop()

# ─── Komputasi ─────────────────────────────────────────────────────────────────
# Muat dari cache (session_state) jika tersedia dan pengguna tidak menekan tombol lagi
if not run and 'results' in st.session_state:
    results = st.session_state['results']
    display_cols = st.session_state.get('display_cols')
    merged = st.session_state.get('merged', merged)
else:
    results = {}

    for col_a, col_b, label in pairs:
        col_a_m = col_a + "_A" if (col_a in df_b_sel.columns and col_a != id_col_b) else col_a
        col_b_m = col_b + "_B" if (col_b in df_a_sel.columns and col_b != id_col_a) else col_b
        if col_a_m not in merged.columns: col_a_m = col_a
        if col_b_m not in merged.columns: col_b_m = col_b
        if col_a_m not in merged.columns or col_b_m not in merged.columns:
            st.warning(f"⚠️ Kolom '{label}' tidak ditemukan setelah merge, dilewati.")
            continue

        price_a_s = clean_price(merged[col_a_m])
        price_b_s = clean_price(merged[col_b_m])

        # compute_status SELALU return pandas Series — tidak ada masalah .str
        status_series = compute_status(price_a_s, price_b_s)

        merged[f"[{label}] Harga A"] = price_a_s
        merged[f"[{label}] Harga B"] = price_b_s
        merged[f"[{label}] Status"]  = status_series
        merged[f"[{label}] Selisih"] = (price_a_s - price_b_s).abs()

        total_valid  = status_series.str.startswith("Sama") | status_series.str.startswith("Tidak Sama")
        sama_count   = (status_series == "Sama").sum()
        beda_count   = status_series.str.startswith("Tidak Sama").sum()
        kosong_ab    = (status_series == "Data Kosong (A & B kosong)").sum()
        kosong_a     = (status_series == "Data Kosong (A kosong, B ada)").sum()
        kosong_b     = (status_series == "Data Kosong (B kosong, A ada)").sum()
        total_kosong = int(kosong_ab + kosong_a + kosong_b)
        total_valid_n = int(total_valid.sum())
        pct_sama     = (sama_count / total_valid_n * 100) if total_valid_n > 0 else 0.0

        results[label] = {
            "matched":     total_valid_n,
            "sama":        int(sama_count),
            "tidak_sama":  int(beda_count),
            "kosong":      total_kosong,
            "kosong_a":    int(kosong_a),
            "kosong_b":    int(kosong_b),
            "kosong_ab":   int(kosong_ab),
            "pct_sama":    pct_sama,
            "pct_beda":    100.0 - pct_sama if total_valid_n > 0 else 0.0,
        }

    # jika tidak ada pasangan yang valid setelah komputasi
    if not results:
        st.error("Tidak ada pasangan kolom yang berhasil dibandingkan.")
        st.stop()

    # bangun display_cols dan simpan hasil ke session_state
    display_cols = [id_col_a]
    for label in results:
        display_cols += [f"[{label}] Harga A", f"[{label}] Harga B",
                         f"[{label}] Status",  f"[{label}] Selisih"]
    display_cols = [c for c in display_cols if c in merged.columns]

    st.session_state['results'] = results
    st.session_state['display_cols'] = display_cols

# ─── Hasil ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">📊 Hasil Analisis</p>', unsafe_allow_html=True)
st.markdown(f"""
<div class="stat-card" style="margin-bottom:1.5rem;background:linear-gradient(135deg,#a8ff7808,#78ffd608);border-color:#a8ff7830">
  <div class="val blue">{len(merged):,}</div>
  <div class="lbl">Baris Berhasil Dicocokkan (ID/SKU)</div>
</div>""", unsafe_allow_html=True)

# ─── Loop per-pasangan: stats + tabel detail ────────────────────────────────
for label, r in results.items():
    st.markdown(f"#### 🔍 {label}")

    # Baris 1: Persentase
    s1, s2 = st.columns(2, gap="large")
    with s1:
        st.markdown(f'<div class="stat-card"><div class="val green">{r["pct_sama"]:.2f}%</div><div class="lbl">% Sama</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card"><div class="val red">{r["pct_beda"]:.2f}%</div><div class="lbl">% Tidak Sama</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

    # Baris 2: Jumlah baris
    s3, s4, s5 = st.columns(3, gap="large")
    with s3:
        st.markdown(f'<div class="stat-card"><div class="val green">{r["sama"]:,}</div><div class="lbl">Baris Sama</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div class="stat-card"><div class="val red">{r["tidak_sama"]:,}</div><div class="lbl">Baris Tidak Sama</div></div>', unsafe_allow_html=True)
    with s5:
        st.markdown(f'<div class="stat-card"><div class="val gold">{r["kosong"]:,}</div><div class="lbl">Baris Data Kosong</div></div>', unsafe_allow_html=True)

    # Detail data kosong
    if r["kosong"] > 0:
        st.markdown(f"""
        <div class="warn-box" style="margin-top:0.75rem">
          📭 <b>Detail Data Kosong ({r["kosong"]:,} baris):</b><br>
          &nbsp;&nbsp;• Harga A kosong, B ada &nbsp;→ <b>{r["kosong_a"]:,} baris</b><br>
          &nbsp;&nbsp;• Harga B kosong, A ada &nbsp;→ <b>{r["kosong_b"]:,} baris</b><br>
          &nbsp;&nbsp;• Keduanya kosong &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ <b>{r["kosong_ab"]:,} baris</b>
        </div>
        """, unsafe_allow_html=True)

    # ─── Tabel Detail per-pasangan ─────────────────────────────────────────────
    st.markdown(f'<p style="font-size:0.9rem; color:#888; margin-top:1rem; margin-bottom:0.5rem;">📋 Tabel Detail</p>', unsafe_allow_html=True)

    # Kolom yang ditampilkan untuk pasangan ini
    pair_cols = [id_col_a, f"[{label}] Harga A", f"[{label}] Harga B",
                 f"[{label}] Status", f"[{label}] Selisih"]
    pair_cols = [c for c in pair_cols if c in merged.columns]
    status_col = f"[{label}] Status"

    # Filter untuk tabel ini
    filter_key = f"filter_{label}"
    filter_sel = st.selectbox("Filter baris:", [
        "Semua", "Sama saja", "Ada perbedaan",
        "Data Kosong", "Data Kosong (A kosong)", "Data Kosong (B kosong)", "Data Kosong (keduanya)"
    ], key=filter_key)

    # Buat DataFrame untuk tabel ini
    base_df = merged[pair_cols].copy().reset_index(drop=True)

    # Filter berdasarkan status kolom
    if status_col in base_df.columns:
        status_series = base_df[status_col].astype(str)

        if filter_sel == "Semua":
            show_df = base_df
        elif filter_sel == "Sama saja":
            show_df = base_df[status_series == "Sama"]
        elif filter_sel == "Ada perbedaan":
            show_df = base_df[status_series.str.contains("Tidak Sama", na=False)]
        elif filter_sel == "Data Kosong":
            show_df = base_df[status_series.str.contains("Data Kosong", na=False)]
        elif filter_sel == "Data Kosong (A kosong)":
            show_df = base_df[status_series.str.contains("A kosong", na=False)]
        elif filter_sel == "Data Kosong (B kosong)":
            show_df = base_df[status_series.str.contains("B kosong", na=False)]
        elif filter_sel == "Data Kosong (keduanya)":
            show_df = base_df[status_series.str.contains("A & B kosong", na=False)]
        else:
            show_df = base_df
    else:
        show_df = base_df

    st.caption(f"Menampilkan {len(show_df):,} baris")
    st.dataframe(show_df.reset_index(drop=True), use_container_width=True, height=400)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-title">⬇️ Download Hasil</p>', unsafe_allow_html=True)

# Bangun display_cols untuk download (semua kolom semua pasangan)
download_cols = [id_col_a]
for label in results:
    download_cols += [f"[{label}] Harga A", f"[{label}] Harga B",
                      f"[{label}] Status",  f"[{label}] Selisih"]
download_cols = [c for c in download_cols if c in merged.columns]

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    merged[download_cols].to_excel(writer, sheet_name="Detail", index=False)
    pd.DataFrame([{
        "Marketplace Pair": lbl,
        "Total Baris Cocok": r["matched"],
        "Sama": r["sama"], "Tidak Sama": r["tidak_sama"], "Data Kosong": r["kosong"],
        "% Sama": f"{r['pct_sama']:.2f}%", "% Tidak Sama": f"{r['pct_beda']:.2f}%",
    } for lbl, r in results.items()]).to_excel(writer, sheet_name="Ringkasan", index=False)

st.download_button("📥 Download Hasil (.xlsx)", data=buf.getvalue(),
                   file_name="hasil_perbandingan_harga.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   use_container_width=True)