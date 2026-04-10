import { type Component, createSignal } from "solid-js";
import { fetchTexts } from "./fetchText";
import { TypingInterface } from "./TypingInterface";

const App: Component = () => {
  const texts = fetchTexts();
  const [sentenceIndex, setSentenceIndex] = createSignal(0);

  const handleSentenceComplete = () => {
    if (sentenceIndex() < texts.length - 1) {
      setSentenceIndex((i) => i + 1);
    }
  };

  const [customText, setCustomText] = createSignal('');

  const handleTextInput = (e: InputEvent) => {
    const textarea = e.currentTarget as HTMLTextAreaElement;

    // When text is inputted, adjust textarea size to match
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px'
    setCustomText(textarea.value)
  };

  return (
    <div>
      <textarea
        placeholder="Enter sentences..."
        onInput={handleTextInput}
        style={{
          "font-size": "24px",
          padding: "8px",
          width: "100%",
          resize: "none",
          overflow: "hidden",
          "min-height": "40px"
        }}
      />
      <TypingInterface
        targetText={texts[sentenceIndex()]}
        onComplete={handleSentenceComplete}
      />
    </div>
  );
};

export default App;
