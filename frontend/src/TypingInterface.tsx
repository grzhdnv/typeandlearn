import {
  type Component,
  For,
  Show,
  createSignal,
  createEffect,
  onMount,
  onCleanup,
} from 'solid-js';

interface TypingInterfaceProps {
  targetText: string;
  hints?: Record<string, string>;
  fullTranslation?: string;
  onComplete?: () => void;
}

// Find the word the cursor is currently on 
// If the cursor is on whitespace aor past the end, look ahead to the next word
const getCurrentWord = (target: string, cursor: number): string => {
  if (target.length === 0) return '';
  const isSpace = (c: string | undefined) => !!c && /\s/.test(c);
  const pos = Math.min(cursor, target.length);

  if (pos >= target.length || isSpace(target[pos])) {
    let start = pos;
    while (start < target.length && isSpace(target[start])) start++;
    if (start >= target.length) {
      let end = target.length;
      while (end > 0 && isSpace(target[end - 1])) end--;
      let wordStart = end;
      while (wordStart > 0 && !isSpace(target[wordStart - 1])) wordStart--;
      return target.slice(wordStart, end);
    }
    let end = start;
    while (end < target.length && !isSpace(target[end])) end++;
    return target.slice(start, end);
  }

  let start = pos;
  while (start > 0 && !isSpace(target[start - 1])) start--;
  let end = pos;
  while (end < target.length && !isSpace(target[end])) end++;
  return target.slice(start, end);
};

export const TypingInterface: Component<TypingInterfaceProps> = (props) => {
  const [typed, setTyped] = createSignal('');
  const [optionPressed, setOptionPressed] = createSignal(false);
  const [commandPressed, setCommandPressed] = createSignal(false);

  // Reset typed text whenever the target sentence changes
  createEffect(() => {
    props.targetText;
    setTyped('');
  });

  const currentWord = () => getCurrentWord(props.targetText, typed().length);

  const currentHint = () => {
    const word = currentWord();
    if (!word) return null;
    const clean = word.replace(/[.,;:!?"'`„“»«]/g, '');
    const hints = props.hints ?? {};
    return hints[clean] ?? hints[word] ?? null;
  };

  const hintVisible = () => optionPressed();
  const fullTranslationVisible = () => optionPressed() && commandPressed();

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Alt') {
      setOptionPressed(true);
      return;
    }

    if (e.key === 'Meta') {
      setCommandPressed(true);
      return;
    }

    if (document.activeElement?.tagName === 'TEXTAREA') return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    // If backspace, remove last character from typed
    if (e.key === 'Backspace') {
      setTyped((prev) => prev.slice(0, -1));
    } else if (e.key.length === 1) {
      setTyped((prev) => {
        // Prevent typing beyond the length of the text
        if (prev.length < props.targetText.length) {
          const next = prev + e.key;

          // Advance as soon as user has typed the full sentence length.
          if (next.length === props.targetText.length) {
            // Use setTimeout so the final character renders before moving on
            setTimeout(() => props.onComplete?.(), 1000);
          }

          return next;
        }
        return prev;
      });
    }
  };

  const handleKeyUp = (e: KeyboardEvent) => {
    if (e.key === 'Alt') {
      setOptionPressed(false);
    }

    if (e.key === 'Meta') {
      setCommandPressed(false);
    }
  };

  const resetModifierState = () => {
    setOptionPressed(false);
    setCommandPressed(false);
  };

  // Event listener for keypresses
  onMount(() => {
    globalThis.addEventListener('keydown', handleKeyDown);
    globalThis.addEventListener('keyup', handleKeyUp);
    globalThis.addEventListener('blur', resetModifierState);
  });
  onCleanup(() => {
    globalThis.removeEventListener('keydown', handleKeyDown);
    globalThis.removeEventListener('keyup', handleKeyUp);
    globalThis.removeEventListener('blur', resetModifierState);
  });

  // Draw the UI
  return (
    <div
      style={{
        "font-size": "24px",
        padding: "20px 0",
        "font-family": "monospace",
        width: "100%",
        "box-sizing": "border-box",
        "line-height": "1.5",
      }}
    >
      <div
        style={{
          "min-height": "28px",
          "margin-bottom": "12px",
          "font-size": "16px",
          color: "#555",
        }}
      >
        <Show
          when={hintVisible()}
          fallback={
            <span style={{ color: "#999", "font-style": "italic" }}>
              Hold ⌥ Option for word hint, ⌥+⌘ for full translation
            </span>
          }
        >
          <Show
            when={fullTranslationVisible()}
            fallback={
              <span>
                <strong>{currentWord()}</strong>
                {currentHint() ? ` → ${currentHint()}` : " (no hint)"}
              </span>
            }
          >
            <span>
              <strong>Translation</strong>
              {props.fullTranslation ? ` → ${props.fullTranslation}` : " (not available)"}
            </span>
          </Show>
        </Show>
      </div>
      {/* Use a for loop to put each char into its own little span */}
      <For each={props.targetText.split('')}>
        {(char, index) => {
          return (
            <span style={{
              opacity: index() < typed().length ? 1 : 0.3,
              color: index() < typed().length && typed()[index()] !== char ? 'red' : 'inherit',
              "background-color": index() < typed().length && typed()[index()] !== char && char === ' ' ? 'rgba(255, 0, 0, 0.2)' : 'transparent'
            }}>
              {char}
            </span>
          );
        }}
      </For>
    </div>
  );
};
