import { useEffect, useState } from 'react';
import {
  Calendar,
  TrendingUp,
  Circle,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Target,
  BookOpen,
} from 'lucide-react';
import { api } from '../api/client';
import { useApp } from '../context/AppContext';
import type { PlanData } from '../types';
import SubjectSelector from './subject-selector';

export default function PlanScreen() {
  const { activeSubjectId, activeSubject } = useApp();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getPlan(activeSubjectId)
      .then((data) => {
        if (!cancelled) setPlan(data);
      })
      .catch(() => {
        if (!cancelled) setPlan(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeSubjectId]);

  const color = '#6D3DF5';

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

            <div className="grid grid-cols-1 xl:grid-cols-2 xl:gap-6">
              {plan.sections.map((section, sectionIndex) => (
                <div key={sectionIndex} className="mb-6">
                  <div className="flex items-center gap-3 mb-4">
                    {section.priority === 'high' && (
                      <div className="bg-destructive/10 rounded-xl size-10 flex items-center justify-center">
                        <AlertCircle className="size-5 text-destructive" />
                      </div>
                    )}
                    {section.priority === 'medium' && (
                      <div className="bg-[#6D3DF5]/10 rounded-xl size-10 flex items-center justify-center">
                        <Circle className="size-5 text-[#6D3DF5]" />
                      </div>
                    )}
                    {section.priority === 'completed' && (
                      <div className="bg-[#6D3DF5]/10 rounded-xl size-10 flex items-center justify-center">
                        <CheckCircle2 className="size-5 text-[#6D3DF5]" />
                      </div>
                    )}
                    <h3 className="font-semibold text-lg">{section.category}</h3>
                  </div>

                  <div className="space-y-3">
                    {section.items.map((item) => (
                      <div
                        key={item.id}
                        className="bg-white rounded-xl p-5 shadow-sm border border-border hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <h4 className="font-semibold">{item.name}</h4>
                              {item.status === 'completed' && (
                                <CheckCircle2 className="size-5 text-[#6D3DF5]" />
                              )}
                            </div>
                            <div className="flex items-center gap-4 flex-wrap">
                              <span
                                className={`text-sm font-medium ${
                                  section.priority === 'high'
                                    ? 'text-destructive'
                                    : section.priority === 'completed'
                                    ? 'text-[#6D3DF5]'
                                    : 'text-[#6D3DF5]'
                                }`}
                              >
                                {item.impact}
                              </span>
                              {item.status !== 'completed' && (
                                <span className="text-sm text-muted-foreground">
                                  {item.progress}% готовности
                                </span>
                              )}
                            </div>
                          </div>
                          <ChevronRight className="size-5 text-muted-foreground shrink-0 ml-2" />
                        </div>
                        {item.status !== 'completed' && (
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                section.priority === 'high'
                                  ? 'bg-destructive'
                                  : ''
                              }`}
                              style={{
                                width: `${item.progress}%`,
                                background:
                                  section.priority !== 'high'
                                    ? color
                                    : undefined,
                              }}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

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
