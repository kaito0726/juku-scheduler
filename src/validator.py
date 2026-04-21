# C:\Users\kaito\Desktop\time\src\validator.py
from typing import List, Tuple
from src.models import Student, Teacher, Slot, Subject, ClassroomState


class ScheduleValidator:
    """
    スケジュールが「ルール違反」していないか判定するクラス
    Soft Constraints（努力目標）ではなく、Hard Constraints（絶対ルール）のみをチェックする。
    """

    @staticmethod
    def check_basic_rules(
        student: Student, teacher: Teacher, subject: Subject, slot: Slot
    ) -> Tuple[bool, str]:
        """
        人・時間・科目の基本ルールをチェックする
        Returns: (is_ok, error_message)
        """
        # 1. 生徒のスケジュール確認
        if not student.is_available(slot):
            return False, f"Student {student.name} is busy at {slot}"

        # 2. 生徒のNG講師確認
        if teacher.id in student.ng_teachers:
            return False, f"Teacher {teacher.name} is NG for student {student.name}"

        # 3. 講師のスケジュール確認
        if not teacher.is_available(slot):
            return False, f"Teacher {teacher.name} is busy at {slot}"

        # 4. 講師の指導可能科目確認
        if subject not in teacher.can_teach_subjects:
            return False, f"Teacher {teacher.name} cannot teach {subject}"

        return True, ""

    @staticmethod
    def check_classroom_rules(
        classroom_state: ClassroomState, group_id: int, teacher_id: str
    ) -> Tuple[bool, str]:
        """
        場所（ブース・島）のルールをチェックする
        """
        # 1. 縄張りチェック（その島は別の先生が使っていないか？）
        if not classroom_state.can_teacher_enter(group_id, teacher_id):
            # 既に別の先生がいる
            # 安全のため get で取得し、Noneチェックを行う
            usage = classroom_state.usage.get(group_id)
            if usage:
                current_owner, _ = usage
                return False, f"Group {group_id} is occupied by {current_owner}"
            return False, f"Group {group_id} is occupied (Unknown error)"

        # 2. 定員チェック（座れる椅子はあるか？）
        remaining = classroom_state.get_remaining_seats(group_id)
        if remaining <= 0:
            return False, f"Group {group_id} is full"

        return True, ""

    @staticmethod
    def find_valid_slots(
        student: Student, teacher: Teacher, subject: Subject, all_slots: List[Slot]
    ) -> List[Slot]:
        """
        このペアで授業可能な時間のリストを返す便利関数
        （場所の空き状況はここでは考慮しない＝まずは人と時間だけで絞り込む）
        """
        candidates = []
        for slot in all_slots:
            is_ok, _ = ScheduleValidator.check_basic_rules(
                student, teacher, subject, slot
            )
            if is_ok:
                candidates.append(slot)
        return candidates
