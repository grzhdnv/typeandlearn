import { Component, Show, createMemo } from "solid-js";
import { getStatusBadgeInfo } from "../utils/status";

interface StatusBadgeProps {
  status: string;
  stage?: string | null;
  completedCount?: number;
  totalCount?: number;
  errorMessage?: string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export const StatusBadge: Component<StatusBadgeProps> = (props) => {
  const badgeInfo = createMemo(() =>
    getStatusBadgeInfo(
      props.status,
      props.stage,
      props.completedCount,
      props.totalCount
    )
  );

  return (
    <Show when={badgeInfo().variant !== "ready"}>
      <div class="flex items-center gap-1.5">
        <span
          class={`font-mono-label text-mono-label uppercase px-2 py-0.5 border flex items-center gap-1.5 select-none ${
            badgeInfo().variant === "error"
              ? "bg-red-50 text-red-700 border-red-300 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800"
              : badgeInfo().variant === "vocab" || badgeInfo().variant === "translating"
              ? "bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800"
              : "bg-surface-container text-on-surface-variant border-outline-variant"
          }`}
          title={props.errorMessage || badgeInfo().description}
        >
          <Show when={badgeInfo().isSpinning}>
            <span class="material-symbols-outlined animate-spin text-[14px]">
              autorenew
            </span>
          </Show>
          <Show when={badgeInfo().variant === "queue"}>
            <span class="material-symbols-outlined text-[14px]">schedule</span>
          </Show>
          <Show when={badgeInfo().variant === "error"}>
            <span class="material-symbols-outlined text-[14px]">warning</span>
          </Show>
          {badgeInfo().label}
        </span>

        <Show when={badgeInfo().canRetry && props.onRetry}>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              props.onRetry?.();
            }}
            disabled={props.isRetrying}
            class="px-2 py-0.5 bg-primary text-on-primary font-mono-label text-mono-label hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-1"
            title="Retry AI enrichment"
          >
            <span class="material-symbols-outlined text-[14px]">refresh</span>
            {props.isRetrying ? "RETRYING..." : "RETRY"}
          </button>
        </Show>
      </div>
    </Show>
  );
};
