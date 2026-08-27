# TODO

## Backend
- **Create endpoints:**
    - **Save text (POST request)**
        - Receive and put in database
            - Clean, generate practice sentences and translation hints
        - Pasted text for now
        - Later PDF and other text files
    - **Request text (GET request)**
    - **Authentication (put off for later)**
        - Users with their own texts, progress tracking, and API keys for LLM

## Frontend
- **Text UI**
    - UI for text upload (POST request)
    - Request original or practice sentences (GET request)
    - Updating and deleting (put off for later)
    - Show sentences to type
- **Typing**
    - Track input string, current sentence, current cursor/word
    - Comparing typed character against expected
    - Key modifiers for special characters (language specific)
    - A special key to prompt translation hints
- **Translation hints:**
    - Listen for the specific hotkey (`keydown` event). When pressed, calculate which word the user is currently typing based on their cursor position, look up that word in the local `translations` dictionary, and immediately pop up a tooltip. *Zero network latency.*
- **User based:**
    - Login
    - Dashboard
    - Progress tracking

## Monkeytype Benchmarking & Typing Core
- **Engine Analysis**: Analyze Monkeytype codebase for caret rendering, input event handling, backspace edge cases, and standard WPM calculations.
- **UX & Analytics**: Shortcuts (`Tab+Enter`, `Esc`), mechanical key sound effects, and post-test analytics graphs (WPM, accuracy, heatmaps).

## Production & AI Reliability Roadmap
- **AI Agent Reliability**: `pydantic-ai` schema enforcement, model fallback policies, retry handling, and evaluation datasets (evals).
- **Testing & Quality**: Keep SolidJS type checking and builds green, expand pytest API tests, and add Vitest component tests and Playwright E2E coverage.
- **Logging & Observability**: Structured JSON logs (`structlog`) with request correlation IDs and LLM token/latency telemetry.
- **Deployment**: Docker containerization, Alembic/SQLModel migrations, GitHub Actions CI/CD pipeline.
