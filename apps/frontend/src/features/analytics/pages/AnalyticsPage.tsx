import { Component, createResource, Show, For } from "solid-js";
import {
  fetchAnalyticsSummary,
  fetchSessionHistory,
  fetchWeakWords,
} from "../api/analyticsApi";

const AnalyticsPage: Component = () => {
  const [summary, { refetch: refetchSummary }] = createResource(fetchAnalyticsSummary);
  const [history, { refetch: refetchHistory }] = createResource(() => fetchSessionHistory(30));
  const [weakWords, { refetch: refetchWeakWords }] = createResource(() => fetchWeakWords());

  const handleRefresh = () => {
    refetchSummary();
    refetchHistory();
    refetchWeakWords();
  };

  const formatSeconds = (totalSeconds: number) => {
    if (totalSeconds < 60) return `${Math.round(totalSeconds)}s`;
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.round(totalSeconds % 60);
    if (mins < 60) return `${mins}m ${secs}s`;
    const hours = (mins / 60).toFixed(1);
    return `${hours}h`;
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <main class="flex-grow pt-24 pb-16 px-margin-mobile md:px-margin-desktop max-w-max-width-content mx-auto w-full flex flex-col">
      {/* Header */}
      <div class="flex flex-col sm:flex-row justify-between sm:items-baseline mb-10 gap-4">
        <div>
          <span class="font-mono-label text-mono-label uppercase tracking-widest text-on-surface-variant block mb-1">
            Learning Analytics
          </span>
          <h1 class="font-headline-md text-headline-md font-bold tracking-tight">
            Performance & History
          </h1>
        </div>
        <button
          onClick={handleRefresh}
          class="flex items-center gap-2 px-4 py-2 border border-outline-variant hover:border-primary font-mono-label text-mono-label uppercase transition-colors self-start sm:self-auto"
        >
          <span class="material-symbols-outlined text-[18px]">refresh</span>
          Refresh
        </button>
      </div>

      <Show
        when={!summary.loading && !summary.error}
        fallback={
          <div class="p-16 text-center font-mono-label text-on-surface-variant">
            {summary.error ? "Failed to load analytics data." : "Loading analytics..."}
          </div>
        }
      >
        {/* KPI Summary Grid */}
        <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-12">
          <div class="bg-surface-container border border-outline-variant p-6 flex flex-col">
            <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase tracking-wider mb-2">
              Drills Done
            </span>
            <span class="font-headline-md text-3xl font-bold text-primary" id="kpi-total-drills">
              {summary()?.total_drills || 0}
            </span>
          </div>

          <div class="bg-surface-container border border-outline-variant p-6 flex flex-col">
            <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase tracking-wider mb-2">
              Average WPM
            </span>
            <span class="font-headline-md text-3xl font-bold text-primary" id="kpi-avg-wpm">
              {summary()?.avg_net_wpm || 0}
            </span>
          </div>

          <div class="bg-surface-container border border-outline-variant p-6 flex flex-col">
            <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase tracking-wider mb-2">
              Peak WPM
            </span>
            <span class="font-headline-md text-3xl font-bold text-primary" id="kpi-peak-wpm">
              {summary()?.peak_net_wpm || 0}
            </span>
          </div>

          <div class="bg-surface-container border border-outline-variant p-6 flex flex-col">
            <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase tracking-wider mb-2">
              Avg Accuracy
            </span>
            <span class="font-headline-md text-3xl font-bold text-primary" id="kpi-avg-accuracy">
              {summary()?.avg_accuracy || 0}%
            </span>
          </div>

          <div class="bg-surface-container border border-outline-variant p-6 flex flex-col col-span-2 lg:col-span-1">
            <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase tracking-wider mb-2">
              Practice Time
            </span>
            <span class="font-headline-md text-3xl font-bold text-primary" id="kpi-total-time">
              {formatSeconds(summary()?.total_practice_seconds || 0)}
            </span>
          </div>
        </div>

        {/* Recent Progression Trend */}
        <div class="mb-12 border border-outline-variant bg-surface p-6">
          <div class="flex justify-between items-center mb-6">
            <h2 class="font-headline-md text-xl font-bold">Recent Speed & Accuracy Progression</h2>
            <span class="font-mono-sm text-mono-sm text-on-surface-variant">Last 20 Drills</span>
          </div>

          <Show
            when={summary()?.recent_trend && summary()!.recent_trend.length > 0}
            fallback={
              <div class="p-8 text-center font-mono-label text-outline">
                No completed drills yet. Start typing a story to build your progression curve!
              </div>
            }
          >
            <div class="h-44 flex items-end gap-2 pt-4 border-b border-outline-variant">
              <For each={summary()!.recent_trend}>
                {(point) => {
                  const heightPercent = Math.min(100, Math.max(10, (point.net_wpm / 120) * 100));
                  return (
                    <div
                      class="flex-1 flex flex-col items-center gap-1 group relative h-full justify-end"
                      title={`${formatDate(point.completed_at)}: ${point.net_wpm} WPM (${point.accuracy}%)`}
                    >
                      <div
                        class="w-full bg-primary/80 group-hover:bg-primary transition-all rounded-t-sm"
                        style={{ height: `${heightPercent}%` }}
                      ></div>
                      <div class="pointer-events-none absolute bottom-full mb-2 bg-[#1e1e1e] text-white font-mono-sm text-xs p-2 rounded shadow opacity-0 group-hover:opacity-100 transition-opacity z-20 whitespace-nowrap">
                        <div>{point.net_wpm} WPM</div>
                        <div class="text-on-surface-variant text-[10px]">{point.accuracy}% accuracy</div>
                      </div>
                    </div>
                  );
                }}
              </For>
            </div>
            <div class="flex justify-between text-mono-sm font-mono-sm text-on-surface-variant mt-2">
              <span>Earlier</span>
              <span>Latest</span>
            </div>
          </Show>
        </div>

        {/* Two-Column: Weak Words & History */}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Weak Words Panel */}
          <div class="border border-outline-variant bg-surface p-6 flex flex-col">
            <div class="flex justify-between items-center mb-6">
              <h2 class="font-headline-md text-xl font-bold">Persistent Weak Words</h2>
              <span class="material-symbols-outlined text-outline">psychology</span>
            </div>

            <Show
              when={weakWords() && weakWords()!.length > 0}
              fallback={
                <div class="p-8 text-center font-mono-label text-outline my-auto">
                  No weak words recorded yet! Mistakes during drills will be tracked here.
                </div>
              }
            >
              <div class="flex flex-col divide-y divide-outline-variant overflow-y-auto max-h-96">
                <For each={weakWords()}>
                  {(item) => (
                    <div class="py-3 flex justify-between items-center">
                      <div>
                        <div class="font-bold font-mono-label text-mono-label">{item.word}</div>
                        <div class="font-mono-sm text-mono-sm text-on-surface-variant">
                          {item.language}
                        </div>
                      </div>
                      <span class="px-2.5 py-0.5 bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300 border border-red-200 font-mono-label text-mono-label">
                        {item.mistake_count} mistake{item.mistake_count === 1 ? "" : "s"}
                      </span>
                    </div>
                  )}
                </For>
              </div>
            </Show>
          </div>

          {/* Session History Table */}
          <div class="lg:col-span-2 border border-outline-variant bg-surface p-6 flex flex-col">
            <div class="flex justify-between items-center mb-6">
              <h2 class="font-headline-md text-xl font-bold">Recent Drills</h2>
              <span class="font-mono-sm text-mono-sm text-on-surface-variant">
                {history()?.length || 0} recorded
              </span>
            </div>

            <Show
              when={history() && history()!.length > 0}
              fallback={
                <div class="p-8 text-center font-mono-label text-outline my-auto">
                  No drills completed yet. Head to the Library or Practice page to start!
                </div>
              }
            >
              <div class="overflow-x-auto">
                <table class="w-full text-left font-mono-label text-mono-label">
                  <thead>
                    <tr class="border-b border-outline-variant text-on-surface-variant text-mono-sm">
                      <th class="py-2 pr-4">Time</th>
                      <th class="py-2 pr-4">Target</th>
                      <th class="py-2 pr-4">WPM</th>
                      <th class="py-2 pr-4">Accuracy</th>
                      <th class="py-2">Time</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-outline-variant">
                    <For each={history()}>
                      {(session) => (
                        <tr class="hover:bg-surface-container/40 transition-colors">
                          <td class="py-3 pr-4 text-mono-sm text-on-surface-variant">
                            {formatDate(session.completed_at)}
                          </td>
                          <td class="py-3 pr-4 max-w-[240px] truncate" title={session.sentence_text}>
                            {session.sentence_text || `Sentence ${session.sentence_index + 1}`}
                          </td>
                          <td class="py-3 pr-4 font-bold text-primary">
                            {session.net_wpm}
                          </td>
                          <td class="py-3 pr-4">
                            {session.accuracy}%
                          </td>
                          <td class="py-3 text-mono-sm text-on-surface-variant">
                            {session.active_seconds}s
                          </td>
                        </tr>
                      )}
                    </For>
                  </tbody>
                </table>
              </div>
            </Show>
          </div>
        </div>
      </Show>
    </main>
  );
};

export default AnalyticsPage;
