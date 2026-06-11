import { useEffect, useState } from 'react';
import DashboardScreen from './components/dashboard-screen';
import TaskScreen from './components/task-screen';
import PlanScreen from './components/plan-screen';
import ChatScreen from './components/chat-screen';
import AuthScreen from './components/auth-screen';
import ProfileScreen from './components/profile-screen';
import BottomNav from './components/bottom-nav';
import SidebarNav from './components/sidebar-nav';
import { LoadingProgress } from './components/LoadingProgress';
import { AppProvider, useApp } from './context/AppContext';
import { api, setAiTestData } from './api/client';
import type { UserAccount } from './types';

const ACCOUNT_KEY = 'edu-user-account';
const SESSION_KEY = 'edu-user-session';
const AUTO_DIAGNOSTIC_KEY = 'edu-auto-diagnostic';

function ApiBanner() {
  const { error } = useApp();
  if (!error) return null;
  return (
    <div className="bg-destructive/10 text-destructive px-4 py-2 text-sm text-center border-b border-destructive/20 shrink-0">
      {error} — в отдельном терминале: <strong>npm run backend</strong>
    </div>
  );
}

function AppShell({
  activeTab,
  setActiveTab,
}: {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}) {
  const { account, setActiveSubject } = useApp();
  const [autoStarting, setAutoStarting] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(AUTO_DIAGNOSTIC_KEY) !== '1') return;
    localStorage.removeItem(AUTO_DIAGNOSTIC_KEY);
    const subjectIds = account.subjects.length > 0 ? account.subjects : ['math'];
    let cancelled = false;
    setAutoStarting(true);
    
    // Set first subject as active, but generate test for all selected subjects
    const firstSubjectId = subjectIds[0];
    setActiveSubject(firstSubjectId)
      .then(() =>
        api.generateTestWithSubjects(
          subjectIds,
          'первичная диагностика',
          3,
          account.email,
          account.examType
        )
      )
      .then((test) => {
        if (cancelled) return;
        if (!test.questions?.length) {
          throw new Error('Не удалось загрузить задания для первичной диагностики');
        }
        setAiTestData({ ...test, subjectIds });
        setActiveTab('task');
      })
      .catch((error) => {
        if (!cancelled) {
          console.error('Primary diagnostic failed:', error);
        }
      })
      .finally(() => {
        if (!cancelled) setAutoStarting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [account.subjects, account.examType, setActiveSubject, setActiveTab]);

  const renderScreen = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardScreen />;
      case 'task':
        return <TaskScreen />;
      case 'plan':
        return <PlanScreen />;
      case 'chat':
        return <ChatScreen />;
      case 'profile':
        return <ProfileScreen />;
      default:
        return <DashboardScreen />;
    }
  };

  return (
    <div className="min-h-dvh flex flex-col bg-background">
      <ApiBanner />
      <div className="flex flex-1 flex-col md:flex-row min-h-0">
        <SidebarNav activeTab={activeTab} onTabChange={setActiveTab} />
        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          <main className="flex-1 overflow-hidden">{renderScreen()}</main>
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </div>
      {autoStarting && (
        <div className="fixed inset-0 z-50 bg-[#F3F4F6]/90 backdrop-blur-sm flex items-center justify-center p-6">
          <LoadingProgress
            title="Ясно! составляет тест"
            description="Проверим стартовый уровень и соберём план подготовки."
            stages={[
              'Подбираем задания по выбранным предметам…',
              'Загружаем условия из банка…',
              'Готовим первичную диагностику…',
            ]}
          />
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [account, setAccount] = useState<UserAccount | null>(() => {
    if (!localStorage.getItem(SESSION_KEY)) return null;
    const saved = localStorage.getItem(ACCOUNT_KEY);
    if (!saved) return null;
    try {
      return JSON.parse(saved) as UserAccount;
    } catch {
      localStorage.removeItem(ACCOUNT_KEY);
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
  });

  const handleAuthComplete = (nextAccount: UserAccount, options?: { startDiagnostic?: boolean }) => {
    localStorage.setItem(ACCOUNT_KEY, JSON.stringify(nextAccount));
    localStorage.setItem(SESSION_KEY, 'active');
    if (options?.startDiagnostic) {
      localStorage.setItem(AUTO_DIAGNOSTIC_KEY, '1');
    }
    setAccount(nextAccount);
    setActiveTab('dashboard');
  };

  const handleAccountChange = (nextAccount: UserAccount) => {
    localStorage.setItem(ACCOUNT_KEY, JSON.stringify(nextAccount));
    setAccount(nextAccount);
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setAccount(null);
    setActiveTab('dashboard');
  };

  if (!account) {
    return <AuthScreen onComplete={handleAuthComplete} />;
  }

  return (
    <AppProvider
      account={account}
      onAccountChange={handleAccountChange}
      onLogout={handleLogout}
      onNavigateToTasks={() => setActiveTab('task')}
      onNavigateToPlan={() => setActiveTab('plan')}
      onNavigateToChat={() => setActiveTab('chat')}
    >
      <AppShell activeTab={activeTab} setActiveTab={setActiveTab} />
    </AppProvider>
  );
}
