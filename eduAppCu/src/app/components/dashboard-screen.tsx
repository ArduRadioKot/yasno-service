import { useEffect, useState } from 'react';
import {
  Target,
  TrendingUp,
  Award,
  Flame,
  Brain,
  ChevronRight,
  Loader2,
  Hand,
  Atom,
  Calculator,
  BookOpen,
  Landmark,
  FlaskConical,
  Laptop,
  Dna,
  Globe,
  ScrollText,
  Languages,
  Users,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { api, setAiTestData } from '../api/client';
import { useApp } from '../context/AppContext';
import { clampTargetForExam, formatTargetShort } from '../utils/exam';
import type { DashboardData, PlanTopicBrief } from '../types';
import SubjectSelector from './subject-selector';
import { LoadingProgress } from './LoadingProgress';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'atom': Atom,
  'calculator': Calculator,
  'book-open': BookOpen,
  'landmark': Landmark,
  'flask-conical': FlaskConical,
  'laptop': Laptop,
  'dna': Dna,
  'globe': Globe,
  'scroll-text': ScrollText,
  'languages': Languages,
  'users': Users,
};

const QUESTION_COUNTS = [3, 5, 8, 10] as const;

function SubjectIcon({ iconName, className }: { iconName: string; className?: string }) {
  const Icon = iconMap[iconName] || Atom;
  return <Icon className={className} />;
}

function QuestionCountPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (count: number) => void;
}) {
  return (
    <div className="py-2">
      <p className="text-sm font-medium text-[#707076] mb-2">Количество вопросов</p>
      <div className="grid grid-cols-4 gap-2">
        {QUESTION_COUNTS.map((count) => (
          <button
            key={count}
            type="button"
            onClick={() => onChange(count)}
            className={`h-11 rounded-xl border font-semibold ${
              value === count
                ? 'border-[#6D3DF5] bg-[#6D3DF5]/5 text-[#6D3DF5]'
                : 'border-border bg-[#F7F7FA] text-muted-foreground'
            }`}
          >
            {count}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function DashboardScreen() {
  const { activeSubjectId, onStartLesson, subjects, setActiveSubject, account, onNavigateToPlan } = useApp();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSubjectModal, setShowSubjectModal] = useState(false);
  const [showAllTopicsModal, setShowAllTopicsModal] = useState(false);
  const [showTopicTestModal, setShowTopicTestModal] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<PlanTopicBrief | null>(null);
  const [generatingTest, setGeneratingTest] = useState(false);
  const [generatingTopicName, setGeneratingTopicName] = useState<string | null>(null);
  const [questionCount, setQuestionCount] = useState(5);
  const [testError, setTestError] = useState<string | null>(null);

  const loadDashboard = () => {
    setLoading(true);
    return api
      .getDashboard(activeSubjectId, account.email, account.examType)
      .then((d) => setData(d))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    loadDashboard().then(() => {
      if (cancelled) return;
    });
    const onTestComplete = () => {
      if (!cancelled) loadDashboard();
    };
    window.addEventListener('edu-test-complete', onTestComplete);
    return () => {
      cancelled = true;
      window.removeEventListener('edu-test-complete', onTestComplete);
    };
  }, [activeSubjectId, account.email, account.examType]);

  const color = '#6D3DF5';
  const userName = account.firstName || data?.userName || 'Ученик';
  const isOge = (data?.examType ?? account.examType) === 'ОГЭ';
  const scoreLabel = data?.scoreLabel ?? (isOge ? 'оценка' : 'баллов');
  const forecastTitle = data?.forecastTitle ?? (isOge ? 'Прогноз ОГЭ' : 'Прогноз ЕГЭ');
  const chartDomain: [number, number] = isOge ? [2, 5] : [0, 100];

  const taskProgressPercent = data
    ? data.tasksTotal > 0
      ? Math.min(100, Math.round((data.tasksCompleted / data.tasksTotal) * 100))
      : 0
    : 0;
  const allTopics = data?.allTopics?.length
    ? data.allTopics
    : (data?.weakTopics ?? []).map((t) => ({
        id: t.id,
        name: t.topic,
        progress: t.progress,
        status: 'pending',
        priority: 'medium',
      }));

  const openTopicTest = (topic: PlanTopicBrief) => {
    setSelectedTopic(topic);
    setTestError(null);
    setShowAllTopicsModal(false);
    setShowTopicTestModal(true);
  };

  const runTest = async (
    subjectId: string,
    topicLabel: string,
    count: number,
    topicName?: string
  ) => {
    setGeneratingTest(true);
    setGeneratingTopicName(topicName ?? null);
    setTestError(null);
    setShowSubjectModal(false);
    setShowTopicTestModal(false);
    setShowAllTopicsModal(false);

    try {
      await setActiveSubject(subjectId);
      const test = await api.generateTest(
        subjectId,
        topicLabel,
        count,
        topicName,
        account.examType,
        account.email
      );
      if (!test.questions?.length) {
        throw new Error('Не удалось загрузить задания для теста');
      }
      setAiTestData(test);
      onStartLesson();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Не удалось загрузить задания';
      setTestError(message);
      if (topicName) {
        setSelectedTopic(
          selectedTopic ?? {
            id: topicName,
            name: topicName,
            progress: 0,
            status: 'pending',
            priority: 'medium',
          }
        );
        setShowTopicTestModal(true);
      } else {
        setShowSubjectModal(true);
      }
      console.error('Failed to generate test:', error);
    } finally {
      setGeneratingTest(false);
      setGeneratingTopicName(null);
    }
  };

  const handleStartLesson = () => {
    setTestError(null);
    setShowSubjectModal(true);
  };

  const handleSubjectSelect = (subjectId: string) => {
    runTest(subjectId, 'диагностика по предмету', questionCount);
  };

  const handleTopicTestStart = () => {
    if (!selectedTopic) return;
    const label = `Тест по теме «${selectedTopic.name}» · ${data?.subject.name ?? ''}`.trim();
    runTest(activeSubjectId, label, questionCount, selectedTopic.name);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#6D3DF5]" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Не удалось загрузить данные. Запустите бэкенд: npm run backend
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 pt-6 md:pt-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-muted-foreground mb-1">Привет,</p>
            <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2">{userName}! <Hand className="size-8" /></h1>
          </div>
          <div className="size-12 rounded-xl flex items-center justify-center text-[#6D3DF5] font-semibold text-lg md:hidden bg-white border border-border">
            {userName[0]}
          </div>
        </div>

        <div className="mb-6">
          <p className="text-sm text-muted-foreground mb-2">Текущий предмет</p>
          <SubjectSelector variant="pills" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="rounded-2xl p-6 shadow-sm border border-border bg-white">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-muted-foreground mb-1">
                    {forecastTitle} · {data.subject.name}
                  </p>
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-4xl sm:text-5xl font-bold text-foreground">{data.score}</h2>
                    <span className="text-muted-foreground text-xl">{scoreLabel}</span>
                  </div>
                </div>
                <div className="bg-[#F7F7FA] rounded-xl px-4 py-2 border border-border">
                  <div className="flex items-center gap-1 text-[#6D3DF5]">
                    <TrendingUp className="size-5" />
                    <span className="font-semibold">+{data.scoreDelta}</span>
                  </div>
                </div>
              </div>
              <div className="h-28 -mx-6 -mb-6 min-h-[112px]">
                {data.chart && data.chart.length > 0 ? (
                  <ResponsiveContainer width="100%" height={112}>
                    <AreaChart data={data.chart} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                      <XAxis dataKey="day" hide />
                      <YAxis hide domain={chartDomain} />
                      <Area
                        type="monotone"
                        dataKey="score"
                        stroke="#6D3DF5"
                        strokeWidth={3}
                        fill="rgba(109, 61, 245, 0.1)"
                        dot={{ r: 3, fill: '#6D3DF5' }}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                    Пройдите диагностику для отображения графика
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="bg-[#F7F7FA] border border-border rounded-xl size-14 flex items-center justify-center">
                    <Flame className="size-7 text-[#6D3DF5]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg mb-1">Серия дней</h3>
                    <p className="text-muted-foreground">Продолжай в том же духе!</p>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className="text-3xl font-bold text-[#6D3DF5]"
                  >
                    {data.streak}
                  </div>
                  <p className="text-sm text-muted-foreground">дней</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-2xl p-5 shadow-sm border border-border">
                <div
                  className="rounded-xl size-12 flex items-center justify-center mb-3 bg-[#F7F7FA] border border-border"
                >
                  <Target className="size-6 text-[#6D3DF5]" />
                </div>
                <h4 className="font-semibold mb-1">План дня</h4>
                <p className="text-sm text-muted-foreground">
                  {data.dailyPlanRemaining} тем осталось
                </p>
              </div>
              <div className="bg-white rounded-2xl p-5 shadow-sm border border-border">
                <div className="bg-[#F7F7FA] border border-border rounded-xl size-12 flex items-center justify-center mb-3">
                  <Award className="size-6 text-[#6D3DF5]" />
                </div>
                <h4 className="font-semibold mb-1">Достижения</h4>
                <p className="text-sm text-muted-foreground">{data.achievements} получено</p>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-4 border border-border">
              <p className="text-sm text-muted-foreground mb-2">Прогресс заданий</p>
              <div className="flex items-center gap-3">
                <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${taskProgressPercent}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <span className="text-sm font-medium shrink-0">
                  {data.tasksCompleted}/{data.tasksTotal}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg">Слабые темы</h3>
                <button
                  type="button"
                  onClick={() => setShowAllTopicsModal(true)}
                  className="text-sm font-medium flex items-center gap-1 text-[#6D3DF5] hover:text-[#5b2fe3]"
                >
                  Все темы
                  <ChevronRight className="size-4" />
                </button>
              </div>
              <div className="space-y-3">
                {data.weakTopics.map((topic) => (
                  <button
                    key={topic.id}
                    type="button"
                    onClick={() =>
                      openTopicTest({
                        id: topic.id,
                        name: topic.topic,
                        progress: topic.progress,
                        status: 'pending',
                        priority: 'medium',
                      })
                    }
                    className="w-full bg-white rounded-2xl p-4 shadow-sm border border-border text-left hover:border-[#6D3DF5]/40 hover:bg-[#6D3DF5]/[0.02] transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-medium">{topic.topic}</span>
                      <span className="text-sm text-muted-foreground">{topic.progress}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${topic.progress}%`,
                          backgroundColor: '#6D3DF5',
                        }}
                      />
                    </div>
                    <p className="text-xs text-[#6D3DF5] mt-2 font-medium">Составить тест по теме</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl p-6 shadow-sm bg-white border border-border">
              <div className="flex items-start gap-4 mb-4">
                <div className="bg-[#F7F7FA] border border-border rounded-xl size-12 flex items-center justify-center shrink-0">
                  <Brain className="size-6 text-[#6D3DF5]" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">Ясно!</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">{data.recommendation}</p>
                </div>
              </div>
              <button
                onClick={handleStartLesson}
                className="w-full bg-[#6D3DF5] text-white font-semibold py-3.5 rounded-xl hover:bg-[#5b2fe3] transition-colors"
              >
                Составить AI-тест
              </button>
            </div>
          </div>
        </div>
      </div>

      <Dialog open={showAllTopicsModal} onOpenChange={setShowAllTopicsModal}>
        <DialogContent className="sm:max-w-md max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Все темы · {data.subject.name}</DialogTitle>
          </DialogHeader>
          <div className="overflow-y-auto flex-1 -mx-1 px-1 space-y-2 py-2">
            {allTopics.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">
                Темы появятся после диагностики или в разделе «План».
              </p>
            ) : (
              allTopics.map((topic) => (
                <button
                  key={topic.id}
                  type="button"
                  onClick={() => openTopicTest(topic)}
                  className="w-full rounded-xl border border-border p-4 text-left hover:border-[#6D3DF5]/40 hover:bg-[#6D3DF5]/[0.02] transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{topic.name}</span>
                    <span className="text-sm text-muted-foreground">{topic.progress}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[#6D3DF5]"
                      style={{ width: `${topic.progress}%` }}
                    />
                  </div>
                  {topic.section && (
                    <p className="text-xs text-muted-foreground mt-2">{topic.section}</p>
                  )}
                </button>
              ))
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setShowAllTopicsModal(false);
              onNavigateToPlan();
            }}
            className="w-full text-sm font-medium text-[#6D3DF5] py-2 hover:text-[#5b2fe3]"
          >
            Открыть подробный план
          </button>
        </DialogContent>
      </Dialog>

      <Dialog open={showTopicTestModal} onOpenChange={setShowTopicTestModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Тест по теме «{selectedTopic?.name ?? ''}»
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Задания подберутся по этой теме и близким разделам, затем ИИ оформит вопросы с вариантами ответов.
          </p>
          <QuestionCountPicker value={questionCount} onChange={setQuestionCount} />
          {testError && (
            <p className="text-sm text-destructive py-1">{testError}</p>
          )}
          <button
            type="button"
            onClick={handleTopicTestStart}
            disabled={!selectedTopic || generatingTest}
            className="w-full bg-[#6D3DF5] text-white font-semibold py-3.5 rounded-xl hover:bg-[#5b2fe3] transition-colors disabled:opacity-50"
          >
            Начать тест
          </button>
        </DialogContent>
      </Dialog>

      <Dialog open={showSubjectModal} onOpenChange={setShowSubjectModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Выберите предмет для теста</DialogTitle>
          </DialogHeader>
          <QuestionCountPicker value={questionCount} onChange={setQuestionCount} />
          {testError && (
            <p className="text-sm text-destructive py-2">{testError}</p>
          )}
          <div className="space-y-3 py-4">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                onClick={() => handleSubjectSelect(subject.id)}
                disabled={generatingTest}
                className="w-full flex items-center gap-4 p-4 rounded-xl border border-border hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors text-left disabled:opacity-50"
              >
                <div className="size-10 flex items-center justify-center">
                <SubjectIcon iconName={subject.icon} className="size-6" />
              </div>
                <div>
                  <div className="font-semibold">{subject.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {formatTargetShort(
                      clampTargetForExam(
                        account.targets[subject.id] ?? subject.targetScore,
                        account.examType
                      ),
                      account.examType
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {generatingTest && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-6">
          <LoadingProgress
            title={
              generatingTopicName
                ? `Составляем тест по теме «${generatingTopicName}»`
                : 'Ясно! составляет диагностику'
            }
            description={
              generatingTopicName
                ? 'Загружаем задания по выбранной теме и готовим вопросы.'
                : 'Вопросы подберутся по предмету, а после теста слабые темы появятся в плане.'
            }
            stages={[
              'Загружаем задания из банка…',
              'Обрабатываем условия задач…',
              'Формируем варианты ответов…',
              'Почти готово…',
            ]}
          />
        </div>
      )}
    </div>
  );
}
