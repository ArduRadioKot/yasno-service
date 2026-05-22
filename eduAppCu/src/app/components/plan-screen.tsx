import { useCallback, useEffect, useState } from 'react';
import {
  Calendar,
  TrendingUp,
  Circle,
  CheckCircle2,
  AlertCircle,
  Target,
  BookOpen,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../context/AppContext';
import type { PlanData, PlanSection, PlanTopic } from '../types';
import SubjectSelector from './subject-selector';

const PRIORITY_CATEGORY = 'Требуют внимания';
const IN_PROGRESS_CATEGORY = 'В процессе';
const COMPLETED_CATEGORY = 'Освоенные темы';

function SectionIcon({ section }: { section: PlanSection }) {
  if (section.category === PRIORITY_CATEGORY || section.priority === 'high') {
    return (
      <div className="bg-destructive/10 rounded-xl size-10 flex items-center justify-center">
        <AlertCircle className="size-5 text-destructive" />
      </div>
    );
  }
  if (section.priority === 'completed' || section.category === COMPLETED_CATEGORY) {
    return (
      <div className="bg-[#6D3DF5]/10 rounded-xl size-10 flex items-center justify-center">
        <CheckCircle2 className="size-5 text-[#6D3DF5]" />
      </div>
    );
  }
  return (
    <div className="bg-[#6D3DF5]/10 rounded-xl size-10 flex items-center justify-center">
      <Circle className="size-5 text-[#6D3DF5]" />
    </div>
  );
}

function TopicCard({
  item,
  section,
  updatingId,
  onStatusChange,
}: {
  item: PlanTopic;
  section: PlanSection;
  updatingId: string | null;
  onStatusChange: (topicId: string, status: 'completed' | 'in-progress') => void;
}) {
  const isCompleted = item.status === 'completed';
  const isUpdating = updatingId === item.id;
  const barColor = '#6D3DF5';

  return (
    <div className="bg-white rounded-xl px-4 py-3 shadow-sm border border-border hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <h4
              className={`font-semibold truncate ${
                isCompleted ? 'text-muted-foreground line-through' : 'text-foreground'
              }`}
            >
              {item.name}
            </h4>
          </div>
          <div className="flex items-center gap-2 flex-wrap text-xs mt-0.5">
            {!isCompleted && (
              <span className="text-muted-foreground">{item.progress}%</span>
            )}
            {isCompleted && <span className="text-[#6D3DF5] font-medium">Освоено</span>}
            {!isCompleted && item.status === 'in-progress' && (
              <span className="text-amber-600 font-medium">В работе</span>
            )}
            {!isCompleted && item.status === 'pending' && (
              <span className="text-muted-foreground">Не начато</span>
            )}
          </div>
          {!isCompleted && (
            <div className="h-1.5 bg-muted rounded-full overflow-hidden mt-2 max-w-xs">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${item.progress}%`, backgroundColor: barColor }}
              />
            </div>
          )}
        </div>

        {!isCompleted ? (
          <button
            type="button"
            disabled={isUpdating}
            onClick={() => onStatusChange(item.id, 'completed')}
            title="Отметить освоенной"
            aria-label="Отметить освоенной"
            className="shrink-0 size-9 rounded-full border-2 border-[#6D3DF5]/30 bg-white text-[#6D3DF5] hover:bg-[#6D3DF5]/10 hover:border-[#6D3DF5] disabled:opacity-50 inline-flex items-center justify-center transition-colors"
          >
            {isUpdating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <CheckCircle2 className="size-4" />
            )}
          </button>
        ) : (
          <button
            type="button"
            disabled={isUpdating}
            onClick={() => onStatusChange(item.id, 'in-progress')}
            title="Вернуть в работу"
            aria-label="Вернуть в работу"
            className="shrink-0 size-9 rounded-full border border-border bg-[#F7F7FA] text-muted-foreground hover:border-[#6D3DF5] hover:text-[#6D3DF5] disabled:opacity-50 inline-flex items-center justify-center transition-colors"
          >
            {isUpdating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RotateCcw className="size-4" />
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default function PlanScreen() {
  const { activeSubjectId, activeSubject, account } = useApp();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatingTopicId, setUpdatingTopicId] = useState<string | null>(null);

  const loadPlan = useCallback(() => {
    setLoading(true);
    return api
      .getPlan(activeSubjectId, account.email)
      .then((data) => setPlan(data))
      .catch(() => setPlan(null))
      .finally(() => setLoading(false));
  }, [activeSubjectId, account.email]);

  useEffect(() => {
    let cancelled = false;
    loadPlan().then(() => {
      if (cancelled) return;
    });
    const onTestComplete = () => {
      if (!cancelled) loadPlan();
    };
    window.addEventListener('edu-test-complete', onTestComplete);
    return () => {
      cancelled = true;
      window.removeEventListener('edu-test-complete', onTestComplete);
    };
  }, [loadPlan]);

  const handleStatusChange = async (topicId: string, status: 'completed' | 'in-progress') => {
    setUpdatingTopicId(topicId);
    try {
      const updated = await api.updatePlanTopic(
        topicId,
        activeSubjectId,
        status,
        account.email,
        status === 'completed' ? 100 : undefined
      );
      setPlan(updated);
    } catch (error) {
      console.error('Failed to update topic:', error);
    } finally {
      setUpdatingTopicId(null);
    }
  };

  const prioritySection = plan?.sections.find((s) => s.category === PRIORITY_CATEGORY);
  const inProgressSection = plan?.sections.find((s) => s.category === IN_PROGRESS_CATEGORY);
  const completedSection = plan?.sections.find((s) => s.category === COMPLETED_CATEGORY);
  const hasAnyTopics =
    (prioritySection?.items.length ?? 0) +
      (inProgressSection?.items.length ?? 0) +
      (completedSection?.items.length ?? 0) >
    0;

  return (
    <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
      <div className="px-4 sm:px-6 lg:px-8 pt-6 md:pt-8 pb-8 bg-white border-b border-border">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-2 text-[#6D3DF5] mb-2">
            <BookOpen className="size-5" />
            <span className="text-sm font-medium">План подготовки</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-2">Твой план</h1>
          <p className="text-muted-foreground mb-6">
            {activeSubject
              ? `${activeSubject.name} — путь к цели ${activeSubject.targetScore} баллов`
              : 'Выбери предмет'}
          </p>

          <div className="mb-6">
            <p className="text-muted-foreground text-sm mb-3 font-medium">Предмет</p>
            <SubjectSelector variant="pills" />
          </div>

          {plan && (
            <div className="bg-[#F7F7FA] rounded-2xl p-5 border border-border">
              <div className="flex items-center gap-2 mb-4 text-foreground">
                <Calendar className="size-5" />
                <span className="font-medium">До экзамена: {plan.daysToExam} дней</span>
              </div>
              <div className="space-y-3">
                {plan.milestones.map((milestone, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <div
                      className={`size-3 rounded-full ${
                        milestone.current ? 'bg-[#6D3DF5] ring-4 ring-[#6D3DF5]/10' : 'bg-[#D8D8DD]'
                      }`}
                    />
                    <div className="flex-1 flex items-center justify-between">
                      <span
                        className={`text-sm ${
                          milestone.current ? 'text-foreground font-semibold' : 'text-muted-foreground'
                        }`}
                      >
                        {milestone.date}
                      </span>
                      <span
                        className={`font-semibold ${
                          milestone.current ? 'text-foreground' : 'text-muted-foreground'
                        }`}
                      >
                        {milestone.score} б
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 -mt-4">
        {loading && (
          <p className="text-muted-foreground text-center py-12">Загрузка плана…</p>
        )}

        {!loading && plan && (
          <>
            <div className="rounded-2xl p-6 mb-6 shadow-sm text-foreground bg-white border border-border">
              <div className="flex items-start gap-4">
                <div className="bg-[#F7F7FA] border border-border rounded-xl size-12 flex items-center justify-center shrink-0">
                  <TrendingUp className="size-6 text-[#6D3DF5]" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground mb-2">Прогноз роста</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed mb-4">{plan.forecast}</p>
                  <div className="flex items-center gap-2">
                    <div className="h-2 bg-muted rounded-full flex-1 overflow-hidden">
                      <div
                        className="h-full bg-[#6D3DF5] rounded-full transition-all"
                        style={{ width: `${plan.currentScore}%` }}
                      />
                    </div>
                    <span className="text-[#6D3DF5] font-semibold text-sm">{plan.currentScore}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-8">
              <p className="text-sm text-muted-foreground mb-3">Все предметы</p>
              <SubjectSelector variant="grid" />
            </div>

            {!hasAnyTopics && (
              <div className="mb-8 bg-white rounded-xl p-8 border border-dashed border-border text-center">
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Пока нет тем в плане. Пройдите AI-тест на главной — после разбора ответов слабые темы
                  появятся здесь автоматически.
                </p>
              </div>
            )}

            {prioritySection && prioritySection.items.length > 0 && (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                  <SectionIcon section={prioritySection} />
                  <div>
                    <h3 className="font-semibold text-lg">{prioritySection.category}</h3>
                    <p className="text-sm text-muted-foreground">
                      Темы из последних тестов, которые стоит разобрать в первую очередь
                    </p>
                  </div>
                </div>
                <div className="space-y-3 mt-4">
                  {prioritySection.items.map((item) => (
                    <TopicCard
                      key={item.id}
                      item={item}
                      section={prioritySection}
                      updatingId={updatingTopicId}
                      onStatusChange={handleStatusChange}
                    />
                  ))}
                </div>
              </div>
            )}

            {inProgressSection && (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <SectionIcon section={inProgressSection} />
                  <div>
                    <h3 className="font-semibold text-lg">{inProgressSection.category}</h3>
                    <p className="text-sm text-muted-foreground">
                      Темы, которые вы сейчас изучаете — отметьте освоенной, когда будете готовы
                    </p>
                  </div>
                </div>
                {inProgressSection.items.length > 0 ? (
                  <div className="space-y-3">
                    {inProgressSection.items.map((item) => (
                      <TopicCard
                        key={item.id}
                        item={item}
                        section={inProgressSection}
                        updatingId={updatingTopicId}
                        onStatusChange={handleStatusChange}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="bg-white rounded-xl p-6 border border-dashed border-border text-center text-muted-foreground text-sm">
                    Нет тем в работе. Пройдите тест или верните тему из блока «Освоенные».
                  </div>
                )}
              </div>
            )}

            {completedSection && (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <SectionIcon section={completedSection} />
                  <div>
                    <h3 className="font-semibold text-lg">{completedSection.category}</h3>
                    <p className="text-sm text-muted-foreground">
                      Уже освоенные темы — можно вернуть в работу для повторения
                    </p>
                  </div>
                </div>
                {completedSection.items.length > 0 ? (
                  <div className="space-y-3">
                    {completedSection.items.map((item) => (
                      <TopicCard
                        key={item.id}
                        item={item}
                        section={completedSection}
                        updatingId={updatingTopicId}
                        onStatusChange={handleStatusChange}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="bg-white rounded-xl p-6 border border-dashed border-border text-center text-muted-foreground text-sm">
                    Пока нет освоенных тем. Отмечайте темы кнопкой «Отметить освоенной».
                  </div>
                )}
              </div>
            )}

            <div className="bg-white rounded-2xl p-6 border border-border shadow-sm">
              <div className="flex items-start gap-4">
                <div className="bg-[#6D3DF5]/20 rounded-2xl size-12 flex items-center justify-center shrink-0">
                  <Target className="size-6 text-[#6D3DF5]" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Цель на неделю</h3>
                  <p className="text-foreground/80 text-sm mb-4">{plan.weeklyGoal}</p>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="h-2 bg-white/60 rounded-full flex-1 max-w-[200px] overflow-hidden">
                      <div
                        className="h-full bg-[#6D3DF5] rounded-full"
                        style={{ width: `${plan.weeklyProgress}%` }}
                      />
                    </div>
                    <span className="text-muted-foreground font-medium">
                      {plan.weeklyTasksDone}/{plan.weeklyTasksTotal} заданий
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
