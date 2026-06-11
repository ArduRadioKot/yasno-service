import { useState } from 'react';
import { Crown, Loader2, LogOut, Mail, Sparkles, Target, UserRound } from 'lucide-react';
import { api } from '../api/client';
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

function formatExpiry(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('ru-RU');
}

export default function ProfileScreen() {
  const { account, logout, activeSubject, premium, refreshPremium } = useApp();
  const [premiumKey, setPremiumKey] = useState('');
  const [activating, setActivating] = useState(false);
  const [premiumMessage, setPremiumMessage] = useState('');
  const [premiumError, setPremiumError] = useState('');
  const name = `${account.firstName || 'Ученик'} ${account.lastName || ''}`.trim();

  const handleActivatePremium = async () => {
    const key = premiumKey.trim();
    if (!key) {
      setPremiumError('Введите ключ премиум подписки');
      setPremiumMessage('');
      return;
    }

    setActivating(true);
    setPremiumError('');
    setPremiumMessage('');

    try {
      const result = await api.activatePremiumKey(key, account.email);
      setPremiumMessage(result.message || 'Ключ успешно активирован');
      setPremiumKey('');
      await refreshPremium();
    } catch (error) {
      setPremiumError(
        error instanceof Error ? error.message : 'Не удалось активировать ключ'
      );
    } finally {
      setActivating(false);
    }
  };

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

        <div className="bg-white border border-border rounded-2xl p-6 shadow-sm mb-6">
          <div className="flex items-center gap-3 mb-5">
            <div className="size-11 rounded-2xl bg-[#6D3DF5]/10 flex items-center justify-center">
              <Crown className="size-5 text-[#6D3DF5]" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">Премиум подписка</h2>
              <p className="text-sm text-muted-foreground">
                Открывает доступ к ИИ-ментору в чате
              </p>
            </div>
          </div>

          {premium?.isPremium ? (
            <div className="rounded-2xl border border-[#6D3DF5]/20 bg-[#6D3DF5]/5 px-4 py-4">
              <div className="flex items-center gap-2 text-[#6D3DF5] font-semibold mb-2">
                <Sparkles className="size-4" />
                Премиум активен
              </div>
              <p className="text-sm text-muted-foreground">
                {premium.daysLeft > 0
                  ? `Осталось ${premium.daysLeft} дн.`
                  : 'Подписка активна'}
                {premium.expiresAt ? ` · до ${formatExpiry(premium.expiresAt)}` : ''}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Получите ключ через Telegram-бота или от администратора, затем активируйте его здесь.
              </p>
              <input
                type="text"
                value={premiumKey}
                onChange={(event) => {
                  setPremiumKey(event.target.value);
                  setPremiumError('');
                  setPremiumMessage('');
                }}
                placeholder="PREMIUM-XXXXXXXXXXXXXXXX"
                className="w-full h-12 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] px-4 text-base outline-none focus:border-[#6D3DF5] focus:bg-white transition-colors"
              />
              {premiumError && <p className="text-sm text-destructive">{premiumError}</p>}
              {premiumMessage && <p className="text-sm text-[#6D3DF5]">{premiumMessage}</p>}
              <button
                type="button"
                onClick={handleActivatePremium}
                disabled={activating}
                className="inline-flex items-center justify-center gap-2 h-12 px-5 rounded-xl bg-[#6D3DF5] text-white font-semibold disabled:opacity-60"
              >
                {activating ? <Loader2 className="size-4 animate-spin" /> : null}
                Активировать ключ
              </button>
            </div>
          )}
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
