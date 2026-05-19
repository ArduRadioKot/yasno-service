import { useEffect, useState } from 'react';
import { Target, TrendingUp, Award, Flame, Brain, ChevronRight, Loader2, Hand, Atom, Calculator, BookOpen, Landmark, FlaskConical, Laptop } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { api, setAiTestData } from '../api/client';
import { useApp } from '../context/AppContext';
import type { DashboardData } from '../types';
import SubjectSelector from './subject-selector';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'atom': Atom,
  'calculator': Calculator,
  'book-open': BookOpen,
  'landmark': Landmark,
  'flask-conical': FlaskConical,
  'laptop': Laptop,
};

function SubjectIcon({ iconName, className }: { iconName: string; className?: string }) {
  const Icon = iconMap[iconName] || Atom;
  return <Icon className={className} />;
}

export default function DashboardScreen() {
  const { activeSubjectId, onStartLesson, subjects, setActiveSubject, account } = useApp();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSubjectModal, setShowSubjectModal] = useState(false);
  const [generatingTest, setGeneratingTest] = useState(false);
  const [questionCount, setQuestionCount] = useState(5);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getDashboard(activeSubjectId, account.email)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeSubjectId, account.email]);

  const color = '#6D3DF5';
  const userName = account.firstName || data?.userName || 'Ученик';

  const handleStartLesson = () => {
    setShowSubjectModal(true);
  };

  const handleSubjectSelect = async (subjectId: string) => {
    setGeneratingTest(true);
    setShowSubjectModal(false);
    
    try {
      await setActiveSubject(subjectId);
      const test = await api.generateTest(subjectId, 'диагностика по предмету', questionCount, account.email);
      setAiTestData(test);
      onStartLesson();
    } catch (error) {
      console.error('Failed to generate test:', error);
    } finally {
      setGeneratingTest(false);
    }
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
                    Прогноз ЕГЭ · {data.subject.name}
                  </p>
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-4xl sm:text-5xl font-bold text-foreground">{data.score}</h2>
                    <span className="text-muted-foreground text-xl">баллов</span>
                  </div>
                </div>
                <div className="bg-[#F7F7FA] rounded-xl px-4 py-2 border border-border">
                  <div className="flex items-center gap-1 text-[#6D3DF5]">
                    <TrendingUp className="size-5" />
                    <span className="font-semibold">+{data.scoreDelta}</span>
                  </div>
                </div>
              </div>
              <div className="h-24 -mx-6 -mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.chart}>
                    <Area
                      type="monotone"
                      dataKey="score"
                      stroke="#6D3DF5"
                      strokeWidth={3}
                      fill="rgba(109, 61, 245, 0.1)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
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
                      width: `${data.tasksTotal ? (data.tasksCompleted / data.tasksTotal) * 100 : 0}%`,
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
                <button className="text-sm font-medium flex items-center gap-1 text-[#6D3DF5]">
                  Все темы
                  <ChevronRight className="size-4" />
                </button>
              </div>
              <div className="space-y-3">
                {data.weakTopics.map((topic, index) => (
                  <div key={index} className="bg-white rounded-2xl p-4 shadow-sm border border-border">
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
                  </div>
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

      <Dialog open={showSubjectModal} onOpenChange={setShowSubjectModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Выберите предмет для теста</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <p className="text-sm font-medium text-[#707076] mb-2">Количество вопросов</p>
            <div className="grid grid-cols-4 gap-2">
              {[3, 5, 8, 10].map((count) => (
                <button
                  key={count}
                  onClick={() => setQuestionCount(count)}
                  className={`h-11 rounded-xl border font-semibold ${
                    questionCount === count
                      ? 'border-[#6D3DF5] bg-[#6D3DF5]/5 text-[#6D3DF5]'
                      : 'border-border bg-[#F7F7FA] text-muted-foreground'
                  }`}
                >
                  {count}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-3 py-4">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                onClick={() => handleSubjectSelect(subject.id)}
                className="w-full flex items-center gap-4 p-4 rounded-xl border border-border hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors text-left"
              >
                <div className="size-10 flex items-center justify-center">
                <SubjectIcon iconName={subject.icon} className="size-6" />
              </div>
                <div>
                  <div className="font-semibold">{subject.name}</div>
                  <div className="text-sm text-muted-foreground">{subject.targetScore} баллов</div>
                </div>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {generatingTest && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl border border-border shadow-sm p-6 w-full max-w-sm text-center">
            <Loader2 className="size-8 animate-spin text-[#6D3DF5] mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Ясно! составляет диагностику</h3>
            <p className="text-sm text-muted-foreground">
              Вопросы подберутся по предмету, а после теста слабые темы появятся в плане.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
