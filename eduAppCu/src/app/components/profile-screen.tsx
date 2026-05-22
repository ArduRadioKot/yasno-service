import { LogOut, Mail, Target, UserRound } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { formatTargetShort } from '../utils/exam';

const subjectLabels: Record<string, string> = {
  math: 'Математика',
  physics: 'Физика',
  russian: 'Русский язык',
  history: 'История',
  chemistry: 'Химия',
  informatics: 'Информатика',
  biology: 'Биология',
  geography: 'География',
  literature: 'Литература',
  french: 'Французский язык',
  social: 'Обществознание',
};

export default function ProfileScreen() {
  const { account, logout, activeSubject } = useApp();
  const name = `${account.firstName || 'Ученик'} ${account.lastName || ''}`.trim();

  return (
    <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
      <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="bg-white border border-border rounded-2xl p-6 shadow-sm mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
            <div className="flex items-center gap-4">
              <div className="size-16 rounded-2xl bg-[#6D3DF5]/10 border border-[#6D3DF5]/20 flex items-center justify-center text-[#6D3DF5] text-2xl font-bold">
                {name[0]?.toUpperCase() || 'У'}
              </div>
              <div>
                <h1 className="text-2xl font-bold">{name}</h1>
                <p className="text-muted-foreground">{account.examType} · AI-подготовка</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl border border-destructive/20 bg-destructive/5 text-destructive font-semibold hover:bg-destructive/10 transition-colors"
            >
              <LogOut className="size-5" />
              Выйти
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-border rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="size-11 rounded-2xl bg-[#6D3DF5]/10 flex items-center justify-center">
                <UserRound className="size-5 text-[#6D3DF5]" />
              </div>
              <h2 className="font-semibold text-lg">Личные данные</h2>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Имя</p>
                <p className="font-medium">{name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Почта</p>
                <div className="flex items-center gap-2 font-medium">
                  <Mail className="size-4 text-muted-foreground" />
                  {account.email}
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Текущий предмет</p>
                <p className="font-medium">{activeSubject?.name ?? 'Не выбран'}</p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-border rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="size-11 rounded-2xl bg-[#6D3DF5]/10 flex items-center justify-center">
                <Target className="size-5 text-[#6D3DF5]" />
              </div>
              <h2 className="font-semibold text-lg">Цели</h2>
            </div>
            <div className="space-y-3">
              {account.subjects.map((subjectId) => (
                <div key={subjectId} className="flex items-center justify-between gap-4 rounded-2xl bg-muted/50 px-4 py-3">
                  <span className="font-medium">{subjectLabels[subjectId] ?? subjectId}</span>
                  <span className="font-bold text-[#6D3DF5]">
                    {formatTargetShort(account.targets[subjectId], account.examType)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
