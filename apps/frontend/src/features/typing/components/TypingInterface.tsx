import {
  type Component,
  For,
  Show,
  createEffect,
  createSignal,
  onCleanup,
  onMount,
} from "solid-js";

interface TypingInterfaceProps {
  targetText: string;
  hints?: { words: string[]; hint: string }[];
  fullTranslation?: string;
  onComplete?: () => void;
}

/**
 * Resolves the active word from a cursor offset in the target text.
 */
const getCurrentWord = (target: string, cursor: number): string => {
  if (target.length === 0) return "";
  const isSpace = (char: string) => /\s/.test(char);

  let lastWord = "";
  let i = 0;
  while (i < target.length) {
    while (i < target.length && isSpace(target[i])) {
      i++;
    }
    if (i >= target.length) break;

    const wordStart = i;
    while (i < target.length && !isSpace(target[i])) {
      i++;
    }
    const wordEnd = i;

    if (wordStart <= cursor) {
      lastWord = target.slice(wordStart, wordEnd);
    } else {
      break;
    }
  }

  return lastWord;
};

/**
 * Keyboard-driven typing surface with per-word hint and translation reveal controls.
 */
export const TypingInterface: Component<TypingInterfaceProps> = (props) => {
  const [typed, setTyped] = createSignal("");
  const [optionPressed, setOptionPressed] = createSignal(false);
  const [commandPressed, setCommandPressed] = createSignal(false);
  let inputRef: HTMLInputElement | undefined;

  createEffect(() => {
    // Reset when target text changes
    props.targetText;
    setTyped("");
  });

  const currentWord = () => getCurrentWord(props.targetText, typed().length);
  const currentHintGroup = () => {
    const word = currentWord();
    if (!word) return null;
    const clean = word.replace(/[.,;:!?"'`„“»«]/g, "");
    const hints = props.hints ?? [];
    return hints.find((h) => h.words.includes(clean) || h.words.includes(word)) ?? null;
  };

  const currentHint = () => {
    const group = currentHintGroup();
    return group ? group.hint : null;
  };

  const hintVisible = () => optionPressed();
  const fullTranslationVisible = () => optionPressed() && commandPressed();

  const isHighlighted = (index: number) => {
    if (!hintVisible()) return false;
    const group = currentHintGroup();
    if (!group) return false;

    const wordAtIndex = getCurrentWord(props.targetText, index);
    if (!wordAtIndex) return false;
    const cleanWordAtIndex = wordAtIndex.replace(/[.,;:!?"'`„“»«]/g, "");
    return group.words.includes(cleanWordAtIndex) || group.words.includes(wordAtIndex);
  };

  /**
   * Track modifier keys for hints
   */
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Alt") setOptionPressed(true);
    if (event.key === "Meta") setCommandPressed(true);

    // Intercept restart shortcuts (Ctrl+R, Cmd+R, Esc) so the browser page does not reload
    if (
      (event.key.toLowerCase() === "r" && (event.ctrlKey || event.metaKey)) ||
      event.key === "Escape"
    ) {
      event.preventDefault();
      setTyped("");
      if (inputRef) {
        inputRef.value = "";
        inputRef.focus();
      }
      return;
    }

    // Auto-focus the input if typing starts and focus is lost
    if (
      event.target instanceof HTMLElement && 
      event.target.tagName !== "INPUT" && 
      event.target.tagName !== "TEXTAREA"
    ) {
      // Don't steal focus if user is triggering a button with keyboard (Enter or Space)
      const isButton = event.target.tagName === "BUTTON" || event.target.tagName === "A";
      const isActionKey = event.key === "Enter" || event.key === " ";
      
      if (isButton && isActionKey) {
        return;
      }

      // If it's a standard typing key (single character or backspace)
      if (event.key.length === 1 || event.key === "Backspace") {
        inputRef?.focus();
      }
    }
  };

  const handleKeyUp = (event: KeyboardEvent) => {
    if (event.key === "Alt") setOptionPressed(false);
    if (event.key === "Meta") setCommandPressed(false);
  };

  const resetModifierState = () => {
    setOptionPressed(false);
    setCommandPressed(false);
  };

  onMount(() => {
    globalThis.addEventListener("keydown", handleKeyDown);
    globalThis.addEventListener("keyup", handleKeyUp);
    globalThis.addEventListener("blur", resetModifierState);
    if (inputRef) {
      inputRef.focus();
    }
  });

  onCleanup(() => {
    globalThis.removeEventListener("keydown", handleKeyDown);
    globalThis.removeEventListener("keyup", handleKeyUp);
    globalThis.removeEventListener("blur", resetModifierState);
  });

  const handleCanvasClick = () => {
    if (inputRef) inputRef.focus();
  };

  return (
    <>
      <div class="relative group" onClick={handleCanvasClick}>
        <div class="absolute -inset-4 border-2 border-primary opacity-0 group-focus-within:opacity-10 transition-opacity pointer-events-none"></div>
        {/* The Typing Canvas */}
        <div class="bg-surface-container-lowest border border-outline-variant p-10 min-h-[320px] shadow-sm relative focus-within:border-primary transition-colors cursor-text" id="typing-canvas">
          <div class="mb-4 pb-2 border-b border-outline-variant/30 text-on-surface-variant font-mono-sm text-mono-sm opacity-60 flex justify-between items-center">
            <span>Type the text as it appears.</span>
            <span class="uppercase tracking-tighter">CTRL+R or ESC to restart</span>
          </div>
          
          {/* Text Container */}
          <div class="font-mono-input text-[24px] leading-[1.8] tracking-normal select-none relative z-10 whitespace-pre-wrap">
            <For each={props.targetText.split("")}>
              {(char, index) => {
                const isMistake = () => index() < typed().length && typed()[index()] !== char;
                const isCurrent = () => index() === typed().length;
                const isTyped = () => index() < typed().length;
                
                return (
                  <>
                    <span
                      class={
                        "relative " + 
                        (isMistake() 
                          ? "text-error bg-error-container" 
                          : isTyped() 
                            ? "text-completed" 
                            : "text-light")
                      }
                      style={{
                        "background-color":
                          isHighlighted(index()) && char !== " " && !isMistake()
                            ? "rgba(59, 130, 246, 0.2)" // Tertiary-like highlight
                            : undefined,
                      }}
                    >
                      <Show when={isCurrent()}>
                        <span class="caret-blink"></span>
                      </Show>
                      {char}
                    </span>
                  </>
                );
              }}
            </For>
            <Show when={typed().length === props.targetText.length}>
               <span class="relative"><span class="caret-blink"></span>&nbsp;</span>
            </Show>
          </div>
          
          {/* Hidden Input to catch focus */}
          <input 
            ref={inputRef}
            value={typed()}
            onInput={(e) => {
              const val = e.currentTarget.value;
              if (val.length <= props.targetText.length) {
                setTyped(val);
                if (val.length === props.targetText.length) {
                  setTimeout(() => props.onComplete?.(), 1000);
                }
              } else {
                e.currentTarget.value = typed();
              }
            }}
            autocomplete="off" 
            autofocus 
            class="absolute inset-0 opacity-0 cursor-default" 
            spellcheck={false} 
            type="text" 
          />
        </div>
      </div>

      {/* Contextual Hints */}
      <div class="mt-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="text-on-surface-variant font-mono-sm text-mono-sm italic opacity-70">
          Hold <span class="not-italic font-bold px-1.5 py-0.5 bg-surface-container border border-outline-variant rounded">⌥ Option</span> for word hint, <span class="not-italic font-bold px-1.5 py-0.5 bg-surface-container border border-outline-variant rounded">⌥+⌘</span> for full translation
        </div>
        <div class="text-on-surface font-mono-label text-mono-label">
          <Show when={hintVisible()} fallback={<span class="opacity-0">Placeholder to maintain height</span>}>
            <Show when={fullTranslationVisible()} fallback={
              <span><strong>{currentWord()}</strong>{currentHint() ? ` → ${currentHint()}` : " (no hint)"}</span>
            }>
              <span><strong>Translation</strong>{props.fullTranslation ? ` → ${props.fullTranslation}` : " (not available)"}</span>
            </Show>
          </Show>
        </div>
      </div>
    </>
  );
};
