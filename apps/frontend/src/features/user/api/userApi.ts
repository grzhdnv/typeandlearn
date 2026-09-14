import { deleteJson, getJson } from "../../../shared/api/http";
import type { UserProfile } from "../../../shared/types/contracts";

/**
 * Fetch profile and authentication state of current user.
 */
export const fetchUserProfile = async (): Promise<UserProfile> => {
  return getJson<UserProfile>("/api/auth/me");
};

/**
 * Trigger machine-readable JSON export of all user-owned data (GDPR Article 20).
 */
export const exportUserData = async (): Promise<void> => {
  const response = await fetch("/api/user/export");
  if (!response.ok) {
    throw new Error(`Export failed with status ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = response.headers.get("Content-Disposition");
  let filename = "typeandlearn-export.json";
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

/**
 * Permanently purge all owned user data across all tables (GDPR Article 17).
 */
export const deleteUserAccount = async (): Promise<{ status: string; owner_id: string }> => {
  return deleteJson<{ status: string; owner_id: string }>("/api/user/account");
};
