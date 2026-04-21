# C:\Users\kaito\Desktop\time\src\evaluator.py
from typing import List, Dict, Set
from src.models import (
    Student,
    Teacher,
    Slot,
    Subject,
    SeasonalLessonCandidate,
    LessonType,
)


class ScheduleEvaluator:
    """
    作成されたスケジュール（候補リスト）の良し悪しを数値化（スコアリング）するクラス
    Soft Constraints（努力目標）を評価する。
    """

    # --- 重み付け（この数字を変えればAIの性格が変わる） ---
    WEIGHT_TEACHER_MATCH = 20  # 同じ先生なら加点
    WEIGHT_GOOD_TIME = 10  # 3~8限なら加点
    WEIGHT_BAD_TIME = -10  # 1~2限なら減点
    WEIGHT_INTERVAL_OK = 30  # 間隔が5~10日なら加点
    WEIGHT_INTERVAL_BAD = -20  # 間隔が近すぎ/遠すぎなら減点
    WEIGHT_SUBJECT_DISTRIBUTION = 10  # 違う科目がバラけていれば加点

    def __init__(self, current_schedule: List[SeasonalLessonCandidate]):
        self.schedule = current_schedule

    def calculate_total_score(
        self, students: Dict[str, Student], teachers: Dict[str, Teacher]
    ) -> int:
        """
        スケジュール全体のスコアを計算する
        """
        total_score = 0

        # 生徒ごとに評価する
        for student_id, student in students.items():
            # この生徒に関連する講習だけを抽出
            my_lessons = [l for l in self.schedule if l.student_id == student_id]
            if not my_lessons:
                continue

            total_score += self._evaluate_student_schedule(
                student, my_lessons, teachers
            )

        return total_score

    def _evaluate_student_schedule(
        self,
        student: Student,
        lessons: List[SeasonalLessonCandidate],
        teachers: Dict[str, Teacher],
    ) -> int:
        score = 0

        # 授業ごとの単体評価
        # 科目ごとの授業日リスト（間隔チェック用）
        subject_dates: Dict[Subject, List[int]] = {}

        for lesson in lessons:
            if lesson.assigned_slot is None or lesson.teacher_id is None:
                score -= 100  # 未割り当ては論外の大減点
                continue

            # 1. 時間帯評価 (3~8限は偉い)
            if 3 <= lesson.assigned_slot.period <= 8:
                score += self.WEIGHT_GOOD_TIME
            else:
                score += self.WEIGHT_BAD_TIME

            # 2. 担当講師の一貫性 (レギュラーと同じ先生か？)
            # レギュラーでその科目を習っているか確認
            # (簡易実装: レギュラー情報の辞書を検索)
            # ※本来は「過去の担当履歴」なども見たいが、今は「レギュラー優先」で
            is_same_teacher = False
            for slot, (t_id, subj) in student.regular_schedule.items():
                if subj == lesson.subject and t_id == lesson.teacher_id:
                    is_same_teacher = True
                    break

            if is_same_teacher:
                score += self.WEIGHT_TEACHER_MATCH

            # 科目ごとの日付記録
            if lesson.subject not in subject_dates:
                subject_dates[lesson.subject] = []
            subject_dates[lesson.subject].append(lesson.assigned_slot.day_idx)

        # 3. 間隔評価 (同じ科目は5日以上空けたい)
        # ※今回は「日数の差」だけで見る（月を跨ぐケースは簡易化して無視）
        for subj, days in subject_dates.items():
            days.sort()
            for i in range(len(days) - 1):
                interval = days[i + 1] - days[i]
                if 5 <= interval <= 10:
                    score += self.WEIGHT_INTERVAL_OK
                else:
                    score += self.WEIGHT_INTERVAL_BAD

        # 4. 科目の分散 (同じ日に違う科目を入れるのはOKだが、同じ科目の連続はNG)
        # 今回のモデルでは「1日1回」制約はないので、同日連続をチェックしてもいい

        return score
