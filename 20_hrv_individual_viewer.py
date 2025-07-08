import streamlit as st
from pathlib import Path
import pandas as pd
from PIL import Image
import re
import math

# ===== 設定 =====
GRAPH_ROOT = Path(r"C:\Users\Yamauchi.Ryosuke\OneDrive - OneOtsuka\02_東京科学大学データ解析\HRV計算\心拍データ")
WHOLE_PLOT_DIR = Path(r"C:\Users\Yamauchi.Ryosuke\OneDrive - OneOtsuka\02_東京科学大学データ解析\HRV計算\05_HRV_visualize_results\01_whole_results\01_plots")
WHOLE_STATS_DIR = Path(r"C:\Users\Yamauchi.Ryosuke\OneDrive - OneOtsuka\02_東京科学大学データ解析\HRV計算\05_HRV_visualize_results\01_whole_results\02_stats")
IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp"]
CSV_NAME = "HRV_3min_individual.csv"
ROWS_PER_PAGE = 30

st.set_page_config(page_title="HRVグラフビューア", layout="wide")
st.title("🍔 HRVグラフビューア")

# ===== Phase名抽出 =====
def extract_phase_from_any_foldername(folderpath: Path):
    match = re.search(r"(Pre-?\d+|POD\d+)", folderpath.name)
    return match.group(1) if match else None

# ===== グラフ構造取得 =====
def get_patient_structure(root: Path):
    patient_dict = {}
    for top_folder in root.rglob("TD???"):
        if top_folder.is_dir():
            patient_id = top_folder.name
            for subfolder in top_folder.rglob("*"):
                if subfolder.is_dir():
                    phase = extract_phase_from_any_foldername(subfolder)
                    if not phase:
                        continue
                    key = (patient_id, phase)
                    csv_file = next(subfolder.glob(f"*{CSV_NAME}"), None)
                    img_files = [img for img in subfolder.glob("*") if img.suffix.lower() in IMG_EXTS]
                    if img_files or csv_file:
                        if key not in patient_dict:
                            patient_dict[key] = {"csv": csv_file, "images": img_files}
                        else:
                            patient_dict[key]["images"].extend(img_files)
                            if not patient_dict[key]["csv"] and csv_file:
                                patient_dict[key]["csv"] = csv_file
    return patient_dict

# ===== グラフ情報抽出・整理 =====
def extract_graph_info(filename):
    match = re.search(r"(Pre-?\d+|POD\d+)[_\\-]?(\d{8})[_\\-]?(\d{6}).*?([a-zA-Z]+)?\.png$", filename)
    if match:
        phase, date, time, graph_type = match.groups()
        datetime = f"{date}_{time}"
        if not graph_type:
            prefix_match = re.match(r"([A-Za-z]+)_", filename)
            graph_type = prefix_match.group(1) if prefix_match else "unknown"
        return datetime, graph_type
    return None, None

def organize_by_datetime(images):
    grouped = {}
    for img in images:
        dt_str, gtype = extract_graph_info(img.name)
        if dt_str and gtype:
            grouped.setdefault(dt_str, {})[gtype] = img
    return grouped

# ===== アプリ構成（タブ） =====
tab1, tab2 = st.tabs(["👤 個別結果", "📊 全体結果"])

# ===== タブ1: 個別表示 =====
with tab1:
    patient_data = get_patient_structure(GRAPH_ROOT)

    if not patient_data:
        st.warning("データが見つかりません。")
    else:
        patient_ids = sorted(set(k[0] for k in patient_data))
        selected_patient = st.sidebar.selectbox("👤 患者IDを選択", patient_ids)

        phase_candidates = sorted(set(k[1] for k in patient_data if k[0] == selected_patient))
        selected_phase = st.sidebar.selectbox("🕒 フェーズを選択", phase_candidates)

        key = (selected_patient, selected_phase)
        entry = patient_data.get(key)

        if not entry:
            st.info("データが見つかりません。")
        else:
            display_mode = st.radio("表示モード", ["CSV表示", "同種グラフ", "日時別グラフ"])

            if display_mode == "CSV表示":
                csv_path = entry["csv"]
                if csv_path and csv_path.exists():
                    df = pd.read_csv(csv_path)
                    total_pages = math.ceil(len(df) / ROWS_PER_PAGE)
                    page = st.number_input("📄 表示ページ", 1, total_pages, 1)
                    start_idx = (page - 1) * ROWS_PER_PAGE
                    end_idx = start_idx + ROWS_PER_PAGE
                    st.dataframe(df.iloc[start_idx:end_idx])
                else:
                    st.warning("CSVファイルが見つかりません。")

            elif display_mode == "同種グラフ":
                image_files = entry["images"]
                graph_types = sorted(set(
                    extract_graph_info(img.name)[1] for img in image_files if extract_graph_info(img.name)[1]
                ))

                search = st.text_input("🔍 グラフ名検索")
                graph_types = [g for g in graph_types if search.lower() in g.lower()] if search else graph_types
                selected_type = st.selectbox("グラフタイプを選択", graph_types)

                for img in image_files:
                    _, gtype = extract_graph_info(img.name)
                    if gtype == selected_type:
                        st.image(str(img), caption=f"🟨 {img.name}", use_container_width=True)

            elif display_mode == "日時別グラフ":
                image_files = entry["images"]
                grouped = organize_by_datetime(image_files)
                datetime_keys = sorted(grouped.keys())
                selected_datetime = st.selectbox("表示する日時", datetime_keys)

                for gtype, img in grouped[selected_datetime].items():
                    st.markdown(f"### 📈 {gtype}")
                    st.image(str(img), use_container_width=True)

# ===== タブ2: 全体表示 =====
with tab2:
    st.subheader("📁 全体結果")

    whole_mode = st.radio("モードを選択", ["統計CSV表示", "グラフ一括表示"])

    if whole_mode == "統計CSV表示":
        csv_map = {
            "Mann-Whitney 統計結果": WHOLE_STATS_DIR / "mannwhitney_results.csv",
            "Summary 統計量": WHOLE_STATS_DIR / "summary_stats.csv"
        }
        selected_csv_name = st.selectbox("CSVを選択", list(csv_map.keys()))
        selected_csv_path = csv_map[selected_csv_name]

        if selected_csv_path.exists():
            df_stats = pd.read_csv(selected_csv_path)
            st.dataframe(df_stats)
        else:
            st.warning(f"{selected_csv_name} が見つかりません。")

    elif whole_mode == "グラフ一括表示":
        if WHOLE_PLOT_DIR.exists():
            # 拡張子でフィルタ
            plot_files = [f for f in WHOLE_PLOT_DIR.rglob("*.png") if f.suffix.lower() in IMG_EXTS]
            # グラフタイプ選択
            graph_types = sorted(set(
                re.search(r"(boxplot|heatmap|timeseries|violinplot)", f.name).group(1)
                for f in plot_files if re.search(r"(boxplot|heatmap|timeseries|violinplot)", f.name)
            ))
            selected_plot_type = st.selectbox("表示するグラフの種類", graph_types)

            selected_files = [
                f for f in plot_files if selected_plot_type in f.name
            ]

            st.subheader(f"📈 {selected_plot_type} グラフ一覧")
            for img_path in selected_files:
                st.image(str(img_path), caption=img_path.name, use_container_width=True)
            
            
        else:
            st.warning("グラフ画像フォルダが見つかりません。")