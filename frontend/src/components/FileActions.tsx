import React, { useState, useRef } from "react";
import { archiveApi } from "../api/archive";

interface FileEntry {
  file: File;
  relativePath: string;
}

interface FileActionsProps {
  caseId: string;
  onFileUploaded: () => void;
}

export const FileActions: React.FC<FileActionsProps> = ({
  caseId,
  onFileUploaded,
}) => {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<FileEntry[]>([]);
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [uploadError, setUploadError] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const entries: FileEntry[] = Array.from(e.target.files).map((file) => ({
        file,
        relativePath: file.webkitRelativePath || file.name,
      }));
      setUploadFiles(entries);
    }
  };

  const handleFileUpload = async () => {
    if (uploadFiles.length === 0 || !caseId) return;

    setUploadStatus("uploading");
    setUploadError("");
    setUploadProgress(0);

    try {
      const formData = new FormData();
      uploadFiles.forEach(({ file, relativePath }) => {
        formData.append("files", file);
        formData.append("relative_paths", relativePath);
      });
      formData.append("case_uuid", caseId);
      formData.append("vault_type", "private");

      const response = await archiveApi.uploadDocuments(caseId, formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            setUploadProgress(percentCompleted);
          }
        },
      });

      if (response.data.status === "success") {
        setUploadStatus("success");
        setUploadProgress(100);
        onFileUploaded();

        setTimeout(() => {
          setIsUploadModalOpen(false);
          setUploadStatus("idle");
          setUploadFiles([]);
          setUploadProgress(0);
          if (fileInputRef.current) {
            fileInputRef.current.value = "";
          }
        }, 2000);
      } else {
        setUploadStatus("error");
        setUploadError(response.data.error || "Failed to upload files");
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadStatus("error");
      setUploadError("Failed to upload files. Please try again.");
    }
  };

  const handlePromoteSelected = async (fileUuid: string) => {
    try {
      const response = await archiveApi.promoteDocument(fileUuid);

      if (response.data.status === "success") {
        alert("Document promoted to formal evidence!");
        onFileUploaded();
      } else {
        alert(
          "Failed to promote document: " +
            (response.data.error || "Unknown error"),
        );
      }
    } catch (error) {
      console.error("Promote failed:", error);
      alert("Failed to promote document. Please try again.");
    }
  };

  return (
    <div className="file-actions">
      <button
        onClick={() => setIsUploadModalOpen(true)}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
      >
        <span>📁</span> Upload Directory to Workspace
      </button>

      {isUploadModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Upload Directory</h2>
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setUploadStatus("idle");
                  setUploadError("");
                  setUploadFiles([]);
                  setUploadProgress(0);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="mb-4">
              <p className="text-gray-600 mb-2">
                Select a folder to upload its contents to your private workspace
              </p>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                webkitdirectory=""
                directory=""
                multiple
                className="w-full border border-gray-300 rounded-lg p-2"
              />

              {uploadFiles.length > 0 && (
                <div className="mt-2 p-2 bg-gray-50 rounded-lg max-h-48 overflow-y-auto">
                  <p className="text-sm font-medium">
                    Selected files ({uploadFiles.length}):
                  </p>
                  <ul className="text-sm text-gray-600 mt-1">
                    {uploadFiles.map((entry, index) => (
                      <li key={index} className="truncate">
                        • {entry.relativePath} (
                        {Math.round(entry.file.size / 1024)} KB)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {uploadStatus === "uploading" && (
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p className="text-center text-blue-700 text-sm">
                  Uploading: {uploadProgress}% complete
                </p>
              </div>
            )}

            {uploadStatus === "success" && (
              <div className="mb-4 p-3 bg-green-100 rounded-lg">
                <p className="text-green-700">Files uploaded successfully!</p>
                <p className="text-green-600 text-sm">
                  Documents are now in your private workspace with folder
                  structure preserved.
                </p>
              </div>
            )}

            {uploadStatus === "error" && uploadError && (
              <div className="mb-4 p-3 bg-red-100 rounded-lg">
                <p className="text-red-700">Error: {uploadError}</p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setUploadStatus("idle");
                  setUploadError("");
                  setUploadFiles([]);
                  setUploadProgress(0);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleFileUpload}
                disabled={
                  uploadStatus === "uploading" || uploadFiles.length === 0
                }
                className={`px-4 py-2 ${uploadStatus === "uploading" || uploadFiles.length === 0 ? "bg-blue-300" : "bg-blue-600 hover:bg-blue-700"} text-white rounded-lg transition-colors`}
              >
                {uploadStatus === "uploading"
                  ? "Uploading..."
                  : `Upload ${uploadFiles.length} File${uploadFiles.length !== 1 ? "s" : ""}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
