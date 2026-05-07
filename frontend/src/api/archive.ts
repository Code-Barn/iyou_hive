import axios from "axios";

const api = axios.create({
  baseURL: "/api/archive",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export const archiveApi = {
  // Get recursive directory tree
  getDirectoryTree: () => api.get("/directory/"),

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
};

export default archiveApi;
