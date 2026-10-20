import { type Component, For, Show } from "solid-js";
import { describeCharacter, type SentenceReview } from "../core/review.ts";

export const MistakeReview: Component<{ review: SentenceReview }> = props => (
  <section aria-label="Mistake review" class="mt-6 min-w-0 space-y-4 border-t border-outline-variant pt-4">
    <h3 class="font-mono-label text-primary">Mistakes · {props.review.mistakes.length}</h3>
    <Show when={props.review.mistakes.length > 0} fallback={
      <p class="font-mono-sm text-on-surface-variant">No mistakes in this sentence.</p>
    }>
      <dl class="space-y-2 font-mono-sm">
        <div class="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
          <dt class="text-on-surface-variant">Expected</dt>
          <dd class="max-h-24 overflow-auto whitespace-pre-wrap break-words" aria-label="Expected sentence">{props.review.expected.join("")}</dd>
        </div>
        <div class="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
          <dt class="text-on-surface-variant">You typed</dt>
          <dd class="max-h-24 overflow-auto whitespace-pre-wrap break-words" aria-label="Typed sentence">
            <For each={props.review.typed}>{(character, index) => (
              <span class={character !== props.review.expected[index()] ? "text-error underline decoration-2" : ""}>{character}</span>
            )}</For>
          </dd>
        </div>
      </dl>
      <p class="font-mono-sm text-on-surface-variant">US QWERTY estimates. Key distance suggests a possible cause; case differences may involve Shift or Caps Lock.</p>
      <div class="max-h-72 sm:max-h-96 overflow-auto">
        <table class="w-full text-left font-mono-sm">
          <caption class="sr-only">Wrong keystrokes, including corrected mistakes</caption>
          <thead class="border-b border-outline-variant">
            <tr><th scope="col" class="py-2 pr-3">Position</th><th scope="col" class="pr-3">Expected</th><th scope="col" class="pr-3">Typed</th><th scope="col">Comparison</th></tr>
          </thead>
          <tbody>
            <For each={props.review.mistakes}>{mistake => (
              <tr class="border-b border-outline-variant/50 align-top">
                <td class="py-3 pr-3">{mistake.position}</td>
                <td class="py-3 pr-3 font-bold">{describeCharacter(mistake.expected)}</td>
                <td class="py-3 pr-3 text-error font-bold">{describeCharacter(mistake.typed)}</td>
                <td class="py-3 space-y-1">
                  <div title={mistake.comparison.explanation}>{mistake.comparison.label}</div>
                  <Show when={mistake.comparison.distance !== undefined}>
                    <div class="text-on-surface-variant">{mistake.comparison.distance === 0 ? "Same key" : `~${mistake.comparison.distance} key width${mistake.comparison.distance === 1 ? "" : "s"}`}</div>
                  </Show>
                  <div class="text-on-surface-variant">{mistake.status}</div>
                </td>
              </tr>
            )}</For>
          </tbody>
        </table>
      </div>
    </Show>
  </section>
);
