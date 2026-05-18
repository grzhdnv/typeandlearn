type FastApiError = {
  detail?: string;
};

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
