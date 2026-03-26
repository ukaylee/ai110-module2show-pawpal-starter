import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state initialization — runs once, persists across reruns
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None   # created when user submits the owner form

# ---------------------------------------------------------------------------
# Step 1: Owner setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    submitted = st.form_submit_button("Set owner")
    if submitted:
        st.session_state.owner = Owner(name=owner_name)
        st.success(f"Owner set to {owner_name}!")

if st.session_state.owner is None:
    st.info("Set an owner above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Step 2: Add a pet  →  calls owner.add_pet()
# ---------------------------------------------------------------------------
st.divider()
st.subheader("2. Pets")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age", min_value=0, max_value=30, value=2)
    add_pet = st.form_submit_button("Add pet")
    if add_pet:
        new_pet = Pet(name=pet_name, species=species, age=int(age))
        owner.add_pet(new_pet)          # <-- Owner.add_pet() called here
        st.success(f"{pet_name} added!")

# Show all current pets
if owner.pets:
    st.write(f"{owner.name}'s pets:")
    st.table([{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.get_tasks())} for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")
    st.stop()

# ---------------------------------------------------------------------------
# Step 3: Add a task to a pet  →  calls pet.add_task()
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Tasks")

with st.form("task_form"):
    pet_names = [p.name for p in owner.pets]
    target_pet_name = st.selectbox("Assign to pet", pet_names)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        task_desc = st.text_input("Description", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col4:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "as needed"])
    with col5:
        preferred_time = st.selectbox("Time slot", ["", "morning", "afternoon", "evening"])
    with col6:
        start_time = st.text_input("Start time (HH:MM)", value="", placeholder="08:00")
    add_task = st.form_submit_button("Add task")
    if add_task:
        target_pet = next(p for p in owner.pets if p.name == target_pet_name)
        new_task = Task(
            description=task_desc,
            duration_minutes=int(duration),
            priority=priority,
            frequency=frequency,
            preferred_time=preferred_time,
            start_time=start_time.strip(),
        )
        target_pet.add_task(new_task)   # <-- Pet.add_task() called here
        st.success(f"Task '{task_desc}' added to {target_pet_name}!")

# Show all tasks grouped by pet, sorted by start_time via Scheduler.sort_by_time()
_display_scheduler = Scheduler(owner=owner, available_minutes=9999)
all_tasks = owner.get_tasks_by_pet()
for pet_name, tasks in all_tasks.items():
    if tasks:
        st.markdown(f"**{pet_name}**")
        sorted_tasks = _display_scheduler.sort_by_time(tasks)

        # Conflict warnings for this pet's tasks
        conflicts = _display_scheduler.detect_conflicts(sorted_tasks)
        for warning in conflicts:
            st.warning(warning)

        st.table([
            {
                "Description": t.description,
                "Start": t.start_time or "—",
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority,
                "Frequency": t.frequency,
                "Time slot": t.preferred_time or "any",
                "Done": "✓" if t.completed else "",
            }
            for t in sorted_tasks
        ])

if not owner.get_all_tasks():
    st.info("No tasks yet. Add one above.")
    st.stop()

# ---------------------------------------------------------------------------
# Step 4: Build schedule  →  calls scheduler.build_daily_plan()
# ---------------------------------------------------------------------------
st.divider()
st.subheader("4. Build Schedule")

col_min, col_max, col_black = st.columns(3)
with col_min:
    available_minutes = st.number_input("Available minutes today", min_value=1, max_value=480, value=60)
with col_max:
    max_tasks = st.number_input("Max tasks", min_value=1, max_value=20, value=5)
with col_black:
    blackout = st.multiselect("Blackout times", ["morning", "afternoon", "evening"])

if st.button("Generate schedule"):
    scheduler = Scheduler(
        owner=owner,
        available_minutes=int(available_minutes),
        blackout_times=blackout,
        max_tasks=int(max_tasks),
    )
    plan = scheduler.build_daily_plan()

    st.success(f"Today's plan for {owner.name} — {plan['minutes_used']} / {available_minutes} min used, {plan['minutes_remaining']} min remaining")

    # Conflict warnings across all chosen tasks
    conflicts = scheduler.detect_conflicts(plan["chosen"])
    for warning in conflicts:
        st.warning(warning)

    st.markdown("### Scheduled")
    if plan["chosen"]:
        # Display chosen tasks sorted chronologically by start_time
        sorted_chosen = scheduler.sort_by_time(plan["chosen"])
        st.table([
            {
                "Pet": t.pet.name,
                "Task": t.description,
                "Start": t.start_time or "—",
                "Time slot": t.preferred_time or "any",
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority,
                "Frequency": t.frequency,
            }
            for t in sorted_chosen
        ])
    else:
        st.info("No tasks could be scheduled.")

    if plan["skipped"]:
        st.markdown("### Skipped")
        st.table([
            {"Pet": s["task"].pet.name if s["task"].pet else "—", "Task": s["task"].description, "Reason": s["reason"]}
            for s in plan["skipped"]
        ])
