# C:\Users\kaito\Desktop\time\tools\generate_mock_data.py
import csv
import os

# --- 設定 ---
INPUT_FILE = "data/regular_schedule.csv"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PERIODS = range(1, 8)  # 1限〜7限


def load_data(filepath):
    """CSVを読み込み、辞書形式に変換する"""
    # 構造: schedule[teacher_id][day_index][period] = subject
    schedule = {}

    if not os.path.exists(filepath):
        print(f"Error: File not found - {filepath}")
        return {}

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t_id = row["teacher_id"]
            d_idx = int(row["day"])
            p_idx = int(row["period"])
            subj = row["subject"]

            if t_id not in schedule:
                schedule[t_id] = {}
            if d_idx not in schedule[t_id]:
                schedule[t_id][d_idx] = {}

            schedule[t_id][d_idx][p_idx] = subj

    return schedule


def print_grid(schedule):
    """講師ごとにグリッド形式で出力する"""
    teachers = sorted(schedule.keys())

    # 列幅の設定
    col_width = 12

    for t_id in teachers:
        print(f"\n{'=' * 20} {t_id} {'=' * 20}")

        # ヘッダー (時限)
        header = "Day |" + "|".join([f"{f'P{p}':^{col_width}}" for p in PERIODS]) + "|"
        print(header)
        print("-" * len(header))

        # 各曜日の行
        for d_idx, day_name in enumerate(DAYS):
            # 日曜(6)までループするが、土曜(5)までしかデータがない場合は空行になるだけ
            if d_idx > 5:
                continue

            row_str = f"{day_name} |"
            for p in PERIODS:
                # 該当スロットに授業があるか？
                cell = schedule[t_id].get(d_idx, {}).get(p, "")
                if cell:
                    # データがある場合
                    cell_str = f"{cell:^{col_width}}"
                else:
                    # 空きの場合
                    cell_str = " " * col_width

                row_str += f"{cell_str}|"
            print(row_str)


if __name__ == "__main__":
    data = load_data(INPUT_FILE)
    if data:
        print_grid(data)
    else:
        print("No data found or empty file.")
