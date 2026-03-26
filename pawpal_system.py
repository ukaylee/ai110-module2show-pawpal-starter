"""Core domain models and scheduling logic for PawPal+.

This module defines:
- Task and Pet entities,
- Owner-level aggregation across pets,
- and a Scheduler that builds a constrained daily plan.
"""

from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Optional

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_FREQUENCIES = {"daily", "weekly", "monthly", "as needed"}
VALID_TIMES = {"morning", "afternoon", "evening", ""}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
FREQUENCY_ORDER = {"daily": 0, "weekly": 1, "monthly": 2, "as needed": 3}
TIME_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "": 3}


@dataclass
class Task:
    """A pet-care task with scheduling metadata and completion state."""

    description: str
    duration_minutes: int
    priority: str               # "low", "medium", "high"
    frequency: str              # "daily", "weekly", "monthly", "as needed"
    preferred_time: str = ""    # "morning", "afternoon", "evening", or ""
    start_time: str = ""        # "HH:MM" format, e.g. "08:30"
    completed: bool = False
    pet: Optional[Pet] = None   # back-reference set when added to a Pet

    def __post_init__(self):
        """Validate task fields at creation time."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be > 0")
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
        if self.frequency not in VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {VALID_FREQUENCIES}")
        if self.preferred_time not in VALID_TIMES:
            raise ValueError(f"preferred_time must be one of {VALID_TIMES}")

    def mark_complete(self) -> None:
        """Mark the task as completed and queue a fresh copy for daily/weekly tasks."""
        self.completed = True
        if self.frequency in ("daily", "weekly") and self.pet is not None:
            self.pet.add_task(replace(self, completed=False, pet=None))


@dataclass
class Pet:
    """A pet that owns a collection of care tasks."""

    name: str
    species: str                # "dog", "cat", "other"
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and enforce single-pet ownership."""
        if task.pet is not None and task.pet is not self:
            raise ValueError(f"Task '{task.description}' already belongs to {task.pet.name}")
        task.pet = self
        self.tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return a shallow copy of all tasks for safe external access."""
        return list(self.tasks)

    def get_pending_tasks(self) -> list[Task]:
        """Return tasks that are not yet completed."""
        return [t for t in self.tasks if not t.completed]


@dataclass
class Owner:
    """A pet owner that may manage multiple pets and their tasks."""

    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        """Flatten and return tasks from all owned pets."""
        return [task for pet in self.pets for task in pet.get_tasks()]

    def get_tasks_by_pet(self) -> dict[str, list[Task]]:
        """Return a mapping of pet name to that pet's tasks."""
        return {pet.name: pet.get_tasks() for pet in self.pets}


