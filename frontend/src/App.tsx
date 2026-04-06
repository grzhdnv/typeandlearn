import { type Component, createSignal } from 'solid-js';
import { fetchTexts } from './fetchText';
import { TypingInterface } from './TypingInterface';

const App: Component = () => {
  const texts = fetchTexts();
  const [sentenceIndex, setSentenceIndex] = createSignal(0);

  const handleSentenceComplete = () => {
    if (sentenceIndex() < texts.length - 1) {
      setSentenceIndex((i) => i + 1);
    }
  };

  return (
    <TypingInterface
      targetText={texts[sentenceIndex()]}
      onComplete={handleSentenceComplete}
    />
  );
};

export default App;