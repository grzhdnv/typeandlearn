/**
 * Truthful status and badge computation for AI enrichment jobs.
 */

export type BadgeVariant = "queue" | "translating" | "vocab" | "error" | "ready";

export interface StatusBadgeInfo {
  label: string;
  variant: BadgeVariant;
  isSpinning: boolean;
  canRetry: boolean;
  description: string;
}

/**
 * Returns true while a text still has enrichment work queued or running.
 */
export function isEnrichmentActive(text: {
  status: string;
  enrichment_stage?: string | null;
}): boolean {
  return (
    text.status === "processing" ||
    text.status === "pending" ||
    text.enrichment_stage === "queued" ||
    text.enrichment_stage === "translating" ||
    text.enrichment_stage === "generating_practice"
  );
}

export function getStatusBadgeInfo(
  status: string,
  stage?: string | null,
  completedCount?: number,
  totalCount?: number
): StatusBadgeInfo {
  const normStatus = (status || "").toLowerCase();
  const normStage = (stage || "").toLowerCase();

  if (normStatus === "failed" || normStage === "failed") {
    return {
      label: "ENRICHMENT FAILED",
      variant: "error",
      isSpinning: false,
      canRetry: true,
      description: "AI enrichment encountered an error and stopped.",
    };
  }

  if (normStage === "generating_practice") {
    return {
      label: "GENERATING VOCAB...",
      variant: "vocab",
      isSpinning: true,
      canRetry: false,
      description: "Extracting key vocabulary and generating practice drills.",
    };
  }

  if (normStage === "translating") {
    const counter =
      typeof completedCount === "number" && typeof totalCount === "number" && totalCount > 0
        ? ` (${completedCount}/${totalCount})`
        : "";
    return {
      label: `TRANSLATING${counter}...`,
      variant: "translating",
      isSpinning: true,
      canRetry: false,
      description: "Translating sentences and generating lexical hints.",
    };
  }

  if (normStatus === "pending" || normStage === "queued") {
    return {
      label: "IN QUEUE",
      variant: "queue",
      isSpinning: false,
      canRetry: false,
      description: "Waiting for background worker.",
    };
  }

  if (normStatus === "processing") {
    return {
      label: "PROCESSING...",
      variant: "translating",
      isSpinning: true,
      canRetry: false,
      description: "Enrichment job in progress.",
    };
  }

  return {
    label: "READY",
    variant: "ready",
    isSpinning: false,
    canRetry: false,
    description: "Fully processed and ready for practice.",
  };
}
