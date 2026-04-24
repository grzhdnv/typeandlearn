import {
  type Component,
  Show,
  createEffect,
  createMemo,
  createResource,
  createSignal,
} from "solid-js";
import { TypingInterface } from "./TypingInterface";
import { fetchStory, fetchTextTitles } from "./fetchText";
import { postText } from "./postText";

type Sentence = {
  text: string;
  hints: Record<string, string>;
  translation: string;
};

const TEXTAREA_MIN_HEIGHT_PX = 40;

const App: Component = () => {
  let textAreaRef: HTMLTextAreaElement | undefined;
  const [selectedTextId, setSelectedTextId] = createSignal("00");
  const [availableTexts] = createResource(fetchTextTitles);
  const [storyData] = createResource(selectedTextId, fetchStory);

  const originalSentences = createMemo<Sentence[]>(() => {
    const story = storyData();
    if (!story) return [];
    return story.original_paragraphs.flatMap((p) =>
      p.sentences.map((s) => ({
        text: s.text,
        hints: s.translation_hints as unknown as Record<string, string>,
        translation: s.translation,
      })),
    );
  });

  const generatedSentences = createMemo<Sentence[]>(() => {
    const story = storyData();
    if (!story) return [];
    return story.practice_sentences.map((p) => ({
      text: p.sentence,
      hints: p.translation_hints as unknown as Record<string, string>,
      translation: p.translation,
    }));
  });

  const [customText, setCustomText] = createSignal("");
  const [isSubmitting, setIsSubmitting] = createSignal(false);
  const [submitMessage, setSubmitMessage] = createSignal("");
  const [submitStatus, setSubmitStatus] = createSignal<"success" | "error" | "idle">(
    "idle",
  );

  const resizeTextarea = (textarea: HTMLTextAreaElement) => {
    const maxHeight = Math.floor(window.innerHeight * 0.5);
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  };

  const handleTextInput = (e: InputEvent) => {
    const textarea = e.currentTarget as HTMLTextAreaElement;

    // When text is inputted, adjust textarea size to match
    resizeTextarea(textarea);
    setCustomText(textarea.value);
    if (submitStatus() !== "idle") {
      setSubmitStatus("idle");
      setSubmitMessage("");
    }
  };

  const handleSubmitText = async () => {
    const text = customText().trim();
    if (!text || isSubmitting()) return;

    try {
      setIsSubmitting(true);
      await postText(text);
      setCustomText("");
      if (textAreaRef) {
        textAreaRef.style.height = `${TEXTAREA_MIN_HEIGHT_PX}px`;
        textAreaRef.style.overflowY = "hidden";
      }
      setSubmitStatus("success");
      setSubmitMessage("Text was added successfully.");
    } catch (error) {
      console.error("Failed to submit text:", error);
      setSubmitStatus("error");
      setSubmitMessage(
        error instanceof Error ? error.message : "Failed to submit text.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };


  const [activeTab, setActiveTab] = createSignal<"original" | "generated">(
    "original",
  );

  const [originalIndex, setOriginalIndex] = createSignal(0);
  const [generatedIndex, setGeneratedIndex] = createSignal(0);

  createEffect(() => {
    const story = storyData();
    if (!story) return;
    setOriginalIndex(0);
    setGeneratedIndex(0);
  });

  const handleOriginalComplete = () => {
    if (originalIndex() < originalSentences().length - 1) {
      setOriginalIndex((i) => i + 1);
    }
  };

  const handleGeneratedComplete = () => {
    if (generatedIndex() < generatedSentences().length - 1) {
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
    <div
      style={{
        width: "100%",
        "max-width": "980px",
        margin: "0 auto",
        padding: "0 20px 32px 20px",
        "box-sizing": "border-box",
      }}
    >
      <header
        style={{
          padding: "14px 0 12px 0",
          "margin-bottom": "12px",
          "border-bottom": "1px solid #e5e5e5",
          "text-align": "center",
        }}
      >
        <h1
          style={{
            margin: 0,
            "font-family": "monospace",
            "font-size": "22px",
            "font-weight": 700,
            "letter-spacing": "0.04em",
            "text-transform": "lowercase",
          }}
        >
          typeandlearn
        </h1>
      </header>
      <textarea
        ref={textAreaRef}
        placeholder="Enter text..."
        onInput={handleTextInput}
        value={customText()}
        style={{
          "font-size": "24px",
          padding: "8px",
          width: "100%",
          resize: "none",
          overflow: "hidden",
          "min-height": `${TEXTAREA_MIN_HEIGHT_PX}px`,
          "max-height": "50vh",
        }}
      />
      <div style={{ padding: "8px 0 0 0" }}>
        <button
          onClick={handleSubmitText}
          disabled={isSubmitting() || !customText().trim()}
          style={{
            "font-size": "16px",
            padding: "8px 16px",
            "font-family": "monospace",
            cursor: isSubmitting() ? "not-allowed" : "pointer",
          }}
        >
          {isSubmitting() ? "Submitting..." : "Submit Text"}
        </button>
      </div>
      <Show when={submitStatus() !== "idle"}>
        <p
          style={{
            margin: "8px 0 0 0",
            "font-family": "monospace",
            color: submitStatus() === "success" ? "#1f7a1f" : "#b00020",
          }}
        >
          {submitMessage()}
        </p>
      </Show>
      
      <div style={{ padding: "20px 20px 0 20px" }}>
        <label
          for="text-select"
          style={{
            display: "block",
            "font-family": "monospace",
            "font-size": "14px",
            "margin-bottom": "6px",
          }}
        >
          Choose a text
        </label>
        <select
          id="text-select"
          value={selectedTextId()}
          onChange={(e) => setSelectedTextId(e.currentTarget.value)}
          disabled={availableTexts.loading}
          style={{
            "font-family": "monospace",
            "font-size": "16px",
            padding: "6px 10px",
            "min-width": "280px",
            "max-width": "100%",
          }}
        >
          <Show
            when={(availableTexts() ?? []).length > 0}
            fallback={<option value="00">No texts found</option>}
          >
            {(availableTexts() ?? []).map((text) => (
              <option value={text.id}>{text.title}</option>
            ))}
          </Show>
        </select>
      </div>

      <h2
        style={{
          "font-family": "monospace",
          padding: "20px 20px 0 20px",
          margin: 0,
        }}
      >
        {storyData.loading ? "Loading text..." : storyData()?.title ?? ""}
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
        when={
          !storyData.loading &&
          !storyData.error &&
          ((activeTab() === "original" && originalSentences().length > 0) ||
            (activeTab() === "generated" && generatedSentences().length > 0))
        }
        fallback={
          <p
            style={{
              "font-family": "monospace",
              padding: "20px",
              color: "#666",
            }}
          >
            {storyData.error
              ? "Failed to load selected text."
              : storyData.loading
                ? "Loading..."
                : "No sentences available for this text."}
          </p>
        }
      >
        <Show
          when={activeTab() === "original"}
        fallback={
          <TypingInterface
            targetText={generatedSentences()[generatedIndex()].text}
            hints={generatedSentences()[generatedIndex()].hints}
            fullTranslation={generatedSentences()[generatedIndex()].translation}
            onComplete={handleGeneratedComplete}
          />
        }
      >
        <TypingInterface
          targetText={originalSentences()[originalIndex()].text}
          hints={originalSentences()[originalIndex()].hints}
          fullTranslation={originalSentences()[originalIndex()].translation}
          onComplete={handleOriginalComplete}
        />
      </Show>
      </Show>
    </div>
  );
};;;

export default App;