class Scheduler:
    """Build and explain a daily plan from pending tasks and constraints."""

    def __init__(
        self,
        owner: Owner,
        available_minutes: int,
        blackout_times: list[str] = None,
        max_tasks: int = 10,
    ):
        """Create a scheduler configured for one owner's planning window."""
        self.owner = owner
        self.available_minutes = available_minutes
        self.blackout_times = blackout_times or []
        self.max_tasks = max_tasks

    def get_pending_tasks(self) -> list[Task]:
        """Return all incomplete tasks across the owner's pets."""
        return [t for t in self.owner.get_all_tasks() if not t.completed]

    def _allows(self, task: Task) -> tuple[bool, str]:
        """Check whether a task passes the scheduler's constraints.

        Args:
            task: The task to evaluate.

        Returns:
            A tuple of (allowed, reason) where allowed is True if the task
            can be scheduled, and reason is an empty string or a short
            explanation of why it was rejected.
        """
        if task.preferred_time in self.blackout_times:
            return False, "time is blacked out"
        if task.duration_minutes > self.available_minutes:
            return False, "too long to fit"
        return True, ""

    def _sort_key(self, task: Task) -> tuple:
        """Return a sort key that orders tasks by priority, frequency, then duration.

        High-priority daily tasks sort first; low-priority as-needed tasks sort
        last. Within the same priority and frequency, shorter tasks are preferred
        so the schedule fits more items into the available window.
        """
        return (
            PRIORITY_ORDER[task.priority],
            FREQUENCY_ORDER[task.frequency],
            task.duration_minutes,
        )

    def build_daily_plan(self) -> dict:
        """Select tasks that fit within the owner's constraints for today.

        Uses a greedy algorithm: tasks are sorted by priority and frequency,
        then accepted one-by-one until time or task limits are reached.
        Chosen tasks are re-ordered by preferred time slot before returning.

        Returns:
            A dict with keys:
                chosen          - list of Task objects scheduled for today
                skipped         - list of dicts with 'task' and 'reason' keys
                minutes_used    - total duration of chosen tasks
                minutes_remaining - available_minutes minus minutes_used
        """
        chosen = []
        skipped = []
        minutes_used = 0

        sorted_tasks = sorted(self.get_pending_tasks(), key=self._sort_key)

        for task in sorted_tasks:
            allowed, reason = self._allows(task)
            if not allowed:
                skipped.append({"task": task, "reason": reason})
            elif len(chosen) >= self.max_tasks:
                skipped.append({"task": task, "reason": "max tasks reached"})
            elif minutes_used + task.duration_minutes > self.available_minutes:
                skipped.append({"task": task, "reason": "not enough time remaining"})
            else:
                chosen.append(task)
                minutes_used += task.duration_minutes

        # Order chosen tasks by preferred time slot for a readable schedule
        chosen_ordered = sorted(chosen, key=lambda t: TIME_SLOT_ORDER[t.preferred_time])

        return {
            "chosen": chosen_ordered,
            "skipped": skipped,
            "minutes_used": minutes_used,
            "minutes_remaining": self.available_minutes - minutes_used,
        }

    def explain_plan(self, plan: dict) -> str:
        """Format a plan dict as a human-readable schedule summary.

        Args:
            plan: The dict returned by build_daily_plan().

        Returns:
            A multi-line string listing scheduled tasks by time slot followed
            by any skipped tasks with their rejection reasons.
        """
        lines = [f"Daily plan for {self.owner.name} ({plan['minutes_used']} / {self.available_minutes} min used)\n"]

        if plan["chosen"]:
            lines.append("Scheduled:")
            for task in plan["chosen"]:
                slot = task.preferred_time or "any time"
                pet_name = task.pet.name if task.pet else "unknown"
                lines.append(
                    f"  - [{slot}] {task.description} ({pet_name}, {task.duration_minutes} min,"
                    f" {task.priority} priority, {task.frequency})"
                )
        else:
            lines.append("No tasks could be scheduled.")

        if plan["skipped"]:
            lines.append("\nSkipped:")
            for entry in plan["skipped"]:
                t = entry["task"]
                lines.append(f"  - {t.description}: {entry['reason']}")

        return "\n".join(lines)

    def filter_tasks(
        self,
        tasks: list[Task] = None,
        completed: bool = None,
        pet_name: str = None,
    ) -> list[Task]:
        """Filter tasks by completion status and/or pet name.

        Args:
            tasks: Task list to filter. Defaults to all owner tasks.
            completed: If True, return only completed tasks. If False, only pending.
                       If None, both are included.
            pet_name: If provided, return only tasks belonging to that pet.
        """
        results = tasks if tasks is not None else self.owner.get_all_tasks()
        if completed is not None:
            results = [t for t in results if t.completed == completed]
        if pet_name is not None:
            results = [t for t in results if t.pet and t.pet.name == pet_name]
        return results

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by start_time in ascending 'HH:MM' order.
        Tasks with no start_time are placed at the end.
        """
        return sorted(tasks, key=lambda task: task.start_time if task.start_time else "99:99")

    def detect_conflicts(self, tasks: list[Task]) -> list[str]:
        """Return warning messages for any tasks whose time windows overlap.

        Strategy: convert each task's start_time to total minutes, then check
        every pair for overlap using (start < other_end and other_start < end).
        Tasks with no start_time set are skipped. Returns warnings, never raises.
        """
        def to_minutes(hhmm: str) -> int | None:
            if not hhmm:
                return None
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        timed = [(t, to_minutes(t.start_time)) for t in tasks if to_minutes(t.start_time) is not None]
        warnings = []

        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a, a_start = timed[i]
                b, b_start = timed[j]
                a_end = a_start + a.duration_minutes
                b_end = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    a_pet = a.pet.name if a.pet else "unknown"
                    b_pet = b.pet.name if b.pet else "unknown"
                    warnings.append(
                        f"WARNING: '{a.description}' ({a_pet}, {a.start_time}-{a_end // 60:02d}:{a_end % 60:02d}) "
                        f"overlaps with '{b.description}' ({b_pet}, {b.start_time}-{b_end // 60:02d}:{b_end % 60:02d})"
                    )

        return warnings

    def mark_chosen_complete(self, plan: dict) -> None:
        """Mark all chosen tasks as completed after running the plan."""
        for task in plan["chosen"]:
            task.mark_complete()
