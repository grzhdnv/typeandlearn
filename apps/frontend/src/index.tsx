/* @refresh reload */
import { render } from 'solid-js/web';
import { Router, Route } from '@solidjs/router';
import 'solid-devtools';

import './index.css';
import App from './app/App';
import LibraryPage from './features/library/pages/LibraryPage';
import PracticePage from './features/practice/pages/PracticePage';
import PracticeRedirect from './features/practice/pages/PracticeRedirect';

const root = document.getElementById('root');

if (import.meta.env.DEV && !(root instanceof HTMLElement)) {
  throw new Error(
    'Root element not found. Did you forget to add it to your index.html? Or maybe the id attribute got misspelled?',
  );
}

render(() => (
  <Router root={App}>
    <Route path="/" component={LibraryPage} />
    <Route path="/practice" component={PracticeRedirect} />
    <Route path="/practice/:id" component={PracticePage} />
  </Router>
), root!);
