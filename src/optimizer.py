import random
import copy
from collections import defaultdict
from typing import List, Dict, Tuple, Set
from tqdm import tqdm  # プログレスバー用
from src.models import (
    Student,
    Teacher,
    Slot,
    SeasonalLessonCandidate,
    ClassroomState,
    Subject,
)

# --- ハイパーパラメータ（報酬の重み） ---
SCORE_INTERVAL_IDEAL = 30  # 5~10日間隔
SCORE_INTERVAL_OK = 0  # 4日 or 11~14日
SCORE_INTERVAL_BAD = -100  # 3日以内（詰め込みすぎ） or 15日以上
SCORE_TIME_LATE = 30  # 3限以降（夕方）
SCORE_TIME_EARLY = -200  # 1-2限
SCORE_SAME_TEACHER = 30  # 同じ講師
SCORE_TEACHER_CHANGE = -5  # 講師変更

# ★追加: 空きコマ（中空き）へのペナルティ
SCORE_TEACHER_GAP = -300  # 1コマ空くごとに減点


class HillClimbingOptimizer:
    def __init__(
        self,
        students: Dict[str, Student],
        teachers: Dict[str, Teacher],
        initial_solution: List[SeasonalLessonCandidate],
    ):
        self.students = students
        self.teachers = teachers
        # 現在の解（ディープコピーして元データを破壊しないようにする）
        self.current_solution = copy.deepcopy(initial_solution)
        # 高速化のために「誰がいつ忙しいか」のキャッシュを作成
        self._rebuild_cache()

    def _rebuild_cache(self):
        """
        現在の解(self.current_solution)をもとに、
        - 講師の予定
        - 生徒の予定
        - 教室(ブース)の使用状況
        を再構築する。
        """
        self.teacher_schedule: Dict[
            Tuple[str, int, int], bool
        ] = {}  # (tid, day, period) -> busy
        self.student_schedule: Dict[
            Tuple[str, int, int], bool
        ] = {}  # (sid, day, period) -> busy
        self.classroom_states: Dict[
            Tuple[int, int], ClassroomState
        ] = {}  # (day, period) -> State

        for cand in self.current_solution:
            slot = cand.assigned_slot
            if not slot:
                continue

            # 生徒・講師の埋まり状況
            self.teacher_schedule[(cand.teacher_id, slot.day_idx, slot.period)] = True
            self.student_schedule[(cand.student_id, slot.day_idx, slot.period)] = True

            # 教室状況
            state_key = (slot.day_idx, slot.period)
            if state_key not in self.classroom_states:
                self.classroom_states[state_key] = ClassroomState()

            state = self.classroom_states[state_key]

            # ClassroomStateの更新ロジック (models.py準拠)
            gid = cand.assigned_group_id
            if gid not in state.usage:
                state.usage[gid] = (cand.teacher_id, [cand.student_id])
            else:
                tid, s_list = state.usage[gid]
                s_list.append(cand.student_id)
                state.usage[gid] = (tid, s_list)

    def calculate_score(self) -> float:
        """
        現在の解の「良さ」を数値化する（報酬関数）
        ※平均点方式（正規化）バージョン
        """

        # --- 集計用データの準備 ---
        student_subject_map = defaultdict(list)
        # 修正: intではなくlistで時限を保持する
        teacher_daily_periods = defaultdict(list)

        for cand in self.current_solution:
            student_subject_map[(cand.student_id, cand.subject)].append(cand)
            if cand.teacher_id:
                # (講師ID, 日付) -> [1, 3, 4] のように時限を追加
                teacher_daily_periods[
                    (cand.teacher_id, cand.assigned_slot.day_idx)
                ].append(cand.assigned_slot.period)

        # ==========================================
        # A. 生徒視点のスコア (合計)
        # ==========================================
        raw_student_score = 0

        for (sid, subj), lessons in student_subject_map.items():
            lessons.sort(key=lambda x: x.assigned_slot.day_idx)

            # 1. 講師の一貫性
            teacher_ids = set(l.teacher_id for l in lessons)
            if len(teacher_ids) == 1:
                raw_student_score += SCORE_SAME_TEACHER * len(lessons)
            else:
                raw_student_score += SCORE_TEACHER_CHANGE * len(lessons)

            # 2. 授業ごとの評価
            for i, lesson in enumerate(lessons):
                slot = lesson.assigned_slot

                # 時間帯
                if slot.period >= 3:
                    raw_student_score += SCORE_TIME_LATE
                else:
                    raw_student_score += SCORE_TIME_EARLY

                # 間隔
                if i > 0:
                    prev_slot = lessons[i - 1].assigned_slot
                    interval = slot.day_idx - prev_slot.day_idx

                    if 5 <= interval <= 10:
                        raw_student_score += SCORE_INTERVAL_IDEAL
                    elif interval < 3 or interval > 14:
                        raw_student_score += SCORE_INTERVAL_BAD
                    else:
                        raw_student_score += SCORE_INTERVAL_OK

        # ==========================================
        # B. 講師視点のスコア (合計)
        # ==========================================
        raw_teacher_score = 0

        # あなたが設定したカスタム評価値
        LOAD_SCORES = {
            1: -400,  # 1コマ出勤は絶対嫌
            2: 30,
            3: 60,  # 最高
            4: 30,
            5: -30,
            6: -600,  # かなりきつい
            7: -2500,  # ブラック
            8: -30000,  # 違法レベル
        }

        for (tid, day), periods in teacher_daily_periods.items():
            # 時限をソート (例: [1, 3, 4])
            periods.sort()
            count = len(periods)

            # 1. コマ数による評価 (既存)
            score = LOAD_SCORES.get(count, -100)
            raw_teacher_score += score

            # 2. ★追加: 空きコマ（中空き）チェック
            if count > 1:
                # 最初の授業から最後の授業までのスパン
                # 例: [1, 3, 4] -> 4 - 1 + 1 = 4スパン
                span = periods[-1] - periods[0] + 1

                # スパンの中に授業がない部分がいくつあるか
                # 例: スパン4 - 実働3 = 空きコマ1
                num_gaps = span - count

                if num_gaps > 0:
                    raw_teacher_score += num_gaps * SCORE_TEACHER_GAP

        # ==========================================
        # C. 正規化（平均点の算出）
        # ==========================================

        # 生徒スコアの平均（リクエスト数で割る）
        num_student_requests = max(1, len(student_subject_map))
        avg_student_score = raw_student_score / num_student_requests

        # 講師スコアの平均（全講師数で割る）
        num_teachers = max(1, len(self.teachers))
        avg_teacher_score = raw_teacher_score / num_teachers

        return avg_student_score + avg_teacher_score

    def run(self, iterations: int = 1000):
        """
        山登り法を実行する
        """
        current_score = self.calculate_score()
        print(f"Initial Score: {current_score}")

        # tqdm で進捗を表示
        for i in tqdm(range(iterations), desc="Optimizing", unit="step"):
            # 1. ランダムに変更対象を選ぶ
            target_idx = random.randint(0, len(self.current_solution) - 1)
            target_lesson = self.current_solution[target_idx]

            # 元の状態をバックアップ
            original_slot = target_lesson.assigned_slot
            original_group = target_lesson.assigned_group_id

            # 2. 新しいスロットをランダムに選ぶ (0~27日, 1~8限)
            new_day = random.randint(0, 27)
            new_period = random.randint(1, 8)
            new_slot = Slot(new_day, new_period)

            # 無駄な移動ならスキップ
            if new_day == original_slot.day_idx and new_period == original_slot.period:
                continue

            # 3. 制約チェック (Hard Constraints)
            # 移動先で生徒が空いているか？
            if (target_lesson.student_id, new_day, new_period) in self.student_schedule:
                continue  # 既に埋まってる

            # 移動先で講師が空いているか？
            if (target_lesson.teacher_id, new_day, new_period) in self.teacher_schedule:
                continue  # 既に埋まってる

            # 移動先の教室に空きがあるか？
            state_key = (new_day, new_period)
            if state_key not in self.classroom_states:
                # まだ誰もいない時間枠ならState新規作成してOK
                can_enter = True
                target_group = random.randint(0, 9)  # とりあえずランダムなグループ
            else:
                state = self.classroom_states[state_key]
                # 空いている、かつ同じ先生がいる(or空)ブースを探す
                valid_groups = []
                for g in range(10):  # 全10グループ
                    if state.can_teacher_enter(g, target_lesson.teacher_id):
                        if state.get_remaining_seats(g) > 0:
                            valid_groups.append(g)

                if not valid_groups:
                    continue  # 満席
                target_group = random.choice(valid_groups)

            # 4. 仮移動 (Try Move)
            target_lesson.assigned_slot = new_slot
            target_lesson.assigned_group_id = target_group

            new_score = self.calculate_score()

            # 5. 判定 (Hill Climbing Logic)
            if new_score > current_score:
                # 採用！ (Keep changes)
                current_score = new_score
                self._rebuild_cache()
            else:
                # 却下 (Revert)
                target_lesson.assigned_slot = original_slot
                target_lesson.assigned_group_id = original_group

        print(f"Final Score: {current_score}")
        return self.current_solution
