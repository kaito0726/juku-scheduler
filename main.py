import pandas as pd
from typing import Dict, Set
from src.models import Student, Teacher, Slot, Subject, DAYS
from src.solver import SimpleSolver


# --- ダミーデータ生成関数 ---
def create_mock_data():
    print(">>> Creating mock data...")

    # 1. 講師データ
    # 佐藤: 英語・数学担当。月曜1限はレギュラーで埋まっている。
    t_sato = Teacher(
        id="Sato",
        name="Sato",
        can_teach_subjects={Subject.MATH, Subject.ENGLISH},
        unavailable_slots=set(),
        fixed_schedule={Slot(0, 1): ("StudentA", Subject.MATH)},  # 月曜1限はNG
    )

    # 鈴木: 理科・社会担当。火曜日は全休。
    t_suzuki = Teacher(
        id="Suzuki",
        name="Suzuki",
        can_teach_subjects={Subject.SCIENCE, Subject.SOCIAL},
        unavailable_slots={Slot(1, p) for p in range(1, 9)},  # 火曜NG
        fixed_schedule={},
    )

    teachers = {"Sato": t_sato, "Suzuki": t_suzuki}

    # 2. 生徒データ
    # 田中君: 数学を4コマとりたい。佐藤先生希望（レギュラーなし）。
    s_tanaka = Student(
        id="Tanaka",
        name="Tanaka",
        grade=3,
        ng_teachers=set(),
        unavailable_slots={Slot(0, 1)},  # 月曜1限は来れない
        required_seasonal_counts={Subject.MATH: 4},
        regular_schedule={},
    )

    # 山田さん: 英語2コマ、理科2コマ。鈴木先生はNG。
    s_yamada = Student(
        id="Yamada",
        name="Yamada",
        grade=2,
        ng_teachers={"Suzuki"},  # 鈴木先生NG
        unavailable_slots=set(),
        required_seasonal_counts={Subject.ENGLISH: 2, Subject.SCIENCE: 2},
        regular_schedule={},
    )

    students = {"Tanaka": s_tanaka, "Yamada": s_yamada}

    return students, teachers


# --- メイン処理 ---
def main():
    # 1. データ準備
    students, teachers = create_mock_data()

    # 2. ソルバー初期化 & 実行
    solver = SimpleSolver(students, teachers)
    results = solver.solve()

    # 3. 結果表示 & CSV出力
    print(f"\n>>> Scheduled {len(results)} lessons.")

    data = []
    for res in results:
        day_str = DAYS[res.assigned_slot.day_idx]
        period = res.assigned_slot.period

        print(
            f"[{day_str} {period}限] {res.student_id} : {res.subject.value} ({res.teacher_id}) @ Booth-{res.assigned_group_id}"
        )

        data.append(
            {
                "Student": res.student_id,
                "Subject": res.subject.value,
                "Teacher": res.teacher_id,
                "Day": day_str,
                "Period": period,
                "BoothGroup": res.assigned_group_id,
            }
        )

    # CSV保存
    if data:
        df = pd.DataFrame(data)
        # 曜日・時限で見やすくソート
        df["DayIdx"] = df["Day"].apply(lambda x: DAYS.index(x))
        df = df.sort_values(["DayIdx", "Period", "Teacher"])

        filename = "final_schedule.csv"
        df.to_csv(filename, index=False)
        print(f"\n>>> Saved to {filename}")
    else:
        print(">>> No schedule created.")


if __name__ == "__main__":
    main()
