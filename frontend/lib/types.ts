export interface StudentMe {
  id: string;
  name: string;
  email: string;
  profile: string | null;
  current_level: string;
  total_xp: number;
  streak_days?: number;
  diagnostic_status: string;
  onboarding_done: boolean;
  stats: {
    lessons_completed: number;
    lessons_available: number;
    lessons_locked: number;
    avg_score: number | null;
  };
}

export interface LessonSummary {
  id: string;
  title: string;
  module: string;
  level_number: number;
  status: string;
  xp_reward: number;
}
