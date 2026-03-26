from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str               # "low", "medium", "high"
    preferred_time: str = ""    # "morning", "afternoon", "evening", or ""
    pet: Pet = None             # back-reference set when added to a Pet


@dataclass
class Pet:
    name: str
    species: str                # "dog", "cat", "other"
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def get_tasks(self) -> list[Task]:
        pass


@dataclass
class UserConstraint:
    available_minutes: int
    blackout_times: list[str] = field(default_factory=list)  # e.g. ["morning"]
    max_tasks: int = 10

    def allows(self, task: Task) -> bool:
        pass


@dataclass
class Owner:
    name: str
    pet: Pet = None
    constraint: UserConstraint = None
