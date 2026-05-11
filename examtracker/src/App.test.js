import { expect, test, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import App from './App.svelte';
import {
  getExamMetrics,
  sortExams,
  getCompletionThreshold,
} from './lib/metrics.js';

const addSubject = async (subject, date, isPM) => {
  const subjectInput = screen.getByLabelText(/Subject/i);
  const dateInput = screen.getByLabelText('Date');
  const pmCheckbox = screen.getByLabelText(/PM/i);
  const addButton = screen.getByRole('button', { name: /add exam/i });

  await fireEvent.input(subjectInput, { target: { value: subject } });
  await fireEvent.input(dateInput, { target: { value: date } });
  if (isPM) {
    await fireEvent.click(pmCheckbox);
  }
  await fireEvent.click(addButton);
};

beforeEach(() => {
  localStorage.clear();
  vi.useRealTimers();
});

afterEach(() => {
  cleanup();
});

test('sortExams orders exams by ascending date', () => {
  const exams = [
    { subject: 'Biology AM', date: '2026-06-15', isPM: false },
    { subject: 'Math PM', date: '2026-05-01', isPM: true },
    { subject: 'Math AM', date: '2026-05-01', isPM: false },
    { subject: 'English AM', date: '2026-07-10', isPM: false },
  ];

  const sorted = sortExams(exams);
  expect(sorted.map((exam) => exam.subject)).toEqual([
    'Math AM',
    'Math PM',
    'Biology AM',
    'English AM',
  ]);
});

test('getExamMetrics returns next exam and completion values', () => {
  const today = new Date('2026-05-11T07:50:00');
  const exams = [{ subject: 'English', date: '2026-05-11', isPM: false }];

  const metrics = getExamMetrics(exams, today);
  expect(metrics.nextExam.subject).toBe('English');
  expect(metrics.msUntilNextExam).toBe(11400000);
  expect(Math.round(metrics.percentComplete)).toBe(0);
  expect(metrics.daysUntilAllFinished).toBe(1);
});

test('getCompletionThreshold returns correct dates for AM and PM', () => {
  const amExam = { date: '2026-05-01', isPM: false };
  const pmExam = { date: '2026-05-01', isPM: true };

  const amThreshold = getCompletionThreshold(amExam);
  const pmThreshold = getCompletionThreshold(pmExam);

  expect(amThreshold.getHours()).toBe(11);
  expect(pmThreshold.getHours()).toBe(15);
});

test('getExamMetrics respects AM/PM completion thresholds', () => {
  const examDate = '2026-05-01';
  const exams = [
    { subject: 'AM Exam', date: examDate, isPM: false }, // Done after 11:00
    { subject: 'PM Exam', date: examDate, isPM: true }, // Done after 15:00
  ];

  // At 10:59 AM, none are done
  const morning = new Date(`${examDate}T10:59:00`);
  let metrics = getExamMetrics(exams, morning);
  expect(metrics.percentComplete).toBe(0);

  // 2. At 11:01 PM, AM exam is done (50%)
  const afternoon = new Date(`${examDate}T11:01:00`);
  metrics = getExamMetrics(exams, afternoon);
  expect(metrics.percentComplete).toBe(50);

  // 3. At 3:01 PM, both are done (100%)
  const lateAfternoon = new Date(`${examDate}T15:01:00`);
  metrics = getExamMetrics(exams, lateAfternoon);
  expect(metrics.percentComplete).toBe(100);
});

test('getExamMetrics calculates "Days until all finished" based on the last exam', () => {
  const today = new Date('2026-05-01T09:00:00');
  const exams = [
    { subject: 'First', date: '2026-05-05', isPM: false },
    { subject: 'Last', date: '2026-05-11', isPM: false },
  ];

  const metrics = getExamMetrics(exams, today);
  // May 1st to May 11th is 10 days.
  expect(metrics.daysUntilAllFinished).toBe(11);

  // Verify it handles the "all done" state
  const afterAllDone = new Date('2026-05-12T00:00:00');
  const finishedMetrics = getExamMetrics(exams, afterAllDone);
  expect(finishedMetrics.daysUntilAllFinished).toBe(0);
});

test('marks exam as done in the UI after threshold', async () => {
  const examDate = '2026-05-01';
  // Mock time to be 12:01 PM on exam day
  vi.useFakeTimers();
  vi.setSystemTime(new Date(`${examDate}T17:00:00`));

  const { container } = render(App);

  await addSubject('Biology', examDate, true);

  // The countdown text should now show "Done" instead of a timer
  expect(screen.getByText('None scheduled')).toBeTruthy(); // Next exam should show "None scheduled" since the PM exam is done after 3:00 PM
  expect(screen.getByText('100%')).toBeTruthy(); // Percent complete should be 100% since the PM exam is done after 3:00 PM
  expect(screen.getByText('N/A')).toBeTruthy(); // Days until next exam should be N/A since there are no more exams

  const completedExam = container.querySelector('.done');
  expect(completedExam).toBeTruthy();
});

test('adds and removes an exam from the UI', async () => {
  const examDate = '2026-08-15';
  vi.spyOn(window, 'confirm').mockImplementation(() => true);

  render(App);

  expect(
    screen.queryByText('No exams scheduled yet. Add your first subject above!'),
  ).toBeTruthy();

  await addSubject('Chemistry', examDate, true);

  expect(screen.getByRole('cell', { name: 'Chemistry' })).toBeTruthy();

  const removeButton = screen.getByRole('button', { name: /remove/i });
  await fireEvent.click(removeButton);

  expect(screen.queryByRole('cell', { name: 'Chemistry' })).toBeNull();
});

test('date until next exam is formatted correctly = less than a day', async () => {
  const timeNow = '2026-05-11';
  const examDate = '2026-05-11';
  vi.useFakeTimers();
  vi.setSystemTime(new Date(`${timeNow}T08:00:00`));
  render(App);

  // Add PM exam, so it starts at 1pm and is done after 3pm
  await addSubject('English', examDate, true);

  expect(screen.getByRole('cell', { name: 'English' })).toBeTruthy();
  expect(screen.getByText('< 1 day')).toBeTruthy();
  expect(screen.getByText('0d 7h 0m')).toBeTruthy();
});

test('date until next exam is formatted correctly - one day', async () => {
  const timeNow = '2026-05-11';
  const examDate = '2026-05-12';
  vi.useFakeTimers();
  vi.setSystemTime(new Date(`${timeNow}T08:00:00`));
  render(App);

  // Add PM exam, so it starts at 1pm and is done after 3pm
  await addSubject('English', examDate, true);

  expect(screen.getByRole('cell', { name: 'English' })).toBeTruthy();
  expect(screen.getByText('1 day')).toBeTruthy();
  expect(screen.getByText('1d 7h 0m')).toBeTruthy();
});

test('date until next exam is formatted correctly - more than a day', async () => {
  const timeNow = '2026-05-11';
  const examDate = '2026-05-13';
  vi.useFakeTimers();
  vi.setSystemTime(new Date(`${timeNow}T08:00:00`));
  render(App);

  // Add PM exam, so it starts at 1pm and is done after 3pm
  await addSubject('English', examDate, true);

  expect(screen.getByRole('cell', { name: 'English' })).toBeTruthy();
  expect(screen.getByText('2 days')).toBeTruthy();
  expect(screen.getByText('2d 7h 0m')).toBeTruthy();
});
