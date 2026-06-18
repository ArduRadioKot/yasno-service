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
import {
  api,
  getAiTestData,
  setAiTestData,
  clearAiTestData,
  getTestResults,
  saveTestResults,
  clearTestResults,
  notifyTestComplete,
} from '../api/client';
import { useApp } from '../context/AppContext';
import type { AiTestAnalysis, AiTestAnswer, AiTestBreakdown, AiTestData, Task, TaskCheckResult } from '../types';
import { HtmlRenderer } from './HtmlRenderer';
import { LoadingProgress } from './LoadingProgress';
import { LoadingOverlay } from './LoadingOverlay';

export default function TaskScreen() {
  const { activeSubjectId, taskSessionKey, account, onNavigateToChat, setActiveSubject } = useApp();
  const [generatingTest, setGeneratingTest] = useState(false);
  const [testQuestionCount, setTestQuestionCount] = useState(5);
  const [testError, setTestError] = useState<string | null>(null);
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

  const isOgeExam = account.examType === 'ОГЭ';

  const formatExamScore = (value: number) => {
    if (isOgeExam) {
      return `${Math.max(2, Math.min(5, Math.round(value)))} (оценка)`;
    }
    return `${value} баллов`;
  };

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
    const savedResults = getTestResults();
    if (savedResults) {
      setAnalysis(savedResults.analysis);
      setTestAnswers(savedResults.answers);
      setShowAnalysis(true);
      setLoading(false);
      return;
    }

    const aiData = getAiTestData();
    if (aiData) {
      setAiTest(aiData);
      setLoading(false);
    } else {
      setTask(null);
      setLoading(false);
    }
  }, [activeSubjectId, taskSessionKey]);

  const handleGenerateTestFromBank = async () => {
    setGeneratingTest(true);
    setTestError(null);
    setShowAnalysis(false);
    setAnalysis(null);
    setTestAnswers([]);
    setCurrentQuestionIndex(0);
    clearAiTestData();
    clearTestResults();
    try {
      await setActiveSubject(activeSubjectId);
      const test = await api.generateTest(
        activeSubjectId,
        'диагностика по предмету',
        testQuestionCount,
        undefined,
        account.examType,
        account.email
      );
      if (!test.questions?.length) {
        throw new Error('Не удалось загрузить задания для теста');
      }
      setAiTestData(test);
      setAiTest(test);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Не удалось загрузить задания. Проверьте интернет и работу сервера.';
      setTestError(message);
      console.error('Failed to generate test from bank:', error);
    } finally {
      setGeneratingTest(false);
    }
  };

  const handleCheck = async () => {
    if (!task || selectedAnswer === null) return;
    setChecking(true);
    try {
      const result = await api.checkTask(task.id, selectedAnswer, account.email);
      setCheckResult(result);
      if (result.correct) {
        notifyTestComplete();
      }
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
    if (!aiTest || analyzing) return;

    const currentQuestion = aiTest.questions[currentQuestionIndex];
    const isCorrect = answerIndex === currentQuestion.correctIndex;
    const isLastQuestion = currentQuestionIndex >= aiTest.questions.length - 1;

    const newAnswers = [
      ...testAnswers,
      {
        topic: currentQuestion.topic || aiTest.topic,
        question: currentQuestion.question,
        questionHtml: currentQuestion.questionHtml,
        selectedAnswer: currentQuestion.answers[answerIndex],
        selectedAnswerHtml: currentQuestion.answersHtml?.[answerIndex],
        correctAnswer: currentQuestion.answers[currentQuestion.correctIndex],
        correctAnswerHtml: currentQuestion.answersHtml?.[currentQuestion.correctIndex],
        correct: isCorrect,
        subjectId: currentQuestion.subjectId || aiTest.subjectId || activeSubjectId,
        problemId: currentQuestion.problemId,
      },
    ];
    setTestAnswers(newAnswers);

    if (!isLastQuestion) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      return;
    }

    setAnalyzing(true);
    analyzeResults(newAnswers);
  };

  const analyzeResults = async (answers: AiTestAnswer[]) => {
    try {
      const multiIds = aiTest?.subjectIds;
      const result = await api.analyzeTestResults(
        activeSubjectId,
        answers,
        multiIds,
        account.email,
        account.examType
      );
      setAnalysis(result);
      setShowAnalysis(true);
      saveTestResults({ analysis: result, answers });
      notifyTestComplete();
    } catch (error) {
      console.error('Failed to analyze test:', error);
      const correct = answers.filter((answer) => answer.correct).length;
      const percent = answers.length ? Math.round((correct / answers.length) * 100) : 0;
      const gaps = Array.from(
        new Set(answers.filter((answer) => !answer.correct).map((answer) => answer.topic))
      );
      const fallback: AiTestAnalysis = {
        analysis: `Вы правильно ответили на ${correct} из ${answers.length}. Повторите темы, где были ошибки.`,
        gaps,
        score: percent,
        examScore: isOgeExam
          ? (percent < 25 ? 2 : percent < 50 ? 3 : percent < 75 ? 4 : 5)
          : Math.round(percent * 0.9),
        examType: account.examType,
        level:
          correct >= answers.length * 0.8
            ? 'сильный'
            : correct >= answers.length * 0.5
              ? 'средний'
              : 'начальный',
        breakdowns: answers
          .filter((answer) => !answer.correct)
          .map((answer) => ({
            question: answer.question,
            topic: answer.topic,
            explanation: `Правильный ответ: ${answer.correctAnswer}`,
            chatPrompt: `Разбери задачу: ${answer.question}. Мой ответ: ${answer.selectedAnswer}.`,
          })),
      };
      setAnalysis(fallback);
      setShowAnalysis(true);
      saveTestResults({ analysis: fallback, answers });
      notifyTestComplete();
    } finally {
      setAnalyzing(false);
    }
  };

  const getBreakdownForAnswer = (answer: AiTestAnswer, index: number): AiTestBreakdown | null => {
    if (answer.correct) return null;
    const fromAnalysis = analysis?.breakdowns?.find(
      (item) => item.question === answer.question || item.topic === answer.topic
    );
    if (fromAnalysis) return fromAnalysis;
    return {
      question: answer.question,
      topic: answer.topic,
      explanation: `Правильный ответ: ${answer.correctAnswer}`,
      chatPrompt: `Разбери подробно задачу по теме «${answer.topic}»: ${answer.question}. Мой ответ: ${answer.selectedAnswer}. Правильный: ${answer.correctAnswer}.`,
      subjectId: answer.subjectId || activeSubjectId,
    };
  };

  if (loading && !task && !aiTest) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="size-8 animate-spin text-[#6D3DF5]" />
      </div>
    );
  }

  if (generatingTest) {
    return (
      <LoadingOverlay>
        <LoadingProgress
          title="Составляем тест из банка"
          description={`Загружаем ${testQuestionCount} задач и формируем варианты ответов`}
          stages={[
            'Подбираем задания из банка заданий',
            'Обрабатываем условия и формулы…',
            'Генерируем варианты ответов…',
            'Почти готово…',
          ]}
        />
      </LoadingOverlay>
    );
  }

  if (!task && !aiTest) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-6 p-6 text-center bg-[#F3F4F6]">
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-border max-w-md w-full">
          <Sparkles className="size-10 text-[#6D3DF5] mx-auto mb-4" />
          <h3 className="font-semibold text-lg mb-2">Тест из банка задач</h3>
          <p className="text-sm text-muted-foreground mb-6">
            Задания подбираются из банка при составлении теста. Выберите количество вопросов и
            нажмите кнопку ниже или «Составить AI-тест» на главной.
          </p>
          <p className="text-sm font-medium text-[#707076] mb-2">Количество вопросов</p>
          <div className="grid grid-cols-4 gap-2 mb-6">
            {[3, 5, 8, 10].map((count) => (
              <button
                key={count}
                onClick={() => setTestQuestionCount(count)}
                className={`h-11 rounded-xl border font-semibold ${
                  testQuestionCount === count
                    ? 'border-[#6D3DF5] bg-[#6D3DF5]/5 text-[#6D3DF5]'
                    : 'border-border bg-[#F7F7FA] text-muted-foreground'
                }`}
              >
                {count}
              </button>
            ))}
          </div>
          {testError && (
            <p className="text-sm text-destructive mb-4">{testError}</p>
          )}
          <button
            onClick={handleGenerateTestFromBank}
            className="w-full bg-[#6D3DF5] text-white font-semibold py-3.5 rounded-xl hover:bg-[#5b2fe3] transition-colors"
          >
            Сгенерировать тест
          </button>
        </div>
      </div>
    );
  }

  // Show AI test analysis
  if (analyzing) {
    return (
      <LoadingOverlay>
        <LoadingProgress
          title="Составляем аналитику"
          description={`ИИ проверяет ответы и считает прогноз ${isOgeExam ? 'оценки (2–5)' : 'баллов'}`}
          stages={[
            'Проверяем правильность ответов…',
            'Выявляем слабые темы…',
            'Считаем прогноз на экзамен…',
            'Обновляем ваш план…',
          ]}
        />
      </LoadingOverlay>
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
                  <div className="text-sm text-muted-foreground mb-1">
                    Прогноз на {isOgeExam ? 'ОГЭ' : 'ЕГЭ'}
                  </div>
                  <div className="font-bold text-lg">
                    {formatExamScore(
                      analysis.examScore ??
                        (isOgeExam
                          ? analysis.score < 25
                            ? 2
                            : analysis.score < 50
                              ? 3
                              : analysis.score < 75
                                ? 4
                                : 5
                          : Math.round(analysis.score * 0.9))
                    )}
                  </div>
                </div>
              </div>
              <div className="bg-[#6D3DF5]/5 rounded-xl p-3 border border-[#6D3DF5]/20">
                <p className="text-xs text-muted-foreground mb-1">Как рассчитывается прогноз:</p>
                <p className="text-sm">
                  {isOgeExam
                    ? 'Оценка от 2 до 5 рассчитывается по доле правильных ответов и отображается на главной.'
                    : 'Баллы рассчитывает ИИ по результатам теста и обновляет график на главной.'}
                </p>
              </div>
            </div>
            
            <div className="bg-[#F7F7FA] rounded-2xl p-6 border border-border mb-6">
              <h3 className="font-semibold text-lg mb-3">Рекомендации</h3>
              <HtmlRenderer html={analysis.analysis} className="leading-relaxed" />
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

            <div className="bg-[#F7F7FA] rounded-2xl p-6 border border-border mb-6">
              <h3 className="font-semibold text-lg mb-4">Разбор по вопросам</h3>
              <div className="space-y-4">
                {testAnswers.map((answer, index) => {
                  const breakdown = getBreakdownForAnswer(answer, index);
                  return (
                  <div
                    key={index}
                    className={`bg-white rounded-xl p-4 border ${
                      answer.correct
                        ? 'border-[#6D3DF5]/20'
                        : 'border-destructive/20'
                    }`}
                  >
                    <div className="flex items-start gap-3 mb-3">
                      <div
                        className={`rounded-xl size-8 flex items-center justify-center shrink-0 ${
                          answer.correct
                            ? 'bg-[#6D3DF5]/10 text-[#6D3DF5]'
                            : 'bg-destructive/10 text-destructive'
                        }`}
                      >
                        {answer.correct ? (
                          <Check className="size-5" />
                        ) : (
                          <XIcon className="size-5" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-sm">Вопрос {index + 1}</span>
                          <span className="text-xs text-muted-foreground">· {answer.topic}</span>
                        </div>
                        <p className="text-sm mb-3">
                          {answer.questionHtml ? (
                            <HtmlRenderer html={answer.questionHtml} />
                          ) : (
                            answer.question
                          )}
                        </p>
                        <div className="space-y-2">
                          <div className="flex items-start gap-2 text-sm">
                            <span className="text-muted-foreground shrink-0">Ваш ответ:</span>
                            <span className={answer.correct ? 'text-[#6D3DF5] font-medium' : 'text-destructive font-medium'}>
                              {answer.selectedAnswerHtml ? (
                                <HtmlRenderer html={answer.selectedAnswerHtml} />
                              ) : (
                                answer.selectedAnswer
                              )}
                            </span>
                          </div>
                          {!answer.correct && (
                            <>
                              <div className="flex items-start gap-2 text-sm">
                                <span className="text-muted-foreground shrink-0">Правильный ответ:</span>
                                <span className="text-[#6D3DF5] font-medium">
                                  {answer.correctAnswerHtml ? (
                                    <HtmlRenderer html={answer.correctAnswerHtml} />
                                  ) : (
                                    answer.correctAnswer
                                  )}
                                </span>
                              </div>
                              {breakdown?.explanation && (
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                  {breakdown.explanation}
                                </p>
                              )}
                              {breakdown?.chatPrompt && (
                                <button
                                  onClick={() =>
                                    onNavigateToChat(
                                      breakdown.chatPrompt,
                                      breakdown.subjectId || answer.subjectId || activeSubjectId
                                    )
                                  }
                                  className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-[#6D3DF5] hover:underline"
                                >
                                  <Sparkles className="size-4" />
                                  Разобрать подробно с ИИ
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
                })}
              </div>
            </div>
            
            <button
              onClick={() => {
                setAiTest(null);
                setShowAnalysis(false);
                setAnalysis(null);
                setTestAnswers([]);
                setCurrentQuestionIndex(0);
                clearAiTestData();
                clearTestResults();
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
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-border mb-6 overflow-hidden">
            <div className="flex items-start gap-3 mb-4 min-w-0">
              <div className="bg-[#6D3DF5] rounded-xl size-10 flex items-center justify-center text-white font-bold shrink-0">
                {currentQuestionIndex + 1}
              </div>
              <div className="min-w-0 flex-1 overflow-x-auto">
                <h3 className="font-semibold text-lg">
                  {currentQuestion.questionHtml ? (
                    <HtmlRenderer html={currentQuestion.questionHtml} />
                  ) : (
                    currentQuestion.question
                  )}
                </h3>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Выберите ответ:</h4>
            <div className="space-y-3">
              {currentQuestion.answers.map((answer, index) => (
                <button
                  key={index}
                  onClick={() => handleAiTestAnswer(index)}
                  disabled={analyzing}
                  className="w-full text-left p-4 rounded-xl border-2 border-border bg-white hover:border-[#6D3DF5] hover:bg-[#6D3DF5]/5 transition-colors disabled:opacity-50 overflow-hidden"
                >
                  <span className="font-medium block min-w-0 overflow-x-auto">
                    {currentQuestion.answersHtml && currentQuestion.answersHtml[index] ? (
                      <HtmlRenderer html={currentQuestion.answersHtml[index]} />
                    ) : (
                      answer
                    )}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const showExplanation = !!checkResult;

  if (!task) {
    return (
      <div className="h-full flex items-center justify-center bg-[#F3F4F6]">
        <div className="text-center p-6">
          <p className="text-muted-foreground">Задание не найдено</p>
        </div>
      </div>
    );
  }

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
              <div className="flex-1">
                <h3 className="font-semibold text-lg mb-3">
                  {task.questionHtml ? (
                    <HtmlRenderer html={task.questionHtml} />
                  ) : (
                    task.question
                  )}
                </h3>
                {task.given.length > 0 && (
                  <div className="bg-muted/50 rounded-2xl p-4 mt-4">
                    <p className="text-sm text-muted-foreground mb-2">Дано:</p>
                    <div className="space-y-1 font-mono text-sm">
                      {task.givenHtml && task.givenHtml.length > 0 ? (
                        task.givenHtml.map((line, i) => (
                          <HtmlRenderer key={i} html={line} />
                        ))
                      ) : (
                        task.given.map((line, i) => (
                          <p key={i}>{line}</p>
                        ))
                      )}
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
                        <span className="font-medium">
                          {answer.html ? (
                            <HtmlRenderer html={answer.html} />
                          ) : (
                            answer.text
                          )}
                        </span>
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
                      {checkResult.explanation.wrongHintHtml ? (
                        <HtmlRenderer html={checkResult.explanation.wrongHintHtml} />
                      ) : (
                        checkResult.explanation.wrongHint
                      )}
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
                        {checkResult.explanation.stepsHtml && checkResult.explanation.stepsHtml[i] ? (
                          <HtmlRenderer html={checkResult.explanation.stepsHtml[i]} />
                        ) : (
                          step
                        )}
                      </div>
                    ))}
                    <div className="bg-[#6D3DF5]/10 rounded-xl p-4 flex items-start gap-2">
                      <Lightbulb className="size-4 text-[#6D3DF5] shrink-0 mt-0.5" />
                      <p className="text-sm font-medium text-[#6D3DF5]">
                        {checkResult.explanation.tipHtml ? (
                          <HtmlRenderer html={checkResult.explanation.tipHtml} />
                        ) : (
                          checkResult.explanation.tip
                        )}
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
