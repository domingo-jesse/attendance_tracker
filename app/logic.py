from __future__ import annotations

from datetime import datetime

from app.db import fetch_df


def get_current_period(now: datetime | None = None):
    now = now or datetime.now()
    weekday = now.isoweekday()
    t = now.time()
    df = fetch_df(
        """
        SELECT b.period_id, p.period_code, p.period_name, b.start_time, b.end_time
        FROM bell_schedule b
        JOIN class_periods p ON p.id = b.period_id
        WHERE b.day_of_week = %s
          AND b.start_time <= %s
          AND b.end_time > %s
        ORDER BY p.sort_order
        LIMIT 1
        """,
        (weekday, t, t),
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def expected_location_for_student(student_id: int, now: datetime | None = None) -> dict:
    """
    Priority order (highest to lowest):
    missing > sick > absent > field trip > special event > manual override > schedule
    """
    now = now or datetime.now()
    weekday = now.isoweekday()
    today = now.date()
    t = now.time()

    student_df = fetch_df(
        "SELECT id, first_name, last_name FROM students WHERE id=%s", (student_id,)
    )
    if student_df.empty:
        return {"status": "unknown", "message": "Student not found"}

    student_name = f"{student_df.iloc[0]['first_name']} {student_df.iloc[0]['last_name']}"
    period = get_current_period(now)

    # 1) Attendance status overrides with highest priorities.
    status_df = fetch_df(
        """
        SELECT status, notes
        FROM attendance_records
        WHERE student_id=%s AND date_for=%s
          AND (period_id IS NULL OR period_id=%s)
          AND status IN ('missing','sick','absent')
        ORDER BY CASE status
            WHEN 'missing' THEN 1
            WHEN 'sick' THEN 2
            WHEN 'absent' THEN 3
            ELSE 99
        END
        LIMIT 1
        """,
        (student_id, today, period["period_id"] if period else None),
    )
    if not status_df.empty:
        row = status_df.iloc[0]
        return {
            "student": student_name,
            "status": row["status"],
            "location": row["status"].upper(),
            "teacher": None,
            "source": "attendance_records",
            "notes": row["notes"],
        }

    # 2) Field trip
    ft_df = fetch_df(
        """
        SELECT ft.trip_name, ft.destination, t.first_name || ' ' || t.last_name AS teacher
        FROM field_trip_participants p
        JOIN field_trips ft ON ft.id = p.field_trip_id
        LEFT JOIN teachers t ON t.id = ft.supervising_teacher_id
        WHERE p.student_id=%s AND ft.trip_date=%s
          AND (ft.start_time IS NULL OR ft.start_time <= %s)
          AND (ft.end_time IS NULL OR ft.end_time > %s)
        LIMIT 1
        """,
        (student_id, today, t, t),
    )
    if not ft_df.empty:
        row = ft_df.iloc[0]
        return {
            "student": student_name,
            "status": "field_trip",
            "location": row["destination"] or row["trip_name"],
            "teacher": row["teacher"],
            "source": "field_trips",
        }

    # 3) Special event
    ev_df = fetch_df(
        """
        SELECT e.event_name, r.room_code, t.first_name || ' ' || t.last_name AS teacher
        FROM special_event_participants p
        JOIN special_events e ON e.id = p.special_event_id
        LEFT JOIN rooms r ON r.id = e.room_id
        LEFT JOIN teachers t ON t.id = e.supervising_teacher_id
        WHERE p.student_id=%s AND e.event_date=%s
          AND (e.start_time IS NULL OR e.start_time <= %s)
          AND (e.end_time IS NULL OR e.end_time > %s)
        LIMIT 1
        """,
        (student_id, today, t, t),
    )
    if not ev_df.empty:
        row = ev_df.iloc[0]
        return {
            "student": student_name,
            "status": "special_event",
            "location": row["room_code"] or row["event_name"],
            "teacher": row["teacher"],
            "source": "special_events",
        }

    # 4) Manual location override
    lo_df = fetch_df(
        """
        SELECT lo.status_label, lo.reason, r.room_code, t.first_name || ' ' || t.last_name AS teacher
        FROM location_overrides lo
        LEFT JOIN rooms r ON r.id = lo.room_id
        LEFT JOIN teachers t ON t.id = lo.teacher_id
        WHERE lo.student_id=%s AND lo.override_date=%s
          AND (lo.start_time IS NULL OR lo.start_time <= %s)
          AND (lo.end_time IS NULL OR lo.end_time > %s)
        ORDER BY lo.created_at DESC
        LIMIT 1
        """,
        (student_id, today, t, t),
    )
    if not lo_df.empty:
        row = lo_df.iloc[0]
        return {
            "student": student_name,
            "status": row["status_label"] or "override",
            "location": row["room_code"] or "Manual Override",
            "teacher": row["teacher"],
            "source": "location_overrides",
            "notes": row["reason"],
        }

    # 5) Scheduled room assignment (fallback)
    if period is None:
        return {
            "student": student_name,
            "status": "no_period",
            "location": "No active class period",
            "teacher": None,
            "source": "bell_schedule",
        }

    sched_df = fetch_df(
        """
        SELECT r.room_code,
               ts.course_name,
               t.first_name || ' ' || t.last_name AS teacher
        FROM student_schedules ts
        JOIN rooms r ON r.id = ts.room_id
        JOIN teachers t ON t.id = ts.teacher_id
        WHERE ts.student_id=%s
          AND ts.day_of_week=%s
          AND ts.period_id=%s
        LIMIT 1
        """,
        (student_id, weekday, period["period_id"]),
    )
    if sched_df.empty:
        return {
            "student": student_name,
            "status": "unscheduled",
            "location": "No scheduled room",
            "teacher": None,
            "source": "student_schedules",
        }

    row = sched_df.iloc[0]
    return {
        "student": student_name,
        "status": "scheduled",
        "location": row["room_code"],
        "teacher": row["teacher"],
        "course": row["course_name"],
        "source": "student_schedules",
        "period": period["period_code"],
    }


def students_in_room_now(room_code: str, now: datetime | None = None):
    now = now or datetime.now()
    period = get_current_period(now)
    if period is None:
        return []

    df = fetch_df(
        """
        SELECT s.id, s.first_name, s.last_name
        FROM student_schedules ss
        JOIN students s ON s.id = ss.student_id
        JOIN rooms r ON r.id = ss.room_id
        WHERE r.room_code=%s
          AND ss.day_of_week=%s
          AND ss.period_id=%s
          AND s.active = TRUE
        ORDER BY s.last_name, s.first_name
        """,
        (room_code, now.isoweekday(), period["period_id"]),
    )
    return df.to_dict(orient="records")


def teacher_for_room_now(room_code: str, now: datetime | None = None):
    now = now or datetime.now()
    period = get_current_period(now)
    if period is None:
        return None

    df = fetch_df(
        """
        SELECT t.first_name || ' ' || t.last_name AS teacher
        FROM teacher_schedules ts
        JOIN teachers t ON t.id = ts.teacher_id
        JOIN rooms r ON r.id = ts.room_id
        WHERE r.room_code=%s
          AND ts.day_of_week=%s
          AND ts.period_id=%s
        LIMIT 1
        """,
        (room_code, now.isoweekday(), period["period_id"]),
    )
    if df.empty:
        return None
    return df.iloc[0]["teacher"]
