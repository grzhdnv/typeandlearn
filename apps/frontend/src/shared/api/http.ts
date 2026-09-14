type FastApiError = {
  detail?: string;
};

/**
 * Performs a JSON request with consistent API error handling.
 *
 * @param url Relative or absolute request URL.
 * @param method HTTP method for the request.
 * @param payload Serializable body for POST/PATCH requests.
 */
const request = async <T>(
  url: string,
  method: string,
  payload?: Record<string, unknown>,
): Promise<T> => {
  const response = await fetch(url, {
    method,
    ...(payload === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
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
 * Performs a GET request and returns the JSON payload.
 */
export const getJson = <T>(url: string): Promise<T> => request<T>(url, "GET");

/**
 * Performs a POST request with JSON body and returns the JSON payload.
 */
export const postJson = <T>(
  url: string,
  payload: Record<string, unknown>,
): Promise<T> => request<T>(url, "POST", payload);

/**
 * Performs a PATCH request with JSON body and returns the JSON payload.
 */
export const patchJson = <T>(
  url: string,
  payload: Record<string, unknown>,
): Promise<T> => request<T>(url, "PATCH", payload);

/**
 * Performs a DELETE request and returns the JSON payload.
 */
export const deleteJson = <T>(url: string): Promise<T> => request<T>(url, "DELETE");
