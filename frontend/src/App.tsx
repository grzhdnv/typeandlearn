import { type Component } from 'solid-js';
import { fetchTexts } from './fetchText';
import { TypingInterface } from './TypingInterface';

const App: Component = () => {
  const texts = fetchTexts();

  // Starting with just the first sentence
  const targetText = texts[0]

  return (
    <TypingInterface targetText={targetText} />
  );
};

export default App;