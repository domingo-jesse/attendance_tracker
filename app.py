from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from app.db import DatabaseConnectionError, bulk_insert_df, execute, fetch_df, run_sql_file
from app.logic import expected_location_for_student, students_in_room_now, teacher_for_room_now

st.set_page_config(page_title="Attendance Coordination", layout="wide")


def export_button(df: pd.DataFrame, label: str, filename: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def page_dashboard():
    st.title("Dashboard")
    st.caption("Real-time expected location and attendance status overview")

    missing = fetch_df(
        "SELECT s.first_name, s.last_name FROM attendance_records a JOIN students s ON s.id=a.student_id WHERE a.date_for=CURRENT_DATE AND a.status='missing'"
    )
    sick = fetch_df(
        "SELECT s.first_name, s.last_name FROM attendance_records a JOIN students s ON s.id=a.student_id WHERE a.date_for=CURRENT_DATE AND a.status='sick'"
    )
    absent = fetch_df(
        "SELECT s.first_name, s.last_name FROM attendance_records a JOIN students s ON s.id=a.student_id WHERE a.date_for=CURRENT_DATE AND a.status='absent'"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Missing", len(missing))
    c2.metric("Sick", len(sick))
    c3.metric("Absent", len(absent))

    st.subheader("Currently Missing")
    st.dataframe(missing, use_container_width=True)


def simple_table_page(title: str, table: str):
    st.title(title)
    df = fetch_df(f"SELECT * FROM {table} ORDER BY 1")
    st.dataframe(df, use_container_width=True)
    export_button(df, f"Export {title}", f"{table}.csv")


def page_students():
    st.title("Students")
    df = fetch_df("SELECT * FROM students ORDER BY last_name, first_name")
    st.dataframe(df, use_container_width=True)
    export_button(df, "Export Students", "students.csv")

    with st.form("add_student"):
        st.subheader("Add student")
        student_number = st.text_input("Student number")
        first_name = st.text_input("First name")
        last_name = st.text_input("Last name")
        grade = st.number_input("Grade", min_value=1, max_value=12, value=9)
        if st.form_submit_button("Create"):
            execute(
                "INSERT INTO students (student_number, first_name, last_name, grade_level) VALUES (%s,%s,%s,%s)",
                (student_number, first_name, last_name, grade),
            )
            st.success("Student created")


def page_attendance():
    st.title("Attendance")
    df = fetch_df(
        """
        SELECT a.id, a.date_for, s.first_name || ' ' || s.last_name AS student, a.status, a.notes
        FROM attendance_records a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.date_for DESC, student
        """
    )
    st.dataframe(df, use_container_width=True)
    export_button(df, "Export Attendance", "attendance.csv")


def page_field_trips_events():
    st.title("Field Trips / Special Events")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Field Trips")
        ft = fetch_df("SELECT * FROM field_trips ORDER BY trip_date DESC")
        st.dataframe(ft, use_container_width=True)
    with col2:
        st.subheader("Special Events")
        ev = fetch_df("SELECT * FROM special_events ORDER BY event_date DESC")
        st.dataframe(ev, use_container_width=True)


def page_schedule_import():
    st.title("Schedule Import (CSV / Excel)")
    st.caption("Upload files and map to tables: rooms, periods, teachers, student schedules.")
    up = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])
    target = st.selectbox("Target table", ["rooms", "class_periods", "teachers", "student_schedules"])

    if up is not None:
        if up.name.lower().endswith(".csv"):
            df = pd.read_csv(up)
        else:
            df = pd.read_excel(up)
        st.write("Preview", df.head())

        if st.button("Import now"):
            bulk_insert_df(df, target)
            st.success(f"Imported {len(df)} rows into {target}")


def page_lookup():
    st.title("Search / AI Lookup")
    st.caption("Natural-language query interpreter. Data and rules in DB remain source of truth.")
    q = st.text_input("Ask a question")
    now = datetime.now()

    if q:
        ql = q.lower()
        if "where is" in ql and "right now" in ql:
            name = q.lower().replace("where is", "").replace("right now", "").replace("?", "").strip()
            parts = name.split()
            if len(parts) >= 2:
                first, last = parts[0].capitalize(), parts[-1].capitalize()
                df = fetch_df("SELECT id FROM students WHERE first_name=%s AND last_name=%s LIMIT 1", (first, last))
                if df.empty:
                    st.warning("Student not found")
                else:
                    result = expected_location_for_student(int(df.iloc[0]["id"]), now)
                    st.success(
                        f"{result.get('student')}: {result.get('status')} @ {result.get('location')} "
                        f"(Teacher: {result.get('teacher') or 'N/A'}, Source: {result.get('source')})"
                    )
        elif "who is in room" in ql:
            room_code = ql.split("who is in room")[-1].replace("right now", "").replace("?", "").strip().upper()
            students = students_in_room_now(room_code, now)
            if not students:
                st.info("No scheduled students right now.")
            else:
                st.write([f"{s['first_name']} {s['last_name']}" for s in students])
        elif "which teacher" in ql and "room" in ql:
            tokens = ql.replace("?", "").split()
            room_code = tokens[-1].upper()
            teacher = teacher_for_room_now(room_code, now)
            st.info(teacher or "No assigned teacher right now")
        elif "absent today" in ql:
            df = fetch_df(
                """
                SELECT DISTINCT s.first_name, s.last_name
                FROM attendance_records a
                JOIN students s ON s.id = a.student_id
                WHERE a.date_for = CURRENT_DATE AND a.status='absent'
                ORDER BY s.last_name
                """
            )
            st.dataframe(df, use_container_width=True)
        elif "missing right now" in ql:
            df = fetch_df(
                """
                SELECT DISTINCT s.first_name, s.last_name
                FROM attendance_records a
                JOIN students s ON s.id = a.student_id
                WHERE a.date_for = CURRENT_DATE AND a.status='missing'
                ORDER BY s.last_name
                """
            )
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Could not confidently parse that question. Try one of the sample prompts.")


def page_init():
    st.title("Initialize Database")
    st.write("Run schema and seed scripts against configured PostgreSQL database.")
    if st.button("Run schema.sql"):
        run_sql_file("sql/schema.sql")
        st.success("Schema applied")
    if st.button("Run seed.sql"):
        run_sql_file("sql/seed.sql")
        st.success("Seed data loaded")


PAGES = {
    "Dashboard": page_dashboard,
    "Students": page_students,
    "Teachers": lambda: simple_table_page("Teachers", "teachers"),
    "Rooms": lambda: simple_table_page("Rooms", "rooms"),
    "Bell Schedule": lambda: simple_table_page("Bell Schedule", "bell_schedule"),
    "Student Schedules": lambda: simple_table_page("Student Schedules", "student_schedules"),
    "Attendance": page_attendance,
    "Field Trips / Special Events": page_field_trips_events,
    "Search / AI Lookup": page_lookup,
    "Schedule Import": page_schedule_import,
    "Initialize DB": page_init,
}

choice = st.sidebar.radio("Navigate", list(PAGES.keys()))
try:
    PAGES[choice]()
except DatabaseConnectionError as exc:
    st.error(str(exc))
    st.info(
        "If you are deploying on Streamlit Cloud, add DATABASE_URL in app secrets, then restart the app."
    )
