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

const AI_TEST_KEY = 'edu-ai-test-data';
const AI_TEST_RESULTS_KEY = 'edu-ai-test-results';

let aiTestData: AiTestData | null = null;

export const setAiTestData = (data: typeof aiTestData) => {
  aiTestData = data;
  if (data) {
    sessionStorage.setItem(AI_TEST_KEY, JSON.stringify(data));
    clearTestResults();
  } else {
    sessionStorage.removeItem(AI_TEST_KEY);
  }
};

export const getAiTestData = (): AiTestData | null => {
  if (aiTestData) return aiTestData;
  const saved = sessionStorage.getItem(AI_TEST_KEY);
  if (!saved) return null;
  try {
    aiTestData = JSON.parse(saved) as AiTestData;
    return aiTestData;
  } catch {
    return null;
  }
};

export const clearAiTestData = () => {
  aiTestData = null;
  sessionStorage.removeItem(AI_TEST_KEY);
};

export const saveTestResults = (payload: {
  analysis: AiTestAnalysis;
  answers: AiTestAnswer[];
}) => {
  sessionStorage.setItem(AI_TEST_RESULTS_KEY, JSON.stringify(payload));
};

export const getTestResults = (): {
  analysis: AiTestAnalysis;
  answers: AiTestAnswer[];
} | null => {
  const saved = sessionStorage.getItem(AI_TEST_RESULTS_KEY);
  if (!saved) return null;
  try {
    return JSON.parse(saved) as { analysis: AiTestAnalysis; answers: AiTestAnswer[] };
  } catch {
    return null;
  }
};

export const clearTestResults = () => {
  sessionStorage.removeItem(AI_TEST_RESULTS_KEY);
};

export const notifyTestComplete = () => {
  window.dispatchEvent(new CustomEvent('edu-test-complete'));
};

const API_BASE = '/api';

function sanitizeUserMessage(message: string): string {
  return message
    .replace(/sdamgia\.ru/gi, 'банка заданий')
    .replace(/sdamgia/gi, 'банка заданий')
    .replace(/sdamgia-api/gi, 'сервис заданий');
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const raw = (err as { error?: string }).error || `HTTP ${res.status}`;
    throw new Error(sanitizeUserMessage(raw));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  getSubjects: (email?: string) =>
    request<{ subjects: Subject[]; activeSubjectId: string }>(
      email ? `/subjects?email=${encodeURIComponent(email)}` : '/subjects'
    ),

  login: (data: { email: string; password: string }) =>
    request<{
      email: string;
      firstName: string;
      lastName: string;
      examType: string;
      marketing: boolean;
      subjects: string[];
      targets: Record<string, number>;
    }>('/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

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

  getDashboard: (subjectId: string, email?: string, examType?: string) =>
    request<DashboardData>(
      email
        ? `/dashboard?subjectId=${subjectId}&email=${encodeURIComponent(email)}${examType ? `&examType=${encodeURIComponent(examType)}` : ''}`
        : `/dashboard?subjectId=${subjectId}${examType ? `?examType=${encodeURIComponent(examType)}` : ''}`
    ),

  getPlan: (subjectId: string, email?: string) =>
    request<PlanData>(
      `/plan?subjectId=${subjectId}${email ? `&email=${encodeURIComponent(email)}` : ''}`
    ),

  updatePlanTopic: (
    topicId: string,
    subjectId: string,
    status: 'completed' | 'in-progress' | 'pending',
    email?: string,
    progress?: number
  ) =>
    request<PlanData>(`/plan/topics/${topicId}?subjectId=${subjectId}`, {
      method: 'PATCH',
      body: JSON.stringify({ subjectId, status, email, progress }),
    }),

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

  checkTask: (taskId: string, answerId: number, email?: string) =>
    request<TaskCheckResult>(`/tasks/${taskId}/check`, {
      method: 'POST',
      body: JSON.stringify({ answerId, ...(email ? { email } : {}) }),
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

  chat: (message: string, subjectId?: string, taskContext?: string) =>
    request<{ role: string; content: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, subjectId, taskContext }),
    }),

  generateTest: (
    subjectId: string,
    topic = 'диагностика по предмету',
    count = 5,
    topicName?: string,
    examType?: string,
    email?: string
  ) =>
    request<AiTestData>('/generate-test', {
      method: 'POST',
      body: JSON.stringify({
        subjectId,
        topic,
        count,
        ...(topicName ? { topicName } : {}),
        ...(examType ? { examType } : {}),
        ...(email ? { email } : {}),
      }),
    }),

  generateTestWithSubjects: (
    subjectIds: string[],
    topic = 'диагностика по предмету',
    count = 3,
    email?: string,
    examType?: string
  ) =>
    request<AiTestData>('/generate-test', {
      method: 'POST',
      body: JSON.stringify({ subjectIds, topic, count, email, examType }),
    }),

  analyzeTestResults: (
    subjectId: string,
    answers: AiTestAnswer[],
    subjectIds?: string[],
    email?: string,
    examType?: string
  ) =>
    request<AiTestAnalysis>(
      `/analyze-test?subjectId=${subjectId}${email ? `&email=${encodeURIComponent(email)}` : ''}`,
      {
        method: 'POST',
        body: JSON.stringify({ answers, subjectIds, subjectId, email, examType }),
      }
    ),
};
