import { Component, createResource, createSignal, createMemo, Show, For } from 'solid-js';
import { fetchTextTitles, postText, updateTextMetadata, deleteText, resetProgress } from '../../../features/texts/api/textsApi';

const LANGUAGES = ["German", "French", "Italian", "Spanish"];
const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Unrated"];

const LibraryPage: Component = () => {
  const [availableTexts, { refetch }] = createResource(fetchTextTitles);
  
  const [customText, setCustomText] = createSignal("");
  const [customTitle, setCustomTitle] = createSignal("");
  const [customAuthor, setCustomAuthor] = createSignal("");
  const [customCategory, setCustomCategory] = createSignal("");
  const [customLanguage, setCustomLanguage] = createSignal("German");
  const [customDifficulty, setCustomDifficulty] = createSignal("");
  const [isSubmitting, setIsSubmitting] = createSignal(false);
  const [isAdding, setIsAdding] = createSignal(false);

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
      await postText(text, customLanguage(), customTitle(), customDifficulty(), customAuthor(), customCategory());
      setCustomText("");
      setCustomTitle("");
      setCustomAuthor("");
      setCustomCategory("");
      setCustomDifficulty("");
      setIsAdding(false);
      refetch();
    } catch (error) {
      console.error("Failed to submit text:", error);
      alert(error instanceof Error ? error.message : "Failed to submit text.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateMetadata = async (id: string, updates: { language?: string; difficultyLevel?: string; author?: string; category?: string }) => {
    try {
      await updateTextMetadata(id, updates.language, updates.difficultyLevel, updates.author, updates.category);
      refetch();
    } catch (error) {
      console.error("Failed to update metadata:", error);
      alert(error instanceof Error ? error.message : "Failed to update metadata.");
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

  return (
    <main class="w-full max-w-max-width-content mx-auto px-margin-mobile md:px-0 py-margin-desktop space-y-12">
      {/* Recently Practiced Section */}
      <Show when={recentlyPracticed()}>
        {(recent) => (
          <section>
            <div class="flex justify-between items-end mb-6">
              <h2 class="font-headline-md text-headline-md text-primary">Recently Practiced</h2>
              <a class="font-mono-label text-mono-label text-on-secondary-container flex items-center gap-2 hover:underline" href="#">
                VIEW HISTORY <span class="material-symbols-outlined text-[16px]">arrow_forward</span>
              </a>
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
      <section class="space-y-6">
        <div class="flex justify-between gap-4">
          <div class="relative group flex-grow">
            <span class="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant">search</span>
            <input 
              class="w-full pl-12 pr-4 py-4 bg-surface border border-outline-variant font-mono-input text-[18px] focus:ring-0 focus:border-primary focus:border-2 outline-none transition-all placeholder:text-outline-variant" 
              placeholder="SEARCH LIBRARY..." 
              type="text"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
            />
          </div>
          <button 
            onClick={() => setIsAdding(!isAdding())}
            class="px-6 py-4 bg-primary text-on-primary font-mono-label hover:bg-on-surface-variant transition-colors whitespace-nowrap flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-[18px]">add</span> ADD TEXT
          </button>
        </div>

        <Show when={isAdding()}>
          <div class="bg-surface-container-low border border-outline-variant p-4 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <select
                class="w-full p-3 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none cursor-pointer"
                value={customLanguage()}
                onChange={(e) => setCustomLanguage(e.currentTarget.value)}
              >
                <option value="" disabled>Select Language</option>
                <option value="German">German</option>
                <option value="French">French</option>
                <option value="Italian">Italian</option>
                <option value="Spanish">Spanish</option>
              </select>
              <input
                class="w-full p-3 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                placeholder="Title (Optional)"
                value={customTitle()}
                onInput={(e) => setCustomTitle(e.currentTarget.value)}
              />
              <select
                class="w-full p-3 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none cursor-pointer"
                value={customDifficulty()}
                onChange={(e) => setCustomDifficulty(e.currentTarget.value)}
              >
                <option value="">Difficulty (Optional)</option>
                <option value="A1">A1 (Beginner)</option>
                <option value="A2">A2 (Elementary)</option>
                <option value="B1">B1 (Intermediate)</option>
                <option value="B2">B2 (Upper Intermediate)</option>
                <option value="C1">C1 (Advanced)</option>
                <option value="C2">C2 (Mastery)</option>
              </select>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input
                class="w-full p-3 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                placeholder="Author (Optional)"
                value={customAuthor()}
                onInput={(e) => setCustomAuthor(e.currentTarget.value)}
              />
              <input
                class="w-full p-3 bg-surface border border-outline-variant focus:border-primary focus:ring-0 font-mono-input outline-none"
                placeholder="Category (Optional)"
                value={customCategory()}
                onInput={(e) => setCustomCategory(e.currentTarget.value)}
              />
            </div>
            <textarea
              class="w-full p-4 border border-outline-variant focus:border-primary focus:ring-0 font-mono-input text-[18px] outline-none"
              rows={4}
              placeholder="Paste new text here..."
              value={customText()}
              onInput={(e) => setCustomText(e.currentTarget.value)}
            />
            <div class="flex justify-end gap-2">
              <button onClick={() => setIsAdding(false)} class="px-4 py-2 font-mono-label text-on-surface-variant hover:text-primary">CANCEL</button>
              <button 
                onClick={handleSubmitText}
                disabled={isSubmitting() || !customText().trim() || !customLanguage().trim()}
                class="px-6 py-2 bg-primary text-on-primary font-mono-label disabled:opacity-50"
              >
                {isSubmitting() ? "SUBMITTING..." : "SUBMIT"}
              </button>
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
        <Show when={!availableTexts.loading} fallback={<p class="font-mono-label text-on-surface-variant">Loading library...</p>}>
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
                        <Show when={text.status === "pending" || text.status === "processing"}>
                          <span class="font-mono-label text-mono-label text-on-surface-variant uppercase">
                            PROCESSING
                          </span>
                        </Show>
                        <Show when={text.completed_sentences > 0}>
                          <button 
                            class="text-outline-variant hover:text-primary transition-colors flex items-center justify-center" 
                            onClick={() => handleResetProgress(text.id)}
                            title="Reset Progress"
                          >
                            <span class="material-symbols-outlined text-[20px]">restart_alt</span>
                          </button>
                        </Show>
                        <button 
                          class="text-outline-variant hover:text-error transition-colors flex items-center justify-center" 
                          onClick={() => handleDeleteText(text.id)}
                          title="Delete Text"
                        >
                          <span class="material-symbols-outlined text-[20px]">delete</span>
                        </button>
                      </div>
                    </div>
                    <div>
                      <h4 class="font-headline-md text-headline-md text-primary mb-1">{text.title}</h4>
                      <div class="flex gap-4 font-mono-sm text-mono-sm text-on-surface-variant">
                        <Show when={text.author}>
                          <span>By {text.author}</span>
                        </Show>
                        <Show when={text.category}>
                          <span class="px-2 bg-surface-container-high">{text.category}</span>
                        </Show>
                      </div>
                      
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
                  <a href={`/practice/${text.id}`} class="mt-6 w-full py-2 bg-transparent border border-primary text-primary font-mono-label text-mono-label hover:bg-primary hover:text-on-primary transition-all text-center block">
                    PRACTICE
                  </a>
                </div>
              )}
            </For>
          </Show>
        </Show>
      </section>
    </main>
  );
};

export default LibraryPage;
