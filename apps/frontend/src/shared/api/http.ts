type FastApiError = {
  detail?: string;
};

/**
 * Performs a GET request and returns JSON payload with consistent API error handling.
 *
 * @param url Relative or absolute request URL.
 */
export const getJson = async <T>(url: string): Promise<T> => {
  const response = await fetch(url);
  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const body = (await response.json()) as FastApiError;
      throw new Error(body.detail ?? `Request failed with status ${response.status}`);
    }
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (!isJson) {
    throw new Error("Expected JSON response from API");
  }

  return (await response.json()) as T;
};

/**
 * Performs a POST request with JSON body and returns JSON payload.
 *
 * @param url Relative or absolute request URL.
 * @param payload Serializable body for the API request.
 */
export const postJson = async <T>(
  url: string,
  payload: Record<string, unknown>,
): Promise<T> => {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const body = (await response.json()) as FastApiError;
      throw new Error(body.detail ?? `Request failed with status ${response.status}`);
    }
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (!isJson) {
    throw new Error("Expected JSON response from API");
  }

  return (await response.json()) as T;
};

/**
 * Performs a DELETE request and returns JSON payload.
 *
 * @param url Relative or absolute request URL.
 */
export const deleteJson = async <T>(url: string): Promise<T> => {
  const response = await fetch(url, {
    method: "DELETE",
  });

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const body = (await response.json()) as FastApiError;
      throw new Error(body.detail ?? `Request failed with status ${response.status}`);
    }
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (!isJson) {
    throw new Error("Expected JSON response from API");
  }

  return (await response.json()) as T;
};

/**
 * Performs a PATCH request with JSON body and returns JSON payload.
 *
 * @param url Relative or absolute request URL.
 * @param payload Serializable body for the API request.
 */
export const patchJson = async <T>(
  url: string,
  payload: Record<string, unknown>,
): Promise<T> => {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const body = (await response.json()) as FastApiError;
      throw new Error(body.detail ?? `Request failed with status ${response.status}`);
    }
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (!isJson) {
    throw new Error("Expected JSON response from API");
  }

  return (await response.json()) as T;
};
