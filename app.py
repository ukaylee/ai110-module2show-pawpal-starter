import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_desc = st.text_input("Task description", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "as needed"])

if st.button("Add task"):
    st.session_state.tasks.append(
        {"description": task_desc, "duration_minutes": int(duration), "priority": priority, "frequency": frequency}
    )

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

col_min, col_max, col_black = st.columns(3)
with col_min:
    available_minutes = st.number_input("Available minutes today", min_value=1, max_value=480, value=60)
with col_max:
    max_tasks = st.number_input("Max tasks", min_value=1, max_value=20, value=5)
with col_black:
    blackout = st.multiselect("Blackout times", ["morning", "afternoon", "evening"])

if st.button("Generate schedule"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        pet = Pet(name=pet_name, species=species, age=0)
        for t in st.session_state.tasks:
            pet.add_task(Task(
                description=t["description"],
                duration_minutes=t["duration_minutes"],
                priority=t["priority"],
                frequency=t["frequency"],
            ))

        owner = Owner(name=owner_name)
        owner.add_pet(pet)

        scheduler = Scheduler(
            owner=owner,
            available_minutes=int(available_minutes),
            blackout_times=blackout,
            max_tasks=int(max_tasks),
        )
        plan = scheduler.build_daily_plan()

        st.success(f"Schedule for {owner_name} and {pet_name}")
        st.markdown(f"**Total time used:** {plan['minutes_used']} / {available_minutes} minutes")

        st.markdown("### Chosen tasks")
        if plan["chosen"]:
            st.table([
                {"Task": t.description, "Duration (min)": t.duration_minutes, "Priority": t.priority, "Frequency": t.frequency}
                for t in plan["chosen"]
            ])
        else:
            st.info("No tasks could be scheduled.")

        if plan["skipped"]:
            st.markdown("### Skipped tasks")
            st.table([
                {"Task": s["task"].description, "Reason": s["reason"]}
                for s in plan["skipped"]
            ])
