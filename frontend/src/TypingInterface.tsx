import { type Component, For, createSignal, onMount, onCleanup } from 'solid-js';

interface TypingInterfaceProps {
  targetText: string;
}

export const TypingInterface: Component<TypingInterfaceProps> = (props) => {
  const [typed, setTyped] = createSignal('');

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    // If backspace, remove last character from typed
    if (e.key === 'Backspace') {
      setTyped((prev) => prev.slice(0, -1));
    } else if (e.key.length === 1) {
      setTyped((prev) => {
        // Prevent typing beyond the length of the text
        if (prev.length < props.targetText.length) {
          return prev + e.key;
        }
        return prev;
      });
    }
  };

  // Event listener for keypresses - activate when component shown, deactivate when removed
  onMount(() => {
    globalThis.addEventListener('keydown', handleKeyDown);
  });
  onCleanup(() => {
    globalThis.removeEventListener('keydown', handleKeyDown);
  });

  // Draw the UI
  return (
    <div style={{ "font-size": "24px", padding: "20px", "font-family": "monospace", "max-width": "800px", "line-height": "1.5" }}>
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
