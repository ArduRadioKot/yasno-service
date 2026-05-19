export type Subject = {
  id: string;
  name: string;
  exam: string;
  icon: string;
  color: string;
  targetScore: number;
  daysToExam: number;
};

export type UserAccount = {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  examType: 'ОГЭ' | 'ЕГЭ';
  subjects: string[];
  targets: Record<string, number>;
  marketing: boolean;
};

export type TaskAnswer = {
  id: number;
  text: string;
};

export type Task = {
  id: string;
  subjectId: string;
  topic: string;
  difficulty: string;
  question: string;
  given: string[];
  answers: TaskAnswer[];
  index: number;
  total: number;
};

export type TaskCheckResult = {
  correct: boolean;
  correctAnswerId: number;
  explanation: {
    wrongHint: string;
    steps: string[];
    tip: string;
  };
};

export type AiTestQuestion = {
  topic: string;
  question: string;
  answers: string[];
  correctIndex: number;
};

export type AiTestData = {
  topic: string;
  questions: AiTestQuestion[];
  subjects?: string[];
};

export type AiTestAnswer = {
  topic: string;
  question: string;
  selectedAnswer: string;
  correctAnswer: string;
  correct: boolean;
};

export type AiTestAnalysis = {
  analysis: string;
  gaps: string[];
  score: number;
  level: string;
};

export type PlanTopic = {
  id: string;
  name: string;
  progress: number;
  status: string;
  impact: string;
};

export type PlanSection = {
  category: string;
  priority: 'high' | 'medium' | 'completed';
  items: PlanTopic[];
};

export type PlanData = {
  subject: Subject;
  targetScore: number;
  daysToExam: number;
  currentScore: number;
  milestones: { date: string; score: number; current: boolean }[];
  forecast: string;
  weeklyGoal: string;
  weeklyProgress: number;
  weeklyTasksDone: number;
  weeklyTasksTotal: number;
  sections: PlanSection[];
};

export type DashboardData = {
  userName: string;
  subject: Subject;
  score: number;
  scoreDelta: number;
  chart: { day: number; score: number }[];
  streak: number;
  achievements: number;
  weakTopics: { topic: string; progress: number; color: string }[];
  recommendation: string;
  dailyPlanRemaining: number;
  tasksTotal: number;
  tasksCompleted: number;
};

export type ChatMessage = {
  id: number;
  role: 'user' | 'assistant';
  content: string;
};
