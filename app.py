import streamlit as st
from brain import rank_my_tasks
from main import get_canvas_data
from datetime import time

st.set_page_config(layout="centered", page_title="AI Planner")

if "confirmed_busy" not in st.session_state:
    st.session_state.confirmed_busy = []

st.title("🎓 Study Planner: Manual Block Entry")
st.info("Enter your class and work times below. The AI will build your study schedule around these blocks.")

# 1. THE AM/PM ENTRY FORM
with st.form("add_block_form", clear_on_submit=True):
    st.subheader("Add a Busy Block")
    day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    
    col1, col2 = st.columns(2)
    # Streamlit uses the browser's locale to determine if it shows AM/PM
    start_t = col1.time_input("Start Time", time(8, 15)) # Defaulting to your 8:15 class time!
    end_t = col2.time_input("End Time", time(9, 30))
    
    label = st.text_input("Label (e.g., History Class, Gym)", "Busy")
    
    if st.form_submit_button("➕ Add to Schedule"):
        # Formatting for the AI and the display
        new_block = {
            "day": day,
            "start": start_t.strftime("%I:%M %p"), # Converts to AM/PM string
            "end": end_t.strftime("%I:%M %p"),     # Converts to AM/PM string
            "title": label
        }
        st.session_state.confirmed_busy.append(new_block)
        st.success(f"Added {label} on {day} at {new_block['start']}!")

# 2. THE DASHBOARD (Formatted for readability)
if st.session_state.confirmed_busy:
    st.divider()
    st.subheader("Your Protected Time")
    
    for idx, block in enumerate(st.session_state.confirmed_busy):
        # Displaying the clean AM/PM times
        st.write(f"🚩 **{block['day']}**: {block['start']} – {block['end']} | *{block['title']}*")
    
    if st.button("🗑️ Clear All"):
        st.session_state.confirmed_busy = []
        st.rerun()

# 3. AI GENERATION
st.divider()
if st.button("🚀 Generate AI Plan", type="primary"):
    if not st.session_state.confirmed_busy:
        st.warning("Please add your class or work times first.")
    else:
        with st.spinner("Analyzing Canvas Course: History of Rome..."):
            canvas_data = get_canvas_data()
            plan = rank_my_tasks(canvas_data, {
                "busy_blocks": st.session_state.confirmed_busy, 
                "max_hours_daily": 4
            })
            st.markdown(plan)