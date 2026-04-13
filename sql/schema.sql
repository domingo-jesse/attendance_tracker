-- Attendance Tracker Schema (PostgreSQL)

CREATE TABLE IF NOT EXISTS students (
    id BIGSERIAL PRIMARY KEY,
    student_number TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    grade_level INTEGER,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teachers (
    id BIGSERIAL PRIMARY KEY,
    teacher_code TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rooms (
    id BIGSERIAL PRIMARY KEY,
    room_code TEXT UNIQUE NOT NULL,
    room_name TEXT,
    building TEXT,
    capacity INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS class_periods (
    id BIGSERIAL PRIMARY KEY,
    period_code TEXT UNIQUE NOT NULL,
    period_name TEXT,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bell_schedule (
    id BIGSERIAL PRIMARY KEY,
    schedule_name TEXT NOT NULL DEFAULT 'Regular Day',
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7), -- ISO weekday
    period_id BIGINT NOT NULL REFERENCES class_periods(id),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    UNIQUE(schedule_name, day_of_week, period_id),
    CHECK (end_time > start_time)
);

CREATE TABLE IF NOT EXISTS student_schedules (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    period_id BIGINT NOT NULL REFERENCES class_periods(id),
    room_id BIGINT NOT NULL REFERENCES rooms(id),
    teacher_id BIGINT NOT NULL REFERENCES teachers(id),
    course_name TEXT,
    UNIQUE(student_id, day_of_week, period_id)
);

CREATE TABLE IF NOT EXISTS teacher_schedules (
    id BIGSERIAL PRIMARY KEY,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    period_id BIGINT NOT NULL REFERENCES class_periods(id),
    room_id BIGINT NOT NULL REFERENCES rooms(id),
    course_name TEXT,
    UNIQUE(teacher_id, day_of_week, period_id)
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    date_for DATE NOT NULL,
    period_id BIGINT REFERENCES class_periods(id),
    status TEXT NOT NULL CHECK (status IN ('present','absent','sick','missing','tardy')),
    notes TEXT,
    recorded_by_teacher_id BIGINT REFERENCES teachers(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(student_id, date_for, period_id, status)
);

CREATE TABLE IF NOT EXISTS field_trips (
    id BIGSERIAL PRIMARY KEY,
    trip_name TEXT NOT NULL,
    trip_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    destination TEXT,
    supervising_teacher_id BIGINT REFERENCES teachers(id),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS field_trip_participants (
    id BIGSERIAL PRIMARY KEY,
    field_trip_id BIGINT NOT NULL REFERENCES field_trips(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(field_trip_id, student_id)
);

CREATE TABLE IF NOT EXISTS special_events (
    id BIGSERIAL PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    room_id BIGINT REFERENCES rooms(id),
    supervising_teacher_id BIGINT REFERENCES teachers(id),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS special_event_participants (
    id BIGSERIAL PRIMARY KEY,
    special_event_id BIGINT NOT NULL REFERENCES special_events(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(special_event_id, student_id)
);

CREATE TABLE IF NOT EXISTS location_overrides (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    override_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    room_id BIGINT REFERENCES rooms(id),
    teacher_id BIGINT REFERENCES teachers(id),
    status_label TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_table TEXT NOT NULL,
    entity_id TEXT,
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bell_schedule_day_time ON bell_schedule(day_of_week, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_student_schedules_lookup ON student_schedules(student_id, day_of_week, period_id);
CREATE INDEX IF NOT EXISTS idx_teacher_schedules_lookup ON teacher_schedules(teacher_id, day_of_week, period_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student_day ON attendance_records(student_id, date_for, period_id);
CREATE INDEX IF NOT EXISTS idx_location_override_student_day ON location_overrides(student_id, override_date);
