import test from "node:test";
import assert from "node:assert/strict";
import { getStatusBadgeInfo } from "../../../apps/frontend/src/features/texts/utils/status.ts";

test("getStatusBadgeInfo handles failed status and stage", () => {
  const fromStatus = getStatusBadgeInfo("failed");
  assert.strictEqual(fromStatus.variant, "error");
  assert.strictEqual(fromStatus.label, "ENRICHMENT FAILED");
  assert.strictEqual(fromStatus.canRetry, true);
  assert.strictEqual(fromStatus.isSpinning, false);

  const fromStage = getStatusBadgeInfo("processing", "failed");
  assert.strictEqual(fromStage.variant, "error");
  assert.strictEqual(fromStage.label, "ENRICHMENT FAILED");
  assert.strictEqual(fromStage.canRetry, true);

  const caseInsensitive = getStatusBadgeInfo("FAILED");
  assert.strictEqual(caseInsensitive.variant, "error");
});

test("getStatusBadgeInfo handles translating stage with and without progress counters", () => {
  const withoutCounts = getStatusBadgeInfo("processing", "translating");
  assert.strictEqual(withoutCounts.variant, "translating");
  assert.strictEqual(withoutCounts.label, "TRANSLATING...");
  assert.strictEqual(withoutCounts.isSpinning, true);
  assert.strictEqual(withoutCounts.canRetry, false);

  const withCounts = getStatusBadgeInfo("processing", "translating", 4, 12);
  assert.strictEqual(withCounts.variant, "translating");
  assert.strictEqual(withCounts.label, "TRANSLATING (4/12)...");
  assert.strictEqual(withCounts.isSpinning, true);
});

test("getStatusBadgeInfo handles generating_practice stage", () => {
  const info = getStatusBadgeInfo("processing", "generating_practice");
  assert.strictEqual(info.variant, "vocab");
  assert.strictEqual(info.label, "GENERATING VOCAB...");
  assert.strictEqual(info.isSpinning, true);
  assert.strictEqual(info.canRetry, false);
});

test("getStatusBadgeInfo handles queued stage and pending status", () => {
  const pending = getStatusBadgeInfo("pending");
  assert.strictEqual(pending.variant, "queue");
  assert.strictEqual(pending.label, "IN QUEUE");
  assert.strictEqual(pending.isSpinning, false);

  const queuedStage = getStatusBadgeInfo("processing", "queued");
  assert.strictEqual(queuedStage.variant, "queue");
  assert.strictEqual(queuedStage.label, "IN QUEUE");
});

test("getStatusBadgeInfo handles generic processing status", () => {
  const info = getStatusBadgeInfo("processing");
  assert.strictEqual(info.variant, "translating");
  assert.strictEqual(info.label, "PROCESSING...");
  assert.strictEqual(info.isSpinning, true);
});

test("getStatusBadgeInfo handles ready/processed status", () => {
  const info = getStatusBadgeInfo("processed", "completed");
  assert.strictEqual(info.variant, "ready");
  assert.strictEqual(info.label, "READY");
  assert.strictEqual(info.isSpinning, false);
  assert.strictEqual(info.canRetry, false);
});
