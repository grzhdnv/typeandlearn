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
  hints?: Record<string, string>;
  fullTranslation?: string;
  onComplete?: () => void;
}

/**
 * Resolves the active word from a cursor offset in the target text.
 *
 * If the cursor is on whitespace or at the end, it falls back to the next/last word.
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

  createEffect(() => {
    props.targetText;
    setTyped("");
  });

  const currentWord = () => getCurrentWord(props.targetText, typed().length);
  const currentHint = () => {
    const word = currentWord();
    if (!word) return null;
    const clean = word.replace(/[.,;:!?"'`„“»«]/g, "");
    const hints = props.hints ?? {};
    return hints[clean] ?? hints[word] ?? null;
  };

  const hintVisible = () => optionPressed();
  const fullTranslationVisible = () => optionPressed() && commandPressed();

  /**
   * Updates typing state and modifier-key visibility state on keydown.
   */
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Alt") {
      setOptionPressed(true);
      return;
    }
    if (event.key === "Meta") {
      setCommandPressed(true);
      return;
    }

    if (document.activeElement?.tagName === "TEXTAREA") return;
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    if (event.key === "Backspace") {
      setTyped((prev) => prev.slice(0, -1));
      return;
    }

    if (event.key.length === 1) {
      setTyped((prev) => {
        if (prev.length < props.targetText.length) {
          const next = prev + event.key;
          if (next.length === props.targetText.length) {
            setTimeout(() => props.onComplete?.(), 1000);
          }
          return next;
        }
        return prev;
      });
    }
  };

  /**
   * Clears modifier-key visibility state when modifier keys are released.
   */
  const handleKeyUp = (event: KeyboardEvent) => {
    if (event.key === "Alt") setOptionPressed(false);
    if (event.key === "Meta") setCommandPressed(false);
  };

  /**
   * Ensures hint overlays are cleared when the window loses focus.
   */
  const resetModifierState = () => {
    setOptionPressed(false);
    setCommandPressed(false);
  };

  onMount(() => {
    globalThis.addEventListener("keydown", handleKeyDown);
    globalThis.addEventListener("keyup", handleKeyUp);
    globalThis.addEventListener("blur", resetModifierState);
  });

  onCleanup(() => {
    globalThis.removeEventListener("keydown", handleKeyDown);
    globalThis.removeEventListener("keyup", handleKeyUp);
    globalThis.removeEventListener("blur", resetModifierState);
  });

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
      <For each={props.targetText.split("")}>
        {(char, index) => (
          <span
            style={{
              opacity: index() < typed().length ? 1 : 0.3,
              color:
                index() < typed().length && typed()[index()] !== char
                  ? "red"
                  : "inherit",
              "background-color":
                index() < typed().length &&
                typed()[index()] !== char &&
                char === " "
                  ? "rgba(255, 0, 0, 0.2)"
                  : "transparent",
            }}
          >
            {char}
          </span>
        )}
      </For>
    </div>
  );
};
