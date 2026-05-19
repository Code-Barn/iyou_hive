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
axios.defaults.xsrfCookieName = 'hiver_csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

/**
 * Read the ``hiver_csrftoken`` cookie and return its raw value,
 * stripped of any surrounding quotation marks, whitespace, or
 * URL-encoding artifacts that would cause a
 * "CSRF token from the 'X-Csrftoken' HTTP header has incorrect length"
 * rejection from Django's ``CsrfViewMiddleware``.
 */
function getCSRFToken(): string | null {
  const name = "hiver_csrftoken";
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
  baseURL: "/api/archive",
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

export const archiveApi = {
  // Create a new case via core API
  createCase: (name: string, description: string, clientLegalName?: string, opposingLegalName?: string) =>
    axios.post("/core/api/cases/", { name, description, client_legal_name: clientLegalName || "", opposing_legal_name: opposingLegalName || "" }, {
      withCredentials: true,
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() || "" },
    }),

  // Get recursive directory tree
  getDirectoryTree: (caseId?: string) =>
    api.get("/directory/", { params: caseId ? { case_id: caseId } : {} }),

  // Get metadata for a specific document
  getDocumentMetadata: (fileUuid: string) =>
    api.get(`/documents/metadata/${fileUuid}/`),

  // Get raw file content for a document by UUID
  getDocumentContent: (fileUuid: string) =>
    api.get(`/documents/content/${fileUuid}/`),

  // Move a file to a new folder
  moveFile: (sourceFileUuid: string, destinationFolderUuid: string) =>
    api.post("/documents/move_file/", {
      source_file_uuid: sourceFileUuid,
      destination_folder_uuid: destinationFolderUuid,
    }),

  // Promote a document to formal evidence
  promoteDocument: (docUuid: string) =>
    api.post(`/documents/${docUuid}/promote/`),

  // Demote a document from formal evidence
  demoteDocument: (docUuid: string) =>
    api.post(`/documents/${docUuid}/demote/`),

  // Upload documents to workspace
  uploadDocuments: (caseId: string, formData: FormData, config?: any) =>
    api.post("/documents/upload/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      ...config,
    }),

  // Smart Ingestion: Upload to Formal Vault or Private Workspace
  uploadToVault: (caseId: string, formData: FormData, config?: any) => {
    // Add CSRF token to FormData for Django
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      formData.append("csrfmiddlewaretoken", csrfToken);
    }
    return api.post("/documents/upload/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      ...config,
    });
  },
};

export const uploadToVault = (formData: FormData) =>
  archiveApi.uploadToVault("", formData);

export default archiveApi;
