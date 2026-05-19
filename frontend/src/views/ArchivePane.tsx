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

import React, { useEffect, useState } from "react";
import { FileTree, FileNode } from "../components/FileTree";
import { InspectorPanel } from "../components/InspectorPanel";
import { FileActions } from "../components/FileActions";
import { archiveApi } from "../api/archive";
import "./ArchivePane.css";

interface ArchivePaneProps {
  caseId: string;
}

const ArchivePane: React.FC<ArchivePaneProps> = ({ caseId }) => {
  const [nodes, setNodes] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDirectory = async () => {
    try {
      setLoading(true);
      const response = await archiveApi.getDirectoryTree(caseId);
      // Defensive guard: ensure data is an array
      const data = response.data;
      setNodes(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch directory tree:", err);
      setError("Failed to load archive directory.");
      setNodes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Only fetch if caseId is valid
    if (caseId && caseId !== "") {
      fetchDirectory();
    }
  }, [caseId]);

  const handleFileSelect = (node: FileNode) => {
    setSelectedFile(node);
  };

  const handleFileDrop = async (sourceUuid: string, targetUuid: string) => {
    try {
      await archiveApi.moveFile(sourceUuid, targetUuid);
      // Refresh tree after move
      await fetchDirectory();
    } catch (err) {
      console.error("Failed to move file:", err);
      alert("Failed to move file. Ensure you are moving a file to a folder.");
    }
  };

  const handlePromote = async (node: FileNode) => {
    if (!node.file_details) return;

    try {
      // Use the UUID from file_details to promote the document
      await archiveApi.promoteDocument(node.file_details.uuid);
      await fetchDirectory();
    } catch (err) {
      console.error("Failed to promote document:", err);
      alert("Failed to promote document.");
    }
  };

  return (
    <div className="archive-pane-container">
      <div className="archive-main">
        <header className="archive-header">
          <h2>Archive Explorer</h2>
          <button onClick={fetchDirectory} className="refresh-btn">
            Refresh
          </button>
        </header>

        {loading ? (
          <div className="archive-loading">Loading directory structure...</div>
        ) : error ? (
          <div className="archive-error">{error}</div>
        ) : (
          <div className="archive-content">
            {/* File Actions Toolbar */}
            <div className="archive-actions-toolbar mb-4">
              <FileActions caseId={caseId} onFileUploaded={fetchDirectory} />
            </div>

            <FileTree
              nodes={nodes}
              onFileSelect={handleFileSelect}
              onFileDrop={handleFileDrop}
              onPromote={handlePromote}
            />
          </div>
        )}
      </div>

      <InspectorPanel selectedFile={selectedFile} />
    </div>
  );
};

export default ArchivePane;
