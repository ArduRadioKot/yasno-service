import { Home, BookOpen, BarChart3, MessageCircle, UserRound } from 'lucide-react';

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

type BottomNavProps = {
  activeTab: string;
  onTabChange: (tab: string) => void;
};

export default function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  return (
    <nav className="md:hidden shrink-0 bg-white border-t border-border z-40">
      <div className="max-w-lg mx-auto px-2 py-2">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex flex-col items-center gap-1 px-3 sm:px-6 py-2.5 rounded-2xl transition-all ${
                  isActive
                    ? 'bg-[#6D3DF5]/10'
                    : 'hover:bg-muted/50'
                }`}
              >
                <Icon
                  className={`size-6 transition-colors ${
                    isActive
                      ? 'text-[#6D3DF5]'
                      : 'text-muted-foreground'
                  }`}
                />
                <span
                  className={`text-xs font-medium transition-colors ${
                    isActive
                      ? 'text-[#6D3DF5]'
                      : 'text-muted-foreground'
                  }`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
