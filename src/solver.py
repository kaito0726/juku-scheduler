# C:\Users\kaito\Desktop\time\src\solver.py
import random
from collections import defaultdict
from typing import List, Dict, Optional, Set, Tuple
from src.models import (
    Student,
    Teacher,
    Slot,
    Subject,
    SeasonalLessonCandidate,
    ClassroomState,
)
from src.validator import ScheduleValidator


class SimpleSolver:
    def __init__(self, students: Dict[str, Student], teachers: Dict[str, Teacher]):
        self.students = students
        self.teachers = teachers
        self.classroom_states: Dict[Slot, ClassroomState] = {}
        self.temp_busy_registry: Set[Tuple[str, Slot]] = set()
        # 今回はシーケンシャルに処理するので、メソッド内でローカルにlast_dayを持てば良いが、
        # 念のためクラス変数としても互換性を保つ
        self.context_memory: Dict[Tuple[str, Subject], Dict] = {}

    def _get_classroom_state(self, slot: Slot) -> ClassroomState:
        if slot not in self.classroom_states:
            self.classroom_states[slot] = ClassroomState()
        return self.classroom_states[slot]

    def _is_person_busy_in_temp(self, person_id: str, slot: Slot) -> bool:
        return (person_id, slot) in self.temp_busy_registry

    def solve(self, day_range: int = 28) -> List[SeasonalLessonCandidate]:
        results: List[SeasonalLessonCandidate] = []

        # --- 戦略変更: 生徒x科目ごとにグループ化し、回数の多い順に処理する ---
        # 理由: コマ数が多い科目ほどスケジューリングが難しい（間隔確保のため）ので、先に場所を確保する。

        requests_map = defaultdict(list)
        for s_id, student in self.students.items():
            for subj, count in student.required_seasonal_counts.items():
                requests_map[(s_id, subj)] = count

        # コマ数が多い順にソート（同じならランダム）
        sorted_requests = sorted(
            requests_map.items(), key=lambda x: (x[1], random.random()), reverse=True
        )

        print(
            f">>> Solving SEQUENTIALLY (Interval > Time >>> Teacher) for {len(sorted_requests)} groups..."
        )

        for (s_id, subj), count in sorted_requests:
            # この生徒・科目の授業を 1回目から順に埋めていく
            # コンテキスト（前回の授業日）をリセット
            last_day = -1
            # レギュラー授業があれば、その最終日を初期値にする戦略もありだが、
            # 今回は「講習は講習」として、講習間の間隔を最重視する

            for i in range(count):
                # i: 0始まりの回数 (0=1回目, 1=2回目...)
                candidate = self._assign_single_lesson(
                    s_id,
                    subj,
                    results,
                    day_range,
                    last_day,
                    lesson_index=i,
                    total_lessons=count,
                )

                if candidate:
                    results.append(candidate)
                    last_day = candidate.assigned_slot.day_idx

                    # メモリにも記録（念のため）
                    mem = self.context_memory.get(
                        (s_id, subj), {"last_day": -1, "teacher_id": None}
                    )
                    mem["teacher_id"] = candidate.teacher_id
                    mem["last_day"] = last_day
                    self.context_memory[(s_id, subj)] = mem
                else:
                    # 割り当て失敗（ログだけ出して次へ）
                    # print(f"Failed to assign {s_id} {subj} #{i+1}")
                    pass

        return results

    def _assign_single_lesson(
        self,
        student_id: str,
        subject: Subject,
        current_results: List[SeasonalLessonCandidate],
        day_range: int,
        last_day: int,
        lesson_index: int,
        total_lessons: int,
    ) -> Optional[SeasonalLessonCandidate]:

        student = self.students[student_id]

        # 1. いつもの先生特定 (レギュラー or 直前)
        preferred_tid = None
        mem = self.context_memory.get((student_id, subject))
        if mem and mem["teacher_id"]:
            preferred_tid = mem["teacher_id"]
        else:
            for slot, (t_id, subj) in student.regular_schedule.items():
                if subj == subject:
                    preferred_tid = t_id
                    break

        # 2. 講師リスト (全員)
        all_potential_teachers = [
            t
            for t in self.teachers.values()
            if subject in t.can_teach_subjects and t.id not in student.ng_teachers
        ]
        random.shuffle(all_potential_teachers)

        pref_teachers = [t for t in all_potential_teachers if t.id == preferred_tid]
        other_teachers = [t for t in all_potential_teachers if t.id != preferred_tid]

        # 3. スロット戦略 (ここが最重要)
        ideal_days = []
        other_days = []

        if last_day == -1:
            # --- 初回授業の配置戦略 ---
            # 全体の回数に応じて、スタート地点を制限する
            # 例: 4回やるなら、最初の1回目は早めにやらないと物理的に詰む

            # 残り日数 / 残り回数 で大体のペース配分
            # しかし厳密すぎると失敗するので、ある程度幅を持たせる

            # シンプルな戦略:
            # 「Day 0 〜 (DayRange - 残り回数*5)」くらいまでに始めたい
            limit_day = day_range - ((total_lessons - 1) * 5)
            if limit_day < 5:
                limit_day = 5  # 最低でも5日分は猶予

            for d in range(day_range):
                if d <= limit_day:
                    ideal_days.append(d)
                else:
                    other_days.append(d)
        else:
            # --- 2回目以降の配置戦略 ---
            # 前回 + 5日〜10日
            for d in range(day_range):
                interval = d - last_day
                if 5 <= interval <= 10:
                    ideal_days.append(d)
                else:
                    if d > last_day:  # 過去には戻らない
                        other_days.append(d)

        # 時間帯定義
        good_periods = list(range(3, 9))  # 3~8限
        bad_periods = [1, 2]  # 1~2限

        def make_slots(days, periods):
            s = [Slot(d, p) for d in days for p in periods]
            random.shuffle(s)
            return s

        # --- フェーズ定義 (優先順位の具現化) ---
        # 要望: 間隔(Interval) > 時間(Time) >>> 講師(Teacher)

        phases = []

        # 1. [最高] 理想間隔 & 良い時間 & いつもの先生
        if pref_teachers:
            phases.append((pref_teachers, make_slots(ideal_days, good_periods)))

        # 2. [本命] 理想間隔 & 良い時間 & 違う先生 (先生妥協)
        if other_teachers:
            phases.append((other_teachers, make_slots(ideal_days, good_periods)))

        # 3. [時間妥協] 理想間隔 & 悪い時間(1-2限) & 全先生 (時間妥協してでも間隔を守る)
        phases.append((all_potential_teachers, make_slots(ideal_days, bad_periods)))

        # --- ここから「間隔」を守れない敗北ルート ---

        # 4. [間隔妥協] 間隔無視(広すぎ/狭すぎ) & 良い時間 & 全先生
        phases.append((all_potential_teachers, make_slots(other_days, good_periods)))

        # 5. [全妥協] 間隔無視 & 悪い時間 & 全先生
        phases.append((all_potential_teachers, make_slots(other_days, bad_periods)))

        # --- 実行 ---
        for teachers_list, slots_list in phases:
            if not teachers_list or not slots_list:
                continue

            for teacher in teachers_list:
                for slot in slots_list:
                    if self._is_person_busy_in_temp(student.id, slot):
                        continue
                    if self._is_person_busy_in_temp(teacher.id, slot):
                        continue

                    is_valid_basic, _ = ScheduleValidator.check_basic_rules(
                        student, teacher, subject, slot
                    )
                    if not is_valid_basic:
                        continue

                    current_state = self._get_classroom_state(slot)
                    # ブース選びもランダムにして分散させる
                    groups = list(range(10))
                    random.shuffle(groups)

                    for group_id in groups:
                        is_valid_room, _ = ScheduleValidator.check_classroom_rules(
                            current_state, group_id, teacher.id
                        )

                        if is_valid_room:
                            cand = SeasonalLessonCandidate(
                                student_id, subject, teacher.id, slot, group_id
                            )
                            self._commit_assignment(cand)
                            return cand
        return None

    def _commit_assignment(self, assignment: SeasonalLessonCandidate):
        slot = assignment.assigned_slot
        state = self._get_classroom_state(slot)

        gid = assignment.assigned_group_id
        tid = assignment.teacher_id
        sid = assignment.student_id

        if gid not in state.usage:
            state.usage[gid] = (tid, [sid])
        else:
            current_tid, students = state.usage[gid]
            students.append(sid)
            state.usage[gid] = (current_tid, students)

        self.temp_busy_registry.add((sid, slot))
        self.temp_busy_registry.add((tid, slot))
