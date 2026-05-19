import type {
  DashboardData,
  AiTestAnswer,
  AiTestAnalysis,
  AiTestData,
  PlanData,
  Subject,
  Task,
  TaskCheckResult,
} from '../types';

// Store AI-generated test data
let aiTestData: AiTestData | null = null;

export const setAiTestData = (data: typeof aiTestData) => {
  aiTestData = data;
};

export const getAiTestData = () => aiTestData;

export const clearAiTestData = () => {
  aiTestData = null;
};

const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getSubjects: (email?: string) =>
    request<{ subjects: Subject[]; activeSubjectId: string }>(
      email ? `/subjects?email=${encodeURIComponent(email)}` : '/subjects'
    ),

  register: (data: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    examType?: string;
    marketing?: boolean;
    subjects?: string[];
    targets?: Record<string, number>;
  }) =>
    request<{ userId: number; message: string }>('/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  setSubject: (subjectId: string) =>
    request<{ subject: Subject; activeSubjectId: string }>('/user/subject', {
      method: 'PUT',
      body: JSON.stringify({ subjectId }),
    }),

  getDashboard: (subjectId: string, email?: string) =>
    request<DashboardData>(
      email ? `/dashboard?subjectId=${subjectId}&email=${encodeURIComponent(email)}` : `/dashboard?subjectId=${subjectId}`
    ),

  getPlan: (subjectId: string) =>
    request<PlanData>(`/plan?subjectId=${subjectId}`),

  getTask: (taskId: string, subjectId: string) =>
    request<Task>(`/tasks/${taskId}?subjectId=${subjectId}`),

  listTasks: (subjectId: string) =>
    request<{
      tasks: { id: string; topic: string; difficulty: string; question: string }[];
      total: number;
    }>(`/tasks?subjectId=${subjectId}`),

  getFirstTask: async (subjectId: string) => {
    const { tasks } = await api.listTasks(subjectId);
    if (!tasks.length) throw new Error('Нет заданий');
    return api.getTask(tasks[0].id, subjectId);
  },

  checkTask: (taskId: string, answerId: number) =>
    request<TaskCheckResult>(`/tasks/${taskId}/check`, {
      method: 'POST',
      body: JSON.stringify({ answerId }),
    }),

  getNextTask: (taskId: string, subjectId: string) =>
    request<Task>(`/tasks/${taskId}/next?subjectId=${subjectId}`),

  generateTask: (subjectId: string, topic?: string, difficulty = 'medium') =>
    request<Task>('/tasks/generate', {
      method: 'POST',
      body: JSON.stringify({ subjectId, topic, difficulty }),
    }),

  getChatSuggestions: (subjectId: string) =>
    request<{ prompts: { text: string; icon: string }[] }>(
      `/chat/suggestions?subjectId=${subjectId}`
    ),

  chat: (message: string, subjectId?: string) =>
    request<{ response: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, subjectId }),
    }),

  generateTest: (subjectId: string, topic = 'диагностика по предмету', count = 5, email?: string) =>
    request<AiTestData>(
      `/generate-test?subjectId=${subjectId}&topic=${encodeURIComponent(topic)}&count=${count}${email ? `&email=${encodeURIComponent(email)}` : ''}`,
      { method: 'POST' }
    ),

  generateTestWithSubjects: (subjectIds: string[], topic = 'диагностика по предмету', count = 3, email?: string) =>
    request<AiTestData>('/generate-test', {
      method: 'POST',
      body: JSON.stringify({ subjectIds, topic, count, email }),
    }),

  analyzeTestResults: (subjectId: string, answers: AiTestAnswer[], subjectIds?: string[], email?: string) =>
    request<AiTestAnalysis>(
      `/analyze-test?subjectId=${subjectId}${email ? `&email=${encodeURIComponent(email)}` : ''}`,
      {
        method: 'POST',
        body: JSON.stringify({ answers, subjectIds, email }),
      }
    ),
};
