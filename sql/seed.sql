-- Seed data
INSERT INTO rooms (room_code, room_name, building, capacity) VALUES
('101','Math Room','Main',30),
('102','Science Room','Main',28),
('GYM','Gymnasium','Athletics',200)
ON CONFLICT (room_code) DO NOTHING;

INSERT INTO teachers (teacher_code, first_name, last_name, email) VALUES
('T001','Alice','Nguyen','alice.nguyen@school.org'),
('T002','Brian','Lee','brian.lee@school.org'),
('T003','Carla','Patel','carla.patel@school.org')
ON CONFLICT (teacher_code) DO NOTHING;

INSERT INTO students (student_number, first_name, last_name, grade_level) VALUES
('S1001','John','Smith',10),
('S1002','Mia','Johnson',10),
('S1003','Liam','Brown',11),
('S1004','Emma','Davis',12)
ON CONFLICT (student_number) DO NOTHING;

INSERT INTO class_periods (period_code, period_name, sort_order) VALUES
('P1','Period 1',1),
('P2','Period 2',2),
('P3','Period 3',3),
('LUNCH','Lunch',4),
('P4','Period 4',5)
ON CONFLICT (period_code) DO NOTHING;

INSERT INTO bell_schedule (schedule_name, day_of_week, period_id, start_time, end_time)
SELECT 'Regular Day', d.day, p.id, p.start_t, p.end_t
FROM (VALUES (1),(2),(3),(4),(5)) AS d(day)
CROSS JOIN (
    SELECT id, period_code,
        CASE period_code
            WHEN 'P1' THEN TIME '08:00'
            WHEN 'P2' THEN TIME '09:00'
            WHEN 'P3' THEN TIME '10:00'
            WHEN 'LUNCH' THEN TIME '11:00'
            WHEN 'P4' THEN TIME '12:00'
        END AS start_t,
        CASE period_code
            WHEN 'P1' THEN TIME '08:50'
            WHEN 'P2' THEN TIME '09:50'
            WHEN 'P3' THEN TIME '10:50'
            WHEN 'LUNCH' THEN TIME '11:40'
            WHEN 'P4' THEN TIME '12:50'
        END AS end_t
    FROM class_periods
) p
WHERE NOT EXISTS (
    SELECT 1 FROM bell_schedule b
    WHERE b.schedule_name='Regular Day' AND b.day_of_week=d.day AND b.period_id=p.id
);

-- Student schedules (Mon-Fri identical in sample)
INSERT INTO student_schedules (student_id, day_of_week, period_id, room_id, teacher_id, course_name)
SELECT s.id, d.day, p.id,
CASE p.period_code WHEN 'P1' THEN r101.id WHEN 'P2' THEN r102.id WHEN 'P3' THEN r101.id WHEN 'P4' THEN r102.id ELSE gym.id END,
CASE p.period_code WHEN 'P1' THEN t1.id WHEN 'P2' THEN t2.id WHEN 'P3' THEN t3.id WHEN 'P4' THEN t2.id ELSE t3.id END,
CASE p.period_code WHEN 'P1' THEN 'Algebra' WHEN 'P2' THEN 'Biology' WHEN 'P3' THEN 'English' WHEN 'P4' THEN 'Chemistry' ELSE 'Lunch' END
FROM students s
JOIN (VALUES (1),(2),(3),(4),(5)) d(day) ON TRUE
JOIN class_periods p ON p.period_code IN ('P1','P2','P3','LUNCH','P4')
JOIN rooms r101 ON r101.room_code='101'
JOIN rooms r102 ON r102.room_code='102'
JOIN rooms gym ON gym.room_code='GYM'
JOIN teachers t1 ON t1.teacher_code='T001'
JOIN teachers t2 ON t2.teacher_code='T002'
JOIN teachers t3 ON t3.teacher_code='T003'
ON CONFLICT (student_id, day_of_week, period_id) DO NOTHING;

INSERT INTO teacher_schedules (teacher_id, day_of_week, period_id, room_id, course_name)
SELECT t.id, d.day, p.id,
CASE
    WHEN t.teacher_code='T001' THEN r101.id
    WHEN t.teacher_code='T002' THEN r102.id
    ELSE gym.id
END,
CASE
    WHEN t.teacher_code='T001' THEN 'Algebra'
    WHEN t.teacher_code='T002' THEN 'Science'
    ELSE 'Advisory'
END
FROM teachers t
JOIN (VALUES (1),(2),(3),(4),(5)) d(day) ON TRUE
JOIN class_periods p ON p.period_code IN ('P1','P2','P3','P4')
JOIN rooms r101 ON r101.room_code='101'
JOIN rooms r102 ON r102.room_code='102'
JOIN rooms gym ON gym.room_code='GYM'
ON CONFLICT (teacher_id, day_of_week, period_id) DO NOTHING;

-- Sample current-day statuses
INSERT INTO attendance_records (student_id, date_for, period_id, status, notes)
SELECT s.id, CURRENT_DATE, NULL, 'present', 'Daily default mark'
FROM students s
ON CONFLICT DO NOTHING;
