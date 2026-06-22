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
import { LoadingOverlay } from './components/LoadingOverlay';
import { AppProvider, useApp } from './context/AppContext';
import { api, setAiTestData, clearAuthToken } from './api/client';
import type { UserAccount } from './types';
import LandingPage from './components/LandingPage';

const SESSION_KEY = 'edu-user-session';
const AUTO_DIAGNOSTIC_KEY = 'edu-auto-diagnostic';
const TOKEN_KEY = 'edu-auth-token';

function ApiBanner() {
  const { error } = useApp();
  if (!error) return null;
  return (
    <div className="bg-destructive/10 text-destructive px-4 py-2 text-sm text-center border-b border-destructive/20 shrink-0">
      {error} — проверьте подключенние к интернету или перезагрузите страницу
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
          <main className="flex-1 min-h-0 overflow-hidden pb-[4.75rem] md:pb-0">{renderScreen()}</main>
          <div className="md:hidden shrink-0">
            <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
          </div>
        </div>
      </div>
      {autoStarting && (
        <LoadingOverlay className="bg-[#F3F4F6]/90">
          <LoadingProgress
            title="Ясно! составляет тест"
            description="Проверим стартовый уровень и соберём план подготовки."
            stages={[
              'Подбираем задания по выбранным предметам…',
              'Загружаем условия из банка…',
              'Готовим первичную диагностику…',
            ]}
          />
        </LoadingOverlay>
      )}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [account, setAccount] = useState<UserAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLanding, setShowLanding] = useState(true);

  useEffect(() => {
    // Check for JWT token
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }

    // If user has token, skip landing page
    setShowLanding(false);

    // Fetch user data from backend
    api.getCurrentUser()
      .then((user) => {
        const userAccount: UserAccount = {
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          examType: user.examType === 'ОГЭ' ? 'ОГЭ' : 'ЕГЭ',
          subjects: user.subjects.length ? user.subjects : ['math'],
          targets: user.targets,
          marketing: user.marketing,
        };
        setAccount(userAccount);
      })
      .catch(() => {
        // Token invalid, clear it
        localStorage.removeItem(TOKEN_KEY);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleAuthComplete = (nextAccount: UserAccount, options?: { startDiagnostic?: boolean }) => {
    localStorage.setItem(SESSION_KEY, 'active');
    if (options?.startDiagnostic) {
      localStorage.setItem(AUTO_DIAGNOSTIC_KEY, '1');
    }
    setAccount(nextAccount);
    setActiveTab('dashboard');
    setShowLanding(false);
  };

  const handleGetStarted = () => {
    setShowLanding(false);
  };

  const handleAccountChange = (nextAccount: UserAccount) => {
    setAccount(nextAccount);
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(TOKEN_KEY);
    clearAuthToken();
    setAccount(null);
    setActiveTab('dashboard');
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#F3F4F6]">
        <div className="text-center">
          <div className="size-8 border-4 border-[#6D3DF5] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (showLanding) {
    return <LandingPage onGetStarted={handleGetStarted} />;
  }

  if (!account) {
    return <AuthScreen onComplete={handleAuthComplete} onBack={() => setShowLanding(true)} />;
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
