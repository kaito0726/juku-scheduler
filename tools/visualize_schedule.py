# C:\Users\kaito\Desktop\time\tools\visualize_schedule.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def visualize_schedule(csv_path="schedule_optimized.csv"):
    # CSV読み込み
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("Error: CSV file not found.")
        return

    # データを扱いやすい形に整形
    # Pivot Table: 行=講師, 列=日付(DayIdx), 値=件数または生徒名
    # ※シンプルにするため、ここでは「その日に何コマ入ってるか」をヒートマップにする

    # 講師×日付のクロス集計
    pivot_df = df.pivot_table(
        index="Teacher",
        columns="DayIdx",
        values="Period",
        aggfunc="count",  # コマ数をカウント
        fill_value=0,
    )

    # 描画サイズ設定
    plt.figure(figsize=(20, 10))

    # ヒートマップ描画
    sns.heatmap(pivot_df, annot=True, fmt="d", cmap="YlGnBu", cbar=False)

    plt.title("Teacher's Daily Load (Lessons per Day)")
    plt.xlabel("Day Index (0-27)")
    plt.ylabel("Teacher ID")

    # 画像保存
    plt.savefig("schedule_heatmap.png")
    print(">>> Saved visualization to 'schedule_heatmap.png'")


if __name__ == "__main__":
    visualize_schedule()
