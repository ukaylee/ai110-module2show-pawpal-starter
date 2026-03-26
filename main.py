from pawpal_system import Task, Pet, Owner, Scheduler

# --- Setup ---

owner = Owner(name="Jordan")

mochi = Pet(name="Mochi", species="dog", age=3)
luna  = Pet(name="Luna",  species="cat", age=5)

# Mochi's tasks
mochi.add_task(Task(description="Morning walk",    duration_minutes=30, priority="high",   frequency="daily",    preferred_time="morning"))
mochi.add_task(Task(description="Feed breakfast",  duration_minutes=5,  priority="high",   frequency="daily",    preferred_time="morning"))
mochi.add_task(Task(description="Evening walk",    duration_minutes=20, priority="medium", frequency="daily",    preferred_time="evening"))
mochi.add_task(Task(description="Bath time",       duration_minutes=25, priority="low",    frequency="weekly",   preferred_time="afternoon"))

# Luna's tasks
luna.add_task(Task(description="Clean litter box", duration_minutes=10, priority="high",   frequency="daily",    preferred_time="morning"))
luna.add_task(Task(description="Brush fur",        duration_minutes=15, priority="medium", frequency="weekly",   preferred_time="afternoon"))
luna.add_task(Task(description="Vet checkup",      duration_minutes=60, priority="high",   frequency="monthly",  preferred_time="afternoon"))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Schedule ---

scheduler = Scheduler(
    owner=owner,
    available_minutes=90,
    blackout_times=["evening"],
    max_tasks=6,
)

plan = scheduler.build_daily_plan()

# --- Output ---

print("=" * 40)
print("       TODAY'S SCHEDULE")
print("=" * 40)
print(scheduler.explain_plan(plan))
print("=" * 40)
print(f"Tasks scheduled : {len(plan['chosen'])}")
print(f"Tasks skipped   : {len(plan['skipped'])}")
print(f"Time remaining  : {plan['minutes_remaining']} min")
