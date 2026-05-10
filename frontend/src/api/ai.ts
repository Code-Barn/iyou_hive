import axios from "axios";

// Function to get CSRF token from cookie
function getCSRFToken(): string | null {
  const name = "csrftoken";
  let cookieValue: string | null = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const api = axios.create({
  baseURL: "/ai/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add CSRF token to all requests
api.interceptors.request.use((config) => {
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    config.headers["X-CSRFToken"] = csrfToken;
  }
  return config;
});

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface AISettings {
  mistral_api_key: string;
  gemini_api_key: string;
  preferred_provider: "mistral" | "gemini";
}

export const aiApi = {
  // Save API key settings - POST /ai/save-api-key/
  saveApiKey: (settings: {
    mistral_api_key?: string;
    gemini_api_key?: string;
    preferred_provider?: string;
  }) => api.post("/save-api-key/", settings),

  // Query timeline with AI - POST /ai/query-timeline/
  queryTimeline: (query: string, caseId?: string, documentContent?: string) =>
    api.post("/query-timeline/", { query, case_id: caseId, document_content: documentContent }),

  // Analyze a document - POST /ai/analyze/
  analyzeDocument: (documentId: string, text?: string) =>
    api.post("/analyze/", { document_id: documentId, text }),

  // Get AI suggestions for new timeline events - POST /ai/suggest-events/
  suggestEvents: (caseId?: string) =>
    api.post("/suggest-events/", { case_id: caseId }),

  // Analyze a specific timeline event - POST /ai/analyze-event/<uuid:event_id>/
  analyzeTimelineEvent: (eventId: string) =>
    api.post(`/analyze-event/${eventId}/`),
};

export default api;
