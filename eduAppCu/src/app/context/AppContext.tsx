import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api } from '../api/client';
import type { Subject, UserAccount } from '../types';

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
  taskSessionKey: number;
  account: UserAccount;
  updateAccount: (account: UserAccount) => void;
  logout: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({
  children,
  onNavigateToTasks,
  account,
  onAccountChange,
  onLogout,
}: {
  children: ReactNode;
  onNavigateToTasks: () => void;
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

  const refreshSubjects = useCallback(async () => {
    try {
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
      setError(e instanceof Error ? e.message : 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, [account.email]);

  useEffect(() => {
    refreshSubjects();
  }, [refreshSubjects]);

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
        taskSessionKey,
        account,
        updateAccount: onAccountChange,
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
