import streamlit as st
import os
import shutil
import json
import base64
import pandas as pd
from datetime import datetime, timedelta
import PyPDF2
from quiz_generator import generate_quiz
from auth import login_user, register_user
import uuid
import altair as alt  # Using Altair for pie charts (compatible with Streamlit)

# ---------------- Attendance helpers & config ----------------
ATT_FILE = "attendance.csv"
RETENTION_DAYS = 31  # keep approximately 1 month (31 days)
ROSTER_FILE = "class_roster.csv"
PARENT_CSV = "parent_student_map.csv"
PARENT_JSON = "parent_student_mapping.json"

def cleanup_attendance(file=ATT_FILE, retention_days=RETENTION_DAYS):
    """Remove attendance records older than retention_days."""
    if not os.path.exists(file):
        return
    try:
        df = pd.read_csv(file, parse_dates=["Date"])
    except Exception:
        # If file malformed, remove it to avoid crashes
        try:
            os.remove(file)
        except OSError:
            pass
        return
    cutoff = pd.Timestamp(datetime.now().date() - timedelta(days=retention_days - 1))
    df = df[df["Date"] >= cutoff]
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df.to_csv(file, index=False)
    else:
        # If no recent data, remove file to start fresh
        try:
            os.remove(file)
        except OSError:
            pass

def append_attendance_records(records, file=ATT_FILE):
    """Append list of dict records [{'Date': 'YYYY-MM-DD', 'Student': 'Name', 'Status': 'Present'}]."""
    if not records:
        return
    df = pd.DataFrame(records)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    header = not os.path.exists(file)
    df.to_csv(file, mode='a', header=header, index=False)
    # cleanup old records after append
    cleanup_attendance(file)

