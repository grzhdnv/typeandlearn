import { createSignal, type Component } from 'solid-js';
import Comp from './Comp';

const App: Component = () => {

  // --- Types ---
  type Dictionary = { [key: string]: unknown };

  type TextsResponse = {
    message?: string;
    data?: Dictionary[]; // Example shape: [{}, {}]
  };

  // --- State ---
  // "Getters" and "setters" for the state
  const [texts, setTexts] = createSignal<Dictionary[]>([]);
  const [errorMessage, setErrorMessage] = createSignal('');

// Function to fetch texts, used on button click
  const fetchTexts = async () => {
    // Clear old error before starting a new request.
    setErrorMessage('');

    try {
      // Request data through Vite dev proxy (`/api` -> backend server).
      const response = await fetch('/api/texts');

      // If server returned a non-2xx status, treat it as an error.
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      // Read response content type header, empty string fallback to avoid null/undefined issues.
      const contentType = response.headers.get('content-type') ?? '';

      // Guard: this endpoint should return JSON, not HTML/text.
      if (!contentType.includes('application/json')) {
        throw new Error('Expected JSON response from API');
      }

      // Parse JSON into our `TextsResponse` shape.
      const data: TextsResponse = await response.json();

      // Save returned list to signal. If `data.data` is missing, use empty array to keep UI stable.
      setTexts(data.data ?? []);
    } catch (error) {
      // Any network/parsing/explicit thrown error ends up here.
      // If it is a real Error object, use its message. Otherwise show a fallback message.
      setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
    }
  };

  // JSX returned by this component.
  return (
    <>
      <h1>Hello world!!!!</h1>
      <Comp />
      
      {/* Button triggers API request when clicked */}
      <button type="button" onClick={fetchTexts}>
        Get texts
      </button>

      {/* Only render list if at least one item exists */}
      {texts().length > 0 && (
        <ul>
          {/* Render each object as a JSON string for quick inspection */}
          {texts().map((text) => (
            <li>{JSON.stringify(text)}</li>
          ))}
        </ul>
      )}

      {/* If an error exists, show it */}
      {errorMessage() && <p>{errorMessage()}</p>}
    </>
  );
};

// Export so other files (like `index.tsx`) can render this component.
export default App;
