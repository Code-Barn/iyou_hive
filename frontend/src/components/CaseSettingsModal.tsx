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

import React, { useState } from "react";
import { timelineApi } from "../api/timeline";

interface CaseSettingsModalProps {
  caseId: string;
  onClose: () => void;
  onEventAdded?: () => void;
}

export const CaseSettingsModal: React.FC<CaseSettingsModalProps> = ({
  caseId,
  onClose,
  onEventAdded,
}) => {
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importStatus, setImportStatus] = useState<
    "idle" | "importing" | "success" | "error"
  >("idle");
  const [importError, setImportError] = useState<string>("");

  // Handle .hive import
  const handleImportHive = async () => {
    if (!importFile || !caseId) return;

    setImportStatus("importing");
    setImportError("");

    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const response = await timelineApi.importHive(caseId, formData);

      if (response.data.status === "success") {
        setImportStatus("success");
        onEventAdded?.();
        setTimeout(() => {
          setIsImportModalOpen(false);
          setImportStatus("idle");
          setImportFile(null);
        }, 2000);
      } else {
        setImportStatus("error");
        setImportError(response.data.error || "Failed to import .hive file");
      }
    } catch (error) {
      console.error("Import failed:", error);
      setImportStatus("error");
      setImportError("Failed to import .hive file. Please try again.");
    }
  };

  // Handle .hive export
  const handleExportHive = async () => {
    if (!caseId) return;

    setIsExporting(true);

    try {
      const response = await timelineApi.exportHive(caseId, false);

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `timeline_${caseId}.hive`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
      alert("Failed to export .hive file. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-800">Case Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="font-semibold text-gray-700 mb-3">Hive Bundle</h3>
            <div className="space-y-2">
              <button
                onClick={() => setIsImportModalOpen(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <span>📥</span> Import .hive
              </button>
              <button
                onClick={handleExportHive}
                disabled={isExporting}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                <span>📤</span> {isExporting ? "Exporting..." : "Export .hive"}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Import/Export timeline data and documents as a .hive bundle
            </p>
          </div>
        </div>

        <div className="flex justify-end mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            Close
          </button>
        </div>
      </div>

      {/* Import .hive Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Import .hive Bundle</h2>
              <button
                onClick={() => {
                  setIsImportModalOpen(false);
                  setImportStatus("idle");
                  setImportError("");
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="mb-4">
              <p className="text-gray-600 mb-2">
                Import a .hive bundle to restore timeline and documents
              </p>
              <input
                type="file"
                accept=".hive"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                className="w-full border border-gray-300 rounded-lg p-2"
              />
            </div>

            {importStatus === "importing" && (
              <div className="mb-4 p-3 bg-blue-100 rounded-lg">
                <p className="text-blue-700">Importing .hive bundle...</p>
              </div>
            )}

            {importStatus === "success" && (
              <div className="mb-4 p-3 bg-green-100 rounded-lg">
                <p className="text-green-700">Import successful!</p>
              </div>
            )}

            {importStatus === "error" && importError && (
              <div className="mb-4 p-3 bg-red-100 rounded-lg">
                <p className="text-red-700">Error: {importError}</p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsImportModalOpen(false);
                  setImportStatus("idle");
                  setImportError("");
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleImportHive}
                disabled={importStatus === "importing" || !importFile}
                className={`px-4 py-2 ${importStatus === "importing" || !importFile ? "bg-purple-300" : "bg-purple-600 hover:bg-purple-700"} text-white rounded-lg transition-colors`}
              >
                {importStatus === "importing" ? "Importing..." : "Import"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseSettingsModal;