def load_attendance_df(file=ATT_FILE):
    if not os.path.exists(file):
        return pd.DataFrame(columns=["Date", "Student", "Status"])
    df = pd.read_csv(file, parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    return df

def get_parent_student_mapping():
    """
    Returns a dict mapping parent_username -> student_name.
    Checks CSV first (PARENT_CSV), then JSON fallback.
    """
    mapping = {}
    if os.path.exists(PARENT_CSV):
        try:
            df = pd.read_csv(PARENT_CSV, dtype=str)
            if "parent_username" in df.columns and "student_name" in df.columns:
                mapping = dict(zip(df["parent_username"].astype(str), df["student_name"].astype(str)))
                return mapping
        except Exception:
            pass
    if os.path.exists(PARENT_JSON):
        try:
            with open(PARENT_JSON, "r") as f:
                mapping = json.load(f)
        except Exception:
            mapping = {}
    return mapping

def save_parent_student_mapping(mapping):
    """
    Save mapping to JSON and CSV (overwrite CSV with current mapping).
    mapping: dict parent_username -> student_name
    """
    # Save JSON
    with open(PARENT_JSON, "w") as f:
        json.dump(mapping, f, indent=2)
    # Save CSV
    try:
        df = pd.DataFrame(list(mapping.items()), columns=["parent_username", "student_name"])
        df.to_csv(PARENT_CSV, index=False)
    except Exception:
        pass

def save_roster_from_upload(uploaded_file):
    """
    Accepts a file-like object from Streamlit uploader and writes to ROSTER_FILE.
    Expected columns: Student OR at least first column is student name.
    """
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        # try reading as simple newline list
        uploaded_file.seek(0)
        txt = uploaded_file.read().decode("utf-8")
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        df = pd.DataFrame({"Student": lines})
    # Normalize column name
    if "Student" not in df.columns:
        df.columns = [str(c).strip() for c in df.columns]
        df.rename(columns={df.columns[0]: "Student"}, inplace=True)
    df = df[["Student"]].dropna()
    df["Student"] = df["Student"].astype(str).str.strip()
    df.to_csv(ROSTER_FILE, index=False)

def load_roster():
    """Return list of student names from roster if it exists, else empty list."""
    if not os.path.exists(ROSTER_FILE):
        return []
    try:
        df = pd.read_csv(ROSTER_FILE, dtype=str)
        if "Student" in df.columns:
            return [s.strip() for s in df["Student"].dropna().astype(str).tolist()]
        else:
            # fallback: use first column
            first_col = df.columns[0]
            return [s.strip() for s in df[first_col].dropna().astype(str).tolist()]
    except Exception:
        return []

# Run cleanup at app start
cleanup_attendance()

# ------------- App Setup -------------
st.set_page_config(page_title="📚 Learn & Teach", layout="wide")
# Read and encode the logo image (if present)
file_path = "logo_college.png"
if os.path.exists(file_path):
    with open(file_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded_image}" width="150" height="189"/>
        </div>
        """,
        unsafe_allow_html=True
    )

# Theme Switcher
if "theme" not in st.session_state:
    st.session_state.theme = "Light"
theme = st.sidebar.radio("🌓 Select Theme", ["Light", "Dark"], index=0 if st.session_state.theme == "Light" else 1)
st.session_state.theme = theme
def set_theme(theme):
    if theme == "Dark":
        dark_css = """<style>/* Dark theme CSS */</style>"""
        st.markdown(dark_css, unsafe_allow_html=True)
    else:
        light_css = """<style>/* Light theme CSS */</style>"""
        st.markdown(light_css, unsafe_allow_html=True)
set_theme(st.session_state.theme)
# Custom CSS
st.markdown("""<style>/* Custom style CSS */</style>""", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("📚 E-Learning using AI")
role = st.sidebar.radio("Who are you?", ["Teacher", "Student", "Parent"])
if role == "Teacher":
    menu = st.sidebar.radio("📋 Teacher Menu", [
        "Login/Register",
        "Upload Lessons",
        "Post Announcement",
        "Create Custom Quiz",
        "Manage Quiz",
        "View Quiz Results",
        "Manage Announcements",
        "View Parent Messages",
        "Upload Class Roster",   # new
        "Mark Attendance",
        "View Attendance Report",
        "Reset App Data"
    ])
elif role == "Student":
    menu = st.sidebar.radio("📋 Student Menu", [
        "Login/Register",
        "View Announcements",
        "View Lessons",
        "Generate Local Quiz",
        "Take Assigned Quiz",
        "Completed Lessons"
    ])
else:
    menu = st.sidebar.radio("📋 Parent Menu", [
        "Login/Register",
        "View Progress Dashboard",
        "Activity Timeline",
        "Curriculum Overview",
        "Notifications & Alerts",
        "Communication Tools",
        "Goal Setting & Rewards",
        "Parental Controls",
        "Analytics & Insights"
    ])

# ---------------- Teacher Panel ----------------
if role == "Teacher":
    if menu == "Login/Register":
        st.markdown("<h2 style='text-align:center;'>🧑‍🏫 Teacher Login/Register</h2>", unsafe_allow_html=True)
        mode = st.radio("Choose:", ["Login", "Register"], key="teacher_mode")
        if mode == "Login":
            login_user("teacher")
        else:
            register_user("teacher")
    elif not st.session_state.get("teacher_logged_in"):
        st.warning("🔒 Please login as a teacher to access this section.")
    else:
        if menu == "Upload Lessons":
            st.markdown("<h2 style='text-align:center;'>📤 Upload Lesson Notes</h2>", unsafe_allow_html=True)
            os.makedirs("content", exist_ok=True)
            uploaded_file = st.file_uploader("Upload PDF or Text File", type=["pdf", "txt"])
            if uploaded_file:
                with open(os.path.join("content", uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ Uploaded: {uploaded_file.name}")
        elif menu == "Post Announcement":
            st.markdown("<h2 style='text-align:center;'>📢 Post Announcement</h2>", unsafe_allow_html=True)
            ann_file = "announcements.json"
            announcement = st.text_area("Enter your message:")
            if st.button("📬 Post Announcement"):
                announcements = []
                if os.path.exists(ann_file):
                    with open(ann_file, "r") as f:
                        announcements = json.load(f)
                new_post = {"message": announcement.strip(), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                announcements.insert(0, new_post)
                with open(ann_file, "w") as f:
                    json.dump(announcements, f, indent=2)
                st.success("✅ Announcement posted!")
                st.rerun()
        elif menu == "Create Custom Quiz":
            st.markdown("<h2 style='text-align:center;'>🧑‍🏫 Create Custom Quiz</h2>", unsafe_allow_html=True)
            quiz_title = st.text_input("Quiz Title")
            if "teacher_custom_quiz" not in st.session_state:
                st.session_state.teacher_custom_quiz = []
            with st.form("custom_quiz_form"):
                q = st.text_input("Enter a question")
                o1, o2, o3 = st.text_input("Option 1"), st.text_input("Option 2"), st.text_input("Option 3")
                ans = st.selectbox("Correct Answer", [o1, o2, o3])
                add_question = st.form_submit_button("➕ Add Question")
                if add_question and all([q, o1, o2, o3, ans]):
                    st.session_state.teacher_custom_quiz.append({"question": q, "options": [o1, o2, o3], "answer": ans})
                    st.success("✅ Question added!")
            if st.session_state.teacher_custom_quiz:
                st.markdown("### Preview Questions")
                for i, q in enumerate(st.session_state.teacher_custom_quiz):
                    st.markdown(f"**Q{i+1}: {q['question']}**")
                    st.markdown(f"Options: {', '.join(q['options'])} | ✅ Answer: {q['answer']}")
                if st.button("📢 Publish Quiz to Students"):
                    if not quiz_title.strip():
                        st.warning("Please enter a quiz title.")
                    else:
                        with open("custom_quiz.json", "w") as f:
                            json.dump({"title": quiz_title, "questions": st.session_state.teacher_custom_quiz}, f, indent=2)
                        st.success("✅ Quiz published!")
                        st.session_state.teacher_custom_quiz = []
        elif menu == "Manage Quiz":
            st.markdown("<h2 style='text-align:center;'>🗑️ Manage Published Quiz</h2>", unsafe_allow_html=True)
            if os.path.exists("custom_quiz.json"):
                with open("custom_quiz.json", "r") as f:
                    quiz = json.load(f)
                st.markdown(f"**Published Quiz:** {quiz['title']}")
                if st.button("❌ Delete Published Quiz"):
                    os.remove("custom_quiz.json")
                    st.success("🗑️ Quiz deleted.")
        elif menu == "View Quiz Results":
            st.markdown("<h2 style='text-align:center;'>📊 Quiz Results from Students</h2>", unsafe_allow_html=True)
            if os.path.exists("custom_quiz_results.csv"):
                st.dataframe(pd.read_csv("custom_quiz_results.csv"))
            else:
                st.info("No results yet.")
        elif menu == "Manage Announcements":
            st.markdown("<h2 style='text-align:center;'>🗑️ Manage Announcements</h2>", unsafe_allow_html=True)
            ann_file = "announcements.json"
            if os.path.exists(ann_file):
                with open(ann_file, "r") as f:
                    announcements = json.load(f)
                for i, ann in enumerate(announcements):
                    with st.expander(f"📅 {ann['timestamp']}"):
                        st.markdown(ann["message"])
                        if st.button("❌ Delete", key=f"del_ann_{i}"):
                            announcements.pop(i)
                            with open(ann_file, "w") as f:
                                json.dump(announcements, f, indent=2)
                            st.success("Deleted.")
                            st.rerun()
            else:
                st.info("No announcements found.")
        elif menu == "View Parent Messages":
            st.markdown("<h2 style='text-align:center;'>📩 Messages from Parents</h2>", unsafe_allow_html=True)
            msg_file = "parent_teacher_messages.json"
            if os.path.exists(msg_file):
                with open(msg_file, "r") as f:
                    messages = json.load(f)
                for i, msg in enumerate(messages):
                    with st.expander(f"📅 {msg['timestamp']} (Student: {msg['student_name']})"):
                        st.markdown(msg["message"])
                        if st.button("❌ Delete", key=f"del_msg_{i}"):
                            messages.pop(i)
                            with open(msg_file, "w") as f:
                                json.dump(messages, f, indent=2)
                            st.success("Deleted.")
                            st.rerun()
            else:
                st.info("No messages from parents found.")

        elif menu == "Upload Class Roster":
            st.markdown("<h2 style='text-align:center;'>📥 Upload Class Roster</h2>", unsafe_allow_html=True)
            st.info("Upload a CSV with a column named `Student` (or with student names in the first column).")
            roster_file = st.file_uploader("Upload roster CSV", type=["csv"])
            if roster_file:
                try:
                    save_roster_from_upload(roster_file)
                    st.success("✅ Roster uploaded and saved.")
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")
            # Show current roster if exists
            roster = load_roster()
            if roster:
                st.markdown("### Current Roster (first 200 shown)")
                st.dataframe(pd.DataFrame({"Student": roster[:200]}))
            else:
                st.info("No roster uploaded yet. Teachers can still mark attendance manually.")

        elif menu == "Mark Attendance":
            st.markdown("<h2 style='text-align:center;'>📅 Mark Student Attendance</h2>", unsafe_allow_html=True)
            st.info("You can either use the uploaded roster (recommended) or paste names manually (comma/newline).")
            roster = load_roster()
            col1, col2 = st.columns([2,1])
            with col1:
                attendance_date = st.date_input("Select Date", datetime.today())
                st.write("Select marking mode:")
                mode = st.radio("Mode", ["Roster (checkboxes)", "Manual entry (comma/newline)"])
                status_default = st.radio("Default status for unmarked/selected", ["Present", "Absent"])
            with col2:
                st.write("Quick actions")
                if st.button("Mark All Present (roster)"):
                    # quick action only if roster exists
                    if roster:
                        date_str = attendance_date.strftime("%Y-%m-%d")
                        records = [{"Date": date_str, "Student": s, "Status": "Present"} for s in roster]
                        append_attendance_records(records)
                        st.success(f"✅ Marked {len(records)} students as Present for {date_str}")
                    else:
                        st.warning("No roster available to mark all present.")
                if st.button("Mark All Absent (roster)"):
                    if roster:
                        date_str = attendance_date.strftime("%Y-%m-%d")
                        records = [{"Date": date_str, "Student": s, "Status": "Absent"} for s in roster]
                        append_attendance_records(records)
                        st.success(f"✅ Marked {len(records)} students as Absent for {date_str}")
                    else:
                        st.warning("No roster available to mark all absent.")

            if mode == "Roster (checkboxes)":
                if not roster:
                    st.info("No roster uploaded. Please upload a roster first or switch to manual entry.")
                else:
                    st.markdown("### Select students who are PRESENT (unselected will be marked as Absent if you choose so)")
                    present_selection = {}
                    # Show checklist in columns to avoid long single column
                    cols = st.columns(4)
                    for i, student in enumerate(roster):
                        c = cols[i % 4]
                        present_selection[student] = c.checkbox(student, value=(status_default=="Present"), key=f"pres_{i}")
                    if st.button("✅ Save Roster Attendance"):
                        date_str = attendance_date.strftime("%Y-%m-%d")
                        # Build records: if checkbox True -> Present else -> Absent
                        records = []
                        for student, present in present_selection.items():
                            st_status = "Present" if present else "Absent"
                            records.append({"Date": date_str, "Student": student, "Status": st_status})
                        append_attendance_records(records)
                        st.success(f"✅ Saved attendance for {len(records)} students on {date_str}")

            else:  # Manual entry
                students_input = st.text_area("Enter Student Name(s) (comma or newline separated):", height=150)
                status = st.radio("Attendance Status for entered names", ["Present", "Absent"], index=0 if status_default=="Present" else 1)
                if st.button("✅ Mark Manual Attendance"):
                    names = []
                    for chunk in str(students_input).splitlines():
                        for name in chunk.split(","):
                            n = name.strip()
                            if n:
                                names.append(n)
                    if not names:
                        st.warning("Please enter at least one student name.")
                    else:
                        date_str = attendance_date.strftime("%Y-%m-%d")
                        records = [{"Date": date_str, "Student": n, "Status": status} for n in names]
                        append_attendance_records(records)
                        st.success(f"✅ Attendance marked for {len(names)} student(s) on {date_str} as {status}.")

        elif menu == "View Attendance Report":
            st.markdown("<h2 style='text-align:center;'>📊 Attendance Report</h2>", unsafe_allow_html=True)
            # Ensure file retention cleanup runs whenever report is opened
            cleanup_attendance()

            if os.path.exists(ATT_FILE):
                att_df = pd.read_csv(ATT_FILE, parse_dates=["Date"])
                # Default date range -> last 30 days
                today = datetime.today().date()
                default_start = today - timedelta(days=29)
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start date", default_start)
                with col2:
                    end_date = st.date_input("End date", today)

                # Student filter
                student_filter = st.text_input("Filter by student name (partial match):").strip()

                # Status filter
                status_options = st.multiselect("Status (choose to filter)", ["Present", "Absent"], default=["Present", "Absent"])

                # Validate date range
                if start_date > end_date:
                    st.error("Start date must be before or equal to End date.")
                else:
                    # filter by date range
                    mask = (att_df["Date"] >= pd.to_datetime(start_date)) & (att_df["Date"] <= pd.to_datetime(end_date))
                    df_filtered = att_df.loc[mask].copy()

                    # filter by student if provided (case-insensitive partial match)
                    if student_filter:
                        df_filtered = df_filtered[df_filtered["Student"].str.contains(student_filter, case=False, na=False)]

                    # filter by status
                    if status_options:
                        df_filtered = df_filtered[df_filtered["Status"].isin(status_options)]
                    else:
                        df_filtered = df_filtered.iloc[0:0]  # empty if nothing selected

                    if df_filtered.empty:
                        st.info("No attendance records match the selected filters.")
                    else:
                        # show summary counts
                        counts = df_filtered["Status"].value_counts().reset_index()
                        counts.columns = ["Status", "Count"]

                        # Pie chart
                        pie_chart = alt.Chart(counts).mark_arc().encode(
                            theta=alt.Theta(field="Count", type="quantitative"),
                            color=alt.Color(field="Status", type="nominal"),
                            tooltip=['Status', 'Count']
                        ).properties(
                            title=f"Attendance from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        )
                        st.altair_chart(pie_chart, use_container_width=True)

                        # show table (sorted)
                        df_display = df_filtered.sort_values(by=["Date", "Student"], ascending=[False, True])
                        st.dataframe(df_display.reset_index(drop=True))

                        # Latest attendance per student (if requested)
                        if st.checkbox("Show latest attendance status per student"):
                            latest = df_display.sort_values("Date").groupby("Student").last().reset_index()
                            st.markdown("### Latest status per student (within selected range)")
                            st.dataframe(latest[["Student", "Date", "Status"]])

                        # Download filtered CSV
                        csv = df_display.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="⬇️ Download filtered results as CSV",
                            data=csv,
                            file_name=f"attendance_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
            else:
                st.info("No attendance data available.")

        elif menu == "Reset App Data":
            st.markdown("<h2 style='text-align:center;'>⚠️ Reset App Data</h2>", unsafe_allow_html=True)
            if st.button("Reset Everything"):
                shutil.rmtree("content", ignore_errors=True)
                os.makedirs("content", exist_ok=True)
                for file in ["quiz_results.csv", "student_progress.csv", "lesson_metadata.json", "custom_quiz.json", PARENT_CSV, PARENT_JSON, "parent_teacher_messages.json", ATT_FILE, ROSTER_FILE]:
                    if os.path.exists(file):
                        os.remove(file)
                st.success("✅ All data cleared!")

# ---------------- Student Panel ----------------
elif role == "Student":
    if menu == "Login/Register":
        st.markdown("<h2 style='text-align:center;'>🧑‍🎓 Student Login/Register</h2>", unsafe_allow_html=True)
        mode = st.radio("Choose:", ["Login", "Register"], key="student_mode")
        if mode == "Login":
            login_user("student")
        else:
            register_user("student")
    elif not st.session_state.get("student_logged_in"):
        st.warning("🔒 Please login as a student to access this section.")
    else:
        if menu == "View Announcements":
            st.markdown("<h2 style='text-align:center;'>📢 Announcements</h2>", unsafe_allow_html=True)
            if os.path.exists("announcements.json"):
                with open("announcements.json", "r") as f:
                    announcements = json.load(f)
                for ann in announcements:
                    st.info(f"📅 {ann['timestamp']}\n\n{ann['message']}")
            else:
                st.info("No announcements yet.")
        elif menu == "View Lessons":
            st.markdown("<h2 style='text-align:center;'>📚 View Lessons</h2>", unsafe_allow_html=True)
            files = os.listdir("content") if os.path.exists("content") else []
            if not files:
                st.info("No lessons available.")
            else:
                selected_file = st.selectbox("Select a file:", files)
                path = os.path.join("content", selected_file)
                if selected_file.endswith(".txt"):
                    with open(path, "r", encoding="utf-8") as f:
                        st.text_area("Lesson Content", f.read(), height=300)
                else:
                    with open(path, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
                    st.markdown(f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700px"/>', unsafe_allow_html=True)
                if st.button("✅ Mark as Done"):
                    with open("student_progress.csv", "a") as f:
                        f.write(f"{st.session_state.get('student_username', 'Anonymous')},{selected_file}\n")
                    st.success("Lesson marked as done.")
        elif menu == "Generate Local Quiz":
            st.markdown("<h2 style='text-align:center;'>🧠 Generate Quiz From Text</h2>", unsafe_allow_html=True)
            text_input = st.text_area("Paste your lesson text here:")
            if st.button("Generate Quiz"):
                if not text_input.strip():
                    st.warning("Please enter content.")
                else:
                    st.session_state.quiz = generate_quiz(text_input)
                    st.session_state.quiz_submitted = False
                    st.session_state.selected_options = {}
            if st.session_state.get("quiz"):
                st.subheader("📝 Quiz Time")
                for i, item in enumerate(st.session_state.quiz):
                    selected = st.radio(f"Q{i+1}. {item['question']}", item['options'], key=f"q_{i}",
                                        disabled=st.session_state.get("quiz_submitted", False))
                    st.session_state.selected_options[i] = selected
                if not st.session_state.get("quiz_submitted", False):
                    if st.button("Submit Answers"):
                        st.session_state.quiz_submitted = True
                if st.session_state.get("quiz_submitted", False):
                    correct = sum(st.session_state.selected_options[i] == item["answer"]
                                  for i, item in enumerate(st.session_state.quiz))
                    
                    st.success(f"🎯 You scored {correct}/{len(st.session_state.quiz)}")
                    result = {
                        "Student Name": st.session_state.get("student_username", "Anonymous"),
                        "Lesson Name": "Pasted Content",
                        "Score": f"{correct}/{len(st.session_state.quiz)}",
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    df = pd.DataFrame([result])
                    df.to_csv("quiz_results.csv", mode='a', header=not os.path.exists("quiz_results.csv"), index=False)
                    st.success("✅ Your result has been saved!")
        elif menu == "Take Assigned Quiz":
            st.markdown("<h2 style='text-align:center;'>🧪 Take Teacher Quiz</h2>", unsafe_allow_html=True)
            if os.path.exists("custom_quiz.json"):
                with open("custom_quiz.json", "r") as f:
                    quiz_data = json.load(f)
                if "student_answers" not in st.session_state:
                    st.session_state.student_answers = {}
                for i, q in enumerate(quiz_data["questions"]):
                    index = (
                        q["options"].index(st.session_state.student_answers[i])
                        if i in st.session_state.student_answers and st.session_state.student_answers[i] in q["options"]
                        else 0
                    )
                    selected = st.radio(
                        f"Q{i+1}. {q['question']}", q["options"], index=index, key=f"custom_q_{i}",
                        disabled=st.session_state.get("student_quiz_submitted", False)
                    )
                    st.session_state.student_answers[i] = selected
                if st.button("✅ Submit Quiz"):
                    correct = sum(st.session_state.student_answers[i] == q["answer"]
                                  for i, q in enumerate(quiz_data["questions"]))
                    total = len(quiz_data["questions"])
                    st.success(f"🎯 You scored {correct}/{total}")
                    result = {
                        "Student Name": st.session_state.get("student_username", "Anonymous"),
                        "Quiz Title": quiz_data["title"],
                        "Score": f"{correct}/{total}",
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    pd.DataFrame([result]).to_csv("custom_quiz_results.csv", mode='a', header=not os.path.exists("custom_quiz_results.csv"), index=False)
                    st.session_state.student_quiz_submitted = True
                    st.success("✅ Submitted to teacher!")
                    del st.session_state.student_answers
            else:
                st.info("No assigned quiz available.")
        elif menu == "Completed Lessons":
            st.markdown("<h2 style='text-align:center;'>📈 Completed Lessons</h2>", unsafe_allow_html=True)
            if os.path.exists("student_progress.csv"):
                progress_df = pd.read_csv("student_progress.csv", header=None, names=["Student Name", "Completed Lessons"])
                student_progress = progress_df[progress_df["Student Name"] == st.session_state.get("student_username", "Anonymous")]
                if not student_progress.empty:
                    st.dataframe(student_progress[["Completed Lessons"]])
                else:
                    st.info("No completed lessons yet.")
            else:
                st.info("No completed lessons yet.")

# ---------------- Parent Panel ----------------
elif role == "Parent":
    if menu == "Login/Register":
        st.markdown("<h2 style='text-align:center;'>👨‍👩‍👧‍👦 Parent Login/Register</h2>", unsafe_allow_html=True)
        mode = st.radio("Choose:", ["Login", "Register"], key="parent_mode")
        if mode == "Login":
            login_user("parent")
            if st.session_state.get("parent_logged_in"):
                mapping = get_parent_student_mapping()
                parent_username = st.session_state.get("parent_username")
                if parent_username in mapping:
                    st.session_state.linked_student = mapping[parent_username]
                    st.success(f"✅ Linked to student: {st.session_state.linked_student}")
                else:
                    student_username = st.text_input("Enter your child's username to link:")
                    if st.button("Link Student"):
                        if student_username:
                            mapping[parent_username] = student_username
                            save_parent_student_mapping(mapping)
                            st.session_state.linked_student = student_username
                            st.success(f"✅ Successfully linked to student: {student_username}")
                        else:
                            st.warning("Please enter a valid student username.")
        else:
            # Register flow: ask for child's username to link at registration time
            student_username = st.text_input("Enter your child's username to link:")
            if student_username:
                register_user("parent")
                if st.session_state.get("parent_logged_in"):
                    parent_username = st.session_state.get("parent_username")
                    mapping = get_parent_student_mapping()
                    mapping[parent_username] = student_username
                    save_parent_student_mapping(mapping)
                    st.session_state.linked_student = student_username
                    st.success(f"✅ Successfully linked to student: {student_username}")
            else:
                st.warning("Please enter your child's username to register.")
    elif not st.session_state.get("parent_logged_in"):
        st.warning("🔒 Please login as a parent to access this section.")
    elif not st.session_state.get("linked_student"):
        st.warning("🔒 Please link to a student account to access this section.")
        student_username = st.text_input("Enter your child's username to link:")
        if st.button("Link Student"):
            if student_username:
                mapping = get_parent_student_mapping()
                parent_username = st.session_state.get("parent_username")
                mapping[parent_username] = student_username
                save_parent_student_mapping(mapping)
                st.session_state.linked_student = student_username
                st.success(f"✅ Successfully linked to student: {student_username}")
            else:
                st.warning("Please enter a valid student username.")
    else:
        st.markdown(f"<h2 style='text-align:center;'>👨‍👩‍👧‍👦 Parent Dashboard for {st.session_state.linked_student}</h2>", unsafe_allow_html=True)
        if menu == "View Progress Dashboard":
            st.subheader(f"📊 {st.session_state.linked_student}'s Progress Dashboard")
            # Existing progress and quiz displays
            if os.path.exists("student_progress.csv"):
                progress_df = pd.read_csv("student_progress.csv", header=None, names=["Student Name", "Completed Lessons"])
                student_progress = progress_df[progress_df["Student Name"] == st.session_state.linked_student]
                if not student_progress.empty:
                    st.dataframe(student_progress[["Completed Lessons"]])
                else:
                    st.info("No progress data available for this student.")
            else:
                st.info("No progress data available.")
            if os.path.exists("quiz_results.csv"):
                quiz_df = pd.read_csv("quiz_results.csv")
                student_quiz_df = quiz_df[quiz_df["Student Name"] == st.session_state.linked_student]
                if not student_quiz_df.empty:
                    st.markdown("### 📝 Local Quiz Scores")
                    st.dataframe(student_quiz_df)
                else:
                    st.info("No local quiz results available for this student.")
            else:
                st.info("No quiz results available.")
            if os.path.exists("custom_quiz_results.csv"):
                custom_quiz_df = pd.read_csv("custom_quiz_results.csv")
                student_custom_quiz_df = custom_quiz_df[custom_quiz_df["Student Name"] == st.session_state.linked_student]
                if not student_custom_quiz_df.empty:
                    st.markdown("### 🧪 Assigned Quiz Scores")
                    st.dataframe(student_custom_quiz_df)
                else:
                    st.info("No assigned quiz results available for this student.")
            else:
                st.info("No assigned quiz results available.")

            # Parent Attendance: Full date-wise attendance table (Option B)
            st.subheader("📅 Full Attendance (last 31 days)")
            cleanup_attendance()
            if os.path.exists(ATT_FILE):
                att_df = pd.read_csv(ATT_FILE, parse_dates=["Date"])
                student_att = att_df[att_df["Student"] == st.session_state.linked_student].copy()
                if student_att.empty:
                    st.info("No attendance data available for this student in the last 31 days.")
                else:
                    # sort descending by date
                    student_att = student_att.sort_values(by="Date", ascending=False).reset_index(drop=True)
                    # display table
                    st.dataframe(student_att[["Date", "Status"]])
                    # show pie chart summary
                    counts = student_att["Status"].value_counts().reset_index()
                    counts.columns = ["Status", "Count"]
                    pie_chart = alt.Chart(counts).mark_arc().encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Status", type="nominal"),
                        tooltip=['Status', 'Count']
                    ).properties(title="Attendance distribution (last 31 days)")
                    st.altair_chart(pie_chart, use_container_width=True)
                    # allow download of student's attendance
                    csv = student_att.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download student's attendance (CSV)",
                        data=csv,
                        file_name=f"{st.session_state.linked_student}_attendance_last31days.csv",
                        mime="text/csv"
                    )
            else:
                st.info("No attendance data available.")
        elif menu == "Activity Timeline":
            st.subheader(f"🕒 {st.session_state.linked_student}'s Learning Activity Timeline")
            if os.path.exists("activity_log.json"):
                with open("activity_log.json", "r") as f:
                    logs = json.load(f)
                student_logs = [log for log in logs if log.get("student_name") == st.session_state.linked_student]
                if student_logs:
                    for log in student_logs:
                        st.info(f"{log['timestamp']}: {log['activity']}")
                else:
                    st.info("No activity logs available for this student.")
            else:
                st.info("No activity logs available.")
        elif menu == "Curriculum Overview":
            st.subheader("📚 Curriculum Overview")
            curriculum = {
                "Subjects": ["Mathematics", "Science", "History", "Languages"],
                "Learning Goals": [
                    "Understand basic algebra",
                    "Learn fundamentals of physics",
                    "Explore major historical events",
                    "Improve language comprehension"
                ]
            }
            st.table(curriculum)
        elif menu == "Notifications & Alerts":
            st.subheader("📩 Notifications & Alerts")
            if os.path.exists("notifications.json"):
                with open("notifications.json", "r") as f:
                    notifications = json.load(f)
                student_notifications = [note for note in notifications if note.get("student_name") == st.session_state.linked_student]
                if student_notifications:
                    for note in student_notifications:
                        st.warning(f"{note['timestamp']}: {note['message']}")
                else:
                    st.info("No notifications available for this student.")
            else:
                st.info("No notifications available.")
        elif menu == "Communication Tools":
            st.subheader("🗣️ Communicate with Teachers")
            message = st.text_area("Write a message to the teacher:")
            if st.button("Send Message"):
                msg_log = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "student_name": st.session_state.linked_student,
                    "message": message.strip()
                }
                messages = []
                if os.path.exists("parent_teacher_messages.json"):
                    with open("parent_teacher_messages.json", "r") as f:
                        messages = json.load(f)
                messages.append(msg_log)
                with open("parent_teacher_messages.json", "w") as f:
                    json.dump(messages, f, indent=2)
                st.success("✅ Message sent to teacher.")
        elif menu == "Goal Setting & Rewards":
            st.subheader(f"🎯 Set Learning Goals & Rewards for {st.session_state.linked_student}")
            goal = st.text_input("Set a learning goal for your child:")
            reward = st.text_input("Define a reward for goal achievement:")
            if st.button("Save Goal & Reward"):
                goal_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "student_name": st.session_state.linked_student,
                    "goal": goal.strip(),
                    "reward": reward.strip()
                }
                goals = []
                if os.path.exists("parent_goals.json"):
                    with open("parent_goals.json", "r") as f:
                        goals = json.load(f)
                goals.append(goal_data)
                with open("parent_goals.json", "w") as f:
                    json.dump(goals, f, indent=2)
                st.success("✅ Goal and reward saved.")
        elif menu == "Parental Controls":
            st.subheader(f"🔒 Parental Controls for {st.session_state.linked_student}")
            max_screen_time = st.slider("Set maximum screen time per day (minutes)", 0, 300, 60)
            restricted_access = st.text_area("Restricted content keywords (comma separated):")
            if st.button("Save Parental Controls"):
                controls = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "student_name": st.session_state.linked_student,
                    "max_screen_time": max_screen_time,
                    "restricted_keywords": [kw.strip() for kw in restricted_access.split(",")]
                }
                with open("parental_controls.json", "w") as f:
                    json.dump(controls, f, indent=2)
                st.success("✅ Parental controls saved.")
        elif menu == "Analytics & Insights":
            st.subheader(f"📈 AI-driven Insights for {st.session_state.linked_student}")
            if os.path.exists("quiz_results.csv") or os.path.exists("custom_quiz_results.csv"):
                total_quizzes = 0
                total_correct = 0
                if os.path.exists("quiz_results.csv"):
                    quiz_df = pd.read_csv("quiz_results.csv")
                    student_quiz_df = quiz_df[quiz_df["Student Name"] == st.session_state.linked_student]
                    for score in student_quiz_df["Score"]:
                        correct, total = map(int, score.split("/"))
                        total_quizzes += total
                        total_correct += correct
                if os.path.exists("custom_quiz_results.csv"):
                    custom_quiz_df = pd.read_csv("custom_quiz_results.csv")
                    student_custom_quiz_df = custom_quiz_df[custom_quiz_df["Student Name"] == st.session_state.linked_student]
                    for score in student_custom_quiz_df["Score"]:
                        correct, total = map(int, score.split("/"))
                        total_quizzes += total
                        total_correct += correct
                if total_quizzes > 0:
                    performance = (total_correct / total_quizzes) * 100
                    st.info(f"Based on performance trends, {st.session_state.linked_student} has a {performance:.2f}% correct answer rate in quizzes.")
                else:
                    st.info("No quiz performance data available.")
                if os.path.exists("student_progress.csv"):
                    progress_df = pd.read_csv("student_progress.csv", header=None, names=["Student Name", "Completed Lessons"])
                    student_progress = progress_df[progress_df["Student Name"] == st.session_state.linked_student]
                    lesson_count = len(student_progress)
                    if lesson_count < 3:
                        st.info(f"{st.session_state.linked_student} has completed {lesson_count} lessons and may need encouragement to complete more.")
                    else:
                        st.info(f"{st.session_state.linked_student} is doing well with {lesson_count} lessons completed.")
            else:
                st.info("No performance data available for insights.")                                                      
