# C:\Users\kaito\Desktop\time\tools\evaluate_schedule.py
import pandas as pd
import numpy as np
import os

INPUT_FILE = "schedule_optimized.csv"


def evaluate_schedule():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run generate_and_run.py first.")
        return

    print(f">>> Loading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # ★追加: レギュラー授業を除外し、AIが生成した「講習(Seasonal)」のみを評価対象にする
    df = df[df["Type"] == "Seasonal"]

    total_lessons = len(df)
    print(f"Total Seasonal Lessons: {total_lessons}")

    if total_lessons == 0:
        print("No seasonal lessons found.")
        return

    # --- 1. 時間帯の評価 (Time Slot Quality) ---
    good_time_slots = df[(df["Period"] >= 3) & (df["Period"] <= 8)]
    time_score = len(good_time_slots) / total_lessons * 100

    print("\n" + "=" * 40)
    print(f"1. 時間帯遵守率 (3-8限率): {time_score:.1f}%")
    print("=" * 40)

    # --- 2. 担当講師の一貫性 (Teacher Consistency) ---
    consistency_scores = []
    grouped = df.groupby(["Student", "Subject"])

    for (student, subject), group in grouped:
        count = len(group)
        if count <= 1:
            continue
        top_teacher_count = group["Teacher"].value_counts().iloc[0]
        score = top_teacher_count / count
        consistency_scores.append(score)

    avg_consistency = np.mean(consistency_scores) * 100 if consistency_scores else 0

    print(f"2. 担当講師一致率 (平均): {avg_consistency:.1f}%")
    print("=" * 40)

    # --- 3. ブース使用率の偏り (Booth Usage) ---
    # -1 (Regular) は除外されているため、0~9のみが出るはず
    booth_counts = df["Booth"].value_counts().sort_index()
    print("3. ブース使用状況:")
    print(booth_counts.to_string())
    std_dev = booth_counts.std()
    print(f"\n   -> バラつき(StdDev): {std_dev:.2f}")
    print("=" * 40)

    # --- 4. 授業間隔の評価 (Interval Check) ---
    valid_intervals = 0
    total_intervals = 0

    for (student, subject), group in grouped:
        if len(group) <= 1:
            continue
        # 日付順にソート
        sorted_days = group.sort_values("DayIdx")["DayIdx"].values
        intervals = np.diff(sorted_days)

        for interval in intervals:
            total_intervals += 1
            if 5 <= interval <= 10:
                valid_intervals += 1

    interval_score = (
        (valid_intervals / total_intervals * 100) if total_intervals > 0 else 0
    )

    print(f"4. 授業間隔遵守率 (5-10日): {interval_score:.1f}%")
    print("=" * 40)


if __name__ == "__main__":
    evaluate_schedule()
