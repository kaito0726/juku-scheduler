# C:\Users\kaito\Desktop\time\src\models.py
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

# --- 定数・Enum ---
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PERIODS = list(range(1, 9))  # 1限〜8限
TOTAL_BOOTHS = 30
GROUP_SIZE = 3  # 3個で1セット


class Subject(str, Enum):
    MATH = "Math"
    ENGLISH = "English"
    SCIENCE = "Science"
    JAPANESE = "Japanese"
    SOCIAL = "Social"


class LessonType(Enum):
    REGULAR = "Regular"
    SEASONAL = "Seasonal"


# --- データモデル ---


@dataclass(frozen=True)
class Slot:
    day_idx: int
    period: int

    def __repr__(self):
        # ★修正箇所: 7日目以降もエラーにならないように % 7 で曜日を循環させる
        # day_idx が 7 なら DAYS[0] (Mon) になる
        day_name = DAYS[self.day_idx % 7]
        return f"Day{self.day_idx + 1}({day_name})-{self.period}限"


@dataclass
class BoothGroup:
    """3つのブースをまとめた1つの島クラス"""

    group_id: int  # 0 ~ 9 (全10グループ)
    booth_ids: List[int]  # 例: [1, 2, 3]

    def __repr__(self):
        return f"BoothGroup-{self.group_id}(Booths:{self.booth_ids})"


@dataclass
class ClassroomState:
    """
    ある瞬間（Slot）の教室の状態を管理する。
    Key: group_id, Value: (TeacherID, [StudentIDs])
    """

    usage: Dict[int, Tuple[Optional[str], List[str]]] = field(default_factory=dict)

    def is_group_free(self, group_id: int) -> bool:
        return group_id not in self.usage

    def can_teacher_enter(self, group_id: int, teacher_id: str) -> bool:
        if group_id not in self.usage:
            return True
        current_teacher, _ = self.usage[group_id]
        return current_teacher == teacher_id

    def get_remaining_seats(self, group_id: int) -> int:
        if group_id not in self.usage:
            return 2

        _, students = self.usage[group_id]
        current_count = len(students)

        if current_count == 2:
            return 1
        elif current_count < 2:
            return 2 - current_count
        else:
            return 0


@dataclass
class Teacher:
    id: str
    name: str
    can_teach_subjects: Set[Subject]
    unavailable_slots: Set[Slot]
    fixed_schedule: Dict[Slot, Tuple[str, Subject]] = field(default_factory=dict)

    def is_available(self, slot: Slot) -> bool:
        if slot in self.unavailable_slots:
            return False
        if slot in self.fixed_schedule:
            return False
        return True


@dataclass
class Student:
    id: str
    name: str
    grade: int
    ng_teachers: Set[str]
    unavailable_slots: Set[Slot]
    required_seasonal_counts: Dict[Subject, int]
    regular_schedule: Dict[Slot, Tuple[str, Subject]] = field(default_factory=dict)

    def is_available(self, slot: Slot) -> bool:
        if slot in self.unavailable_slots:
            return False
        if slot in self.regular_schedule:
            return False
        return True


@dataclass
class SeasonalLessonCandidate:
    student_id: str
    subject: Subject
    teacher_id: Optional[str] = None
    assigned_slot: Optional[Slot] = None
    assigned_group_id: Optional[int] = None
