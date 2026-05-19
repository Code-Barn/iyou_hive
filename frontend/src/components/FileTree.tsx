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

import React, { useState, useEffect } from "react";
import "./FileTree.css";
import { FileNode } from "../types/shared";

interface FileTreeProps {
  caseId: string;
  nodes?: FileNode[];
  onFileSelect: (node: FileNode) => void;
  onFileDrop: (sourceUuid: string, targetUuid: string) => void;
  onPromote: (node: FileNode) => void;
  onDocumentSelect?: (
    docUuid: string,
    docPath: string,
    docTitle: string,
  ) => void;
}

const FileTreeNode: React.FC<{
  node: FileNode;
  level: number;
  onFileSelect: (node: FileNode) => void;
  onFileDrop: (sourceUuid: string, targetUuid: string) => void;
  onPromote: (node: FileNode) => void;
  onDocumentSelect?: (docUuid: string) => void;
}> = ({
  node,
  level,
  onFileSelect,
  onFileDrop,
  onPromote,
  onDocumentSelect,
}) => {
  const [isOpen, setIsOpen] = useState(level === 0); // Root levels open by default

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  const handleClick = () => {
    if (node.is_folder) {
      setIsOpen(!isOpen);
    } else {
      onFileSelect(node);
      if (onDocumentSelect && node.file_details?.uuid) {
        onDocumentSelect(
          node.file_details.uuid,
          node.file_details.path || node.path,
          node.file_details.title || node.name,
        );
      }
    }
  };

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("sourceUuid", node.uuid);
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (node.is_folder) {
      e.preventDefault();
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const sourceUuid = e.dataTransfer.getData("sourceUuid");
    if (sourceUuid && node.is_folder) {
      onFileDrop(sourceUuid, node.uuid);
    }
  };

  const getIcon = () => {
    if (node.is_folder) return isOpen ? "📂" : "📁";
    const ext = node.name.split(".").pop()?.toLowerCase();
    if (["pdf"].includes(ext || "")) return "📄";
    if (["jpg", "jpeg", "png", "gif"].includes(ext || "")) return "🖼️";
    if (["doc", "docx"].includes(ext || "")) return "📝";
    return "📎";
  };

  const getVaultBadge = () => {
    const path = (node.path || "").toLowerCase();
    if (
      path.includes("/formal/") ||
      path.includes("01_raw") ||
      path.includes("04_strategy")
    ) {
      return (
        <span className="vault-badge vault-formal" title="Formal Vault">
          🔒
        </span>
      );
    }
    if (
      path.includes("/private/") ||
      path.includes("02_wiki") ||
      path.includes("03_drafts") ||
      path.includes("05_exports")
    ) {
      return (
        <span className="vault-badge vault-private" title="Private Workspace">
          ✏️
        </span>
      );
    }
    return null;
  };

  return (
    <div
      className={`file-tree-node ${node.is_folder ? "folder" : "file"} level-${level}`}
      draggable={!node.is_folder}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div
        className="node-content"
        style={{ paddingLeft: `${level * 20}px` }}
        onClick={handleClick}
      >
        <span className="node-icon">{getIcon()}</span>
        <span className="node-name">{node.name}</span>
        {node.file_details?.is_promoted && (
          <span className="promoted-badge">⚖️</span>
        )}
        {node.file_details?.has_md_twin && (
          <span
            className="twin-badge"
            title="Machine-Readable Version Available"
          >
            🤖
          </span>
        )}
        {getVaultBadge()}
      </div>
      {node.is_folder &&
        isOpen &&
        node.children &&
        Array.isArray(node.children) &&
        node.children.length > 0 && (
          <div className="node-children">
            {node.children.map((child) => (
              <FileTreeNode
                key={child.uuid}
                node={child}
                level={level + 1}
                onFileSelect={onFileSelect}
                onFileDrop={onFileDrop}
                onPromote={onPromote}
                onDocumentSelect={onDocumentSelect}
              />
            ))}
          </div>
        )}
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({
  caseId,
  nodes: initialNodes,
  onFileSelect,
  onFileDrop,
  onPromote,
  onDocumentSelect,
}) => {
  const [nodes, setNodes] = useState<FileNode[]>(initialNodes || []);
  const [loading, setLoading] = useState(!initialNodes);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialNodes) {
      setNodes(initialNodes);
      return;
    }

    // Fetch file tree if not provided
    const fetchFileTree = async () => {
      if (!caseId) return;

      setLoading(true);
      try {
        const res = await fetch(`/api/archive/directory/?case_id=${caseId}`, {
          credentials: "include",
        });
        if (!res.ok) {
          // Do NOT attempt to parse JSON on non-ok responses
          setNodes([]);
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        // Defensive guard: ensure data is an array
        setNodes(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to fetch file tree:", err);
        setError("Failed to load files");
        setNodes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFileTree();
  }, [caseId, initialNodes]);

  if (loading) return <div className="p-4 text-gray-500">Loading files...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (nodes.length === 0)
    return (
      <div className="p-4 text-gray-500">
        No files yet. Upload documents to get started.
      </div>
    );

  return (
    <div className="file-tree">
      {Array.isArray(nodes) &&
        nodes.map((node) => (
          <FileTreeNode
            key={node.uuid}
            node={node}
            level={0}
            onFileSelect={onFileSelect}
            onFileDrop={onFileDrop}
            onPromote={onPromote}
            onDocumentSelect={onDocumentSelect}
          />
        ))}
    </div>
  );
};

export default FileTree;
