import { createSignal, type Component } from 'solid-js';
import Comp from './Comp';

// below is a working connection to the backend, feel free to rework
const App: Component = () => {
  const [translationMessage, setTranslationMessage] = createSignal('');
  const [errorMessage, setErrorMessage] = createSignal('');

  const fetchTranslation = async () => {
    setErrorMessage('');

    try {
      const response = await fetch('/api/translation');

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data: { message?: string } = await response.json();
      setTranslationMessage(data.message ?? 'No message returned');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Unknown error');
    }
  };

  return (
    <>
      <h1>Hello world!!!!</h1>
      <Comp />
      
      {/* this is a button to fetch the translation message */}
      <button type="button" onClick={fetchTranslation}>
        Get translation message
      </button>
      {translationMessage() && <p>{translationMessage()}</p>}
      {errorMessage() && <p>{errorMessage()}</p>}
    </>
  );
};

export default App;
