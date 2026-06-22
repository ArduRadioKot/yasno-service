import { useMemo, useState } from 'react';
import { ChevronDown, ChevronLeft, Eye, EyeOff } from 'lucide-react';
import type { UserAccount } from '../types';
import { api } from '../api/client';
import {
  clampTargetForExam,
  defaultTargetForExam,
  normalizeTargetsForExam,
  OGE_GRADES,
} from '../utils/exam';

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

const defaultTargets = {
  math: 90,
  physics: 85,
  russian: 88,
};

type AuthScreenProps = {
  onComplete: (account: UserAccount, options?: { startDiagnostic?: boolean }) => void;
  onBack?: () => void;
};

function AuthLogo() {
  return <img src="/logo.png" alt="Логотип" className="mx-auto mb-8 size-16 object-contain" />;
}

function Progress({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-1.5 w-60 mx-auto">
      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className={`h-1.5 flex-1 rounded-full ${item <= step ? 'bg-[#6D3DF5]' : 'bg-[#E0E0E4]'}`}
        />
      ))}
    </div>
  );
}

function Field({
  label,
  placeholder,
  type = 'text',
  value,
  onChange,
  withEye,
}: {
  label: string;
  placeholder: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  withEye?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const inputType = withEye ? (visible ? 'text' : 'password') : type;
  return (
    <label className="block">
      <span className="block text-sm font-medium text-[#707076] mb-2">{label}</span>
      <div className="relative">
        <input
          type={inputType}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="w-full h-13 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] px-4 text-base outline-none focus:border-[#6D3DF5] focus:bg-white transition-colors"
        />
        {withEye && (
          <button
            type="button"
            onClick={() => setVisible((current) => !current)}
            className="absolute right-3 top-1/2 -translate-y-1/2 size-8 flex items-center justify-center text-[#B8B8C0] hover:text-[#6D3DF5]"
            aria-label={visible ? 'Скрыть пароль' : 'Показать пароль'}
          >
            {visible ? <Eye className="size-5" /> : <EyeOff className="size-5" />}
          </button>
        )}
      </div>
    </label>
  );
}

export default function AuthScreen({ onComplete, onBack }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [account, setAccount] = useState<UserAccount>({
    email: '',
    password: '',
    firstName: '',
    lastName: '',
    examType: 'ЕГЭ',
    subjects: ['math', 'physics', 'russian'],
    targets: defaultTargets,
    marketing: false,
  });
  const [repeatPassword, setRepeatPassword] = useState('');
  const [offerAccepted, setOfferAccepted] = useState(false);
  const [subjectsOpen, setSubjectsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const selectedSubjectsText = useMemo(
    () => account.subjects.map((id) => subjectLabels[id]).join(', '),
    [account.subjects]
  );

  const update = (patch: Partial<UserAccount>) => {
    setError('');
    setAccount((current) => ({ ...current, ...patch }));
  };

  const saveAndEnter = async (nextAccount: UserAccount) => {
    try {
      await api.register({
        email: nextAccount.email,
        password: nextAccount.password || "",
        firstName: nextAccount.firstName,
        lastName: nextAccount.lastName,
        examType: nextAccount.examType,
        marketing: nextAccount.marketing,
        subjects: nextAccount.subjects,
        targets: nextAccount.targets,
      });
      onComplete(nextAccount, { startDiagnostic: true });
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Ошибка при регистрации');
    }
  };

  const handleLogin = async () => {
    const email = account.email.trim();
    const password = account.password || '';
    if (!email || !password) {
      setError('Введите почту и пароль');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const user = await api.login({ email, password });
      const nextAccount: UserAccount = {
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        examType: user.examType === 'ОГЭ' ? 'ОГЭ' : 'ЕГЭ',
        subjects: user.subjects.length ? user.subjects : ['math'],
        targets: user.targets,
        marketing: user.marketing,
      };
      onComplete(nextAccount);
    } catch (loginError) {
      setError(
        loginError instanceof Error ? loginError.message : 'Не удалось войти в аккаунт'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterNext = () => {
    if (step === 1) {
      const strongPassword =
        account.password.length >= 8 &&
        /[A-ZА-Я]/.test(account.password) &&
        /[a-zа-я]/.test(account.password) &&
        /[^A-Za-zА-Яа-я0-9]/.test(account.password);
      if (!account.email.includes('@') || !strongPassword) {
        setError('Введите почту и надежный пароль');
        return;
      }
      if (account.password !== repeatPassword) {
        setError('Пароли не совпадают');
        return;
      }
      if (!offerAccepted) {
        setError('Нужно согласиться с публичной офертой');
        return;
      }
      setStep(2);
      return;
    }
    if (step === 2) {
      if (!account.firstName.trim() || !account.lastName.trim()) {
        setError('Заполните имя и фамилию');
        return;
      }
      if (!account.subjects.length) {
        setError('Выберите хотя бы один предмет');
        return;
      }
      setStep(3);
      return;
    }
    saveAndEnter({
      ...account,
      targets: normalizeTargetsForExam(
        account.targets,
        account.subjects,
        account.examType
      ),
    });
  };

  return (
    <div className="min-h-dvh bg-[#F3F4F6] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-[520px]">
        {onBack && (
          <button
            onClick={onBack}
            className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-[#6D3DF5] hover:text-[#5a2fd9]"
          >
            <ChevronLeft className="size-4" />
            Назад на главную
          </button>
        )}
        <AuthLogo />
        <div className="bg-white rounded-[18px] border border-[#DDDDE4] shadow-sm px-5 sm:px-6 py-6">
          {mode === 'register' && step > 1 && (
            <div className="grid grid-cols-[1fr_auto_1fr] items-center mb-8">
              <button
                onClick={() => {
                  setError('');
                  setStep((current) => Math.max(1, current - 1));
                }}
                className="inline-flex items-center gap-1 text-sm font-medium text-[#6D3DF5]"
              >
                <ChevronLeft className="size-4" />
                назад
              </button>
              <Progress step={step} />
              <span className="text-sm font-medium text-right">{step}/3</span>
            </div>
          )}

          {mode === 'login' ? (
            <>
              <h1 className="text-2xl font-semibold mb-1">Войти в аккаунт</h1>
              <p className="text-sm text-[#707076] mb-8">Чтобы получить доступ к задачам</p>
              <div className="space-y-5">
                <Field label="Почта" placeholder="email@example.com" value={account.email} onChange={(email) => update({ email })} />
                <Field label="Пароль" placeholder="пароль" type="password" value={account.password || ""} onChange={(password) => update({ password })} withEye />
              </div>
              {error && <p className="text-sm text-destructive mt-4">{error}</p>}
              <button
                type="button"
                onClick={handleLogin}
                disabled={loading}
                className="w-full h-13 mt-5 rounded-xl bg-[#6D3DF5] text-white font-semibold disabled:opacity-60"
              >
                {loading ? 'Входим…' : 'Войти с помощью почты'}
              </button>
              <div className="flex items-center gap-3 my-8 text-sm text-[#9A9AA2]">
                <div className="h-px bg-[#D8D8DD] flex-1" />
                Нет аккаунта?
                <div className="h-px bg-[#D8D8DD] flex-1" />
              </div>
              <button onClick={() => { setMode('register'); setError(''); }} className="w-full mt-5 text-sm font-semibold text-[#6D3DF5]">
                Создать аккаунт
              </button>
            </>
          ) : (
            <>
              {step === 1 && (
                <>
                  <h1 className="text-2xl font-semibold mb-1">Создайте аккаунт</h1>
                  <p className="text-sm text-[#707076] mb-8">Чтобы получить доступ к задачам</p>
                  <div className="space-y-5">
                    <Field label="Почта" placeholder="email@example.com" value={account.email} onChange={(email) => update({ email })} />
                    <Field label="Пароль" placeholder="Надежный пароль" type="password" value={account.password || ""} onChange={(password) => update({ password })} withEye />
                    <ul className="text-sm text-[#5F5F66] space-y-2 list-disc pl-4">
                      <li>Больше 8 символов</li>
                      <li>Большие и строчные буквы</li>
                      <li>Не менее одного специального символа</li>
                    </ul>
                    <Field label="Повторите пароль" placeholder="Повторите пароль" type="password" value={repeatPassword} onChange={setRepeatPassword} withEye />
                  </div>
                  <label className="flex items-center gap-3 mt-5 text-sm text-[#707076]">
                    <input type="checkbox" checked={account.marketing} onChange={(event) => update({ marketing: event.target.checked })} className="size-5 rounded border-[#DDDDE4]" />
                    Хочу получать рекламную рассылку
                  </label>
                  <label className="flex items-center gap-3 mt-3 text-sm text-[#707076]">
                    <input type="checkbox" checked={offerAccepted} onChange={(event) => { setError(''); setOfferAccepted(event.target.checked); }} className="size-5 rounded border-[#DDDDE4]" />
                    Соглашаюсь с <span className="text-[#6D3DF5]">публичной офертой</span>
                  </label>
                </>
              )}

              {step === 2 && (
                <>
                  <h1 className="text-2xl font-semibold mb-1">Расскажите о себе</h1>
                  <p className="text-sm text-[#707076] mb-8">Чтобы получить доступ к задачам</p>
                  <div className="space-y-5">
                    <Field label="Имя" placeholder="Иван" value={account.firstName} onChange={(firstName) => update({ firstName })} />
                    <Field label="Фамилия" placeholder="Иванов" value={account.lastName} onChange={(lastName) => update({ lastName })} />
                    <div>
                      <p className="text-sm font-medium text-[#707076] mb-2">К чему готовимся?</p>
                      <div className="grid grid-cols-2 gap-2">
                        {(['ОГЭ', 'ЕГЭ'] as const).map((examType) => (
                          <button
                            key={examType}
                            onClick={() =>
                              update({
                                examType,
                                targets: normalizeTargetsForExam(
                                  account.targets,
                                  account.subjects,
                                  examType
                                ),
                              })
                            }
                            className={`h-13 rounded-xl border ${account.examType === examType ? 'border-[#6D3DF5] bg-white' : 'border-[#DDDDE4] bg-[#F7F7FA]'} font-medium`}
                          >
                            {examType}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button
                      onClick={() => setSubjectsOpen((open) => !open)}
                      className="w-full h-13 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] px-4 flex items-center justify-between text-[#9A9AA2]"
                    >
                      <span className="truncate">{selectedSubjectsText || 'Выберите предметы'}</span>
                      <ChevronDown className="size-5" />
                    </button>
                    {subjectsOpen && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {Object.entries(subjectLabels).map(([subjectId, label]) => {
                          const selected = account.subjects.includes(subjectId);
                          return (
                            <button
                              key={subjectId}
                              onClick={() => {
                                const subjects = selected
                                  ? account.subjects.filter((id) => id !== subjectId)
                                  : [...account.subjects, subjectId];
                                update({
                                  subjects,
                                  targets: {
                                    ...account.targets,
                                    [subjectId]:
                                      account.targets[subjectId] ??
                                      defaultTargetForExam(account.examType),
                                  },
                                });
                              }}
                              className={`h-11 rounded-xl border text-sm font-medium ${
                                selected
                                  ? 'border-[#6D3DF5] bg-[#6D3DF5]/5 text-[#6D3DF5]'
                                  : 'border-[#DDDDE4] bg-[#F7F7FA] text-[#707076]'
                              }`}
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </>
              )}

              {step === 3 && (
                <>
                  <h1 className="text-2xl font-semibold mb-1">К какому результату идем?</h1>
                  <p className="text-sm text-[#707076] mb-8">
                    {account.examType === 'ОГЭ'
                      ? 'Выберите целевую оценку на экзамен (от 2 до 5)'
                      : 'Укажите целевой балл на экзамен (0–100)'}
                  </p>
                  <div className="space-y-5">
                    {account.subjects.map((subjectId) => {
                      const current = clampTargetForExam(
                        account.targets[subjectId],
                        account.examType
                      );
                      return (
                        <div key={subjectId}>
                          <p className="text-sm font-medium text-[#707076] mb-2">
                            {subjectLabels[subjectId]}
                          </p>
                          {account.examType === 'ОГЭ' ? (
                            <div className="grid grid-cols-4 gap-2">
                              {OGE_GRADES.map((grade) => (
                                <button
                                  key={grade}
                                  type="button"
                                  onClick={() =>
                                    update({
                                      targets: { ...account.targets, [subjectId]: grade },
                                    })
                                  }
                                  className={`h-13 rounded-xl border font-semibold text-lg transition-colors ${
                                    current === grade
                                      ? 'border-[#6D3DF5] bg-[#6D3DF5]/10 text-[#6D3DF5]'
                                      : 'border-[#DDDDE4] bg-[#F7F7FA] text-[#707076] hover:border-[#6D3DF5]/40'
                                  }`}
                                >
                                  {grade}
                                </button>
                              ))}
                            </div>
                          ) : (
                            <div className="grid grid-cols-[60px_1fr_60px] gap-2">
                              <button
                                type="button"
                                onClick={() =>
                                  update({
                                    targets: {
                                      ...account.targets,
                                      [subjectId]: Math.max(0, current - 1),
                                    },
                                  })
                                }
                                className="h-13 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] text-[#9A9AA2]"
                              >
                                -
                              </button>
                              <div className="h-13 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] flex items-center justify-center text-lg">
                                {current}
                              </div>
                              <button
                                type="button"
                                onClick={() =>
                                  update({
                                    targets: {
                                      ...account.targets,
                                      [subjectId]: Math.min(100, current + 1),
                                    },
                                  })
                                }
                                className="h-13 rounded-xl border border-[#DDDDE4] bg-[#F7F7FA] text-[#9A9AA2]"
                              >
                                +
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}

              {error && <p className="text-sm text-destructive mt-4">{error}</p>}
              <div className={step === 2 ? 'grid grid-cols-2 gap-2 mt-6' : 'mt-6'}>
                {step === 2 && (
                  <button onClick={() => setStep(3)} className="h-13 rounded-xl bg-[#E4D9FF] text-[#6D3DF5] font-semibold">
                    Пропустить
                  </button>
                )}
                <button onClick={handleRegisterNext} className="w-full h-13 rounded-xl bg-[#6D3DF5] text-white font-semibold">
                  Продолжить
                </button>
              </div>
              {step === 1 && (
                <button onClick={() => { setMode('login'); setError(''); }} className="w-full mt-5 text-sm font-semibold text-[#6D3DF5]">
                  Уже есть аккаунт
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
