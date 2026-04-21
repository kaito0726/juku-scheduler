# C:\Users\kaito\Desktop\time\generate_and_run.py
import random
import pandas as pd
from src.models import Student, Teacher, Slot, Subject
from src.solver import SimpleSolver

# 追加: optimizerをインポート
from src.optimizer import HillClimbingOptimizer
from tqdm import tqdm

# --- 設定 ---
NUM_STUDENTS = 80
NUM_TEACHERS = 15
DAYS_RANGE = 28
SEASONAL_ATTENDANCE_RATE = 0.85  # 追加: 講習受講率 (85%の生徒が受講)


SUBJECTS = [
    Subject.MATH,
    Subject.ENGLISH,
    Subject.SCIENCE,
    Subject.JAPANESE,
    Subject.SOCIAL,
]


def generate_large_dataset():
    print(f">>> Generating Mock Data with ~300 lessons target...")

    # --- 1. 講師生成 ---
    teachers = {}
    for i in range(1, NUM_TEACHERS + 1):
        t_id = f"T{i:02d}"
        my_subjects = set(random.sample(SUBJECTS, k=random.randint(2, 3)))
        unavailable = set()
        fixed = {}
        for d in range(DAYS_RANGE):
            if d % 7 == (i % 7):  # 週1回休み
                for p in range(1, 9):
                    unavailable.add(Slot(d, p))
            else:
                for p in range(1, 9):  # レギュラー授業
                    if random.random() < 0.2:
                        fixed[Slot(d, p)] = (
                            "ExistingStudent",
                            random.choice(list(my_subjects)),
                        )

        teachers[t_id] = Teacher(
            t_id, f"Teacher_{t_id}", my_subjects, unavailable, fixed
        )

    # --- 2. 生徒生成 ---
    students = {}
    for i in range(1, NUM_STUDENTS + 1):
        s_id = f"S{i:03d}"
        grade = random.choice([1, 2, 3])
        req_counts = {}

        # ★調整ポイント: 受講率と科目数・コマ数を減らす
        if random.random() < SEASONAL_ATTENDANCE_RATE:
            # 科目数を 1〜2 に制限 (以前は 1~3)
            target_subjs = random.sample(SUBJECTS, k=random.randint(1, 2))
            for subj in target_subjs:
                # コマ数を 2 or 4 に制限 (以前は 2,4,6)
                req_counts[subj] = random.choice([2, 4])

        unavailable = set()
        for d in range(DAYS_RANGE):
            if d % 7 < 5 and random.random() < 0.3:  # 部活
                unavailable.add(Slot(d, 6))
                unavailable.add(Slot(d, 7))
                unavailable.add(Slot(d, 8))

        students[s_id] = Student(
            s_id, f"Student_{s_id}", grade, set(), unavailable, req_counts, {}
        )

    return students, teachers


def save_to_csv(results, teachers, filename="schedule.csv"):
    """
    修正版: ブース番号を自然な数値（1始まり）に変換して保存する
    """
    data = []
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # 講習データの処理
    for res in results:
        day_idx = res.assigned_slot.day_idx

        # 修正1: 内部の0始まりのIDに +1 して、1始まりにする
        # (例: 0 -> 1, 9 -> 10)
        booth_display_id = res.assigned_group_id + 1

        data.append(
            {
                "DayIdx": day_idx,
                "Date": f"Day{day_idx + 1}({week_days[day_idx % 7]})",
                "Period": res.assigned_slot.period,
                "Student": res.student_id,
                "Subject": res.subject.value,
                "Teacher": res.teacher_id,
                "Booth": booth_display_id,  # 修正済み
                "Type": "Seasonal",
            }
        )

    # レギュラー授業データの処理
    for t_id, teacher in teachers.items():
        for slot, (info, subj) in teacher.fixed_schedule.items():
            if slot.day_idx >= DAYS_RANGE:
                continue

            # 修正2: -1 ではなく、1〜10 の適当なブース番号を割り当てる
            # (レギュラーは場所が決まっているはずなので、ダミーとして割り振る)
            dummy_booth_id = random.randint(1, 10)

            data.append(
                {
                    "DayIdx": slot.day_idx,
                    "Date": f"Day{slot.day_idx + 1}({week_days[slot.day_idx % 7]})",
                    "Period": slot.period,
                    "Student": f"Reg({info})",
                    "Subject": subj.value if isinstance(subj, Subject) else subj,
                    "Teacher": t_id,
                    "Booth": dummy_booth_id,  # 修正済み
                    "Type": "Regular",
                }
            )

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values(["DayIdx", "Period", "Teacher"])
        df.to_csv(filename, index=False)
        print(f">>> Saved to {filename} (Booths are now 1-indexed)")
    else:
        print(">>> No schedule data to save.")


def main():
    # 1. データ生成
    students, teachers = generate_large_dataset()
    total_lessons = sum(
        [sum(s.required_seasonal_counts.values()) for s in students.values()]
    )
    print(f">>> Target: {total_lessons} seasonal lessons.")

    # 2. 初期解の生成 (SimpleSolver)
    print("\n--- Phase 1: Initial Solution (Greedy) ---")
    solver = SimpleSolver(students, teachers)
    initial_results = solver.solve(day_range=DAYS_RANGE)
    print(f">>> Assigned: {len(initial_results)} / {total_lessons}")

    # 初期解をCSV保存
    save_to_csv(initial_results, teachers, "schedule_initial.csv")

    # 3. 最適化 (Hill Climbing)
    print("\n--- Phase 2: Optimization (Hill Climbing) ---")
    optimizer = HillClimbingOptimizer(
        students=students, teachers=teachers, initial_solution=initial_results
    )

    # 実行 (50000回試行)
    optimized_results = optimizer.run(iterations=500000)

    # 4. 最適化後の結果をCSV保存
    save_to_csv(optimized_results, teachers, "schedule_optimized.csv")

    # 結果のチラ見せ
    print("\n>>> Optimization Finished. Top 5 assignments:")
    for res in optimized_results[:5]:
        print(
            f"  {res.student_id} | {res.subject.value} | {res.assigned_slot} | {res.teacher_id}"
        )


if __name__ == "__main__":
    main()
