import { Component, createResource, createSignal, createMemo, Show, For, createEffect, onCleanup } from 'solid-js';
import { fetchTextTitles, postText, updateTextMetadata, deleteText, resetProgress, retryEnrichment } from '../../../features/texts/api/textsApi';
import { StatusBadge } from '../../../features/texts/components/StatusBadge';

const LANGUAGES = ["German", "French", "Italian", "Spanish", "English"];
const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Unrated"];

const LibraryPage: Component = () => {
  const [availableTexts, { refetch }] = createResource(fetchTextTitles);
  const [retryingId, setRetryingId] = createSignal<string | null>(null);

  createEffect(() => {
    let intervalId: number | undefined;
    const texts = availableTexts();
    const hasActiveJob = texts?.some(
      (t) =>
        t.status === "processing" ||
        t.status === "pending" ||
        t.enrichment_stage === "queued" ||
        t.enrichment_stage === "translating" ||
        t.enrichment_stage === "generating_practice"
    );

    if (hasActiveJob) {
      intervalId = window.setInterval(() => {
        refetch();
      }, 2000);
    }

    onCleanup(() => {
      if (intervalId) window.clearInterval(intervalId);
    });
  });

  const [customText, setCustomText] = createSignal("");
  const [intakeLanguage, setIntakeLanguage] = createSignal("");
  const [submitError, setSubmitError] = createSignal("");
  const [isSavingMetadata, setIsSavingMetadata] = createSignal(false);
  const [isSubmitting, setIsSubmitting] = createSignal(false);
  const [isAdding, setIsAdding] = createSignal(false);
  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [editTitle, setEditTitle] = createSignal("");
  const [editAuthor, setEditAuthor] = createSignal("");
  const [editCategory, setEditCategory] = createSignal("");

  const [filterLanguage, setFilterLanguage] = createSignal("ALL LANGUAGES");
  const [filterLevel, setFilterLevel] = createSignal("ANY LEVEL");
  const [searchQuery, setSearchQuery] = createSignal("");

  const languageCounts = createMemo(() => {
    const texts = availableTexts() || [];
    const query = searchQuery().toLowerCase();
    const counts: Record<string, number> = {};
    for (const lang of LANGUAGES) counts[lang] = 0;
    for (const text of texts) {
      const matchSearch = !query || text.title.toLowerCase().includes(query);
      const matchLevel = filterLevel() === "ANY LEVEL" || text.difficulty_level === filterLevel();
      if (!matchSearch || !matchLevel) continue;

      if (counts[text.language] !== undefined) {
        counts[text.language]++;
      }
    }
    return counts;
  });

  const levelCounts = createMemo(() => {
    const texts = availableTexts() || [];
    const query = searchQuery().toLowerCase();
    const counts: Record<string, number> = {};
    for (const lvl of LEVELS) counts[lvl] = 0;
    for (const text of texts) {
      const matchSearch = !query || text.title.toLowerCase().includes(query);
      const matchLang = filterLanguage() === "ALL LANGUAGES" || text.language === filterLanguage();
      if (!matchSearch || !matchLang) continue;

      if (counts[text.difficulty_level] !== undefined) {
        counts[text.difficulty_level]++;
      }
    }
    return counts;
  });

  const filteredTexts = createMemo(() => {
    const texts = availableTexts() || [];
    const query = searchQuery().toLowerCase();
    return texts.filter(t => {
      const matchLang = filterLanguage() === "ALL LANGUAGES" || t.language === filterLanguage();
      const matchLevel = filterLevel() === "ANY LEVEL" || t.difficulty_level === filterLevel();
      const matchSearch = !query || t.title.toLowerCase().includes(query);
      return matchLang && matchLevel && matchSearch;
    });
  });

  const recentlyPracticed = createMemo(() => {
    const texts = availableTexts() || [];
    if (texts.length === 0) return null;

    // Find first text in progress
    const inProgress = texts.find(t => t.completed_sentences > 0 && t.completed_sentences < t.total_sentences);
    if (inProgress) return inProgress;

    // Otherwise return the first text
    return texts[0];
  });

  const handleSubmitText = async () => {
    const text = customText().trim();
    if (!text || isSubmitting()) return;

    try {
      setIsSubmitting(true);
      setSubmitError("");
      await postText(text, intakeLanguage());
      setCustomText("");
      setIsAdding(false);
      refetch();
    } catch (error) {
      console.error("Failed to submit text:", error);
      setSubmitError(error instanceof Error ? error.message : "Failed to submit text.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const applyMetadata = async (id: string, updates: { title?: string; language?: string; difficultyLevel?: string; author?: string; category?: string }) => {
    try {
      await updateTextMetadata(id, updates.language, updates.difficultyLevel, updates.author, updates.category, updates.title);
      return true;
    } catch (error) {
      console.error("Failed to update metadata:", error);
      alert(error instanceof Error ? error.message : "Failed to update metadata.");
      return false;
    }
  };

  const handleUpdateMetadata = async (id: string, updates: { language?: string; difficultyLevel?: string; author?: string; category?: string }) => {
    await applyMetadata(id, updates);
    refetch();
  };

  const startEditing = (text: { id: string; title: string; author?: string; category?: string }) => {
    setEditingId(text.id);
    setEditTitle(text.title);
    setEditAuthor(text.author ?? "");
    setEditCategory(text.category ?? "");
  };

  const stopEditing = async () => {
    const id = editingId();
    const title = editTitle().trim();
    if (!id || !title || isSavingMetadata()) return;
    setIsSavingMetadata(true);
    try {
      if (await applyMetadata(id, { title, author: editAuthor().trim(), category: editCategory().trim() })) {
        setEditingId(null);
        await refetch();
      }
    } finally {
      setIsSavingMetadata(false);
    }
  };

  const handleDeleteText = async (id: string) => {
    if (!confirm("Are you sure you want to delete this text?")) return;
    try {
      await deleteText(id);
      refetch();
    } catch (error) {
      console.error("Failed to delete text:", error);
      alert(error instanceof Error ? error.message : "Failed to delete text.");
    }
  };

  const handleResetProgress = async (id: string) => {
    if (!confirm("Are you sure you want to reset your progress for this text?")) return;
    try {
      await resetProgress(id);
      refetch();
    } catch (error) {
      console.error("Failed to reset progress:", error);
      alert(error instanceof Error ? error.message : "Failed to reset progress.");
    }
  };

  const handleRetry = async (textId: string) => {
    if (retryingId()) return;
    try {
      setRetryingId(textId);
      await retryEnrichment(textId);
      refetch();
    } catch (error) {
      console.error("Failed to retry enrichment:", error);
      alert(error instanceof Error ? error.message : "Failed to retry enrichment.");
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <section aria-label="Library Overview" class="w-full max-w-max-width-content mx-auto px-margin-mobile md:px-0 py-margin-desktop space-y-12">
      {/* Recently Practiced Section */}
      <Show when={recentlyPracticed()}>
        {(recent) => (
          <section>
            <div class="flex justify-between items-end mb-6">
              <h2 class="font-headline-md text-headline-md text-primary">Recently Practiced</h2>
              <span class="font-mono-sm text-mono-sm text-on-surface-variant opacity-60 uppercase">
                Progress
              </span>
            </div>
            <div class="bg-surface-container-lowest border border-outline-variant p-gutter flex flex-col md:flex-row gap-6 items-center">
              <div class="w-full md:w-32 h-32 bg-surface-container flex-shrink-0 flex items-center justify-center border border-outline-variant overflow-hidden">
                <span class="material-symbols-outlined text-outline-variant text-4xl">book</span>
              </div>
              <div class="flex-grow space-y-2 w-full">
                <div class="flex flex-wrap gap-2">
                  <span class="px-2 py-0.5 bg-surface-container border border-outline-variant font-mono-sm text-mono-sm uppercase">
                    {recent().language}
                  </span>
                  <Show when={recent().difficulty_level !== "Unrated"}>
                    <span class="px-2 py-0.5 bg-surface-container border border-outline-variant font-mono-sm text-mono-sm uppercase">
                      {recent().difficulty_level}
                    </span>
                  </Show>
                </div>
                <h3 class="font-headline-md text-headline-md text-primary line-clamp-1">{recent().title}</h3>
                <div class="w-full bg-surface-container h-1 mt-4">
                  <div class="bg-secondary h-1 transition-all" style={{ width: `${recent().total_sentences > 0 ? (recent().completed_sentences / recent().total_sentences) * 100 : 0}%` }}></div>
                </div>
                <div class="flex justify-between font-mono-sm text-mono-sm text-on-surface-variant pt-1">
                  <span>{recent().total_sentences > 0 ? Math.round((recent().completed_sentences / recent().total_sentences) * 100) : 0}% COMPLETED</span>
                  <span>{recent().estimated_time_minutes} MIN EST. TIME</span>
                </div>
              </div>
              <a href={`/practice/${recent().id}`} class="w-full md:w-auto px-8 py-3 bg-primary text-on-primary font-mono-label text-mono-label hover:border-2 hover:border-secondary transition-all text-center block">
                CONTINUE
              </a>
            </div>
          </section>
        )}
      </Show>

      {/* Search & Filters & Add */}
      <section class="space-y-6" aria-label="Library Controls">
        <div class="flex flex-col sm:flex-row justify-between gap-4">
          <div class="relative group flex-grow min-w-0">
            <span class="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant">search</span>
            <input
              class="w-full pl-12 pr-4 py-4 bg-surface border border-outline-variant font-mono-input text-[18px] focus:ring-0 focus:border-primary focus:border-2 outline-none transition-all placeholder:text-outline-variant"
              placeholder="SEARCH LIBRARY..."
              type="text"
              aria-label="Search library texts"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
            />
          </div>
          <button
            id="btn-add-text"
            onClick={() => setIsAdding(!isAdding())}
            aria-expanded={isAdding() ? "true" : "false"}
            aria-label="Add Text"
            class="px-6 py-4 bg-primary text-on-primary font-mono-label hover:bg-on-surface-variant transition-colors whitespace-nowrap flex items-center gap-2 cursor-pointer"
          >
            <span aria-hidden="true" class="material-symbols-outlined text-[18px]">add</span> ADD TEXT
          </button>
        </div>

        <Show when={isAdding()}>
          <div class="bg-surface-container-low border border-outline-variant p-4 space-y-4">
            <label class="block font-mono-label">
              Text language
              <select aria-label="Text language" value={intakeLanguage()} onChange={e => setIntakeLanguage(e.currentTarget.value)} class="ml-3 p-2 border border-outline-variant bg-surface">
                <option value="">Detect automatically with AI</option>
                <For each={LANGUAGES}>{language => <option value={language}>{language}</option>}</For>
              </select>
            </label>
            <textarea
              aria-label="Source text"
              class="w-full p-4 border border-outline-variant focus:border-primary focus:ring-0 font-mono-input text-[18px] outline-none"
              rows={6}
              placeholder="Paste new text here..."
              value={customText()}
              onInput={(e) => setCustomText(e.currentTarget.value)}
            />
            <Show when={submitError()}><p role="alert" class="text-error">{submitError()}</p></Show>
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span class="font-mono-sm text-mono-sm text-on-surface-variant opacity-70">
                Metadata is detected automatically when AI is available. Select a language to add text without AI; you can edit metadata afterward.
              </span>
              <div class="flex justify-end gap-2">
                <button onClick={() => setIsAdding(false)} class="px-4 py-2 font-mono-label text-on-surface-variant hover:text-primary">CANCEL</button>
                <button
                  onClick={handleSubmitText}
                  disabled={isSubmitting() || !customText().trim()}
                  class="px-6 py-2 bg-primary text-on-primary font-mono-label disabled:opacity-50"
                >
                  {isSubmitting() ? "ANALYZING..." : "SUBMIT"}
                </button>
              </div>
            </div>
          </div>
        </Show>

        <div class="flex flex-wrap gap-4 items-center border-b border-outline-variant pb-6">
          <div class="flex items-center gap-2">
            <span class="font-mono-label text-mono-label text-on-surface-variant">LANGUAGE:</span>
            <select
              class="bg-transparent border-none font-mono-label text-mono-label text-primary focus:ring-0 cursor-pointer"
              value={filterLanguage()}
              onChange={(e) => setFilterLanguage(e.currentTarget.value)}
            >
              <option value="ALL LANGUAGES">ALL LANGUAGES</option>
              <For each={LANGUAGES}>
                {(lang) => (
                  <option value={lang} disabled={languageCounts()[lang] === 0}>
                    {lang.toUpperCase()} ({languageCounts()[lang]})
                  </option>
                )}
              </For>
            </select>
          </div>
          <div class="h-4 w-px bg-outline-variant mx-2"></div>
          <div class="flex items-center gap-2">
            <span class="font-mono-label text-mono-label text-on-surface-variant">LEVEL:</span>
            <select
              class="bg-transparent border-none font-mono-label text-mono-label text-primary focus:ring-0 cursor-pointer"
              value={filterLevel()}
              onChange={(e) => setFilterLevel(e.currentTarget.value)}
            >
              <option value="ANY LEVEL">ANY LEVEL</option>
              <For each={LEVELS}>
                {(lvl) => (
                  <option value={lvl} disabled={levelCounts()[lvl] === 0}>
                    {lvl.toUpperCase()} ({levelCounts()[lvl]})
                  </option>
                )}
              </For>
            </select>
          </div>
        </div>
      </section>

      {/* Text Cards Grid */}
      <section class="grid grid-cols-1 md:grid-cols-2 gap-gutter">
        <Show when={Boolean(availableTexts())} fallback={<p class="font-mono-label text-on-surface-variant">Loading library...</p>}>
          <Show when={filteredTexts().length} fallback={
            <div class="col-span-1 md:col-span-2 p-12 text-center border border-outline-variant bg-surface-container-lowest">
              <span class="material-symbols-outlined text-4xl text-outline-variant mb-4">library_books</span>
              <h3 class="font-headline-md text-primary mb-2">No matching texts</h3>
              <p class="font-body-md text-on-surface-variant">Try adjusting your filters or add a new text.</p>
            </div>
          }>
            <For each={filteredTexts()}>
              {(text) => (
                <div class="bg-surface border border-outline-variant p-6 flex flex-col justify-between text-card-hover transition-colors min-h-[240px]">
                  <div class="space-y-4">
                    <div class="flex justify-between items-start">
                      <div class="flex gap-2">
                        <select
                          class="appearance-none bg-none px-2 py-0.5 bg-surface-container-high border border-outline-variant font-mono-sm text-mono-sm uppercase cursor-pointer outline-none focus:border-primary hover:bg-surface-container text-center"
                          value={text.language}
                          onChange={(e) => handleUpdateMetadata(text.id, { language: e.currentTarget.value })}
                        >
                          <For each={LANGUAGES}>{(l) => <option value={l}>{l.toUpperCase()}</option>}</For>
                        </select>
                        <select
                          class="appearance-none bg-none px-2 py-0.5 bg-surface-container-high border border-outline-variant font-mono-sm text-mono-sm uppercase cursor-pointer outline-none focus:border-primary hover:bg-surface-container text-center"
                          value={text.difficulty_level}
                          onChange={(e) => handleUpdateMetadata(text.id, { difficultyLevel: e.currentTarget.value })}
                        >
                          <For each={LEVELS}>{(l) => <option value={l}>{l.toUpperCase()}</option>}</For>
                        </select>
                      </div>
                      <div class="flex gap-2 items-center">
                        <StatusBadge
                          status={text.status}
                          stage={text.enrichment_stage}
                          completedCount={text.completed_sentences}
                          totalCount={text.total_sentences}
                          errorMessage={text.error_message}
                          onRetry={() => handleRetry(text.id)}
                          isRetrying={retryingId() === text.id}
                        />
                        <Show when={text.completed_sentences > 0}>
                          <button
                            class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center"
                            onClick={() => handleResetProgress(text.id)}
                            title="Reset Progress"
                            aria-label={`Reset progress for ${text.title}`}
                          >
                            <span class="material-symbols-outlined text-[20px]">restart_alt</span>
                          </button>
                        </Show>
                        <button
                          class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center"
                          disabled={isSavingMetadata() || (editingId() === text.id && !editTitle().trim())}
                          onClick={() => editingId() === text.id ? stopEditing() : startEditing(text)}
                          title={editingId() === text.id ? "Done editing" : "Edit metadata"}
                          aria-label={`${editingId() === text.id ? "Done editing" : "Edit metadata for"} ${text.title}`}
                        >
                          <span class="material-symbols-outlined text-[20px]">{editingId() === text.id ? "check" : "edit"}</span>
                        </button>
                        <button
                          class="text-outline-variant hover:text-error transition-colors flex items-center justify-center"
                          onClick={() => handleDeleteText(text.id)}
                          title="Delete Text"
                          aria-label={`Delete text: ${text.title}`}
                        >
                          <span class="material-symbols-outlined text-[20px]">delete</span>
                        </button>
                      </div>
                    </div>
                    <div>
                      <Show when={editingId() === text.id} fallback={
                        <>
                          <h4 class="font-headline-md text-headline-md text-primary mb-1">{text.title}</h4>
                          <div class="flex gap-4 font-mono-sm text-mono-sm text-on-surface-variant">
                            <Show when={text.author}>
                              <span>By {text.author}</span>
                            </Show>
                            <Show when={text.category}>
                              <span class="px-2 bg-surface-container-high">{text.category}</span>
                            </Show>
                          </div>
                        </>
                      }>
                        <div class="space-y-2">
                          <input
                            class="w-full p-2 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                            aria-label={`Title for ${text.title}`}
                            placeholder="Title"
                            value={editTitle()}
                            onInput={(e) => setEditTitle(e.currentTarget.value)}
                          />
                          <input
                            class="w-full p-2 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                            aria-label={`Author for ${text.title}`}
                            placeholder="Author"
                            value={editAuthor()}
                            onInput={(e) => setEditAuthor(e.currentTarget.value)}
                          />
                          <input
                            class="w-full p-2 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                            aria-label={`Category for ${text.title}`}
                            placeholder="Category"
                            value={editCategory()}
                            onInput={(e) => setEditCategory(e.currentTarget.value)}
                          />
                        </div>
                      </Show>

                      <div class="w-full bg-surface-container h-1 mt-4">
                        <div
                          class="bg-secondary h-1"
                          style={{ width: `${text.total_sentences > 0 ? (text.completed_sentences / text.total_sentences) * 100 : 0}%` }}
                        ></div>
                      </div>
                      <div class="flex justify-between font-mono-sm text-mono-sm text-on-surface-variant pt-1">
                        <span>{text.total_sentences > 0 ? Math.round((text.completed_sentences / text.total_sentences) * 100) : 0}% COMPLETED</span>
                      </div>

                    </div>
                    <div class="flex items-center gap-4 font-mono-sm text-mono-sm text-outline">
                      <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">timer</span> {text.estimated_time_minutes} MIN</span>
                      <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">description</span> {text.word_count} WORDS</span>
                    </div>
                  </div>
                  <a
                    href={`/practice/${text.id}`}
                    aria-label={`Practice text: ${text.title}`}
                    class="mt-6 w-full py-2 bg-transparent border border-primary text-primary font-mono-label text-mono-label hover:bg-primary hover:text-on-primary transition-all text-center block"
                  >
                    PRACTICE
                  </a>
                </div>
              )}
            </For>
          </Show>
        </Show>
      </section>
    </section>
  );
};

export default LibraryPage;
