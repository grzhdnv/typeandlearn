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

//   // --- Types ---
//   type Dictionary = { [key: string]: unknown };

//   type TextsResponse = {
//     message?: string;
//     data?: Dictionary[]; // Example shape: [{}, {}]
//   };

//   // --- State ---
//   // "Getters" and "setters" for the state
//   const [texts, setTexts] = createSignal<Dictionary[]>([]);
//   const [errorMessage, setErrorMessage] = createSignal('');

// // Function to fetch texts, used on button click
//   const fetchTextsData = async () => {
//     // Clear old error before starting a new request.
//     setErrorMessage('');

//     try {
//       // Request data through Vite dev proxy (`/api` -> backend server).
//       const response = await fetch('/api/texts');

//       // If server returned a non-2xx status, treat it as an error.
//       if (!response.ok) {
//         throw new Error(`Request failed with status ${response.status}`);
//       }

//       // Read response content type header, empty string fallback to avoid null/undefined issues.
//       const contentType = response.headers.get('content-type') ?? '';

//       // Guard: this endpoint should return JSON, not HTML/text.
//       if (!contentType.includes('application/json')) {
//         throw new Error('Expected JSON response from API');
//       }

//       // Parse JSON into our `TextsResponse` shape.
//       const data: TextsResponse = await response.json();

//       // Save returned list to signal. If `data.data` is missing, use empty array to keep UI stable.
//       setTexts(data.data ?? []);
//     } catch (error) {
//       // Any network/parsing/explicit thrown error ends up here.
//       // If it is a real Error object, use its message. Otherwise show a fallback message.
//       setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
//     }
//   };



  return (
    
    <div>
            <textarea
        placeholder="Enter text..."
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
