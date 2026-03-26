import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Task, Pet, Owner, Scheduler


def test_mark_complete_changes_status():
    task = Task(description="Morning walk", duration_minutes=30, priority="high", frequency="daily")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(description="Feed breakfast", duration_minutes=5, priority="high", frequency="daily"))
    assert len(pet.get_tasks()) == 1


# --- Sorting Correctness ---

def test_sort_by_time_chronological_order():
    pet = Pet(name="Biscuit", species="dog", age=2)
    owner = Owner(name="Alex", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t1 = Task(description="Evening walk", duration_minutes=20, priority="low", frequency="daily", start_time="18:00")
    t2 = Task(description="Morning meds", duration_minutes=5, priority="high", frequency="daily", start_time="08:00")
    t3 = Task(description="Afternoon play", duration_minutes=15, priority="medium", frequency="daily", start_time="13:30")

    sorted_tasks = scheduler.sort_by_time([t1, t2, t3])
    times = [t.start_time for t in sorted_tasks]
    assert times == ["08:00", "13:30", "18:00"]


def test_sort_by_time_tasks_without_start_time_go_last():
    pet = Pet(name="Biscuit", species="dog", age=2)
    owner = Owner(name="Alex", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t_no_time = Task(description="Grooming", duration_minutes=30, priority="low", frequency="weekly")
    t_timed = Task(description="Morning meds", duration_minutes=5, priority="high", frequency="daily", start_time="08:00")

    sorted_tasks = scheduler.sort_by_time([t_no_time, t_timed])
    assert sorted_tasks[0].start_time == "08:00"
    assert sorted_tasks[1].start_time == ""


# --- Recurrence Logic ---

def test_daily_task_recurs_after_mark_complete():
    pet = Pet(name="Mochi", species="cat", age=4)
    task = Task(description="Feed breakfast", duration_minutes=5, priority="high", frequency="daily")
    pet.add_task(task)

    assert len(pet.get_tasks()) == 1
    task.mark_complete()

    # Original task is completed; a new pending copy should have been added
    all_tasks = pet.get_tasks()
    assert len(all_tasks) == 2
    assert all_tasks[0].completed is True
    assert all_tasks[1].completed is False
    assert all_tasks[1].description == "Feed breakfast"


def test_monthly_task_does_not_recur_after_mark_complete():
    pet = Pet(name="Mochi", species="cat", age=4)
    task = Task(description="Vet checkup", duration_minutes=60, priority="medium", frequency="monthly")
    pet.add_task(task)

    task.mark_complete()

    # Only the original (now completed) task should exist
    assert len(pet.get_tasks()) == 1
    assert pet.get_tasks()[0].completed is True


# --- Conflict Detection ---

def test_detect_conflicts_flags_overlapping_tasks():
    pet = Pet(name="Rex", species="dog", age=5)
    owner = Owner(name="Sam", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t1 = Task(description="Walk", duration_minutes=30, priority="high", frequency="daily", start_time="08:00")
    t2 = Task(description="Training", duration_minutes=30, priority="medium", frequency="daily", start_time="08:20")

    warnings = scheduler.detect_conflicts([t1, t2])
    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Training" in warnings[0]


def test_detect_conflicts_no_warning_for_back_to_back_tasks():
    pet = Pet(name="Rex", species="dog", age=5)
    owner = Owner(name="Sam", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t1 = Task(description="Walk", duration_minutes=30, priority="high", frequency="daily", start_time="08:00")
    t2 = Task(description="Training", duration_minutes=30, priority="medium", frequency="daily", start_time="08:30")

    warnings = scheduler.detect_conflicts([t1, t2])
    assert len(warnings) == 0


def test_detect_conflicts_flags_identical_start_times():
    pet = Pet(name="Rex", species="dog", age=5)
    owner = Owner(name="Sam", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t1 = Task(description="Walk", duration_minutes=20, priority="high", frequency="daily", start_time="09:00")
    t2 = Task(description="Bath", duration_minutes=20, priority="low", frequency="weekly", start_time="09:00")

    warnings = scheduler.detect_conflicts([t1, t2])
    assert len(warnings) == 1


def test_detect_conflicts_skips_tasks_without_start_time():
    pet = Pet(name="Rex", species="dog", age=5)
    owner = Owner(name="Sam", pets=[pet])
    scheduler = Scheduler(owner=owner, available_minutes=120)

    t1 = Task(description="Walk", duration_minutes=30, priority="high", frequency="daily", start_time="08:00")
    t2 = Task(description="Grooming", duration_minutes=30, priority="low", frequency="weekly")  # no start_time

    warnings = scheduler.detect_conflicts([t1, t2])
    assert len(warnings) == 0
