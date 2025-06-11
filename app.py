import streamlit as st
import os
import shutil
import json
import base64
import pandas as pd
from datetime import datetime
import PyPDF2
from quiz_generator import generate_quiz
from auth import login_user, register_user

# ------------- App Setup -------------
st.set_page_config(page_title="📚 Learn & Teach", layout="wide")
import streamlit as st
import base64

# Read and encode the image
file_path = "logo_college.png"  # Make sure this file is in the same directory or provide full path
with open(file_path, "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode()

# Display image using HTML
st.markdown(
    f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded_image}" width="150" height="189"/>
        </div>
    """,
    unsafe_allow_html=True
   
)

# 🌗 Theme Switcher
if "theme" not in st.session_state:
    st.session_state.theme = "Light"

theme = st.sidebar.radio("🌓 Select Theme", ["Light", "Dark"], index=0 if st.session_state.theme == "Light" else 1)
st.session_state.theme = theme
def set_theme(theme):
    if theme == "Dark":
        dark_css = """
        <style>
            .stApp {
                background-color: #121212;
                color: #ffffff;
            }

            /* Text color for all labels and inputs */
            label, .stRadio label, .stSelectbox label, .css-1cpxqw2, .css-qrbaxs {
                color: #ffffff !important;
            }

            /* Radio button labels */
            .stRadio > div > label {
                color: white !important;
            }

            /* Inputs and text areas */
            input, textarea, .stTextInput input, .stTextArea textarea {
                background-color: #1e1e1e !important;
                color: #ffffff !important;
                border: 1px solid #444444;
            }

            /* Buttons */
            .stButton>button, .stDownloadButton>button {
                background-color: #333333 !important;
                color: #ffffff !important;
                border: 1px solid #555555 !important;
            }

            /* Markdown inside quiz display */
            .markdown-text-container {
                color: #ffffff !important;
            }

            /* Sidebar */
            .css-1d391kg, .css-1v0mbdj, .css-ffhzg2 {
                color: black !important;
                background-color:black;
            }

            /* Expander text */
            .streamlit-expanderHeader {
                color: black !important;
            }

            .block-container {
                padding: 2rem 1rem;
            }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)

    else:
        light_css = """
        <style>
            .stApp {
                background-color: #ffffff;
                color: #000000;
            }

            label, .stRadio label, .stSelectbox label, .css-1cpxqw2, .css-qrbaxs {
                color: #000000 !important;
            }

            input, textarea {
                background-color: #ffffff !important;
                color: #000000 !important;
            }

            .stButton>button, .stDownloadButton>button {
                background-color: #f0f0f0 !important;
                color: #000000 !important;
            }

            .streamlit-expanderHeader {
                color: #000000 !important;
            }

            .block-container {
                padding: 2rem 1rem;
            }
        </style>
        """
        st.markdown(light_css, unsafe_allow_html=True)



# 💡 Apply selected theme
set_theme(st.session_state.theme)




# Custom CSS for style and layout
st.markdown("""
    <style>
        /* Align sidebar buttons on left */
        .css-18ni7ap.e8zbici2 { 
            background-color: black;
            padding: 15px;
            border-radius: 8px;
        }

        /* Title style */
        .title-style {
            text-align: center;
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        /* Subheader */
        .subheader-style {
            font-size: 1.4em;
            color: #34495e;
            margin-top: 15px;
        }

        /* Buttons */
        .stButton>button {
            background-color: #1abc9c;
            color: white;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
        }

        .stButton>button:hover {
            background-color: #16a085;
            color: white;
        }

        /* Text inputs and text areas */
        textarea, input[type="text"], input[type="password"] {
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #bdc3c7;
        }

        /* Container centering */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 900px;
            margin: auto;
        }

        /* Info boxes */
        .stAlert {
            background-color: #ecf0f1 !important;
            border-left: 5px solid #3498db !important;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 10px;
        }
        ::-webkit-scrollbar-thumb {
            background: #1abc9c;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-track {
            background: #ecf0f1;
        }

        /* Announcement cards */
        .announcement-box {
            border: 1px solid #dcdcdc;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #fdfefe;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        }

        .announcement-box strong {
            color: #2c3e50;
        }
    </style>
""", unsafe_allow_html=True)



# ------------- Sidebar Navigation -------------
st.sidebar.title("📚 E-Learning using AI")
role = st.sidebar.radio("Who are you?", ["Teacher", "Student"])

if role == "Teacher":
    menu = st.sidebar.radio("📋 Teacher Menu", [
        "Login/Register", 
        "Upload Lessons", 
        "Post Announcement", 
        "Create Custom Quiz", 
        "Manage Quiz", 
        "View Quiz Results", 
        "Manage Announcements", 
        "Reset App Data"
    ])
else:
    menu = st.sidebar.radio("📋 Student Menu", [
        "Login/Register", 
        "View Announcements", 
        "View Lessons", 
        "Generate Local Quiz", 
        "Take Assigned Quiz", 
        "Completed Lessons"
    ])

# ------------- Teacher Panel -------------
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

        elif menu == "Reset App Data":
            st.markdown("<h2 style='text-align:center;'>⚠️ Reset App Data</h2>", unsafe_allow_html=True)
            if st.button("Reset Everything"):
                shutil.rmtree("content", ignore_errors=True)
                os.makedirs("content", exist_ok=True)
                for file in ["quiz_results.csv", "student_progress.csv", "lesson_metadata.json", "custom_quiz.json"]:
                    if os.path.exists(file):
                        os.remove(file)
                st.success("✅ All data cleared!")

# ------------- Student Panel -------------
else:
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
            files = os.listdir("content")
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
                        f.write(f"{selected_file}\n")
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
                    st.success("✅ Submitted to teacher!")
                    del st.session_state.student_answers
            else:
                st.info("no quiz given ")
        elif menu == "Completed Lessons":
            st.markdown("<h2 style='text-align:center;'>📈 Completed Lessons</h2>", unsafe_allow_html=True)
            if os.path.exists("student_progress.csv"):
                st.dataframe(pd.read_csv("student_progress.csv", header=None, names=["Completed Lessons"]))
            else:
                st.info("No completed lessons yet.")
