import { type Component, createSignal, Show } from "solid-js";
import { TypingInterface } from "./TypingInterface";

const App: Component = () => {
  const [activeTab, setActiveTab] = createSignal<"original" | "generated">(
    "original",
  );

  const [customText, setCustomText] = createSignal("");

  const originalSentences = () =>
    customText()
      .split("\n")
      .filter((s) => s.trim() !== "");
  const generatedSentences = [
    "Placeholder generated sentence one.",
    "Placeholder generated sentence two.",
  ];

  const [originalIndex, setOriginalIndex] = createSignal(0);
  const [generatedIndex, setGeneratedIndex] = createSignal(0);

  const handleOriginalComplete = () => {
    if (originalIndex() < originalSentences().length - 1) {
      setOriginalIndex((i) => i + 1);
    }
  };

  const handleGeneratedComplete = () => {
    if (generatedIndex() < generatedSentences.length - 1) {
      setGeneratedIndex((i) => i + 1);
    }
  };

  const handleTextInput = (e: InputEvent) => {
    const textarea = e.currentTarget as HTMLTextAreaElement;

    // When text is inputted, adjust textarea size to match
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
    setCustomText(textarea.value);
  };

  // Style for tabs, specific to each of the two
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
          "min-height": "40px",
        }}
      />
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
            targetText={generatedSentences[generatedIndex()]}
            onComplete={handleGeneratedComplete}
          />
        }
      >
        <TypingInterface
          targetText={originalSentences()[originalIndex()] ?? ""}
          onComplete={handleOriginalComplete}
        />
      </Show>
    </div>
  );
};

export default App;
