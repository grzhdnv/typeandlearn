import { Component, createResource, createSignal, createMemo, Show, createEffect, onMount, onCleanup } from 'solid-js';
import { useNavigate, useParams } from '@solidjs/router';
import { fetchStory, updateProgress, resetProgress, regenerateTopWords, retryEnrichment } from '../../../features/texts/api/textsApi';
import { recordPracticeSession } from '../../../features/analytics/api/analyticsApi';
import { StatusBadge } from '../../../features/texts/components/StatusBadge';
import { TypingInterface } from '../../../features/typing/components/TypingInterface';
import { HintGroup } from '../../../shared/types/contracts';
import type { TypingMetrics } from '../../../features/typing/core/types.ts';

type UiSentence = {
  text: string;
  hints: HintGroup[];
  translation: string;
};

const PracticePage: Component = () => {
  const params = useParams();
  const navigate = useNavigate();
  const [storyData, { refetch: refetchStory }] = createResource(() => params.id, fetchStory);
  const [isRegenerating, setIsRegenerating] = createSignal(false);
  const [isRetrying, setIsRetrying] = createSignal(false);
  const [filteringMethod, setFilteringMethod] = createSignal<"spacy" | "llm">("spacy");

  const [activeTab, setActiveTab] = createSignal<"original" | "generated">("original");
  const [originalIndex, setOriginalIndex] = createSignal(0);
  const [generatedIndex, setGeneratedIndex] = createSignal(0);
  const [liveMetrics, setLiveMetrics] = createSignal<TypingMetrics | null>(null);
  const [completedMetrics, setCompletedMetrics] = createSignal<TypingMetrics | null>(null);
  const [srAnnouncement, setSrAnnouncement] = createSignal("");
  const [attempt, setAttempt] = createSignal(0);

  let lastStoryId: number | undefined | null = null;
  createEffect(() => {
    const story = storyData();
    if (story && story.id !== lastStoryId) {
      lastStoryId = story.id;
      const completed = new Set(story.completed_sentence_indices ?? []);
      const firstIncomplete = Array.from({ length: story.total_sentences }, (_, index) => index)
        .find(index => !completed.has(index));
      setOriginalIndex(firstIncomplete ?? 0);
      setGeneratedIndex(0);
      setCompletedMetrics(null);
      setLiveMetrics(null);
    }
  });

  createEffect(() => {
    let intervalId: number | undefined;
    const story = storyData();
    const isJobActive =
      story?.status === "processing" ||
      story?.status === "pending" ||
      story?.enrichment_stage === "queued" ||
      story?.enrichment_stage === "translating" ||
      story?.enrichment_stage === "generating_practice";

    if (isJobActive) {
      intervalId = window.setInterval(() => {
        refetchStory();
      }, 2000);
    }
    
    onCleanup(() => {
      if (intervalId) window.clearInterval(intervalId);
    });
  });

  const originalSentences = createMemo<UiSentence[]>(() => {
    const story = storyData();
    if (!story) return [];
    return story.original_paragraphs.flatMap((paragraph) =>
      paragraph.sentences.map((sentence) => ({
        text: sentence.text,
        hints: sentence.translation_hints,
        translation: sentence.translation,
      }))
    );
  });

  const generatedSentences = createMemo<UiSentence[]>(() => {
    const story = storyData();
    if (!story) return [];
    return story.practice_sentences.map((sentence) => ({
      text: sentence.sentence,
      hints: sentence.translation_hints,
      translation: sentence.translation,
    }));
  });

  const previousDisabled = () =>
    activeTab() === "original" ? originalIndex() === 0 : generatedIndex() === 0;
  
  const nextDisabled = () =>
    activeTab() === "original"
      ? originalIndex() >= originalSentences().length - 1
      : generatedIndex() >= generatedSentences().length - 1;

  const goToPreviousSentence = () => {
    setCompletedMetrics(null);
    setLiveMetrics(null);
    if (activeTab() === "original" && originalIndex() > 0) {
      setOriginalIndex((i) => {
        const next = i - 1;
        setSrAnnouncement(`Navigated to sentence ${next + 1} of ${originalSentences().length}`);
        return next;
      });
    } else if (activeTab() === "generated" && generatedIndex() > 0) {
      setGeneratedIndex((i) => {
        const next = i - 1;
        setSrAnnouncement(`Navigated to sentence ${next + 1} of ${generatedSentences().length}`);
        return next;
      });
    }
  };

  const goToNextSentence = () => {
    setCompletedMetrics(null);
    setLiveMetrics(null);
    if (activeTab() === "original" && originalIndex() < originalSentences().length - 1) {
      setOriginalIndex((i) => {
        const next = i + 1;
        setSrAnnouncement(`Navigated to sentence ${next + 1} of ${originalSentences().length}`);
        return next;
      });
    } else if (activeTab() === "generated" && generatedIndex() < generatedSentences().length - 1) {
      setGeneratedIndex((i) => {
        const next = i + 1;
        setSrAnnouncement(`Navigated to sentence ${next + 1} of ${generatedSentences().length}`);
        return next;
      });
    }
  };

  const handleSentenceComplete = (metrics: TypingMetrics) => {
    setSrAnnouncement(
      `Drill completed. Speed: ${metrics.netWpm} words per minute. Accuracy: ${metrics.accuracy} percent.`
    );
    if (params.id) {
      const idx = activeTab() === "original" ? originalIndex() : generatedIndex();
      if (activeTab() === "original") updateProgress(params.id, idx).catch(console.error);

      const sentences = activeTab() === "original" ? originalSentences() : generatedSentences();
      const sentenceText = sentences[idx]?.text || "";

      recordPracticeSession({
        text_id: Number.parseInt(params.id, 10),
        sentence_index: idx,
        sentence_text: sentenceText,
        target_type: activeTab(),
        net_wpm: metrics.netWpm,
        raw_wpm: metrics.rawWpm,
        accuracy: metrics.accuracy,
        active_seconds: metrics.activeSeconds,
        mistake_count: metrics.mistakeCount,
      }).catch(console.error);
    }
    if (nextDisabled()) {
      setCompletedMetrics(metrics);
    } else {
      setSrAnnouncement("Sentence complete. Press Enter to continue.");
    }
  };

  const navigateSentence = (direction: "previous" | "next") => {
    if (direction === "previous" && !previousDisabled()) goToPreviousSentence();
    if (direction === "next" && !nextDisabled()) goToNextSentence();
  };

  const continuePractice = () => {
    if (nextDisabled()) {
      navigate("/");
      return;
    }
    setCompletedMetrics(null);
    setLiveMetrics(null);
    if (activeTab() === "original") {
      if (originalIndex() < originalSentences().length - 1) {
        setOriginalIndex((i) => i + 1);
      }
    } else {
      if (generatedIndex() < generatedSentences().length - 1) {
        setGeneratedIndex((i) => i + 1);
      }
    }
  };

  const handleResetProgress = async () => {
    if (!params.id) return;
    if (!confirm("Are you sure you want to reset your progress for this text?")) return;
    try {
      await resetProgress(params.id);
      setOriginalIndex(0);
      setGeneratedIndex(0);
      setCompletedMetrics(null);
      setLiveMetrics(null);
      setAttempt(value => value + 1);
    } catch (error) {
      console.error("Failed to reset progress:", error);
      alert(error instanceof Error ? error.message : "Failed to reset progress.");
    }
  };

  const handleRegenerateWords = async () => {
    if (!params.id) return;
    setIsRegenerating(true);
    try {
      await regenerateTopWords(params.id, filteringMethod());
      refetchStory();
      setOriginalIndex(0);
      setGeneratedIndex(0);
    } catch (error) {
      console.error("Failed to regenerate words:", error);
      alert(error instanceof Error ? error.message : "Failed to regenerate words.");
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleRetry = async () => {
    if (!params.id) return;
    setIsRetrying(true);
    try {
      await retryEnrichment(params.id);
      refetchStory();
    } catch (error) {
      console.error("Failed to retry enrichment:", error);
      alert(error instanceof Error ? error.message : "Failed to retry enrichment.");
    } finally {
      setIsRetrying(false);
    }
  };

  const handleControlClick = (action: () => void) => () => action();

  createEffect(() => {
    if (completedMetrics()) {
      queueMicrotask(() => document.getElementById("btn-results-review")?.focus());
    }
  });

  onMount(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is using modifier keys
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      
      if (completedMetrics()) {
        if (e.key === "Tab") {
          e.preventDefault();
          const first = document.getElementById("btn-results-review");
          const last = document.getElementById("btn-results-next");
          (document.activeElement === first ? last : first)?.focus();
          return;
        }
        if (e.key === "Enter" && e.target instanceof HTMLButtonElement) return;
        if (e.key === "Enter") {
          e.preventDefault();
          continuePractice();
          return;
        } else if (e.key === "Escape") {
          e.preventDefault();
          setCompletedMetrics(null);
          return;
        }
      }

      const target = e.target;
      if (e.defaultPrevented || e.isComposing || e.repeat ||
          (target instanceof HTMLElement && target.closest("input, textarea, select, button, a, [contenteditable=true]"))) return;

      if (e.key === "[") {
        e.preventDefault();
        navigateSentence("previous");
      } else if (e.key === "]") {
        e.preventDefault();
        navigateSentence("next");
      }
    };
    
    globalThis.addEventListener("keydown", handleGlobalKeyDown);
    onCleanup(() => {
      globalThis.removeEventListener("keydown", handleGlobalKeyDown);
    });
  });

  const currentIndex = () => activeTab() === "original" ? originalIndex() : generatedIndex();
  const totalSentences = () => activeTab() === "original" ? originalSentences().length : generatedSentences().length;
  const progressPercent = () => totalSentences() === 0 ? 0 : ((currentIndex() + 1) / totalSentences()) * 100;

  return (
    <section
      aria-label="Typing Practice Canvas"
      class="flex-grow pt-8 md:pt-16 pb-8 px-margin-mobile md:px-margin-desktop max-w-max-width-content mx-auto w-full flex flex-col"
    >
      {/* Screen Reader Live Announcements (WCAG 2.1 AA) */}
      <div
        class="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        id="sr-practice-status"
      >
        {srAnnouncement()}
      </div>

      <Show when={Boolean(storyData()) && !storyData.error} fallback={
        <div class="flex items-center justify-center h-64 font-mono-label text-on-surface-variant">
          {storyData.error ? "Failed to load text." : "Loading..."}
        </div>
      }>
        {/* Header Info */}
        <div class="flex flex-col md:flex-row justify-between mb-12 gap-6 items-baseline">
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <span class="bg-surface-container border border-outline-variant px-2 py-0.5 text-mono-label font-mono-label">
                {storyData()?.language?.toUpperCase() || "UNKNOWN"}
              </span>
              <Show when={storyData()?.difficulty_level && storyData()?.difficulty_level !== "Unrated"}>
                <span class="bg-surface-container border border-outline-variant px-2 py-0.5 text-mono-label font-mono-label">
                  {storyData()?.difficulty_level?.toUpperCase()}
                </span>
              </Show>
              <Show when={storyData()?.category}>
                <span class="bg-surface-container border border-outline-variant px-2 py-0.5 text-mono-label font-mono-label">
                  {storyData()?.category?.toUpperCase()}
                </span>
              </Show>
              <span class="text-on-surface-variant text-mono-sm font-mono-sm opacity-60">ID: {params.id}</span>
              <Show when={storyData()}>
                <StatusBadge
                  status={storyData()!.status}
                  stage={storyData()!.enrichment_stage}
                  errorMessage={storyData()!.error_message}
                  onRetry={handleRetry}
                  isRetrying={isRetrying()}
                />
              </Show>
            </div>
            <h1 class="font-headline-md text-headline-md leading-tight">{storyData()?.title || "Untitled"}</h1>
            <Show when={storyData()?.author}>
              <div class="text-on-surface-variant font-mono-sm">By {storyData()?.author}</div>
            </Show>
          </div>
          
          {/* Real-time Stats - Live calculation from typing engine */}
          <div class="flex gap-8 border-l border-outline-variant pl-8 items-center" title="Real-time typing statistics">
            <div class="flex flex-col">
              <span class="text-mono-sm font-mono-sm text-on-surface-variant uppercase tracking-wider">Accuracy</span>
              <span class="font-mono-label text-headline-md text-primary" id="metric-accuracy">
                {liveMetrics() ? `${liveMetrics()!.accuracy}%` : "--%"}
              </span>
            </div>
            <div class="flex flex-col">
              <span class="text-mono-sm font-mono-sm text-on-surface-variant uppercase tracking-wider">WPM</span>
              <span class="font-mono-label text-headline-md text-primary" id="metric-wpm">
                {liveMetrics() ? liveMetrics()!.netWpm : "--"}
              </span>
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div class="mb-4 flex gap-2">
          <div class="flex bg-surface-container border border-outline-variant p-0.5">
            <button 
              onClick={handleControlClick(() => { setActiveTab("original"); setLiveMetrics(null); })}
              class={`px-6 py-1.5 text-mono-label font-mono-label shadow-sm transition-colors ${activeTab() === "original" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
            >
              Original
            </button>
            <button 
              onClick={handleControlClick(() => { setActiveTab("generated"); setLiveMetrics(null); })}
              class={`px-6 py-1.5 text-mono-label font-mono-label shadow-sm transition-colors ${activeTab() === "generated" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
            >
              Generated
            </button>
          </div>
        </div>

        <Show when={
          storyData()?.status === "processing" ||
          storyData()?.status === "pending" ||
          storyData()?.enrichment_stage === "queued" ||
          storyData()?.enrichment_stage === "translating" ||
          storyData()?.enrichment_stage === "generating_practice"
        }>
          <div class="p-4 mb-6 bg-amber-50 border border-amber-300 dark:bg-amber-950/30 dark:border-amber-800 text-amber-900 dark:text-amber-200 font-mono-label flex items-center gap-3">
            <span class="material-symbols-outlined animate-spin text-[20px]">autorenew</span>
            <span>
              {storyData()?.enrichment_stage === "translating"
                ? "Translating sentences and hints with AI... "
                : storyData()?.enrichment_stage === "generating_practice"
                ? "Extracting vocabulary and generating practice drills... "
                : "AI enrichment in progress... "}
              You can start typing the original text now while enrichment completes.
            </span>
          </div>
        </Show>

        <Show when={storyData()?.status === "failed" || storyData()?.enrichment_stage === "failed"}>
          <div class="p-4 mb-6 bg-red-50 border border-red-300 dark:bg-red-950/30 dark:border-red-800 text-red-900 dark:text-red-200 font-mono-label flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined text-red-600 dark:text-red-400 text-[20px]">warning</span>
              <div>
                <div class="font-bold">AI Enrichment Failed</div>
                <div class="text-xs text-red-700 dark:text-red-300">
                  {storyData()?.error_message || "An error occurred during AI enrichment. You can still practice typing the original text."}
                </div>
              </div>
            </div>
            <button
              onClick={handleRetry}
              disabled={isRetrying()}
              class="px-4 py-2 bg-primary text-on-primary font-mono-label text-mono-label hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2 self-start sm:self-auto"
            >
              <span class={`material-symbols-outlined text-[16px] ${isRetrying() ? "animate-spin" : ""}`}>
                {isRetrying() ? "autorenew" : "refresh"}
              </span>
              {isRetrying() ? "Retrying..." : "Retry Enrichment"}
            </button>
          </div>
        </Show>

        <Show when={totalSentences() > 0} fallback={
          <div class="p-10 text-center font-mono-label text-outline">
            {activeTab() === "generated" && (storyData()?.status === "processing" || storyData()?.status === "pending")
              ? "Practice sentences are being generated by AI. They will appear here once enrichment completes."
              : "No sentences available for this text yet."}
          </div>
        }>
          <Show when={activeTab() === "original"} fallback={
            <TypingInterface
              sessionKey={`${params.id}:generated:${generatedIndex()}:${attempt()}`}
              disabled={Boolean(completedMetrics())}
              targetText={generatedSentences()[generatedIndex()].text}
              hints={generatedSentences()[generatedIndex()].hints}
              fullTranslation={generatedSentences()[generatedIndex()].translation}
              onContinue={continuePractice}
              continueLabel={nextDisabled() ? "Enter to finish" : "Enter to continue"}
              onNavigate={navigateSentence}
              onComplete={handleSentenceComplete}
              onMetricsUpdate={setLiveMetrics}
            />
          }>
            <TypingInterface
              sessionKey={`${params.id}:original:${originalIndex()}:${attempt()}`}
              disabled={Boolean(completedMetrics())}
              targetText={originalSentences()[originalIndex()].text}
              hints={originalSentences()[originalIndex()].hints}
              fullTranslation={originalSentences()[originalIndex()].translation}
              onContinue={continuePractice}
              continueLabel={nextDisabled() ? "Enter to finish" : "Enter to continue"}
              onNavigate={navigateSentence}
              onComplete={handleSentenceComplete}
              onMetricsUpdate={setLiveMetrics}
            />
          </Show>

          {/* Top Frequency Words Section */}
          <Show when={storyData()}>
            <div class="mt-16 flex flex-col gap-4">
              <div class="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
                <span class="text-mono-sm font-mono-sm text-on-surface-variant uppercase tracking-wider">Top Frequency Words</span>
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-2">
                    <span class="text-mono-sm font-mono-sm text-on-surface-variant">Filter with:</span>
                    <div class="flex bg-surface-container border border-outline-variant p-0.5">
                      <button 
                        onClick={handleControlClick(() => setFilteringMethod("spacy"))}
                        class={`px-3 py-1 text-[11px] font-mono-label uppercase tracking-wider transition-colors ${filteringMethod() === "spacy" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
                      >
                        spaCy
                      </button>
                      <button 
                        onClick={handleControlClick(() => setFilteringMethod("llm"))}
                        class={`px-3 py-1 text-[11px] font-mono-label uppercase tracking-wider transition-colors ${filteringMethod() === "llm" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
                      >
                        AI
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={handleControlClick(handleRegenerateWords)}
                    disabled={isRegenerating()}
                    class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center disabled:opacity-50"
                    title="Regenerate Words & Practice Sentences"
                  >
                    <span class={`material-symbols-outlined text-[18px] ${isRegenerating() ? 'animate-spin' : ''}`}>autorenew</span>
                  </button>
                </div>
              </div>
              <Show when={storyData()?.top_words && storyData()!.top_words.length > 0} fallback={
                <div class="text-mono-sm font-mono-sm text-on-surface-variant italic mt-2">
                  No frequency list available. Select a filter and regenerate to extract the top words.
                </div>
              }>
                <div class="flex flex-wrap gap-3">
                  {storyData()!.top_words.map(item => (
                    <div class="relative group inline-block">
                      <span class="bg-surface-container border border-outline-variant px-3 py-1 text-mono-label font-mono-label text-on-surface cursor-help transition-colors group-hover:border-primary block">
                        {item.word}
                      </span>
                      
                      {/* Immediate Custom Tooltip */}
                      <div class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-[300px] p-3 bg-[#1e1e1e] text-white text-[12px] leading-relaxed rounded opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-xl whitespace-pre-wrap">
                        {item.translation || "Translation unavailable"}
                        
                        {/* Tooltip arrow */}
                        <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#1e1e1e]"></div>
                      </div>
                    </div>
                  ))}
                </div>
              </Show>
            </div>
          </Show>
        </Show>

        {/* Controls Footer */}
        <div class="mt-8 pt-8 border-t border-outline-variant grid grid-cols-2 gap-4 md:flex md:justify-between md:items-center">
          <button 
            title="Previous sentence ([)"
            disabled={previousDisabled()}
            onClick={handleControlClick(goToPreviousSentence)}
            class="flex items-center justify-center gap-2 px-3 md:px-8 py-3 bg-white border border-outline-variant text-on-surface hover:border-primary transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
          >
            <span class="material-symbols-outlined text-base">arrow_back</span>
            <span class="font-mono-label text-mono-label uppercase tracking-widest">Previous</span>
          </button>
          
          <div class="col-span-2 row-start-1 flex gap-4 items-center justify-center min-w-0">
            <span class="text-mono-sm font-mono-sm text-on-surface-variant">
              Sentence {currentIndex() + 1} of {totalSentences()}
            </span>
            <div class="w-24 sm:w-48 h-1 bg-surface-container overflow-hidden">
              <div class="h-full bg-primary transition-all duration-300" style={{ width: `${progressPercent()}%` }}></div>
            </div>
            <button
              onClick={handleControlClick(handleResetProgress)}
              class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center ml-2"
              title="Reset Progress"
            >
              <span class="material-symbols-outlined text-[20px]">restart_alt</span>
            </button>
          </div>

          <button 
            title="Next sentence (])"
            disabled={nextDisabled()}
            onClick={handleControlClick(goToNextSentence)}
            class="flex items-center justify-center gap-2 px-3 md:px-10 py-3 bg-primary text-on-primary hover:bg-on-primary-fixed-variant transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
          >
            <span class="font-mono-label text-mono-label uppercase tracking-widest">Next</span>
            <span class="material-symbols-outlined text-base">arrow_forward</span>
          </button>
        </div>
      </Show>

      {/* Post-Session Results Modal */}
      <Show when={completedMetrics()}>
        {(metrics) => (
          <div
            class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
            id="results-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="results-modal-title"
          >
            <div class="bg-surface border-2 border-primary max-w-md w-full p-8 shadow-2xl space-y-6">
              <div class="space-y-1">
                <span class="font-mono-label text-mono-label text-primary uppercase tracking-widest">
                  Drill Completed
                </span>
                <h2 id="results-modal-title" class="font-headline-md text-headline-md">Session Performance</h2>
              </div>

              <div class="grid grid-cols-2 gap-4 py-4 border-y border-outline-variant">
                <div class="space-y-1">
                  <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase">Net WPM</span>
                  <div class="font-headline-md text-3xl font-bold text-primary" id="results-net-wpm">{metrics().netWpm}</div>
                </div>
                <div class="space-y-1">
                  <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase">Accuracy</span>
                  <div class="font-headline-md text-3xl font-bold text-primary" id="results-accuracy">{metrics().accuracy}%</div>
                </div>
                <div class="space-y-1">
                  <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase">Active Time</span>
                  <div class="font-mono-label text-lg" id="results-active-time">{metrics().activeSeconds}s</div>
                </div>
                <div class="space-y-1">
                  <span class="font-mono-sm text-mono-sm text-on-surface-variant uppercase">Mistakes</span>
                  <div class="font-mono-label text-lg text-error" id="results-mistakes">{metrics().mistakeCount}</div>
                </div>
              </div>

              <div class="flex gap-4">
                <button
                  onClick={() => setCompletedMetrics(null)}
                  class="flex-1 py-3 border border-outline-variant hover:border-primary font-mono-label text-mono-label transition-colors uppercase tracking-wider"
                  id="btn-results-review"
                >
                  Review (Esc)
                </button>
                <button
                  onClick={continuePractice}
                  class="flex-1 py-3 bg-primary text-on-primary font-mono-label text-mono-label hover:bg-primary/90 transition-colors uppercase tracking-wider font-bold"
                  id="btn-results-next"
                >
                  {nextDisabled() ? "Finish" : "Next →"}
                </button>
              </div>
            </div>
          </div>
        )}
      </Show>
    </section>
  );
};

export default PracticePage;
