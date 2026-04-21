# C:\Users\kaito\Desktop\time\tools\export_excel.py
import pandas as pd
import os

INPUT_FILE = "schedule_optimized.csv"
OUTPUT_FILE = "visualized_schedule.xlsx"


def export_to_excel():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print(f">>> Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # 見やすいようにデータを加工
    # 例: "Math" -> "数" (短縮)
    subject_map = {
        "Math": "数",
        "English": "英",
        "Science": "理",
        "Japanese": "国",
        "Social": "社",
    }
    df["SubjShort"] = df["Subject"].map(subject_map).fillna(df["Subject"])

    # 表示用テキストを作成
    # 講師用ビュー: "S001(数)"
    df["Cell_For_Teacher"] = df["Student"] + "(" + df["SubjShort"] + ")"

    # 生徒用ビュー: "T01(数)@3限"
    # ※同じ日に複数授業がある場合に対応するため、カンマ区切りにする準備
    df["Cell_For_Student"] = (
        df["Period"].astype(str) + "限:" + df["SubjShort"] + "(" + df["Teacher"] + ")"
    )

    print(f">>> Creating Excel file: {OUTPUT_FILE}...")

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        # --- Sheet 1: 講師別スケジュール (Teacher Matrix) ---
        # 行: 日付・時限, 列: 講師ID
        print("  - Generating Teacher View...")
        teacher_pivot = df.pivot_table(
            index=["DayIdx", "Date", "Period"],
            columns="Teacher",
            values="Cell_For_Teacher",
            aggfunc="first",  # 重複はないはずだが念のため
        )
        teacher_pivot.to_excel(writer, sheet_name="Teacher_View")

        # --- Sheet 2: 生徒別スケジュール (Student Matrix) ---
        # 行: 生徒ID, 列: 日付 (中身は授業リスト)
        print("  - Generating Student View...")

        # 生徒x日付でグルーピングして、授業を結合する (例: "3限:数(T1), 5限:英(T2)")
        student_daily = (
            df.groupby(["Student", "DayIdx", "Date"])["Cell_For_Student"]
            .apply(lambda x: " / ".join(x))
            .reset_index()
        )

        student_pivot = student_daily.pivot(
            index="Student", columns=["DayIdx", "Date"], values="Cell_For_Student"
        )
        student_pivot.to_excel(writer, sheet_name="Student_View")

        # --- Sheet 3: ブース使用状況 (Booth Map) ---
        # 行: 日付・時限, 列: ブースID
        print("  - Generating Booth View...")
        df["Cell_For_Booth"] = df["Teacher"] + " -> " + df["Student"]
        booth_pivot = df.pivot_table(
            index=["DayIdx", "Date", "Period"],
            columns="Booth",
            values="Cell_For_Booth",
            aggfunc="first",
        )
        booth_pivot.to_excel(writer, sheet_name="Booth_View")

    print(f"\n>>> Done! Open '{OUTPUT_FILE}' to verify.")


if __name__ == "__main__":
    export_to_excel()
