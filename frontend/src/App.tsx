import { type Component, createSignal, Show } from "solid-js";
import { TypingInterface } from "./TypingInterface";
import { fetchStory } from "./fetchText";
const storyData = await fetchStory();

type Sentence = { text: string; hints: Record<string, string> };

const originalSentences: Sentence[] = storyData.original_paragraphs.flatMap(
  (p) =>
    p.sentences.map((s) => ({
      text: s.text,
      hints: s.translation_hints as unknown as Record<string, string>,
    })),
);

const generatedSentences: Sentence[] = storyData.practice_sentences.map((p) => ({
  text: p.sentence,
  hints: p.translation_hints as unknown as Record<string, string>,
}));

const App: Component = () => {
    const [customText, setCustomText] = createSignal("");

    const handleTextInput = (e: InputEvent) => {
      const textarea = e.currentTarget as HTMLTextAreaElement;

      // When text is inputted, adjust textarea size to match
      textarea.style.height = "auto";
      textarea.style.height = textarea.scrollHeight + "px";
      setCustomText(textarea.value);
    };


  const [activeTab, setActiveTab] = createSignal<"original" | "generated">(
    "original",
  );

  const [originalIndex, setOriginalIndex] = createSignal(0);
  const [generatedIndex, setGeneratedIndex] = createSignal(0);

  const handleOriginalComplete = () => {
    if (originalIndex() < originalSentences.length - 1) {
      setOriginalIndex((i) => i + 1);
    }
  };

  const handleGeneratedComplete = () => {
    if (generatedIndex() < generatedSentences.length - 1) {
      setGeneratedIndex((i) => i + 1);
    }
  };

  const tabButtonStyle = (tab: "original" | "generated") => ({
    "font-size": "18px",
    padding: "8px 16px",
    "font-family": "monospace",
    cursor: "pointer",
    border: "1px solid #ccc",
    "background-color": activeTab() === tab ? "#ddd" : "transparent",
    "font-weight": activeTab() === tab ? "bold" : "normal",
  });

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
      <h2
        style={{
          "font-family": "monospace",
          padding: "20px 20px 0 20px",
          margin: 0,
        }}
      >
        {storyData.title}
      </h2>
      <div style={{ display: "flex", gap: "8px", padding: "20px 20px 0 20px" }}>
        <button
          style={tabButtonStyle("original")}
          onClick={() => setActiveTab("original")}
        >
          Original
        </button>
        <button
          style={tabButtonStyle("generated")}
          onClick={() => setActiveTab("generated")}
        >
          Generated
        </button>
      </div>
      <Show
        when={activeTab() === "original"}
        fallback={
          <TypingInterface
            targetText={generatedSentences[generatedIndex()].text}
            hints={generatedSentences[generatedIndex()].hints}
            onComplete={handleGeneratedComplete}
          />
        }
      >
        <TypingInterface
          targetText={originalSentences[originalIndex()].text}
          hints={originalSentences[originalIndex()].hints}
          onComplete={handleOriginalComplete}
        />
      </Show>
    </div>
  );
};;;

export default App;
