import { type Component, JSX, createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { AccountModal } from "../features/user/components/AccountModal";

type AppProps = {
  children?: JSX.Element;
};

const App: Component<AppProps> = (props) => {
  const [isAccountModalOpen, setIsAccountModalOpen] = createSignal(false);

  return (
    <div class="bg-surface text-on-surface min-h-screen font-body-md flex flex-col selection:bg-secondary-container selection:text-on-secondary-container">
      {/* Skip to main content link for keyboard accessibility */}
      <a
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          const target = document.getElementById("main-content");
          if (target) {
            target.focus();
            target.scrollIntoView();
          }
        }}
        class="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 bg-primary text-on-primary font-bold border-2 border-outline shadow-xl"
      >
        Skip to main content
      </a>

      {/* TopNavBar */}
      <nav
        class="w-full h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-margin-mobile md:px-margin-desktop max-w-max-width-content mx-auto sticky top-0 z-40"
        aria-label="Main Navigation"
      >
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
            class="material-symbols-outlined text-on-surface-variant hover:text-primary p-2 transition-colors cursor-pointer"
            title="Account & Privacy"
            aria-label="Account and Privacy Settings"
            id="btn-account-nav"
            onClick={() => setIsAccountModalOpen(true)}
          >
            person
          </button>
        </div>
      </nav>

      <AccountModal
        isOpen={isAccountModalOpen()}
        onClose={() => setIsAccountModalOpen(false)}
      />

      {/* Main Content Canvas */}
      <main id="main-content" class="flex-1 flex flex-col focus:outline-none" tabindex="-1">
        {props.children}
      </main>

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
