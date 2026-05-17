import React, { useState, useRef } from "react";
import { uploadToVault } from "../api/archive";

interface FileEntry {
  file: File;
  relativePath: string;
}

interface CaseDetailModalProps {
  caseId: string;
  onClose: () => void;
  onEventAdded?: () => void;
  initialTab?: "overview" | "vault" | "bulk" | "ingestion";
}

type VaultType = "FORMAL" | "PRIVATE";

const CaseDetailModal: React.FC<CaseDetailModalProps> = ({
  caseId,
  onClose,
  onEventAdded,
  initialTab = "overview",
}) => {
  const [activeTab, setActiveTab] = useState<
    "overview" | "vault" | "bulk" | "ingestion"
  >(initialTab);
  const [vaultType, setVaultType] = useState<VaultType>("FORMAL");
  const [selectedFiles, setSelectedFiles] = useState<FileEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const entries: FileEntry[] = Array.from(e.target.files).map((file) => ({
        file,
        relativePath: file.webkitRelativePath || file.name,
      }));
      setSelectedFiles(entries);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setUploadStatus("No files selected");
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      selectedFiles.forEach(({ file, relativePath }) => {
        formData.append("files", file);
        formData.append("relative_paths", relativePath);
      });
      formData.append("case_id", caseId);
      formData.append("vault_type", vaultType.toLowerCase());

      const response = await uploadToVault(formData);
      setUploadStatus(
        `Upload successful: ${response.data.message || selectedFiles.length + " files uploaded"}`,
      );
      onEventAdded?.();
    } catch (error: any) {
      const message =
        error.response?.data?.error ||
        error.response?.data?.message ||
        "Failed to upload files";
      console.error("Upload failed:", error.response?.data || error);
      setUploadStatus(message);
    } finally {
      setUploading(false);
      setSelectedFiles([]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
        <div className="bg-gray-800 text-white px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h2 className="text-xl font-semibold">
            Forensic Cockpit - Case Details
          </h2>
          <button onClick={onClose} className="text-2xl hover:text-gray-300">
            ×
          </button>
        </div>

        <div className="p-6">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200 mb-6">
            <button
              onClick={() => setActiveTab("overview")}
              className={`px-4 py-2 text-sm font-medium ${activeTab === "overview" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"}`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab("vault")}
              className={`px-4 py-2 text-sm font-medium ${activeTab === "vault" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"}`}
            >
              Vault Admin
            </button>
            <button
              onClick={() => setActiveTab("bulk")}
              className={`px-4 py-2 text-sm font-medium ${activeTab === "bulk" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"}`}
            >
              Bulk Actions
            </button>
            <button
              onClick={() => setActiveTab("ingestion")}
              className={`px-4 py-2 text-sm font-medium ${activeTab === "ingestion" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"}`}
            >
              Smart Ingestion
            </button>
          </div>

          {/* Tab Content */}
          <div className="min-h-[300px]">
            {activeTab === "overview" && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-800">
                  Case Overview
                </h3>
                <p className="text-gray-600">
                  Comprehensive case information and status.
                </p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Case ID:</span>
                    <span className="ml-2 text-gray-600">{caseId}</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "vault" && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-800">
                  Vault Administration
                </h3>
                <p className="text-gray-600">
                  Manage formal and private vaults.
                </p>
              </div>
            )}

            {activeTab === "bulk" && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-800">
                  Bulk Actions
                </h3>
                <p className="text-gray-600">
                  Perform operations on multiple items.
                </p>
              </div>
            )}

            {activeTab === "ingestion" && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-800">
                  Smart Ingestion
                </h3>
                <p className="text-gray-600">
                  Upload documents to Formal or Private workspace.
                </p>

                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="font-medium text-gray-800 mb-3">
                    Select Vault Type
                  </h4>
                  <div className="flex gap-4 mb-4">
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="vaultType"
                        value="FORMAL"
                        checked={vaultType === "FORMAL"}
                        onChange={() => setVaultType("FORMAL")}
                        className="mr-2"
                      />
                      <span className="text-sm">Formal Vault (Shared)</span>
                    </label>
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="vaultType"
                        value="PRIVATE"
                        checked={vaultType === "PRIVATE"}
                        onChange={() => setVaultType("PRIVATE")}
                        className="mr-2"
                      />
                      <span className="text-sm">Private Workspace</span>
                    </label>
                  </div>

                  <div className="border-t border-gray-200 pt-4">
                    <h4 className="font-medium text-gray-800 mb-3">
                      Select Directory
                    </h4>
                    <input
                      type="file"
                      ref={fileInputRef}
                      webkitdirectory=""
                      directory=""
                      multiple
                      onChange={handleFileChange}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                    {selectedFiles.length > 0 && (
                      <div className="mt-2 p-2 bg-gray-50 rounded-lg max-h-32 overflow-y-auto">
                        <p className="text-sm font-medium">
                          Selected ({selectedFiles.length} files):
                        </p>
                        <ul className="text-sm text-gray-600 mt-1">
                          {selectedFiles.map((entry, index) => (
                            <li key={index} className="truncate">
                              • {entry.relativePath}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-gray-200 pt-4">
                    <button
                      onClick={handleUpload}
                      disabled={uploading || selectedFiles.length === 0}
                      className={`px-4 py-2 text-sm font-medium rounded ${uploading || selectedFiles.length === 0 ? "bg-gray-300 cursor-not-allowed" : "bg-primary text-white hover:bg-orange-600"}`}
                    >
                      {uploading ? "Uploading..." : "Upload to Vault"}
                    </button>
                    {uploadStatus && (
                      <p
                        className={`text-sm mt-2 ${uploadStatus.includes("successful") ? "text-green-600" : "text-red-500"}`}
                      >
                        {uploadStatus}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaseDetailModal;
