export function getErrorMessage(err, fallback = "Something went wrong. Please try again.") {
  if (!err?.response) {
    return "We couldn't reach the server. Check your connection and try again.";
  }

  const { status, data } = err.response;

  if (status === 429) return "Too many attempts. Please wait a few minutes and try again.";

  // django-axes lockout / HTML error pages
  if (typeof data === "string") {
    if (status === 403) return "Too many failed attempts. Your access is temporarily locked.";
    return data.trim().startsWith("<") ? fallback : data;
  }

  if (data?.error) return data.error;
  if (data?.detail) return data.detail;
  if (data?.message) return data.message;
  if (Array.isArray(data?.non_field_errors)) return data.non_field_errors[0];

  // DRF serializer errors: { field: ["msg"] }
  if (data && typeof data === "object") {
    const first = Object.values(data).flat()[0];
    if (typeof first === "string") return first;
  }

  if (status >= 500) return "Our server ran into a problem. Please try again shortly.";
  return fallback;
}