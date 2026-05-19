import { Home, BookOpen, BarChart3, MessageCircle, UserRound, LogOut } from 'lucide-react';
import { useApp } from '../context/AppContext';

type NavItem = {
  id: string;
  icon: typeof Home;
  label: string;
};

const navItems: NavItem[] = [
  { id: 'dashboard', icon: Home, label: 'Главная' },
  { id: 'task', icon: BookOpen, label: 'Задания' },
  { id: 'plan', icon: BarChart3, label: 'План' },
  { id: 'chat', icon: MessageCircle, label: 'AI Чат' },
  { id: 'profile', icon: UserRound, label: 'Кабинет' },
];

type SidebarNavProps = {
  activeTab: string;
  onTabChange: (tab: string) => void;
};

export default function SidebarNav({ activeTab, onTabChange }: SidebarNavProps) {
  const { activeSubject, account, logout } = useApp();
  const name = `${account.firstName || 'Ученик'} ${account.lastName || ''}`.trim();

  return (
    <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-white">
      <div className="flex items-center gap-3 px-6 py-6 border-b border-border">
        <img src="/logo.png" alt="Ясно!" className="size-10 object-contain" />
        <div>
          <p className="font-bold text-lg leading-tight">Ясно!</p>
          <p className="text-xs text-muted-foreground">AI-подготовка</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all text-left ${
                isActive
                  ? 'bg-[#6D3DF5]/10 text-[#6D3DF5]'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              }`}
            >
              <Icon className={`size-5 shrink-0 ${isActive ? 'text-[#6D3DF5]' : ''}`} />
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <button
          onClick={() => onTabChange('profile')}
          className="w-full flex items-center gap-3 px-3 py-3 rounded-2xl bg-muted/50 hover:bg-muted transition-colors text-left"
        >
          <div className="size-10 rounded-xl bg-[#6D3DF5]/10 text-[#6D3DF5] border border-[#6D3DF5]/20 flex items-center justify-center font-semibold shrink-0">
            {name[0]?.toUpperCase() || 'У'}
          </div>
          <div className="min-w-0">
            <p className="font-medium truncate">{name}</p>
            <p className="text-xs text-muted-foreground">
              {activeSubject ? `цель ${activeSubject.targetScore} б.` : 'выбери предмет'}
            </p>
          </div>
        </button>
        <button
          onClick={logout}
          className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-3 rounded-2xl text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors"
        >
          <LogOut className="size-4" />
          Выйти
        </button>
      </div>
    </aside>
  );
}
