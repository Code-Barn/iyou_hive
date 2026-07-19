/*
 * Copyright (C) 2026 Byers Brands, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

import axios from "axios";

axios.defaults.withCredentials = true;
axios.defaults.xsrfCookieName = 'hive_csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

/**
 * Read the ``hive_csrftoken`` cookie and return its raw value,
 * stripped of any surrounding quotation marks, whitespace, or
 * URL-encoding artifacts that would cause a
 * "CSRF token from the 'X-Csrftoken' HTTP header has incorrect length"
 * rejection from Django's ``CsrfViewMiddleware``.
 */
function getCSRFToken(): string | null {
  const name = "hive_csrftoken";
  let cookieValue: string | null = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(
          cookie.substring(name.length + 1),
        )
          .replace(/^["']|["']$/g, "")   // strip surrounding quotes
          .trim();                        // strip surrounding whitespace
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
  queryTimeline: (query: string, caseId?: string, documentContent?: string, perspectiveMode?: string) =>
    api.post("/query-timeline/", { query, case_id: caseId, document_content: documentContent, perspective_mode: perspectiveMode }),

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
