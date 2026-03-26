from pawpal_system import Task, Pet, Owner, Scheduler

# --- Setup ---

owner = Owner(name="Jordan")

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks — added out of order (evening before morning)
mochi.add_task(Task(description="Evening walk",    duration_minutes=20, priority="medium", frequency="daily",   preferred_time="evening",   start_time="18:00"))
mochi.add_task(Task(description="Bath time",       duration_minutes=25, priority="low",    frequency="weekly",  preferred_time="afternoon", start_time="14:00"))
mochi.add_task(Task(description="Feed breakfast",  duration_minutes=5,  priority="high",   frequency="daily",   preferred_time="morning",   start_time="07:00"))
mochi.add_task(Task(description="Morning walk",    duration_minutes=30, priority="high",   frequency="daily",   preferred_time="morning",   start_time="08:30"))

# Luna's tasks — added out of order (afternoon before morning)
luna.add_task(Task(description="Brush fur",        duration_minutes=15, priority="medium", frequency="weekly",  preferred_time="afternoon", start_time="15:30"))
luna.add_task(Task(description="Vet checkup",      duration_minutes=60, priority="high",   frequency="monthly", preferred_time="afternoon", start_time="13:00"))
luna.add_task(Task(description="Clean litter box", duration_minutes=10, priority="high",   frequency="daily",   preferred_time="morning",   start_time="07:30"))

# Intentional conflicts for testing:
# "Feed Mochi" starts at 07:00 — overlaps with "Feed breakfast" (07:00, 5 min) for Mochi
# "Morning playtime" starts at 08:45 — overlaps with "Morning walk" (08:30, 30 min) for Mochi (different pet)
mochi.add_task(Task(description="Morning playtime", duration_minutes=20, priority="medium", frequency="daily",  preferred_time="morning",   start_time="08:45"))
luna.add_task( Task(description="Feed Luna",         duration_minutes=10, priority="high",   frequency="daily",  preferred_time="morning",   start_time="07:00"))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Scheduler ---

scheduler = Scheduler(
    owner=owner,
    available_minutes=90,
    blackout_times=["evening"],
    max_tasks=6,
)

plan = scheduler.build_daily_plan()

# --- Original Schedule Output ---

print("=" * 40)
print("       TODAY'S SCHEDULE")
print("=" * 40)
print(scheduler.explain_plan(plan))
print("=" * 40)
print(f"Tasks scheduled : {len(plan['chosen'])}")
print(f"Tasks skipped   : {len(plan['skipped'])}")
print(f"Time remaining  : {plan['minutes_remaining']} min")

# --- sort_by_time() demo ---

all_tasks = owner.get_all_tasks()

print("\n" + "=" * 40)
print("  CONFLICT DETECTION")
print("=" * 40)
conflicts = scheduler.detect_conflicts(plan["chosen"])
if conflicts:
    for warning in conflicts:
        print(warning)
else:
    print("  No conflicts detected.")

print("\n" + "=" * 40)
print("  TASKS SORTED BY START TIME (HH:MM)")
print("=" * 40)
for t in scheduler.sort_by_time(all_tasks):
    time_label = t.start_time if t.start_time else "no time set"
    pet_name   = t.pet.name if t.pet else "unknown"
    print(f"  {time_label}  |  {t.description} ({pet_name})")

# --- filter_tasks() demos ---

print("\n" + "=" * 40)
print("  FILTER: PENDING TASKS ONLY")
print("=" * 40)
for t in scheduler.filter_tasks(completed=False):
    print(f"  [ ] {t.description} ({t.pet.name if t.pet else 'unknown'})")

# Mark chosen tasks complete so we have a mix of states
scheduler.mark_chosen_complete(plan)

print("\n" + "=" * 40)
print("  FILTER: COMPLETED TASKS (after running plan)")
print("=" * 40)
for t in scheduler.filter_tasks(completed=True):
    print(f"  [x] {t.description} ({t.pet.name if t.pet else 'unknown'})")

print("\n" + "=" * 40)
print("  FILTER: MOCHI'S TASKS ONLY")
print("=" * 40)
for t in scheduler.filter_tasks(pet_name="Mochi"):
    status = "x" if t.completed else " "
    print(f"  [{status}] {t.description}")

print("\n" + "=" * 40)
print("  FILTER: LUNA'S PENDING TASKS ONLY")
print("=" * 40)
for t in scheduler.filter_tasks(completed=False, pet_name="Luna"):
    print(f"  [ ] {t.description}")
