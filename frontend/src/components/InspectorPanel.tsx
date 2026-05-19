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

import React from "react";
import { FileNode } from "./FileTree";
import "./InspectorPanel.css";

interface InspectorPanelProps {
  selectedFile: FileNode | null;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  selectedFile,
}) => {
  if (!selectedFile) {
    return (
      <div className="inspector-panel empty">
        <p>Select a file to view metadata</p>
      </div>
    );
  }

  const { file_details } = selectedFile;

  return (
    <div className="inspector-panel">
      <h3>File Inspector</h3>
      <div className="inspector-field">
        <label>Title:</label>
        <span>{selectedFile.name}</span>
      </div>
      <div className="inspector-field">
        <label>Type:</label>
        <span>{selectedFile.type}</span>
      </div>
      {file_details && (
        <>
          <div className="inspector-field">
            <label>Promoted:</label>
            <span
              className={
                file_details.is_promoted ? "status-promoted" : "status-private"
              }
            >
              {file_details.is_promoted ? "Yes (Vault)" : "No (Workspace)"}
            </span>
          </div>
          {file_details.promoted_at && (
            <div className="inspector-field">
              <label>Promoted At:</label>
              <span>{new Date(file_details.promoted_at).toLocaleString()}</span>
            </div>
          )}
          <div className="inspector-field">
            <label>Trust Level:</label>
            <span
              className={`trust-level trust-${file_details.trust_level.toLowerCase().replace(" ", "-")}`}
            >
              {file_details.trust_level}
            </span>
          </div>
          <div className="inspector-field">
            <label>Linked Events:</label>
            <div className="linked-events">
              {file_details.timeline_event_uuids &&
              Array.isArray(file_details.timeline_event_uuids) &&
              file_details.timeline_event_uuids.length > 0 ? (
                file_details.timeline_event_uuids.map((uuid) => (
                  <div key={uuid} className="event-link">
                    Event: {uuid.substring(0, 8)}...
                  </div>
                ))
              ) : (
                <span>No linked events</span>
              )}
            </div>
          </div>
          <div className="inspector-field">
            <label>Logical Path:</label>
            <span className="path-text">{file_details.path}</span>
          </div>
        </>
      )}
    </div>
  );
};
