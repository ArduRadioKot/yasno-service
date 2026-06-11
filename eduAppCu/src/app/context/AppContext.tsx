import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api } from '../api/client';
import type { Subject, UserAccount, PremiumStatus } from '../types';

const STORAGE_KEY = 'edu-active-subject';

type AppContextValue = {
  subjects: Subject[];
  activeSubjectId: string;
  activeSubject: Subject | null;
  loading: boolean;
  error: string | null;
  setActiveSubject: (id: string) => Promise<void>;
  refreshSubjects: () => Promise<void>;
  onStartLesson: () => void;
  onNavigateToPlan: () => void;
  onNavigateToChat: (prompt?: string, subjectId?: string) => void;
  pendingChatPrompt: string | null;
  clearPendingChatPrompt: () => void;
  taskSessionKey: number;
  account: UserAccount;
  updateAccount: (account: UserAccount) => void;
  premium: PremiumStatus | null;
  refreshPremium: () => Promise<void>;
  logout: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({
  children,
  onNavigateToTasks,
  onNavigateToPlan,
  onNavigateToChat,
  account,
  onAccountChange,
  onLogout,
}: {
  children: ReactNode;
  onNavigateToTasks: () => void;
  onNavigateToPlan: () => void;
  onNavigateToChat: (prompt?: string, subjectId?: string) => void;
  account: UserAccount;
  onAccountChange: (account: UserAccount) => void;
  onLogout: () => void;
}) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [activeSubjectId, setActiveSubjectId] = useState(
    () => localStorage.getItem(STORAGE_KEY) || 'physics'
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskSessionKey, setTaskSessionKey] = useState(0);
  const [pendingChatPrompt, setPendingChatPrompt] = useState<string | null>(null);
  const [premium, setPremium] = useState<PremiumStatus | null>(null);

  const refreshPremium = useCallback(async () => {
    try {
      const status = await api.getPremiumStatus(account.email);
      setPremium(status);
    } catch {
      setPremium({
        isPremium: false,
        daysLeft: 0,
        message: 'Не удалось проверить статус подписки',
      });
    }
  }, [account.email]);

  const refreshSubjects = useCallback(async () => {
    try {
      await api.health();
      setError(null);
      const data = await api.getSubjects(account.email);
      setSubjects(data.subjects);
      const stored = localStorage.getItem(STORAGE_KEY);
      const id =
        stored && data.subjects.some((s) => s.id === stored)
          ? stored
          : data.activeSubjectId;
      setActiveSubjectId(id);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Ошибка загрузки';
      if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
        setError('Backend недоступен — запустите: npm run backend');
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [account.email]);

  useEffect(() => {
    refreshSubjects();
    refreshPremium();
  }, [refreshSubjects, refreshPremium]);

  const setActiveSubject = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.setSubject(id);
      setActiveSubjectId(id);
      localStorage.setItem(STORAGE_KEY, id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сменить предмет');
    }
  }, []);

  const activeSubject =
    subjects.find((s) => s.id === activeSubjectId) ?? null;

  const onStartLesson = useCallback(() => {
    setTaskSessionKey((k) => k + 1);
    onNavigateToTasks();
  }, [onNavigateToTasks]);

  const handleNavigateToChat = useCallback(
    async (prompt?: string, subjectId?: string) => {
      if (subjectId && subjectId !== activeSubjectId) {
        await setActiveSubject(subjectId);
      }
      if (prompt) {
        setPendingChatPrompt(prompt);
      }
      onNavigateToChat();
    },
    [activeSubjectId, onNavigateToChat, setActiveSubject]
  );

  const clearPendingChatPrompt = useCallback(() => {
    setPendingChatPrompt(null);
  }, []);

  return (
    <AppContext.Provider
      value={{
        subjects,
        activeSubjectId,
        activeSubject,
        loading,
        error,
        setActiveSubject,
        refreshSubjects,
        onStartLesson,
        onNavigateToPlan,
        onNavigateToChat: handleNavigateToChat,
        pendingChatPrompt,
        clearPendingChatPrompt,
        taskSessionKey,
        account,
        updateAccount: onAccountChange,
        premium,
        refreshPremium,
        logout: onLogout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
