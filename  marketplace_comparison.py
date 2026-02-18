import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import re

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Price Comparison Dashboard",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --accent: #00e5ff;
    --accent2: #ff3dff;
    --accent3: #ffe600;
    --text: #e8e8f0;
    --muted: #6b6b88;
    --success: #00ff9d;
    --danger: #ff4d6d;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    font-family: 'DM Mono', monospace;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}

h1, h2, h3, h4 { font-family: 'Syne', sans-serif !important; }

.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: #000 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.5rem !important;
    letter-spacing: 0.05em !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }

div[data-testid="metric-container"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 1rem !important;
}

.card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.tag-same {
    background: rgba(0,255,157,0.15);
    color: var(--success);
    border: 1px solid var(--success);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 500;
}
.tag-diff {
    background: rgba(255,77,109,0.15);
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 500;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}

.stSelectbox label, .stMultiSelect label {
    color: var(--muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 8px;
}

.section-label {
    color: var(--accent);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    font-weight: 500;
    margin-bottom: 0.25rem;
}

div[data-baseweb="select"] > div {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

MARKETPLACE_KEYWORDS = {
    "Shopee":    ["shopee", "shp"],
    "Tokopedia": ["tokopedia", "tokped", "toped"],
    "TikTok":    ["tiktok", "tik tok", "tt"],
    "Web":       ["web", "website"],
    "Lazada":    ["lazada", "lzd"],
    "Blibli":    ["blibli"],
}

CATEGORY_KEYWORDS = {
    "Portal": ["portal"],
    "Omni":   ["omni"],
}

def detect_marketplace(col_name: str):
    low = col_name.lower()
    for name, kws in MARKETPLACE_KEYWORDS.items():
        if any(k in low for k in kws):
            return name
    return None

def detect_category(col_name: str):
    low = col_name.lower()
    for name, kws in CATEGORY_KEYWORDS.items():
        if any(k in low for k in kws):
            return name
    return None

def load_file(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    else:
        return pd.read_excel(uploaded)

def compare_prices(df, col_a, col_b, label_a, label_b):
    a = pd.to_numeric(df[col_a], errors="coerce")
    b = pd.to_numeric(df[col_b], errors="coerce")
    valid = a.notna() & b.notna()
    result = pd.DataFrame({
        label_a: a,
        label_b: b,
    })
    result["Status"] = "N/A"
    result.loc[valid & (a == b), "Status"] = "Sama"
    result.loc[valid & (a != b), "Status"] = "Tidak Sama"
    result["Selisih"] = np.where(valid & (a != b), (a - b).abs(), np.nan)
    result["Selisih"] = result["Selisih"].apply(
        lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "-"
    )
    return result, valid

def pct_summary(result_df):
    total = len(result_df[result_df["Status"] != "N/A"])
    sama  = (result_df["Status"] == "Sama").sum()
    diff  = (result_df["Status"] == "Tidak Sama").sum()
    pct_s = (sama / total * 100) if total else 0
    pct_d = (diff / total * 100) if total else 0
    return total, sama, diff, pct_s, pct_d

def to_excel(dfs: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)
    return buf.getvalue()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="section-label">Upload Data</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["xlsx", "xls", "csv"], label_visibility="collapsed")

    if uploaded:
        df_raw = load_file(uploaded)
        cols = list(df_raw.columns)

        st.markdown("---")
        st.markdown('<p class="section-label">Auto-Detected Columns</p>', unsafe_allow_html=True)

        auto_pairs = {}
        for c in cols:
            mp  = detect_marketplace(c)
            cat = detect_category(c)
            if mp and cat:
                if mp not in auto_pairs:
                    auto_pairs[mp] = {}
                auto_pairs[mp][cat] = c

        detected_info = []
        for mp, cats in auto_pairs.items():
            for cat, col in cats.items():
                detected_info.append(f"✦ {col} → {mp} / {cat}")
        if detected_info:
            st.code("\n".join(detected_info), language=None)
        else:
            st.info("Tidak ada kolom terdeteksi otomatis. Pilih manual di bawah.")

        st.markdown("---")
        st.markdown('<p class="section-label">Manual Column Pairing</p>', unsafe_allow_html=True)
        st.caption("Tambah pasangan kolom yang ingin dibandingkan")

        if "pairs" not in st.session_state:
            st.session_state.pairs = []
            for mp, cats in auto_pairs.items():
                if "Portal" in cats and "Omni" in cats:
                    st.session_state.pairs.append({
                        "label": mp,
                        "col_a": cats["Portal"],
                        "col_b": cats["Omni"],
                        "cat_a": "Portal",
                        "cat_b": "Omni",
                    })

        if st.button("+ Tambah Pasangan"):
            st.session_state.pairs.append({"label": "", "col_a": cols[0], "col_b": cols[0], "cat_a": "A", "cat_b": "B"})

        to_remove = []
        for i, pair in enumerate(st.session_state.pairs):
            with st.expander(f"Pasangan {i+1}: {pair['label'] or '(belum diberi nama)'}", expanded=(i==0)):
                pair["label"] = st.text_input("Nama Pasangan", value=pair["label"], key=f"lbl_{i}")
                pair["cat_a"] = st.text_input("Label Kolom A", value=pair.get("cat_a","A"), key=f"ca_{i}")
                pair["col_a"] = st.selectbox("Kolom A", cols, index=cols.index(pair["col_a"]) if pair["col_a"] in cols else 0, key=f"a_{i}")
                pair["cat_b"] = st.text_input("Label Kolom B", value=pair.get("cat_b","B"), key=f"cb_{i}")
                pair["col_b"] = st.selectbox("Kolom B", cols, index=cols.index(pair["col_b"]) if pair["col_b"] in cols else 0, key=f"b_{i}")
                if st.button("🗑 Hapus", key=f"del_{i}"):
                    to_remove.append(i)

        for i in sorted(to_remove, reverse=True):
            st.session_state.pairs.pop(i)

        st.markdown("---")
        run = st.button("🚀 Jalankan Analisis", use_container_width=True)
    else:
        run = False


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown('<p class="hero-title">Price<br>Comparison<br>Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p style="color:#6b6b88;font-size:0.85rem;margin-top:-0.5rem;margin-bottom:2rem;">Upload file · Pilih kolom · Analisis harga marketplace</p>', unsafe_allow_html=True)

if not uploaded:
    st.markdown("""
    <div class="card" style="text-align:center;padding:3rem;">
        <div style="font-size:3rem;margin-bottom:1rem;">📂</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:700;color:#e8e8f0;">
            Upload file Excel atau CSV di sidebar
        </div>
        <div style="color:#6b6b88;margin-top:0.5rem;font-size:0.85rem;">
            Program akan otomatis mendeteksi kolom marketplace yang ada
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not run:
    st.markdown("""
    <div class="card" style="padding:2rem;">
        <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#00e5ff;">
            ✦ File berhasil diupload
        </div>
        <div style="color:#6b6b88;margin-top:0.5rem;font-size:0.85rem;">
            Periksa pasangan kolom di sidebar, lalu klik <strong style="color:#e8e8f0">Jalankan Analisis</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-label">Preview Data</p>', unsafe_allow_html=True)
    st.dataframe(df_raw.head(10), use_container_width=True, height=250)
    st.stop()


# ── Analysis ──────────────────────────────────────────────────────────────────
pairs = [p for p in st.session_state.pairs if p["col_a"] and p["col_b"] and p["label"]]
if not pairs:
    st.warning("Tidak ada pasangan kolom yang valid. Tambahkan pasangan di sidebar.")
    st.stop()

all_results = {}
summaries   = []

for pair in pairs:
    res, valid = compare_prices(df_raw, pair["col_a"], pair["col_b"], pair["cat_a"], pair["cat_b"])
    total, sama, diff, pct_s, pct_d = pct_summary(res)
    all_results[pair["label"]] = res
    summaries.append({
        "Marketplace":  pair["label"],
        "Total Data":   total,
        "Sama":         sama,
        "Tidak Sama":   diff,
        "% Sama":       pct_s,
        "% Tidak Sama": pct_d,
    })


# ── KPI Cards ──────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label" style="margin-top:1rem;">Ringkasan Keseluruhan</p>', unsafe_allow_html=True)
kpi_cols = st.columns(len(pairs))
for i, s in enumerate(summaries):
    with kpi_cols[i]:
        st.metric(
            label=s["Marketplace"],
            value=f"{s['% Sama']:.2f}% Sama",
            delta=f"{s['Sama']:,} dari {s['Total Data']:,} data",
        )


# ── Bar Chart Summary ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">Persentase Perbandingan Harga</p>', unsafe_allow_html=True)

df_sum = pd.DataFrame(summaries)
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    name="Sama",
    x=df_sum["Marketplace"],
    y=df_sum["% Sama"],
    marker_color="#00ff9d",
    marker_line_width=0,
))
fig_bar.add_trace(go.Bar(
    name="Tidak Sama",
    x=df_sum["Marketplace"],
    y=df_sum["% Tidak Sama"],
    marker_color="#ff4d6d",
    marker_line_width=0,
))
fig_bar.update_layout(
    barmode="stack",
    plot_bgcolor="#111118",
    paper_bgcolor="#111118",
    font=dict(family="DM Mono", color="#e8e8f0", size=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    margin=dict(l=10, r=10, t=20, b=10),
    yaxis=dict(ticksuffix="%", gridcolor="#1a1a24", range=[0,100]),
    xaxis=dict(gridcolor="#1a1a24"),
    height=320,
)
st.plotly_chart(fig_bar, use_container_width=True)


# ── Donut Charts ───────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Distribusi per Marketplace</p>', unsafe_allow_html=True)
donut_cols = st.columns(len(pairs))
for i, s in enumerate(summaries):
    with donut_cols[i]:
        fig_d = go.Figure(go.Pie(
            labels=["Sama","Tidak Sama"],
            values=[s["Sama"], s["Tidak Sama"]],
            hole=0.65,
            marker_colors=["#00ff9d","#ff4d6d"],
            textinfo="percent",
            textfont=dict(family="DM Mono", size=11, color="#e8e8f0"),
        ))
        fig_d.update_layout(
            showlegend=False,
            plot_bgcolor="#111118",
            paper_bgcolor="#111118",
            margin=dict(l=10,r=10,t=10,b=10),
            height=200,
            annotations=[dict(
                text=f"<b>{s['% Sama']:.1f}%</b>",
                font=dict(size=16, family="Syne", color="#00ff9d"),
                showarrow=False,
            )],
        )
        st.markdown(f'<div style="text-align:center;font-family:Syne,sans-serif;font-weight:700;font-size:0.9rem;color:#e8e8f0;margin-bottom:0.25rem;">{s["Marketplace"]}</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_d, use_container_width=True)


# ── Scatter: selisih harga ────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">Detail Selisih Harga</p>', unsafe_allow_html=True)
scatter_tab = st.tabs([p["label"] for p in pairs])

for i, pair in enumerate(pairs):
    with scatter_tab[i]:
        res = all_results[pair["label"]]
        col_a, col_b = pair["cat_a"], pair["cat_b"]
        plot_df = res[res["Status"] != "N/A"].copy()
        plot_df["_selisih_num"] = pd.to_numeric(
            plot_df["Selisih"].str.replace("Rp ","").str.replace(",",""), errors="coerce"
        ).fillna(0)

        fig_sc = px.scatter(
            plot_df.reset_index(),
            x=col_a, y=col_b,
            color="Status",
            color_discrete_map={"Sama":"#00ff9d","Tidak Sama":"#ff4d6d"},
            hover_data={"Selisih": True, "index": False},
            size_max=6,
            opacity=0.6,
        )
        fig_sc.update_traces(marker=dict(size=4))
        fig_sc.update_layout(
            plot_bgcolor="#111118",
            paper_bgcolor="#111118",
            font=dict(family="DM Mono", color="#e8e8f0", size=11),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10,r=10,t=20,b=10),
            xaxis=dict(gridcolor="#1a1a24"),
            yaxis=dict(gridcolor="#1a1a24"),
            height=380,
        )
        st.plotly_chart(fig_sc, use_container_width=True)


# ── Data Table ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">Tabel Perbandingan Detail</p>', unsafe_allow_html=True)

tab_labels = [p["label"] for p in pairs]
tabs = st.tabs(tab_labels)

for i, pair in enumerate(pairs):
    with tabs[i]:
        res = all_results[pair["label"]]
        show_filter = st.radio(
            "Filter", ["Semua","Sama","Tidak Sama"],
            horizontal=True, key=f"filter_{i}"
        )
        display = res if show_filter == "Semua" else res[res["Status"] == show_filter]

        def style_row(row):
            if row["Status"] == "Sama":
                return ["background-color: rgba(0,255,157,0.06)"]*len(row)
            elif row["Status"] == "Tidak Sama":
                return ["background-color: rgba(255,77,109,0.06)"]*len(row)
            return [""]*len(row)

        st.dataframe(
            display.style.apply(style_row, axis=1),
            use_container_width=True,
            height=400,
        )
        st.caption(f"Menampilkan {len(display):,} dari {len(res):,} baris")


# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-label">Download Hasil</p>', unsafe_allow_html=True)

dl_col1, dl_col2 = st.columns(2)

with dl_col1:
    export_sheets = {"Summary": df_sum}
    export_sheets.update({k: v for k, v in all_results.items()})
    excel_bytes = to_excel(export_sheets)
    st.download_button(
        label="⬇ Download Excel (Semua Sheet)",
        data=excel_bytes,
        file_name="price_comparison_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with dl_col2:
    summary_csv = df_sum.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV (Summary)",
        data=summary_csv,
        file_name="price_comparison_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown('<p style="color:#2a2a3a;text-align:center;font-size:0.7rem;margin-top:2rem;">Price Comparison Dashboard · Built with Streamlit</p>', unsafe_allow_html=True)