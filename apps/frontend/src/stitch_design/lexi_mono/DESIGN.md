---
name: Lexi-Mono
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#4c4546'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#7e7576'
  outline-variant: '#cfc4c5'
  surface-tint: '#5e5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1b1b1b'
  on-primary-container: '#848484'
  inverse-primary: '#c6c6c6'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#001a42'
  on-tertiary-container: '#3980f4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c6'
  on-primary-fixed: '#1b1b1b'
  on-primary-fixed-variant: '#474747'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#d8e2ff'
  tertiary-fixed-dim: '#adc6ff'
  on-tertiary-fixed: '#001a42'
  on-tertiary-fixed-variant: '#004395'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  mono-input:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 32px
  mono-label:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  max-width-content: 800px
---

## Brand & Style

The brand identity centers on the intersection of academic rigor and modern digital efficiency. It is designed for learners who value focus, clarity, and the tactile rhythm of typing. The personality is intellectual yet accessible—avoiding the "gamified" clutter of traditional language apps in favor of a "study tool" aesthetic.

The visual style is **Modern Brutalism mixed with Minimalism**. It utilizes high-contrast surfaces, thin but intentional borders, and generous whitespace to reduce cognitive load during intense learning sessions. The "Typewriter" influence is felt through the disciplined use of monospaced typography for interactive elements, creating a sense of precision and technical craft.

**Key Visual Principles:**
- **Extreme Clarity:** Content is always the hero; UI chrome is secondary.
- **Rhythmic Spacing:** A strict 8px grid ensures that typing areas and text blocks feel structured and balanced.
- **Intentional Contrast:** Vibrant accents are reserved strictly for feedback, progress, and success to keep the user's attention on the learning task.

## Colors

The palette is anchored in a monochromatic core to evoke the look of printed educational materials and classic terminal interfaces.

- **Primary:** Pure Black (#000000) for text, primary buttons, and heavy borders.
- **Secondary (Accent/Success):** Emerald Green (#10B981) used for "correct" states, progress indicators, and completion celebrations.
- **Tertiary (Focus/Info):** Bright Blue (#3B82F6) for active cursor states, text selection, and grammar hints.
- **Neutral:** A range of architectural grays. #FFFFFF (Pure White) for the main workspace, #F9FAFB for subtle container backgrounds, and #E5E7EB for low-contrast borders.

The UI relies on **tonal shifts** rather than vibrant colors to indicate state changes, ensuring the single accent color remains impactful when it appears.

## Typography

This design system uses a dual-font strategy to separate **Reading/Navigation** from **Typing/Interacting**.

- **Hanken Grotesk:** A modern, clean sans-serif used for all UI instructions, headlines, and general body text. It provides a professional, approachable feel.
- **JetBrains Mono:** A high-legibility monospace font used for all learner-input areas, code blocks, or literal language examples. The consistent character width in this font helps users recognize spelling patterns and character placement.

**Scale and Hierarchy:**
- Headlines use Hanken Grotesk with tight letter spacing for a modern, editorial look.
- Interactive labels and "hints" use JetBrains Mono in uppercase to distinguish them as functional UI elements.
- Typing areas (Textareas/Inputs) utilize `mono-input` with generous line-height to ensure clarity when diacritics are involved in different languages.

## Layout & Spacing

The layout philosophy is **Fixed-Fluid Hybrid**. On desktop, the learning workspace is constrained to a central column (800px) to prevent eye strain and maintain line-length readability for long-form typing.

- **Grid System:** A 12-column grid is used for layout-heavy pages (dashboards, settings), but the core learning interface uses a single-column stack.
- **Spacing Rhythm:** Based on an 8px scale.
  - **4px/8px:** For internal component padding (buttons, inputs).
  - **16px/24px:** For spacing between related elements (label to input).
  - **48px/64px:** For large section breaks.
- **Breakpoints:**
  - **Mobile (<640px):** Single column, 16px side margins, typography downscales.
  - **Tablet (640px - 1024px):** 32px side margins, content expands to max-width.
  - **Desktop (>1024px):** Fixed 800px center container with 64px vertical margins.

## Elevation & Depth

To maintain a clean, typewriter-inspired aesthetic, this design system avoids soft shadows and blurs.

- **Flat Depth:** Hierarchy is established through background color shifts (e.g., a light gray background for a container against a white page).
- **Hard Borders:** Elevation is signaled by 1px or 2px solid borders.
- **Active State:** When an element is focused (like an input field), the border thickness increases to 2px and changes to the primary black or tertiary blue.
- **Ghosting:** Inactive or "background" content uses lower opacity (60%) rather than a different color, maintaining the monochrome feel.

## Shapes

The shape language is **Soft-Square**. While the aesthetic is brutalist, 0.25rem (4px) corner radii are used to prevent the UI from feeling overly aggressive or dated.

- **Base (4px):** Standard buttons, inputs, and cards.
- **Large (8px):** Main content containers or modals.
- **Interactive Elements:** Maintain the same radius to ensure a consistent "block" feel across the interface.

## Components

### Buttons
- **Primary:** Solid Black background, White JetBrains Mono text. No shadow. 2px hover border in Secondary green.
- **Secondary:** White background, Black border (1px), Black JetBrains Mono text.
- **Ghost:** No background, No border, JetBrains Mono text. Used for "Previous" or "Cancel" actions.

### Input Fields (The Workspace)
- **Typing Area:** White background, 1px Gray-300 border. On focus, the border becomes 2px Black.
- **Placeholder Text:** Light Gray (#9CA3AF) in JetBrains Mono.
- **Caret:** A custom thick, blinking block cursor (consistent with monospace/typewriter themes).

### Chips & Tags
- Used for language selection or "hints." Rectangular with 4px radius, light gray background, and `mono-sm` text.

### Feedback Cards
- **Success:** Emerald green border (2px), white background.
- **Error/Correction:** Black border with a red-tinted strike-through for incorrect characters.

### Lists
- Clean, unstyled lists with 1px bottom borders separating items. No bullet points; use JetBrains Mono numbers (01., 02.) for a technical look.