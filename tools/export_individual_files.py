# C:\Users\kaito\Desktop\time\tools\export_individual_files.py
import pandas as pd
import os
import shutil

# --- 設定 ---
CSV_PATH = "schedule_optimized.csv"
BASE_DIR = "reports"
SUB_DIRS = ["students", "teachers", "daily"]

# 時間割の定義（表示用）
TIME_MAP = {
    1: "13:00-14:20",
    2: "14:30-15:50",
    3: "16:00-17:20",
    4: "17:30-18:50",
    5: "19:00-20:20",
    6: "20:30-21:50",
    7: "Special",
    8: "Special",
}


def clean_and_create_dirs():
    """フォルダの初期化（古いファイルを削除して作り直す）"""
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)

    os.makedirs(BASE_DIR)
    for d in SUB_DIRS:
        os.makedirs(os.path.join(BASE_DIR, d))
    print(f">>> Created directory structure in '{BASE_DIR}/'")


def export_all_files():
    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"Error: {CSV_PATH} not found. Run generate_and_run.py first.")
        return

    clean_and_create_dirs()

    # 表示用の「時間」列を追加
    df["Time"] = df["Period"].map(TIME_MAP)

    # ==========================================
    # 1. 生徒別ファイル出力 (Students)
    # ==========================================
    students = df["Student"].unique()
    print(f">>> Exporting {len(students)} student files...")

    for student in students:
        # その生徒のデータのみ抽出
        subset = df[df["Student"] == student].copy()
        subset = subset.sort_values(["DayIdx", "Period"])

        # 必要な列だけ選ぶ
        output_cols = ["Date", "Time", "Period", "Subject", "Teacher", "Booth", "Type"]

        # ファイル名に使えない文字があれば置換（念のため）
        safe_name = str(student).replace("/", "_")
        filename = os.path.join(BASE_DIR, "students", f"{safe_name}.xlsx")

        subset[output_cols].to_excel(filename, index=False)

    # ==========================================
    # 2. 講師別ファイル出力 (Teachers)
    # ==========================================
    teachers = df["Teacher"].unique()
    print(f">>> Exporting {len(teachers)} teacher files...")

    for teacher in teachers:
        subset = df[df["Teacher"] == teacher].copy()
        subset = subset.sort_values(["DayIdx", "Period"])

        output_cols = ["Date", "Time", "Period", "Subject", "Student", "Booth", "Type"]

        safe_name = str(teacher).replace("/", "_")
        filename = os.path.join(BASE_DIR, "teachers", f"{safe_name}.xlsx")

        subset[output_cols].to_excel(filename, index=False)

    # ==========================================
    # 3. 日別ファイル出力 (Daily)
    # ==========================================
    days = df["DayIdx"].unique()
    days.sort()
    print(f">>> Exporting {len(days)} daily files...")

    for day_idx in days:
        subset = df[df["DayIdx"] == day_idx].copy()
        # 時間順 -> ブース順 でソート（現場で見やすい順）
        subset = subset.sort_values(["Period", "Booth"])

        output_cols = [
            "Period",
            "Time",
            "Booth",
            "Student",
            "Teacher",
            "Subject",
            "Type",
        ]

        # 日付文字列を取得（ファイル名用）
        date_str = subset.iloc[0]["Date"].split("(")[0]  # "Day1" など
        filename = os.path.join(BASE_DIR, "daily", f"{date_str}.xlsx")

        subset[output_cols].to_excel(filename, index=False)

    print(f"\n>>> Done! Check the '{BASE_DIR}' folder.")


if __name__ == "__main__":
    export_all_files()
