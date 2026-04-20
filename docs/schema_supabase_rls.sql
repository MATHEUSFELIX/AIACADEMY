-- Apply on Supabase (or Postgres with auth.uid() / auth.role() from Supabase helpers).
-- Run after docs/schema.sql

ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE procedural_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE xp_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY students_self ON students
  FOR ALL USING (auth.uid() = auth_user_id);

CREATE POLICY slp_self ON student_lesson_progress
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY episodic_self ON episodic_memory
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY procedural_self ON procedural_memory
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY submissions_self ON exercise_submissions
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY objectives_self ON student_objectives
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY xp_self ON xp_transactions
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
CREATE POLICY lessons_read ON lessons
  FOR SELECT USING (auth.role() = 'authenticated' AND is_active = TRUE);
