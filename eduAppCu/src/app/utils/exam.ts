import type { UserAccount } from '../types';

export const OGE_GRADES = [2, 3, 4, 5] as const;

export function defaultTargetForExam(examType: UserAccount['examType']): number {
  return examType === 'ОГЭ' ? 4 : 80;
}

/** Приводит цель к шкале ОГЭ (2–5) или ЕГЭ (0–100). */
export function clampTargetForExam(
  value: number | undefined,
  examType: UserAccount['examType']
): number {
  const fallback = defaultTargetForExam(examType);
  if (value === undefined || Number.isNaN(value)) {
    return fallback;
  }
  if (examType === 'ОГЭ') {
    const rounded = Math.round(value);
    if (rounded >= 2 && rounded <= 5) {
      return rounded;
    }
    if (rounded < 25) return 2;
    if (rounded < 50) return 3;
    if (rounded < 75) return 4;
    return 5;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function normalizeTargetsForExam(
  targets: Record<string, number>,
  subjectIds: string[],
  examType: UserAccount['examType']
): Record<string, number> {
  return Object.fromEntries(
    subjectIds.map((id) => [id, clampTargetForExam(targets[id], examType)])
  );
}

export function formatTargetShort(
  value: number | undefined,
  examType: UserAccount['examType']
): string {
  const score = clampTargetForExam(value, examType);
  if (examType === 'ОГЭ') {
    return `оценка ${score}`;
  }
  return `${score} б.`;
}

export function formatTargetLong(
  value: number | undefined,
  examType: UserAccount['examType']
): string {
  const score = clampTargetForExam(value, examType);
  if (examType === 'ОГЭ') {
    return `цель — оценка ${score}`;
  }
  return `цель ${score} баллов`;
}
