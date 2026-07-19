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

// Create axios instance with Django CSRF support
const api = axios.create({
  baseURL: "/api/timeline",
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

// Timeline Events API
export interface MaterializePayload {
  date: string;
  event: string;
  category?: string;
  notes?: string;
  source_party?: string;
  source_type?: string;
  status?: string;
  trust_level?: number;
  citation?: string;
  evidence_ids?: string[];
  section_header?: string;
  is_system_source?: boolean;
}

export const timelineApi = {
  // Get all events for a case
  getEvents: (caseId: string, filters?: Record<string, string | boolean>) =>
    api.get(`/cases/${caseId}/events/`, { params: filters }),

  // Get single event
  getEvent: (caseId: string, eventId: string) =>
    api.get(`/cases/${caseId}/events/${eventId}/`),

  // Create event
  createEvent: (caseId: string, data: Record<string, any>) =>
    api.post(`/cases/${caseId}/events/`, data),

  // Update event (PATCH for partial updates)
  updateEvent: (caseId: string, eventId: string, data: Record<string, any>) =>
    api.patch(`/cases/${caseId}/events/${eventId}/`, data),

  // Delete event
  deleteEvent: (caseId: string, eventId: string) =>
    api.delete(`/cases/${caseId}/events/${eventId}/`),

  // Contest an event (create counter-claim)
  contestEvent: (
    caseId: string,
    eventId: string,
    data: { source_party?: string; notes?: string; evidence_ids?: string[] },
  ) => api.post(`/cases/${caseId}/events/${eventId}/contest/`, data),

  // Resolve a conflict
  resolveConflict: (
    caseId: string,
    eventId: string,
    data: {
      resolution: string;
      evidence_ids?: string[];
      date?: string;
      event?: string;
      category?: string;
      notes?: string;
      citation?: string;
    },
  ) => api.post(`/cases/${caseId}/events/${eventId}/resolve/`, data),

  // Upload timeline markdown file
  uploadTimeline: (caseId: string, formData: FormData) =>
    api.post(`/cases/${caseId}/upload-markdown/`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),

  // Materialize an AI-suggested event into a real TimelineEvent
  materializeEvent: (caseId: string, payload: MaterializePayload) =>
    api.post(`/cases/${caseId}/materialize/`, payload),

  // Generate PDF of timeline
  generatePdf: (caseId: string) =>
    api.get(`/cases/${caseId}/generate-pdf/`, {
      responseType: "blob", // Important for file downloads
    }),

  // Export timeline as .hive bundle
  exportHive: (caseId: string, includePrivate: boolean = false) =>
    api.get(`/cases/${caseId}/export-hive/`, {
      params: { include_private: includePrivate },
      responseType: "blob",
    }),

  // Import timeline from .hive bundle
  importHive: (caseId: string, formData: FormData) =>
    api.post(`/cases/${caseId}/import-hive/`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }),
};

// Diff View API
export const diffApi = {
  // Get diff view data
  getDiffView: (caseId: string, leftParty?: string, rightParty?: string) => {
    const params: Record<string, string> = {};
    if (leftParty) params.left = leftParty;
    if (rightParty) params.right = rightParty;
    return api.get(`/cases/${caseId}/diff/`, { params });
  },
};

// Collections API
export const collectionApi = {
  // Get all collections for a case
  getCollections: (caseId: string) => api.get(`/cases/${caseId}/collections/`),

  // Get single collection
  getCollection: (caseId: string, collectionId: string) =>
    api.get(`/cases/${caseId}/collections/${collectionId}/`),

  // Create collection
  createCollection: (
    caseId: string,
    data: { name: string; description?: string; is_public?: boolean },
  ) => api.post(`/cases/${caseId}/collections/`, data),

  // Delete collection
  deleteCollection: (caseId: string, collectionId: string) =>
    api.delete(`/cases/${caseId}/collections/${collectionId}/`),

  // Add event to collection
  addEventToCollection: (
    caseId: string,
    collectionId: string,
    eventId: string,
  ) =>
    api.post(`/cases/${caseId}/collections/${collectionId}/add-event/`, {
      event_id: eventId,
    }),

  // Remove event from collection
  removeEventFromCollection: (
    caseId: string,
    collectionId: string,
    eventId: string,
  ) =>
    api.post(`/cases/${caseId}/collections/${collectionId}/remove-event/`, {
      event_id: eventId,
    }),
};

export default api;
