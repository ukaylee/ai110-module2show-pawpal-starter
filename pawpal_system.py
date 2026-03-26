from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

"""Core domain models and scheduling logic for PawPal+.

This module defines:
- task and pet entities,
- owner-level aggregation across pets,
- and a scheduler that builds a constrained daily plan.
"""

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
        """Mark the task as completed."""
        self.completed = True


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
        """Returns (allowed, reason_if_not)."""
        if task.preferred_time in self.blackout_times:
            return False, "time is blacked out"
        if task.duration_minutes > self.available_minutes:
            return False, "too long to fit"
        return True, ""

    def _sort_key(self, task: Task) -> tuple:
        """Sort by priority, then frequency urgency, then shortest duration first."""
        return (
            PRIORITY_ORDER[task.priority],
            FREQUENCY_ORDER[task.frequency],
            task.duration_minutes,
        )

    def build_daily_plan(self) -> dict:
        """Select tasks that fit constraints and return chosen/skipped breakdown."""
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
        """Generate a human-readable explanation of scheduled and skipped tasks."""
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

    def mark_chosen_complete(self, plan: dict) -> None:
        """Mark all chosen tasks as completed after running the plan."""
        for task in plan["chosen"]:
            task.mark_complete()
