import React, { useEffect, useState } from "react";
import { FileTree, FileNode } from "../components/FileTree";
import { InspectorPanel } from "../components/InspectorPanel";
import { archiveApi } from "../api/archive";
import "./ArchivePane.css";

const ArchivePane: React.FC = () => {
  const [nodes, setNodes] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDirectory = async () => {
    try {
      setLoading(true);
      const response = await archiveApi.getDirectoryTree();
      setNodes(response.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch directory tree:", err);
      setError("Failed to load archive directory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDirectory();
  }, []);

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
