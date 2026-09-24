// Entry point. Self-hosted JetBrains Mono (font-display: swap, so text paints
// immediately in the fallback monospace and swaps when the font arrives).
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import '@fontsource/jetbrains-mono/700.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './components/shell/App.jsx';
import { ErrorBoundary } from './components/shell/ErrorBoundary.jsx';
import { loadJobs } from './data/jobs-source.js';
import { loadContributors } from './data/contributors-source.js';

// Both loads start immediately. The app mounts as soon as jobs are in;
// contributors (contributors.json + GitHub API) keep loading in the background
// and that view shows its own loading state until the promise settles.
const contributorsPromise = loadContributors();

loadJobs().then((jobsState) => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <ErrorBoundary>
        <App jobsState={jobsState} contributorsPromise={contributorsPromise} />
      </ErrorBoundary>
    </StrictMode>,
  );
});
