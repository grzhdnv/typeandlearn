export type PostTextResponse = {
	message: string;
	text: string;
};

type FastApiError = {
	detail?: string;
};

export const postText = async (text: string): Promise<PostTextResponse> => {
	const trimmed = text.trim();
	if (!trimmed) {
		throw new Error("Text cannot be empty");
	}

	const response = await fetch("/api/texts", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({ text: trimmed }),
	});

	const contentType = response.headers.get("content-type") ?? "";
	const isJson = contentType.includes("application/json");

	if (!response.ok) {
		if (isJson) {
			const errorBody = (await response.json()) as FastApiError;
			throw new Error(errorBody.detail ?? `Request failed with status ${response.status}`);
		}
		throw new Error(`Request failed with status ${response.status}`);
	}

	if (!isJson) {
		throw new Error("Expected JSON response from API");
	}

	return (await response.json()) as PostTextResponse;
};
