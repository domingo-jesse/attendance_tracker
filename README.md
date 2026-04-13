# School Attendance Coordination App

Streamlit + PostgreSQL application to compute each student's **expected current location** using bell schedule, schedules, and attendance/event overrides.

## Features
- PostgreSQL schema with required tables
- Seed data for quick bootstrapping
- Streamlit pages for dashboard, CRUD-style table views, attendance, events, schedule import, and AI-like lookup
- Rule-based natural language query interpreter that only returns data-backed answers
- CSV export on major pages

## Setup
1. Create PostgreSQL database, e.g. `attendance_tracker`.
2. Set env var:
   ```bash
   export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/attendance_tracker'
   ```
   For hosted databases, add SSL in the DSN:
   ```bash
   export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require'
   ```
   On Streamlit Cloud, set the same key in **Secrets**:
   ```toml
   DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require"
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run app:
   ```bash
   streamlit run app.py
   ```

## DB initialization
Use **Initialize DB** page or run manually:
```bash
psql "$DATABASE_URL" -f sql/schema.sql
psql "$DATABASE_URL" -f sql/seed.sql
```

## Expected location resolution logic
Implemented in `app/logic.py` with this precedence:
1. `missing`
2. `sick`
3. `absent`
4. active `field_trip`
5. active `special_event`
6. active `location_override`
7. scheduled room assignment from `student_schedules`

The app determines the active period from `bell_schedule` + current time/day first, then evaluates these rules.
