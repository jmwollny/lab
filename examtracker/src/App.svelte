<script>
  import { onMount } from 'svelte';
  import ExamList from './lib/ExamList.svelte';
  import {
    getExamMetrics,
    sortExams,
    getCompletionThreshold,
  } from './lib/metrics.js';

  let subject = '';
  let date = '';
  let isPM = false;
  let exams = [];
  let isInitialized = false;
  let now = new Date();

  function formatCountdown(exam, currentTime) {
    const target = getCompletionThreshold(exam);
    const diff = target - currentTime;
    if (diff <= 0) return 'Done';

    const days = Math.floor(diff / 86400000);
    const hours = Math.floor((diff % 86400000) / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    return `${days}d ${hours}h ${mins}m`;
  }

  $: countdownText = metrics.nextExam
    ? formatCountdown(metrics.nextExam, now)
    : '';

  onMount(() => {
    const saved = localStorage.getItem('exams');
    if (saved) {
      try {
        exams = JSON.parse(saved);
      } catch (err) {
        console.error('Failed to parse exams from localStorage:', err);
      }
    }
    isInitialized = true;

    const interval = setInterval(() => {
      now = new Date();
    }, 1000);
    return () => clearInterval(interval);
  });

  const addExam = () => {
    const trimmedSubject = subject.trim();
    if (!trimmedSubject || !date) return;

    const [year, month, day] = date.split('-').map(Number);
    const examDate = new Date(year, month - 1, day);
    examDate.setHours(isPM ? 13 : 9, 0, 0, 0); // 9 AM for AM, 1 PM for PM

    exams = [
      ...exams,
      { id: Date.now(), subject: trimmedSubject, date, examDate, isPM },
    ];

    subject = '';
    date = '';
    isPM = false;
  };

  const removeExam = (id) => {
    if (confirm('Are you sure you want to remove this exam?')) {
      exams = exams.filter((exam) => exam.id !== id);
    }
  };

  const clearExams = () => {
    if (confirm('Clear all exams? This cannot be undone.')) {
      exams = [];
    }
  };

  $: {
    if (isInitialized) {
      localStorage.setItem('exams', JSON.stringify(exams));
    }
  }

  $: sortedExams = sortExams(exams); // Still needed for metrics
  $: displayExams = sortedExams.map((exam) => ({
    ...exam,
    isDone: getCompletionThreshold(exam) <= now,
  }));
  $: metrics = getExamMetrics(sortedExams, now); // metrics still uses sortedExams
</script>

<main>
  <section class="hero">
    <div>
      <h1>Exam Tracker</h1>
      <p>
        Enter exam dates and subjects, then watch the next exam and completion
        summary update automatically.
      </p>
    </div>
  </section>

  <div class="dashboard-grid">
    <div class="sidebar">
      <section class="card">
        <form on:submit|preventDefault={addExam}>
          <div class="field-stack">
            <label for="subject-input">
              Subject
              <input
                id="subject-input"
                type="text"
                bind:value={subject}
                placeholder="Enter exam subject"
              />
            </label>
            <div class="date-row">
              <label for="date-input">
                Date
                <input id="date-input" type="date" bind:value={date} />
              </label>
              <label class="checkbox-field" for="pm-checkbox">
                PM?
                <input id="pm-checkbox" type="checkbox" bind:checked={isPM} />
              </label>
            </div>
          </div>
          <button type="submit" disabled={!subject.trim() || !date}
            >Add exam</button
          >
        </form>
      </section>

      <section class="card">
        <div class="metric-grid">
          <div>
            <dt>Next exam</dt>
            <dd>
              {metrics.nextExam ? metrics.nextExam.subject : 'None scheduled'}
              {#if metrics.nextExam}
                <span class="countdown">{countdownText}</span>
              {/if}
            </dd>
          </div>
          <div>
            <dt>Days until next exam</dt>
            <dd>{metrics.nextExam ? metrics.daysUntilNextExam : 'N/A'}</dd>
          </div>
          <div>
            <dt>Percentage complete</dt>
            <dd>{sortedExams.length ? `${metrics.percentComplete}%` : '0%'}</dd>
          </div>
          <div>
            <dt>Days until all exams finished</dt>
            <dd>{sortedExams.length ? metrics.daysUntilAllFinished : 'N/A'}</dd>
          </div>
        </div>
      </section>
    </div>

    <div class="list-pane">
      <ExamList
        exams={displayExams}
        on:remove={(e) => removeExam(e.detail)}
        on:clear={clearExams}
      />
    </div>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: system-ui, sans-serif;
    background: #eef2ff;
    color: #0f172a;
    box-sizing: border-box;
  }

  :global(*),
  :global(*::before),
  :global(*::after) {
    box-sizing: inherit;
  }

  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1rem 0;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .hero {
    margin-bottom: 1.5rem;
  }

  h1 {
    margin: 0 0 0.5rem;
    font-size: clamp(2rem, 3vw, 2.75rem);
  }

  .dashboard-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: 360px 1fr;
    flex: 1;
    min-height: 0;
    margin-bottom: 2rem;
  }

  @media (max-width: 1024px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
      margin-bottom: 3rem;
    }
    main {
      max-width: 820px;
      height: auto;
      display: block;
    }
  }

  .field-stack {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }

  .date-row {
    display: grid;
    gap: 1rem;
    grid-template-columns: 1fr auto;
    align-items: end;
  }

  label {
    display: grid;
    gap: 0.5rem;
    font-weight: 600;
    color: #334155;
  }

  .checkbox-field {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: #334155;
  }

  .checkbox-field input {
    width: auto;
    margin: 0;
  }

  input {
    width: 100%;
    padding: 0.85rem 1rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.85rem;
    font: inherit;
  }

  button {
    border: none;
    background: #4338ca;
    color: white;
    padding: 0.95rem 1.2rem;
    border-radius: 0.9rem;
    cursor: pointer;
    font-weight: 700;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .metric-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  dt {
    font-weight: 700;
    color: #334155;
  }

  dd {
    margin: 0.35rem 0 0;
    color: #111827;
  }

  .countdown {
    display: block;
    font-size: 0.75rem;
    color: #4f46e5;
    font-weight: 600;
    margin-top: 0.25rem;
  }

  .list-pane {
    overflow-y: auto;
    height: 100%;
    padding-right: 0.5rem;
  }

  .sidebar {
    overflow-y: auto;
    height: 100%;
    padding-right: 0.25rem;
  }
</style>
