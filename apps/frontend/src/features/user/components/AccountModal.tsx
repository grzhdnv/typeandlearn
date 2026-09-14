import { Component, Show, createEffect, createSignal, onCleanup, onMount } from "solid-js";
import { deleteUserAccount, exportUserData, fetchUserProfile } from "../api/userApi";
import type { UserProfile } from "../../../shared/types/contracts";

interface AccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AccountModal: Component<AccountModalProps> = (props) => {
  const [profile, setProfile] = createSignal<UserProfile | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [exporting, setExporting] = createSignal(false);
  const [exportSuccess, setExportSuccess] = createSignal(false);
  const [exportError, setExportError] = createSignal<string | null>(null);

  const [confirmDelete, setConfirmDelete] = createSignal(false);
  const [deleting, setDeleting] = createSignal(false);
  const [deleteSuccess, setDeleteSuccess] = createSignal(false);
  const [deleteError, setDeleteError] = createSignal<string | null>(null);

  createEffect(() => {
    if (!props.isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        props.onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    onCleanup(() => {
      window.removeEventListener("keydown", handleKeyDown);
    });
  });

  onMount(async () => {
    try {
      setLoading(true);
      const data = await fetchUserProfile();
      setProfile(data);
    } catch {
      // Non-fatal if unauthenticated or offline
    } finally {
      setLoading(false);
    }
  });

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    setExportSuccess(false);
    try {
      await exportUserData();
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 4000);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Failed to export data archive");
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteUserAccount();
      setDeleteSuccess(true);
      setTimeout(() => {
        window.location.href = "/";
      }, 1500);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete account data");
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  return (
    <Show when={props.isOpen}>
      <div
        class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        id="account-modal-backdrop"
        onClick={(e) => {
          if (e.target === e.currentTarget) props.onClose();
        }}
      >
        <div
          class="bg-surface border-2 border-outline-variant max-w-lg w-full p-6 md:p-8 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto"
          id="account-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="account-modal-title"
        >
          {/* Header */}
          <div class="flex justify-between items-start border-b border-outline-variant pb-4">
            <div class="space-y-1">
              <span class="font-mono-label text-mono-label text-primary uppercase tracking-widest">
                Identity & Governance
              </span>
              <h2 id="account-modal-title" class="font-headline-md text-headline-md font-bold text-on-surface">
                Account & Privacy
              </h2>
            </div>
            <button
              onClick={props.onClose}
              class="text-on-surface-variant hover:text-on-surface p-1 transition-colors"
              id="btn-close-account-modal"
              aria-label="Close modal"
            >
              <span class="material-symbols-outlined text-2xl">close</span>
            </button>
          </div>

          {/* Profile Card */}
          <div class="bg-surface-container/40 border border-outline-variant p-4 space-y-3">
            <span class="font-mono-label text-mono-label text-on-surface-variant uppercase">
              Current Identity
            </span>
            <Show
              when={!loading() && profile()}
              fallback={<div class="font-mono-sm text-mono-sm text-on-surface-variant animate-pulse">Loading identity profile...</div>}
            >
              <div class="space-y-2 font-mono-sm text-mono-sm">
                <div class="flex justify-between items-center">
                  <span class="text-on-surface-variant">Owner ID:</span>
                  <span class="font-bold text-primary truncate max-w-[240px]" id="profile-owner-id">
                    {profile()?.owner_id}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-on-surface-variant">Authentication:</span>
                  <span class="uppercase tracking-wider">
                    {profile()?.auth_mode === "jwt" ? "Managed JWT" : "Local Workspace Default"}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-on-surface-variant">State:</span>
                  <span class="px-2 py-0.5 bg-primary/10 text-primary border border-primary/30 uppercase text-[11px] font-bold">
                    {profile()?.authenticated ? "Authenticated" : "Local Mode"}
                  </span>
                </div>
              </div>
            </Show>
          </div>

          {/* Data Portability (GDPR Art. 20) */}
          <div class="border border-outline-variant p-4 space-y-3">
            <div class="flex items-center gap-2 text-primary">
              <span class="material-symbols-outlined text-xl">download</span>
              <h3 class="font-headline-sm text-base font-bold">Data Export (GDPR Article 20)</h3>
            </div>
            <p class="font-body-sm text-body-sm text-on-surface-variant">
              Download a complete, machine-readable JSON archive of your personal data, including all imported texts,
              vocabulary frequencies, practice drills, learning sessions, weak words, and token usage records.
            </p>
            <Show when={exportError()}>
              <p class="font-mono-sm text-mono-sm text-error" id="export-error">{exportError()}</p>
            </Show>
            <Show when={exportSuccess()}>
              <p class="font-mono-sm text-mono-sm text-green-600 dark:text-green-400 font-bold" id="export-success">
                Export downloaded successfully!
              </p>
            </Show>
            <button
              onClick={handleExport}
              disabled={exporting()}
              class="w-full py-2.5 px-4 bg-surface border border-outline-variant hover:border-primary font-mono-label text-mono-label transition-colors uppercase tracking-wider flex items-center justify-center gap-2 font-medium disabled:opacity-50"
              id="btn-export-data"
            >
              <Show
                when={!exporting()}
                fallback={<span>Preparing Archive...</span>}
              >
                <span class="material-symbols-outlined text-lg">file_download</span>
                <span>Export All Data (JSON)</span>
              </Show>
            </button>
          </div>

          {/* Right to Erasure / Danger Zone (GDPR Art. 17) */}
          <div class="border border-error/50 bg-error/5 p-4 space-y-3">
            <div class="flex items-center gap-2 text-error">
              <span class="material-symbols-outlined text-xl">delete_forever</span>
              <h3 class="font-headline-sm text-base font-bold">Danger Zone: Right to Erasure</h3>
            </div>
            <p class="font-body-sm text-body-sm text-on-surface-variant">
              Permanently purge all texts, sentence progress, session statistics, weak words, and usage history
              associated with your identity. This action is irreversible.
            </p>
            <Show when={deleteError()}>
              <p class="font-mono-sm text-mono-sm text-error" id="delete-error">{deleteError()}</p>
            </Show>
            <Show when={deleteSuccess()}>
              <p class="font-mono-sm text-mono-sm text-error font-bold" id="delete-success">
                All data purged successfully. Resetting workspace...
              </p>
            </Show>

            <Show when={!deleteSuccess()}>
              <Show
                when={confirmDelete()}
                fallback={
                  <button
                    onClick={() => setConfirmDelete(true)}
                    class="w-full py-2.5 px-4 border border-error text-error hover:bg-error hover:text-white font-mono-label text-mono-label transition-colors uppercase tracking-wider flex items-center justify-center gap-2 font-bold"
                    id="btn-delete-account"
                  >
                    <span class="material-symbols-outlined text-lg">warning</span>
                    <span>Purge All Account Data</span>
                  </button>
                }
              >
                <div class="space-y-3 pt-2">
                  <p class="font-mono-sm text-mono-sm text-error font-bold uppercase tracking-wider">
                    Are you absolutely sure? All progress will be deleted immediately.
                  </p>
                  <div class="flex gap-3">
                    <button
                      onClick={() => setConfirmDelete(false)}
                      class="flex-1 py-2 border border-outline-variant font-mono-label text-mono-label uppercase tracking-wider hover:border-on-surface transition-colors"
                      id="btn-cancel-delete"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleDelete}
                      disabled={deleting()}
                      class="flex-1 py-2 bg-error text-white font-mono-label text-mono-label uppercase tracking-wider hover:bg-error/90 transition-colors font-bold disabled:opacity-50"
                      id="btn-confirm-delete"
                    >
                      {deleting() ? "Purging..." : "Confirm Purge"}
                    </button>
                  </div>
                </div>
              </Show>
            </Show>
          </div>
        </div>
      </div>
    </Show>
  );
};
