import { Component, createResource, createSignal, createMemo, Show, createEffect, onMount, onCleanup } from 'solid-js';
import { useParams } from '@solidjs/router';
import { fetchStory, updateProgress, resetProgress, regenerateTopWords } from '../../../features/texts/api/textsApi';
import { TypingInterface } from '../../../features/typing/components/TypingInterface';
import { HintGroup } from '../../../shared/types/contracts';

type UiSentence = {
  text: string;
  hints: HintGroup[];
  translation: string;
};

const PracticePage: Component = () => {
  const params = useParams();
  const [storyData, { refetch: refetchStory }] = createResource(() => params.id, fetchStory);
  const [isRegenerating, setIsRegenerating] = createSignal(false);
  const [filteringMethod, setFilteringMethod] = createSignal<"spacy" | "llm">("spacy");

  const [activeTab, setActiveTab] = createSignal<"original" | "generated">("original");
  const [originalIndex, setOriginalIndex] = createSignal(0);
  const [generatedIndex, setGeneratedIndex] = createSignal(0);

  createEffect(() => {
    if (storyData()) {
      setOriginalIndex(0);
      setGeneratedIndex(0);
    }
  });

  createEffect(() => {
    let intervalId: number | undefined;
    const story = storyData();
    if (story?.status === "processing") {
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
    if (activeTab() === "original" && originalIndex() > 0) {
      setOriginalIndex((i) => i - 1);
    } else if (activeTab() === "generated" && generatedIndex() > 0) {
      setGeneratedIndex((i) => i - 1);
    }
  };

  const goToNextSentence = () => {
    if (activeTab() === "original" && originalIndex() < originalSentences().length - 1) {
      setOriginalIndex((i) => i + 1);
    } else if (activeTab() === "generated" && generatedIndex() < generatedSentences().length - 1) {
      setGeneratedIndex((i) => i + 1);
    }
  };

  const handleOriginalComplete = () => {
    if (params.id) updateProgress(params.id, originalIndex()).catch(console.error);
    if (originalIndex() < originalSentences().length - 1) setOriginalIndex((i) => i + 1);
  };
  
  const handleGeneratedComplete = () => {
    if (params.id) updateProgress(params.id, generatedIndex()).catch(console.error);
    if (generatedIndex() < generatedSentences().length - 1) setGeneratedIndex((i) => i + 1);
  };

  const handleResetProgress = async () => {
    if (!params.id) return;
    if (!confirm("Are you sure you want to reset your progress for this text?")) return;
    try {
      await resetProgress(params.id);
      setOriginalIndex(0);
      setGeneratedIndex(0);
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

  // Prevent synthetic clicks on buttons from stealing focus during typing
  const handleMouseOnlyClick = (action: () => void) => (event: MouseEvent) => {
    if (event.detail === 0) {
      event.preventDefault();
      return;
    }
    action();
    (event.currentTarget as HTMLButtonElement).blur();
  };

  onMount(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is using modifier keys
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      
      if (e.key === "[") {
        e.preventDefault();
        if (!previousDisabled()) goToPreviousSentence();
      } else if (e.key === "]") {
        e.preventDefault();
        if (!nextDisabled()) goToNextSentence();
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
    <main class="flex-grow pt-32 pb-16 px-margin-desktop max-w-max-width-content mx-auto w-full flex flex-col">
      <Show when={!storyData.loading && !storyData.error} fallback={
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
              <span class="text-on-surface-variant text-mono-sm font-mono-sm opacity-60">ID: {params.id}</span>
            </div>
            <h1 class="font-headline-md text-headline-md leading-tight">{storyData()?.title || "Untitled"}</h1>
          </div>
          
          {/* Real-time Stats - Placeholder for now since API doesn't return these yet */}
          <div class="flex gap-12 border-l border-outline-variant pl-8 space-y-4">
            <div class="flex flex-col">
              <span class="text-mono-sm font-mono-sm text-on-surface-variant uppercase tracking-wider">Accuracy</span>
              <span class="font-mono-label text-headline-md">--%</span>
            </div>
            <div class="flex flex-col">
              <span class="text-mono-sm font-mono-sm text-on-surface-variant uppercase tracking-wider">WPM</span>
              <span class="font-mono-label text-headline-md">--</span>
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div class="mb-4 flex gap-2">
          <div class="flex bg-surface-container border border-outline-variant p-0.5">
            <button 
              onClick={handleMouseOnlyClick(() => setActiveTab("original"))}
              class={`px-6 py-1.5 text-mono-label font-mono-label shadow-sm transition-colors ${activeTab() === "original" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
            >
              Original
            </button>
            <button 
              onClick={handleMouseOnlyClick(() => setActiveTab("generated"))}
              class={`px-6 py-1.5 text-mono-label font-mono-label shadow-sm transition-colors ${activeTab() === "generated" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
            >
              Generated
            </button>
          </div>
        </div>

        <Show when={storyData()?.status === "processing"}>
           <div class="p-6 mb-6 bg-tertiary-fixed border border-on-tertiary-fixed text-on-tertiary-fixed font-mono-label flex items-center gap-3">
             <span class="material-symbols-outlined animate-spin text-[20px]">autorenew</span>
             Translating text with AI... Please wait, the page will update automatically.
           </div>
        </Show>

        <Show when={storyData()?.status !== "processing" && totalSentences() > 0} fallback={
          <div class="p-10 text-center font-mono-label text-outline">No sentences available for this text yet.</div>
        }>
          <Show when={activeTab() === "original"} fallback={
            <TypingInterface
              targetText={generatedSentences()[generatedIndex()].text}
              hints={generatedSentences()[generatedIndex()].hints}
              fullTranslation={generatedSentences()[generatedIndex()].translation}
              onComplete={handleGeneratedComplete}
            />
          }>
            <TypingInterface
              targetText={originalSentences()[originalIndex()].text}
              hints={originalSentences()[originalIndex()].hints}
              fullTranslation={originalSentences()[originalIndex()].translation}
              onComplete={handleOriginalComplete}
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
                        onClick={handleMouseOnlyClick(() => setFilteringMethod("spacy"))}
                        class={`px-3 py-1 text-[11px] font-mono-label uppercase tracking-wider transition-colors ${filteringMethod() === "spacy" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
                      >
                        spaCy
                      </button>
                      <button 
                        onClick={handleMouseOnlyClick(() => setFilteringMethod("llm"))}
                        class={`px-3 py-1 text-[11px] font-mono-label uppercase tracking-wider transition-colors ${filteringMethod() === "llm" ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-primary"}`}
                      >
                        AI
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={handleMouseOnlyClick(handleRegenerateWords)}
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
                <div class="flex flex-wrap gap-2">
                  {storyData()!.top_words.map(word => (
                    <span class="bg-surface-container border border-outline-variant px-3 py-1 text-mono-label font-mono-label text-on-surface">
                      {word}
                    </span>
                  ))}
                </div>
              </Show>
            </div>
          </Show>
        </Show>

        {/* Controls Footer */}
        <div class="mt-16 pt-8 border-t border-outline-variant flex justify-between items-center">
          <button 
            disabled={previousDisabled()}
            onClick={handleMouseOnlyClick(goToPreviousSentence)}
            class="flex items-center gap-2 px-8 py-3 bg-white border border-outline-variant text-on-surface hover:border-primary transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
          >
            <span class="material-symbols-outlined text-base">arrow_back</span>
            <span class="font-mono-label text-mono-label uppercase tracking-widest">Previous</span>
          </button>
          
          <div class="flex gap-4 items-center">
            <span class="text-mono-sm font-mono-sm text-on-surface-variant">
              Sentence {currentIndex() + 1} of {totalSentences()}
            </span>
            <div class="w-48 h-1 bg-surface-container overflow-hidden">
              <div class="h-full bg-primary transition-all duration-300" style={{ width: `${progressPercent()}%` }}></div>
            </div>
            <button
              onClick={handleMouseOnlyClick(handleResetProgress)}
              class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center ml-2"
              title="Reset Progress"
            >
              <span class="material-symbols-outlined text-[20px]">restart_alt</span>
            </button>
          </div>

          <button 
            disabled={nextDisabled()}
            onClick={handleMouseOnlyClick(goToNextSentence)}
            class="flex items-center gap-2 px-10 py-3 bg-primary text-on-primary hover:bg-on-primary-fixed-variant transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
          >
            <span class="font-mono-label text-mono-label uppercase tracking-widest">Next</span>
            <span class="material-symbols-outlined text-base">arrow_forward</span>
          </button>
        </div>
      </Show>
    </main>
  );
};

export default PracticePage;
