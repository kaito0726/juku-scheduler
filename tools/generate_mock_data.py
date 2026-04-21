# C:\Users\kaito\Desktop\time\tools\generate_mock_data.py
import pandas as pd
import random
import os

# --- 設定 ---
TEACHERS = ["Sato", "Suzuki", "Takahashi", "Tanaka", "Ito"]
DAYS = list(range(6))  # 月〜土 (日曜は休みとする想定)
PERIODS = list(range(1, 8))  # 1限〜7限
FILL_RATE = 0.4  # レギュラー授業の埋まり具合 (40%が埋まっているとする)

OUTPUT_DIR = "data"
OUTPUT_FILE = "regular_schedule.csv"


def generate_mock_regular_data():
    data = []

    print(f">>> Generating mock data for {len(TEACHERS)} teachers...")

    for teacher in TEACHERS:
        for d in DAYS:
            for p in PERIODS:
                # 確率でレギュラー授業を入れる
                if random.random() < FILL_RATE:
                    subject = random.choice(["Math", "Eng", "Sci", "Jpn"])
                    student_id = random.randint(100, 999)

                    data.append(
                        {
                            "teacher_id": teacher,
                            "day": d,
                            "period": p,
                            "subject": f"{subject}_{student_id}",
                        }
                    )

    # DataFrame化
    df = pd.DataFrame(data)

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    df.to_csv(file_path, index=False)

    print(f">>> Success! Generated {len(df)} regular slots.")
    print(f">>> Saved to: {file_path}")

    # 中身を少し表示
    print("\n[Preview]")
    print(df.head())


if __name__ == "__main__":
    generate_mock_regular_data()
