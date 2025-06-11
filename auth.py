import streamlit as st
import json
import os

def get_user_file(role):
    return f"{role}_users.json"

def load_users(role):
    file = get_user_file(role)
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_users(role, users):
    file = get_user_file(role)
    with open(file, "w") as f:
        json.dump(users, f, indent=2)

def register_user(role):
    username = st.text_input(f"Choose a {role} username", key=f"{role}_reg_user")
    password = st.text_input("Choose a password", type="password", key=f"{role}_reg_pass")
    if st.button("📝 Register", key=f"{role}_register_btn"):
        file = f"{role}s.json"
        users = {}
        if os.path.exists(file):
            with open(file, "r") as f:
                users = json.load(f)
        if username in users:
            st.warning("⚠️ Username already exists!")
        else:
            users[username] = {"password": password}
            with open(file, "w") as f:
                json.dump(users, f, indent=2)
            st.success("✅ Registration successful!")

def login_user(role):
    username = st.text_input(f"{role.capitalize()} Username", key=f"{role}_login_user")
    password = st.text_input("Password", type="password", key=f"{role}_login_pass")
    if st.button("🔐 Login", key=f"{role}_login_btn"):
        file = f"{role}s.json"
        if os.path.exists(file):
            with open(file, "r") as f:
                users = json.load(f)
            if username in users and users[username]["password"] == password:
                st.session_state[f"{role}_logged_in"] = True
                st.session_state[f"{role}_username"] = username
                st.success("✅ Login successful!")
            else:
                st.error("❌ Invalid username or password.")
        else:
            st.error("❌ No users registered yet.")