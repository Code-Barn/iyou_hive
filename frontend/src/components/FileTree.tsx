import React, { useState } from 'react';
import './FileTree.css';

export interface FileNode {
  uuid: string;
  name: string;
  type: string;
  is_folder: boolean;
  children?: FileNode[];
  file_details?: {
    uuid: string;
    title: string;
    file_type: string;
    path: string;
    is_promoted: boolean;
    promoted_at: string | null;
    timeline_event_uuids: string[];
    trust_level: string;
  };
}

interface FileTreeProps {
  nodes: FileNode[];
  onFileSelect: (node: FileNode) => void;
  onFileDrop: (sourceUuid: string, targetUuid: string) => void;
  onPromote: (node: FileNode) => void;
}

const FileTreeNode: React.FC<{
  node: FileNode;
  level: number;
  onFileSelect: (node: FileNode) => void;
  onFileDrop: (sourceUuid: string, targetUuid: string) => void;
  onPromote: (node: FileNode) => void;
}> = ({ node, level, onFileSelect, onFileDrop, onPromote }) => {
  const [isOpen, setIsOpen] = useState(level === 0); // Root levels open by default

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('sourceUuid', node.uuid);
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (node.is_folder) {
      e.preventDefault();
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const sourceUuid = e.dataTransfer.getData('sourceUuid');
    if (sourceUuid && sourceUuid !== node.uuid) {
      onFileDrop(sourceUuid, node.uuid);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    if (!node.is_folder && !node.file_details?.is_promoted) {
      e.preventDefault();
      // Simple context menu logic could go here, or just trigger onPromote
      if (window.confirm(`Promote "${node.name}" to evidence?`)) {
        onPromote(node);
      }
    }
  };

  const icon = node.is_folder ? (isOpen ? '📂' : '📁') : '📄';
  const branchClass = node.name.includes('Vault') ? 'vault-branch' : node.name.includes('Workspace') ? 'workspace-branch' : '';

  return (
    <div className={`file-tree-node ${branchClass}`} style={{ paddingLeft: `${level * 16}px` }}>
      <div
        className={`node-content ${node.is_folder ? 'folder' : 'file'}`}
        onClick={() => node.is_folder ? handleToggle(null) : onFileSelect(node)}
        onDragStart={node.is_folder ? undefined : handleDragStart}
        draggable={!node.is_folder}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onContextMenu={handleContextMenu}
      >
        <span className="node-icon">{icon}</span>
        <span className="node-name">{node.name}</span>
        {node.file_details?.is_promoted && <span className="promoted-badge">⚖️</span>}
      </div>
      {node.is_folder && isOpen && node.children && (
        <div className="node-children">
          {node.children.map(child => (
            <FileTreeNode
              key={child.uuid}
              node={child}
              level={level + 1}
              onFileSelect={onFileSelect}
              onFileDrop={onFileDrop}
              onPromote={onPromote}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FileTree: React.FC<FileTreeProps> = ({ nodes, onFileSelect, onFileDrop, onPromote }) => {
  return (
    <div className="file-tree">
      {nodes.map(node => (
        <FileTreeNode
          key={node.uuid}
          node={node}
          level={0}
          onFileSelect={onFileSelect}
          onFileDrop={onFileDrop}
          onPromote={onPromote}
        />
      ))}
    </div>
  );
};
