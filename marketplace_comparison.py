import streamlit as st
import pandas as pd
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
h1, h2, h3, h4 { font-family: 'Syne', sans-serif !important; }
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
    padding: 1.25rem 1.5rem; text-align: center; margin-bottom: 0.5rem;
}
.stat-card .val { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 0.25rem; }
.stat-card .lbl { font-size: 0.72rem; color: #888; letter-spacing: 0.1em; text-transform: uppercase; }
.green  { color: #a8ff78; } .red { color: #ff7878; } .blue { color: #78c8ff; }
.gold   { color: #ffd878; } .purple { color: #c8a8ff; }
.section-title {
    font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #e8e8f0;
    letter-spacing: 0.05em; margin: 0 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #ffffff10;
}
.tabel-title {
    font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700; color: #78ffd6;
    letter-spacing: 0.05em; margin: 1.5rem 0 0.75rem; padding: 0.5rem 1rem;
    background: #78ffd608; border-left: 3px solid #78ffd6; border-radius: 0 8px 8px 0;
}
.info-box   { background: #78ffd608; border: 1px solid #78ffd620; border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.8rem; color: #78ffd6; margin-bottom: 1rem; }
.warn-box   { background: #ffd87808; border: 1px solid #ffd87820; border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.8rem; color: #ffd878; margin-bottom: 1rem; }
.kosong-box { background: #ffd87808; border: 1px solid #ffd87830; border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.82rem; color: #ffd878; margin-top: 0.75rem; }
button[kind="primary"] {
    background: linear-gradient(135deg, #a8ff78, #78ffd6) !important; color: #0a0a0f !important;
    border: none !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Helpers ───────────────────────────────────────────────────────────────────
PRICE_KW    = ["harga","price","amount","cost","nilai","rate","web","shopee","tokped","tiktok","tokopedia"]
ID_KW       = ["id","sku","kode","code","barcode","artikel","no","nomor","number","ref","item"]
BRAND_KW    = ["brand","merk","merek","vendor","manufaktur","manufacturer"]
KATEGORI_KW = ["kategori","category","cat","tipe","type","jenis","group","grup","divisi","kelas"]
NAMA_KW     = ["nama","name","produk","product","item","title","judul","description","deskripsi"]

def sim(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def best_col(df, keywords):
    """Return nama kolom yang paling cocok dengan keywords, atau None."""
    cols = df.columns.tolist()
    if not cols: return None
    return sorted(cols, key=lambda c: max(sim(c.lower(), k) for k in keywords), reverse=True)[0]

def auto_detect(df, kind="price"):
    kw_map = {
        "price":    PRICE_KW,
        "id":       ID_KW,
        "brand":    BRAND_KW,
        "kategori": KATEGORI_KW,
        "nama":     NAMA_KW,
    }
    kw = kw_map.get(kind, PRICE_KW)
    return sorted(df.columns, key=lambda c: max(sim(c.lower(), k) for k in kw), reverse=True)[:5]

def detect_info_cols(df):
    """Auto-detect kolom SKU, Nama, Brand, Kategori dari Portal."""
    return {
        "SKU/ID":     best_col(df, ID_KW),
        "Nama Produk":best_col(df, NAMA_KW),
        "Brand":      best_col(df, BRAND_KW),
        "Kategori":   best_col(df, KATEGORI_KW),
    }

def load_file(f):
    if f is None: return None
    try:
        return pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

def is_kosong(val):
    """True jika nilai dianggap kosong: NaN, blank, atau 0."""
    if pd.isna(val):
        return True
    s = str(val).strip().replace(",","").replace("Rp","").strip()
    if s == "" or s == "0" or s == "0.0":
        return True
    try:
        return float(s) == 0
    except:
        return True

def to_num(val):
    """Konversi ke float, return None jika kosong."""
    if is_kosong(val):
        return None
    try:
        return float(str(val).replace(",","").replace("Rp","").strip())
    except:
        return None

def compute_status(portal_series, omni_series, b_exists):
    """
    - 0/blank/NaN = kosong, dicek DULU sebelum bandingkan
    - b_exists False = produk tidak ada di Omni sama sekali (LEFT JOIN)
    - Selisih selalu positif
    """
    out = []
    for portal_raw, omni_raw, exists in zip(portal_series, omni_series, b_exists):
        # Produk tidak ada di Omni sama sekali (hasil LEFT JOIN)
        if not exists:
            out.append("Tidak Ada di Omni")
            continue

        portal_kos = is_kosong(portal_raw)
        omni_kos   = is_kosong(omni_raw)

        if portal_kos and omni_kos:
            out.append("Data Kosong (Portal & Omni)")
        elif portal_kos:
            out.append("Data Kosong (Portal kosong)")
        elif omni_kos:
            out.append("Data Kosong (Omni kosong)")
        else:
            portal = float(str(portal_raw).replace(",","").replace("Rp","").strip())
            omni   = float(str(omni_raw).replace(",","").replace("Rp","").strip())
            if portal == omni:
                out.append("Sama")
            elif portal > omni:
                out.append(f"Tidak Sama - Portal Lebih Mahal (selisih Rp{portal-omni:,.0f})")
            else:
                out.append(f"Tidak Sama - Omni Lebih Mahal (selisih Rp{omni-portal:,.0f})")

    return pd.Series(out, index=portal_series.index)

def filter_df(df, status_col, sel):
    col = df[status_col].astype(str)
    if sel == "Semua":                          return df
    elif sel == "Sama":                         return df[col == "Sama"]
    elif sel == "Tidak Sama":                   return df[col.str.startswith("Tidak Sama")]
    elif sel == "Portal Lebih Mahal":           return df[col.str.contains("Portal Lebih Mahal")]
    elif sel == "Omni Lebih Mahal":             return df[col.str.contains("Omni Lebih Mahal")]
    elif sel == "Data Kosong":                  return df[col.str.startswith("Data Kosong")]
    elif sel == "Data Kosong (Portal kosong)":  return df[col == "Data Kosong (Portal kosong)"]
    elif sel == "Data Kosong (Omni kosong)":    return df[col == "Data Kosong (Omni kosong)"]
    elif sel == "Data Kosong (Keduanya)":       return df[col == "Data Kosong (Portal & Omni)"]
    elif sel == "Tidak Ada di Omni":            return df[col == "Tidak Ada di Omni"]
    return df

FILTER_OPTS = [
    "Semua", "Sama", "Tidak Sama", "Portal Lebih Mahal", "Omni Lebih Mahal",
    "Data Kosong", "Data Kosong (Portal kosong)", "Data Kosong (Omni kosong)",
    "Data Kosong (Keduanya)", "Tidak Ada di Omni"
]

# ─── Session state ─────────────────────────────────────────────────────────────
for key in ["merged","results","pairs_info","id_col_a","info_cols"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>💹 Price Comparator</h1>
  <p>Portal vs Omni — bandingkan harga per marketplace, deteksi perbedaan & data kosong</p>
</div>
""", unsafe_allow_html=True)

# ─── Upload ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown('<div class="label-tag">File A — Portal</div>', unsafe_allow_html=True)
    file_a = st.file_uploader("Upload File Portal", type=["xlsx","xls","csv"], key="fa", label_visibility="collapsed")
with c2:
    st.markdown('<div class="label-tag">File B — Omni</div>', unsafe_allow_html=True)
    file_b = st.file_uploader("Upload File Omni", type=["xlsx","xls","csv"], key="fb", label_visibility="collapsed")

if not file_a or not file_b:
    st.markdown('<div class="warn-box">⬆️ Upload kedua file (Portal & Omni) untuk mulai analisis.</div>', unsafe_allow_html=True)
    st.stop()

df_a = load_file(file_a)
df_b = load_file(file_b)
if df_a is None or df_b is None:
    st.stop()

st.success(f"✅ Portal: **{len(df_a):,} baris**, {len(df_a.columns)} kolom  |  Omni: **{len(df_b):,} baris**, {len(df_b.columns)} kolom")
st.markdown("---")

# ─── Konfigurasi Kolom ─────────────────────────────────────────────────────────
st.markdown('<p class="section-title">⚙️ Konfigurasi Kolom</p>', unsafe_allow_html=True)

all_cols_a = df_a.columns.tolist()
all_cols_b = df_b.columns.tolist()

ci1, ci2 = st.columns(2, gap="large")
with ci1:
    id_hint_a = auto_detect(df_a, "id")
    id_col_a  = st.selectbox("Kolom ID/SKU — Portal", all_cols_a,
                              index=all_cols_a.index(id_hint_a[0]) if id_hint_a else 0)
with ci2:
    id_hint_b = auto_detect(df_b, "id")
    id_col_b  = st.selectbox("Kolom ID/SKU — Omni", all_cols_b,
                              index=all_cols_b.index(id_hint_b[0]) if id_hint_b else 0)

hint_a = auto_detect(df_a, "price")
hint_b = auto_detect(df_b, "price")
st.markdown(f'<div class="info-box">💡 <b>Saran kolom harga Portal:</b> {", ".join(hint_a)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="info-box">💡 <b>Saran kolom harga Omni:</b> {", ".join(hint_b)}</div>', unsafe_allow_html=True)

cp1, cp2 = st.columns(2, gap="large")
with cp1:
    price_cols_a = st.multiselect("Kolom Harga — Portal (bisa lebih dari 1)", all_cols_a, default=[])
with cp2:
    price_cols_b = st.multiselect("Kolom Harga — Omni (bisa lebih dari 1)", all_cols_b, default=[])

if not price_cols_a or not price_cols_b:
    st.markdown('<div class="warn-box">⚠️ Pilih minimal 1 kolom harga dari masing-masing file.</div>', unsafe_allow_html=True)
    st.stop()

# ─── Pasangkan Kolom ───────────────────────────────────────────────────────────
st.markdown("##### 🔗 Pasangkan Kolom Harga (Portal ↔ Omni)")
st.markdown('<div class="info-box">💡 Contoh: Web Portal ↔ Web Omni, Shopee Portal ↔ Shopee Omni</div>', unsafe_allow_html=True)

num_pairs = st.number_input("Jumlah pasangan kolom", min_value=1,
                             max_value=max(len(price_cols_a), len(price_cols_b)),
                             value=min(len(price_cols_a), len(price_cols_b)))
pairs = []
for i in range(int(num_pairs)):
    pc1, pc2, pc3 = st.columns([2, 2, 1])
    with pc1:
        col_a = st.selectbox(f"Harga Portal #{i+1}", price_cols_a, index=min(i, len(price_cols_a)-1), key=f"pa_{i}")
    with pc2:
        col_b = st.selectbox(f"Harga Omni #{i+1}", price_cols_b, index=min(i, len(price_cols_b)-1), key=f"pb_{i}")
    with pc3:
        label = st.text_input("Label", value=f"Pair {i+1}", key=f"lbl_{i}")
    pairs.append((col_a, col_b, label))

st.markdown("---")
run = st.button("🚀 Jalankan Analisis", type="primary", use_container_width=True)

# ─── Proses ────────────────────────────────────────────────────────────────────
if run:
    with st.spinner("Memproses data..."):
        try:
            used_a   = list(dict.fromkeys([p[0] for p in pairs]))
            used_b   = list(dict.fromkeys([p[1] for p in pairs]))

            # Auto-detect kolom info produk dari Portal SEBELUM merge
            info_cols_raw = detect_info_cols(df_a)
            info_col_vals = [v for v in info_cols_raw.values() if v and v in df_a.columns]
            # Deduplikasi
            seen_ic = set()
            info_col_vals = [c for c in info_col_vals if not (c in seen_ic or seen_ic.add(c))]

            # Sertakan kolom info produk di df_a_sel
            cols_a_all = list(dict.fromkeys([id_col_a] + info_col_vals + used_a))
            df_a_sel = df_a[cols_a_all].copy()
            df_b_sel = df_b[list(dict.fromkeys([id_col_b] + used_b))].copy()
            df_a_sel[id_col_a] = df_a_sel[id_col_a].astype(str).str.strip()
            df_b_sel[id_col_b] = df_b_sel[id_col_b].astype(str).str.strip()

            merged = pd.merge(df_a_sel, df_b_sel, left_on=id_col_a, right_on=id_col_b,
                              how="left", suffixes=("_Portal", "_Omni"))
        except Exception as e:
            st.error(f"Error saat merge: {e}")
            st.stop()

        results    = {}
        pairs_info = []  # simpan info kolom per pair untuk tabel

        for col_a, col_b, label in pairs:
            col_a_m = col_a + "_Portal" if (col_a in df_b_sel.columns and col_a != id_col_b) else col_a
            col_b_m = col_b + "_Omni"   if (col_b in df_a_sel.columns and col_b != id_col_a) else col_b
            if col_a_m not in merged.columns: col_a_m = col_a
            if col_b_m not in merged.columns: col_b_m = col_b
            if col_a_m not in merged.columns or col_b_m not in merged.columns:
                st.warning(f"⚠️ Kolom '{label}' tidak ditemukan, dilewati.")
                continue

            b_exists = merged[id_col_b].notna() if id_col_b in merged.columns else pd.Series(True, index=merged.index)

            portal_s = merged[col_a_m]
            omni_s   = merged[col_b_m]
            status_s = compute_status(portal_s, omni_s, b_exists)

            harga_portal_col = f"[{label}] Harga Portal"
            harga_omni_col   = f"[{label}] Harga Omni"
            status_col       = f"[{label}] Status"

            merged[harga_portal_col] = portal_s.apply(to_num)
            merged[harga_omni_col]   = omni_s.apply(to_num)
            merged[status_col]       = status_s

            # Statistik
            sama_n       = int((status_s == "Sama").sum())
            tidak_sama_n = int(status_s.str.startswith("Tidak Sama").sum())
            portal_mahal = int(status_s.str.contains("Portal Lebih Mahal").sum())
            omni_mahal   = int(status_s.str.contains("Omni Lebih Mahal").sum())
            kosong_n     = int(status_s.str.startswith("Data Kosong").sum())
            kosong_p     = int((status_s == "Data Kosong (Portal kosong)").sum())
            kosong_o     = int((status_s == "Data Kosong (Omni kosong)").sum())
            kosong_both  = int((status_s == "Data Kosong (Portal & Omni)").sum())
            tidak_ada_n  = int((status_s == "Tidak Ada di Omni").sum())
            valid_n      = sama_n + tidak_sama_n
            pct_sama     = (sama_n / valid_n * 100) if valid_n > 0 else 0.0
            pct_beda     = (tidak_sama_n / valid_n * 100) if valid_n > 0 else 0.0

            results[label] = {
                "total": len(status_s), "valid": valid_n,
                "sama": sama_n, "pct_sama": pct_sama,
                "tidak_sama": tidak_sama_n, "pct_beda": pct_beda,
                "portal_mahal": portal_mahal, "omni_mahal": omni_mahal,
                "kosong": kosong_n, "kosong_p": kosong_p,
                "kosong_o": kosong_o, "kosong_both": kosong_both,
                "tidak_ada": tidak_ada_n,
            }

            pairs_info.append({
                "label":       label,
                "id_col":      id_col_a,
                "portal_col":  harga_portal_col,
                "omni_col":    harga_omni_col,
                "status_col":  status_col,
            })

        # Pastikan kolom info yang terdeteksi ada di merged
        info_cols_valid = {k: v for k, v in info_cols_raw.items() if v and v in merged.columns}

        st.session_state.merged     = merged
        st.session_state.results    = results
        st.session_state.pairs_info = pairs_info
        st.session_state.id_col_a   = id_col_a
        st.session_state.info_cols  = info_cols_valid

# ─── Tampilkan Hasil ───────────────────────────────────────────────────────────
if st.session_state.merged is None:
    st.stop()

merged     = st.session_state.merged
results    = st.session_state.results
pairs_info = st.session_state.pairs_info
id_col_a   = st.session_state.id_col_a
info_cols  = st.session_state.info_cols or {}

st.markdown('<p class="section-title">📊 Hasil Analisis</p>', unsafe_allow_html=True)

st.markdown(f"""
<div class="stat-card" style="margin-bottom:1.5rem;background:linear-gradient(135deg,#a8ff7808,#78ffd608);border-color:#a8ff7830">
  <div class="val blue">{len(merged):,}</div>
  <div class="lbl">Total Produk Portal</div>
</div>""", unsafe_allow_html=True)

# ── Statistik + Tabel per pasangan ────────────────────────────────────────────
for info in pairs_info:
    label      = info["label"]
    status_col = info["status_col"]
    r          = results[label]

    # ── Statistik ──
    st.markdown(f"#### 🔍 {label}")

    s1, s2 = st.columns(2, gap="large")
    with s1:
        st.markdown(f'<div class="stat-card"><div class="val green">{r["pct_sama"]:.2f}%</div><div class="lbl">% Sama (dari data valid)</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card"><div class="val red">{r["pct_beda"]:.2f}%</div><div class="lbl">% Tidak Sama (dari data valid)</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)

    s3, s4, s5, s6 = st.columns(4, gap="large")
    with s3:
        st.markdown(f'<div class="stat-card"><div class="val green">{r["sama"]:,}</div><div class="lbl">Baris Sama</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div class="stat-card"><div class="val red">{r["tidak_sama"]:,}</div><div class="lbl">Baris Tidak Sama</div></div>', unsafe_allow_html=True)
    with s5:
        st.markdown(f'<div class="stat-card"><div class="val gold">{r["kosong"]:,}</div><div class="lbl">Data Kosong</div></div>', unsafe_allow_html=True)
    with s6:
        st.markdown(f'<div class="stat-card"><div class="val purple">{r["tidak_ada"]:,}</div><div class="lbl">Tidak Ada di Omni</div></div>', unsafe_allow_html=True)

    if r["tidak_sama"] > 0:
        st.markdown(f"""
        <div class="info-box" style="margin-top:0.75rem">
          📊 <b>Detail Tidak Sama ({r["tidak_sama"]:,} baris):</b><br>
          &nbsp;&nbsp;• Portal lebih mahal → <b>{r["portal_mahal"]:,} baris</b><br>
          &nbsp;&nbsp;• Omni lebih mahal &nbsp;→ <b>{r["omni_mahal"]:,} baris</b>
        </div>""", unsafe_allow_html=True)

    if r["kosong"] > 0:
        st.markdown(f"""
        <div class="kosong-box">
          📭 <b>Detail Data Kosong ({r["kosong"]:,} baris):</b><br>
          &nbsp;&nbsp;• Portal kosong, Omni ada &nbsp;→ <b>{r["kosong_p"]:,} baris</b><br>
          &nbsp;&nbsp;• Omni kosong, Portal ada &nbsp;→ <b>{r["kosong_o"]:,} baris</b><br>
          &nbsp;&nbsp;• Keduanya kosong &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ <b>{r["kosong_both"]:,} baris</b>
        </div>""", unsafe_allow_html=True)

    # ── Tabel Detail langsung di bawah statistik pair ini ──
    st.markdown(f'<div class="tabel-title">📋 Tabel Detail — {label}</div>', unsafe_allow_html=True)

    tabel_cols = [id_col_a, info["portal_col"], info["omni_col"], status_col]
    tabel_cols = [c for c in tabel_cols if c in merged.columns]
    base_df    = merged[tabel_cols].copy().reset_index(drop=True)

    filter_key = f"filter_{label}"
    filter_sel = st.selectbox(f"Filter — {label}:", FILTER_OPTS, key=filter_key)
    show_df    = filter_df(base_df, status_col, filter_sel)

    st.caption(f"Menampilkan {len(show_df):,} dari {len(base_df):,} baris")
    st.dataframe(show_df.reset_index(drop=True), use_container_width=True, height=380)

    st.markdown("---")

# ─── Download ──────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">⬇️ Download Hasil</p>', unsafe_allow_html=True)

# Tampilkan info kolom yang terdeteksi
if info_cols:
    detected_str = " &nbsp;|&nbsp; ".join([f"<b>{k}</b>: {v}" for k, v in info_cols.items()])
    st.markdown(f'<div class="info-box">🔍 Kolom info produk yang disertakan di Excel: {detected_str}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="warn-box">⚠️ Tidak ada kolom SKU/Brand/Kategori/Nama yang terdeteksi otomatis dari file Portal.</div>', unsafe_allow_html=True)

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    # Sheet detail per pair
    # Kolom info produk yang akan disertakan di setiap sheet
    info_col_list = [v for v in info_cols.values() if v and v in merged.columns]
    # Hapus duplikat tapi jaga urutan
    seen = set()
    info_col_list = [c for c in info_col_list if not (c in seen or seen.add(c))]

    for info in pairs_info:
        label      = info["label"]
        base_cols  = [id_col_a] + info_col_list + [info["portal_col"], info["omni_col"], info["status_col"]]
        tbl_cols   = [c for c in dict.fromkeys(base_cols) if c in merged.columns]
        sheet_name = label[:31]
        df_sheet   = merged[tbl_cols].copy()
        # Rename kolom info supaya lebih rapi di Excel
        rename_map = {v: k for k, v in info_cols.items() if v in df_sheet.columns}
        df_sheet.rename(columns=rename_map, inplace=True)
        df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)

    # Sheet ringkasan
    pd.DataFrame([{
        "Marketplace":         lbl,
        "Total Produk Portal": r["total"],
        "Data Valid":          r["valid"],
        "Sama":                r["sama"],
        "% Sama":              f"{r['pct_sama']:.2f}%",
        "Tidak Sama":          r["tidak_sama"],
        "% Tidak Sama":        f"{r['pct_beda']:.2f}%",
        "Portal Lebih Mahal":  r["portal_mahal"],
        "Omni Lebih Mahal":    r["omni_mahal"],
        "Data Kosong":         r["kosong"],
        "Kosong (Portal)":     r["kosong_p"],
        "Kosong (Omni)":       r["kosong_o"],
        "Kosong (Keduanya)":   r["kosong_both"],
        "Tidak Ada di Omni":   r["tidak_ada"],
    } for lbl, r in results.items()]).to_excel(writer, sheet_name="Ringkasan", index=False)

st.download_button("📥 Download Hasil (.xlsx)", data=buf.getvalue(),
                   file_name="hasil_perbandingan_harga.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   use_container_width=True)