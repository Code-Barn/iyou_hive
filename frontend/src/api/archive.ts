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
  // Get recursive directory tree
  getDirectoryTree: (caseId?: string) =>
    api.get("/directory/", { params: caseId ? { case_id: caseId } : {} }),

  // Get metadata for a specific document
  getDocumentMetadata: (fileUuid: string) =>
    api.get(`/documents/metadata/${fileUuid}/`),

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
  uploadToVault: (caseId: string, formData: FormData, config?: any) =>
    api.post("/api/documents/upload/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      ...config,
    }),
};

export const uploadToVault = (formData: FormData) =>
  archiveApi.uploadToVault("", formData);

export default archiveApi;
