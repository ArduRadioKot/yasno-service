import { useCallback, useEffect, useState } from 'react';
import {
  X,
  ChevronLeft,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Loader2,
  List,
  Check,
  X as XIcon,
} from 'lucide-react';
import { api, getAiTestData, clearAiTestData } from '../api/client';
import { useApp } from '../context/AppContext';
import type { AiTestAnalysis, AiTestAnswer, AiTestData, Task, TaskCheckResult } from '../types';

export default function TaskScreen() {
  const { activeSubjectId, taskSessionKey, account } = useApp();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [checkResult, setCheckResult] = useState<TaskCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [taskList, setTaskList] = useState<{ id: string; topic: string; difficulty: string }[]>([]);
  const [showList, setShowList] = useState(false);
  const [aiTest, setAiTest] = useState<AiTestData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [testAnswers, setTestAnswers] = useState<AiTestAnswer[]>([]);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [analysis, setAnalysis] = useState<AiTestAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const loadTask = useCallback(
    async (taskId?: string) => {
      setLoading(true);
      setSelectedAnswer(null);
      setCheckResult(null);
      try {
        const t = taskId
          ? await api.getTask(taskId, activeSubjectId)
          : await api.generateTask(activeSubjectId);
        setTask(t);
        api
          .listTasks(activeSubjectId)
          .then((d) => setTaskList(d.tasks))
          .catch(() => setTaskList([]));
      } catch {
        try {
          const fallback = await api.getFirstTask(activeSubjectId);
          setTask(fallback);
        } catch {
          setTask(null);
        }
      } finally {
        setLoading(false);
      }
    },
    [activeSubjectId]
  );

  useEffect(() => {
    // Check if there's AI-generated test data
    const aiData = getAiTestData();
    if (aiData) {
      setAiTest(aiData);
      setLoading(false);
    } else {
      loadTask();
      api
        .listTasks(activeSubjectId)
        .then((d) => setTaskList(d.tasks))
        .catch(() => setTaskList([]));
    }
  }, [activeSubjectId, taskSessionKey, loadTask]);

  const handleCheck = async () => {
    if (!task || selectedAnswer === null) return;
    setChecking(true);
    try {
      const result = await api.checkTask(task.id, selectedAnswer);
      setCheckResult(result);
    } finally {
      setChecking(false);
    }
  };

  const handleNext = async () => {
    if (!task) return;
    setLoading(true);
    try {
      const next = await api.generateTask(activeSubjectId, task.topic, task.difficulty);
      setTask(next);
      setSelectedAnswer(null);
      setCheckResult(null);
      api
        .listTasks(activeSubjectId)
        .then((d) => setTaskList(d.tasks))
        .catch(() => setTaskList([]));
    } finally {
      setLoading(false);
    }
  };

  const handleSimilar = () => {
    if (!task) return;
    setLoading(true);
    api
      .generateTask(activeSubjectId, task.topic, task.difficulty)
      .then((next) => {
        setTask(next);
        setSelectedAnswer(null);
        setCheckResult(null);
      })
      .finally(() => setLoading(false));
  };

  const handleNewAiTask = () => {
    setLoading(true);
    api
      .generateTask(activeSubjectId)
      .then((next) => {
        setTask(next);
        setSelectedAnswer(null);
        setCheckResult(null);
        api
          .listTasks(activeSubjectId)
          .then((d) => setTaskList(d.tasks))
          .catch(() => setTaskList([]));
      })
      .finally(() => setLoading(false));
  };

  const handleAiTestAnswer = (answerIndex: number) => {
    if (!aiTest) return;
    
    const currentQuestion = aiTest.questions[currentQuestionIndex];
    const isCorrect = answerIndex === currentQuestion.correctIndex;
    
    const newAnswers = [
      ...testAnswers,
      {
        topic: currentQuestion.topic || aiTest.topic,
        question: currentQuestion.question,
        selectedAnswer: currentQuestion.answers[answerIndex],
        correctAnswer: currentQuestion.answers[currentQuestion.correctIndex],
        correct: isCorrect,
      },
    ];
    setTestAnswers(newAnswers);
    
    if (currentQuestionIndex < aiTest.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // Test completed, analyze results
      analyzeResults(newAnswers);
    }
  };

  const analyzeResults = async (answers: AiTestAnswer[]) => {
    setAnalyzing(true);
    try {
      const subjectIds = aiTest?.subjects;
      const result = await api.analyzeTestResults(activeSubjectId, answers, subjectIds, account.email);
      setAnalysis(result);
      setShowAnalysis(true);
    } catch (error) {
      console.error('Failed to analyze test:', error);
      const correct = answers.filter((answer) => answer.correct).length;
      const gaps = Array.from(
        new Set(answers.filter((answer) => !answer.correct).map((answer) => answer.topic))
      );
      setAnalysis({
        analysis: `Вы правильно ответили на ${correct} из ${answers.length}. Повторите темы, где были ошибки, и вернитесь к диагностике позже.`,
        gaps,
        score: answers.length ? Math.round((correct / answers.length) * 100) : 0,
        level: correct >= answers.length * 0.8 ? 'сильный' : correct >= answers.length * 0.5 ? 'средний' : 'начальный',
      });
      setShowAnalysis(true);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading && !task && !aiTest) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#6D3DF5]" />
      </div>
    );
  }

  if (!task && !aiTest) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-muted-foreground">Задания не найдены. Запустите Flask: npm run backend</p>
      </div>
    );
  }

  // Show AI test analysis
  if (analyzing) {
    return (
      <div className="h-full flex items-center justify-center bg-[#F3F4F6]">
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-border text-center max-w-sm">
          <Loader2 className="size-12 animate-spin text-[#6D3DF5] mx-auto mb-4" />
          <h3 className="font-semibold text-lg mb-2">Анализируем результаты</h3>
          <p className="text-sm text-muted-foreground">AI составляет персональные рекомендации</p>
        </div>
      </div>
    );
  }

  if (showAnalysis && analysis) {
    const correctCount = testAnswers.filter(a => a.correct).length;
    const totalQuestions = testAnswers.length;
    
    return (
      <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
        <div className="max-w-3xl mx-auto p-4 sm:p-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-border">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-[#6D3DF5] rounded-2xl size-12 flex items-center justify-center">
                <Sparkles className="size-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Анализ результатов</h2>
                <p className="text-muted-foreground">AI-анализ вашего теста</p>
              </div>
            </div>
            
            <div className="bg-[#F7F7FA] rounded-2xl p-6 border border-border mb-6">
              <div className="flex items-center justify-between gap-4 mb-4">
                <h3 className="font-semibold text-lg">Ваш результат</h3>
                <div className="text-right">
                  <div className="font-bold text-2xl text-[#6D3DF5]">{analysis.score}%</div>
                  <div className="text-xs text-muted-foreground">{analysis.level}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-white rounded-xl p-3 border border-border">
                  <div className="text-sm text-muted-foreground mb-1">Правильных ответов</div>
                  <div className="font-bold text-lg">{correctCount} из {totalQuestions}</div>
                </div>
                <div className="bg-white rounded-xl p-3 border border-border">
                  <div className="text-sm text-muted-foreground mb-1">Прогноз на экзамен</div>
                  <div className="font-bold text-lg">{Math.round(analysis.score * 0.9)} баллов</div>
                </div>
              </div>
              <div className="bg-[#6D3DF5]/5 rounded-xl p-3 border border-[#6D3DF5]/20">
                <p className="text-xs text-muted-foreground mb-1">Как рассчитывается прогноз:</p>
                <p className="text-sm">Балл = (процент правильных ответов × 0.9). Это консервативная оценка с учетом стресса на экзамене.</p>
              </div>
            </div>
            
            <div className="bg-[#F7F7FA] rounded-2xl p-6 border border-border mb-6">
              <h3 className="font-semibold text-lg mb-3">Рекомендации</h3>
              <p className="leading-relaxed">{analysis.analysis}</p>
            </div>
            
            {analysis.gaps.length > 0 && (
              <div className="bg-destructive/5 rounded-2xl p-6 border border-destructive/20 mb-6">
                <h3 className="font-semibold text-lg mb-3">Темы для повторения</h3>
                <ul className="space-y-2">
                  {analysis.gaps.map((gap, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <div className="size-2 rounded-full bg-destructive" />
                      <span>{gap}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            <button
              onClick={() => {
                setAiTest(null);
                setShowAnalysis(false);
                setAnalysis(null);
                setTestAnswers([]);
                setCurrentQuestionIndex(0);
                clearAiTestData();
                loadTask();
              }}
              className="w-full bg-[#6D3DF5] text-white font-semibold py-4 rounded-xl shadow-lg hover:shadow-xl transition-all"
            >
              Вернуться к заданиям
            </button>
            {analysis.gaps.length > 0 && (
              <p className="text-center text-sm text-muted-foreground mt-3">
                Эти темы уже добавлены в раздел «План».
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Show AI test
  if (aiTest) {
    const currentQuestion = aiTest.questions[currentQuestionIndex];
    return (
      <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
        <div className="bg-white border-b border-border px-4 sm:px-6 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between max-w-3xl mx-auto">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                Вопрос {currentQuestionIndex + 1} из {aiTest.questions.length}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Тема: {currentQuestion.topic || aiTest.topic}
              </p>
            </div>
            <button
              onClick={() => {
                setAiTest(null);
                setCurrentQuestionIndex(0);
                setTestAnswers([]);
                clearAiTestData();
                loadTask();
              }}
              className="size-10 rounded-full hover:bg-muted flex items-center justify-center transition-colors"
            >
              <X className="size-6" />
            </button>
          </div>
        </div>

        <div className="max-w-3xl mx-auto p-4 sm:p-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-border mb-6">
            <div className="flex items-start gap-3 mb-4">
              <div className="bg-[#6D3DF5] rounded-xl size-10 flex items-center justify-center text-white font-bold shrink-0">
                {currentQuestionIndex + 1}
              </div>
              <h3 className="font-semibold text-lg">{currentQuestion.question}</h3>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Выберите ответ:</h4>
            <div className="space-y-3">
              {currentQuestion.answers.map((answer, index) => (
                <button
                  key={index}
                  onClick={() => handleAiTestAnswer(index)}
                  className="w-full text-left p-4 rounded-xl border-2 border-border bg-white hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors"
                >
                  <span className="font-medium">{answer}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const showExplanation = !!checkResult;

  return (
    <div className="h-full overflow-y-auto pb-6 md:pb-8 bg-[#F3F4F6]">
      <div className="bg-white border-b border-border px-4 sm:px-6 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <button
            onClick={() => setShowList(!showList)}
            className="size-10 rounded-full hover:bg-muted flex items-center justify-center transition-colors"
            title="Список заданий"
          >
            <List className="size-6" />
          </button>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Задание {task.index} из {task.total}
            </p>
            <div className="flex gap-1 mt-2 justify-center">
              {Array.from({ length: Math.min(task.total, 12) }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 w-6 sm:w-8 rounded-full transition-colors ${
                    i < task.index ? 'bg-[#6D3DF5]' : 'bg-muted'
                  }`}
                />
              ))}
            </div>
          </div>
          <button
            onClick={() => {
              setCheckResult(null);
              setSelectedAnswer(null);
            }}
            className="size-10 rounded-full hover:bg-muted flex items-center justify-center transition-colors"
          >
            <X className="size-6" />
          </button>
        </div>
      </div>

      {showList && (
        <div className="bg-white border-b border-border px-4 py-3 max-h-48 overflow-y-auto">
          <div className="max-w-7xl mx-auto space-y-2">
            {taskList.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  loadTask(t.id);
                  setShowList(false);
                }}
                className={`w-full text-left px-4 py-2 rounded-xl text-sm transition-colors ${
                  t.id === task.id ? 'bg-[#6D3DF5]/10 text-[#6D3DF5]' : 'hover:bg-muted'
                }`}
              >
                <span className="font-medium">{t.topic}</span>
                <span className="text-muted-foreground ml-2">· {t.difficulty}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-6">
          <div className="inline-flex items-center gap-2 bg-[#6D3DF5]/10 text-[#6D3DF5] px-4 py-2 rounded-full">
            <div className="size-2 rounded-full bg-[#6D3DF5]" />
            <span className="font-medium">{task.topic}</span>
            <span className="text-xs opacity-70">· {task.difficulty}</span>
          </div>
          <button
            onClick={handleNewAiTask}
            disabled={loading}
            className="inline-flex items-center gap-2 bg-white border border-border px-4 py-2 rounded-full text-sm font-semibold hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin text-[#6D3DF5]" />
            ) : (
              <Sparkles className="size-4 text-[#6D3DF5]" />
            )}
            Новое AI-задание
          </button>
        </div>

        <div className="lg:grid lg:grid-cols-2 lg:gap-8 lg:items-start">
          <div className="bg-white rounded-2xl p-6 mb-6 lg:mb-0 shadow-sm border border-border">
            <div className="flex items-start gap-3">
              <div className="bg-[#6D3DF5] rounded-xl size-10 flex items-center justify-center text-white font-bold shrink-0">
                {task.index}
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-3">{task.question}</h3>
                {task.given.length > 0 && (
                  <div className="bg-muted/50 rounded-2xl p-4 mt-4">
                    <p className="text-sm text-muted-foreground mb-2">Дано:</p>
                    <div className="space-y-1 font-mono text-sm">
                      {task.given.map((line, i) => (
                        <p key={i}>{line}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div>
            <div className="mb-6">
              <h4 className="font-semibold mb-4">Выберите ответ:</h4>
              <div className="space-y-3">
                {task.answers.map((answer) => {
                  const isSelected = selectedAnswer === answer.id;
                  const isCorrect =
                    showExplanation && checkResult?.correctAnswerId === answer.id;
                  const isWrong =
                    showExplanation && isSelected && !checkResult?.correct;

                  return (
                    <button
                      key={answer.id}
                      onClick={() => !showExplanation && setSelectedAnswer(answer.id)}
                      disabled={showExplanation || checking}
                      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                        isSelected && !showExplanation
                          ? 'border-[#6D3DF5] bg-[#6D3DF5]/5'
                          : isCorrect
                          ? 'border-[#6D3DF5] bg-[#6D3DF5]/10'
                          : isWrong
                          ? 'border-destructive bg-destructive/5'
                          : 'border-border bg-white hover:border-[#6D3DF5]/50'
                      } ${showExplanation ? 'pointer-events-none' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{answer.text}</span>
                        {isCorrect && <Check className="size-6 text-[#6D3DF5]" />}
                        {isWrong && <XIcon className="size-6 text-destructive" />}
                      </div>
                    </button>
                  );
                })}
              </div>
              </div>

            {!showExplanation && (
              <button
                onClick={handleCheck}
                disabled={selectedAnswer === null || checking}
                className="w-full bg-[#6D3DF5] text-white font-semibold py-4 rounded-xl shadow-lg  disabled:opacity-50 transition-all hover:shadow-xl flex items-center justify-center gap-2"
              >
                {checking ? <Loader2 className="size-5 animate-spin" /> : null}
                Проверить
              </button>
            )}

            {showExplanation && checkResult && (
              <div className="space-y-4">
                {!checkResult.correct && (
                  <div className="bg-destructive/5 rounded-2xl p-6 border border-destructive/20">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="bg-destructive/10 rounded-xl size-10 flex items-center justify-center shrink-0">
                        <Lightbulb className="size-5 text-destructive" />
                      </div>
                      <h4 className="font-semibold text-lg">Почему это ошибка?</h4>
                    </div>
                    <p className="text-foreground/80 leading-relaxed">
                      {checkResult.explanation.wrongHint}
                    </p>
                  </div>
                )}

                <div className="bg-[#F7F7FA] rounded-2xl p-6 border border-border">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="bg-[#6D3DF5]/20 rounded-xl size-10 flex items-center justify-center shrink-0">
                      <Sparkles className="size-5 text-[#6D3DF5]" />
                    </div>
                    <h4 className="font-semibold text-lg">Как решать правильно</h4>
                  </div>
                  <div className="space-y-4">
                    {checkResult.explanation.steps.map((step, i) => (
                      <div key={i} className="bg-white/60 backdrop-blur-sm rounded-xl p-4 font-mono text-center text-sm">
                        {step}
                      </div>
                    ))}
                    <div className="bg-[#6D3DF5]/10 rounded-xl p-4 flex items-start gap-2">
                      <Lightbulb className="size-4 text-[#6D3DF5] shrink-0 mt-0.5" />
                      <p className="text-sm font-medium text-[#6D3DF5]">
                        {checkResult.explanation.tip}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-6">
                  <button
                    onClick={handleSimilar}
                    className="bg-white border-2 border-border font-semibold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-muted transition-colors"
                  >
                    <RefreshCw className="size-5" />
                    Ещё раз
                  </button>
                  <button
                    onClick={handleNext}
                    className="bg-[#6D3DF5] text-white font-semibold py-4 rounded-xl shadow-lg  hover:shadow-xl transition-all"
                  >
                    Продолжить
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
