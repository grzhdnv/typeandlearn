import { type Component, JSX } from "solid-js";
import { A } from "@solidjs/router";

type AppProps = {
  children?: JSX.Element;
};

const App: Component<AppProps> = (props) => {
  return (
    <div class="bg-surface text-on-surface min-h-screen font-body-md flex flex-col selection:bg-secondary-container selection:text-on-secondary-container">
      {/* TopNavBar */}
      <nav class="w-full h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-margin-mobile md:px-margin-desktop max-w-max-width-content mx-auto sticky top-0 z-50">
        <div class="flex items-center gap-8">
          <span class="font-headline-md text-headline-md font-bold text-primary tracking-tight">
            typeandlearn
          </span>
          <div class="hidden md:flex gap-6 items-center">
            <A
              class="font-body-md text-body-md"
              href="/"
              activeClass="border-primary text-primary font-bold border-b-2 pb-1"
              inactiveClass="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200"
              end
            >
              Library
            </A>
            <A
              class="font-body-md text-body-md"
              href="/practice"
              activeClass="border-primary text-primary font-bold border-b-2 pb-1"
              inactiveClass="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200"
            >
              Practice
            </A>
            <A
              class="font-body-md text-body-md"
              href="/analytics"
              activeClass="border-primary text-primary font-bold border-b-2 pb-1"
              inactiveClass="text-on-surface-variant font-medium hover:text-primary transition-colors duration-200"
            >
              Analytics
            </A>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button
            class="material-symbols-outlined text-outline-variant p-2 cursor-default"
            title="Local Single-User Mode (Auth planned for Milestone M4)"
            aria-label="Local Single-User Mode"
            disabled
          >
            person
          </button>
        </div>
      </nav>

      {/* Main Content Canvas */}
      {props.children}

      {/* Footer */}
      <footer class="w-full py-base bg-surface border-t border-outline-variant mt-auto">
        <div class="flex flex-col md:flex-row justify-between items-center px-margin-mobile md:px-margin-desktop max-w-max-width-content mx-auto w-full gap-4 md:gap-0">
          <span class="font-mono-label text-mono-label uppercase tracking-widest text-primary">
            typeandlearn
          </span>
          <div class="flex gap-6 font-mono-sm text-mono-sm text-on-surface-variant opacity-60">
            <span>Prototype v2 (Local Development)</span>
          </div>
          <span class="font-mono-sm text-mono-sm text-on-surface-variant opacity-60">
            © 2026 typeandlearn.
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
