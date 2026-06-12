import { Component, createResource, createEffect } from 'solid-js';
import { useNavigate } from '@solidjs/router';
import { fetchTextTitles } from '../../../features/texts/api/textsApi';

const PracticeRedirect: Component = () => {
  const [texts] = createResource(fetchTextTitles);
  const navigate = useNavigate();

  createEffect(() => {
    if (texts()) {
      if (texts()!.length > 0) {
        const ts = texts()!;
        const inProgress = ts.find(t => t.completed_sentences > 0 && t.completed_sentences < t.total_sentences);
        const id = inProgress ? inProgress.id : ts[0].id;
        navigate(`/practice/${id}`, { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    }
  });

  return (
    <main class="flex-grow pt-32 pb-16 px-margin-desktop max-w-max-width-content mx-auto w-full flex flex-col">
      <div class="flex items-center justify-center h-64 font-mono-label text-on-surface-variant">
        Loading practice...
      </div>
    </main>
  );
};

export default PracticeRedirect;
