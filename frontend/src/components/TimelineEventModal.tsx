import React, { useState, useEffect } from "react";
import { timelineApi } from "../api/timeline";
import { TimelineEvent, SourceParty, Status } from "../types/timeline";

interface TimelineEventModalProps {
  event: TimelineEvent;
  caseId: string;
  onClose: () => void;
  onEventUpdated: (updatedEvent: TimelineEvent) => void;
}

const partyOptions: { value: SourceParty; label: string }[] = [
  { value: "CLIENT", label: "Client" },
  { value: "OPPOSING", label: "Opposing" },
  { value: "NEUTRAL", label: "Neutral" },
  { value: "COURT", label: "Court" },
  { value: "WITNESS", label: "Witness" },
];

const statusOptions: { value: Status; label: string }[] = [
  { value: "UNDISPUTED", label: "Undisputed" },
  { value: "CONTESTED", label: "Contested" },
  { value: "REFUTED", label: "Refuted" },
  { value: "STIPULATED", label: "Stipulated" },
  { value: "PENDING", label: "Pending" },
];

const TimelineEventModal: React.FC<TimelineEventModalProps> = ({
  event,
  caseId,
  onClose,
  onEventUpdated,
}) => {
  const [editedEvent, setEditedEvent] = useState<TimelineEvent>({ ...event });
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const handleFieldChange = (
    field: keyof TimelineEvent,
    value: string | SourceParty | Status,
  ) => {
    setEditedEvent((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    if (!editedEvent.id) return;

    setSaving(true);
    setSaveStatus(null);

    try {
      const changes = {
        source_party: editedEvent.source_party,
        status: editedEvent.status,
      };

      const response = await timelineApi.updateEvent(caseId, editedEvent.id, changes);
      onEventUpdated(response.data);
      setSaveStatus("Saved successfully!");

      // Close after a brief delay to show success message
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error: any) {
      const message =
        error.response?.data?.error ||
        error.response?.data?.message ||
        "Failed to save changes";
      console.error("Save failed:", error.response?.data || error);
      setSaveStatus(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-auto">
        <div className="bg-gray-800 text-white px-6 py-4 flex items-center justify-between rounded-t-lg">
          <h2 className="text-xl font-semibold">Event Inspector</h2>
          <button onClick={onClose} className="text-2xl hover:text-gray-300">
            ×
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Date - Read Only */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700 block">Date</label>
            <div className="p-2 border border-gray-300 rounded bg-gray-50">
              {event.date ? new Date(event.date).toLocaleDateString() : "N/A"}
            </div>
          </div>

          {/* Event Text - Read Only */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700 block">Event</label>
            <div className="p-2 border border-gray-300 rounded bg-gray-50 whitespace-pre-wrap">
              {event.event}
            </div>
          </div>

          {/* Source Party - Editable Dropdown */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700 block">
              Source Party
            </label>
            <select
              value={editedEvent.source_party || ""}
              onChange={(e) => handleFieldChange("source_party", e.target.value as SourceParty)}
              className="w-full p-2 border border-gray-300 rounded bg-white"
            >
              {partyOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status - Editable Dropdown */}
          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700 block">Status</label>
            <select
              value={editedEvent.status || ""}
              onChange={(e) => handleFieldChange("status", e.target.value as Status)}
              className="w-full p-2 border border-gray-300 rounded bg-white"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Evidence Links - Read Only */}
          {event.evidence && event.evidence.length > 0 && (
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 block">
                Linked Evidence ({event.evidence.length})
              </label>
              <div className="p-2 border border-gray-300 rounded bg-gray-50">
                <div className="space-y-1">
                  {event.evidence.map((doc: any) => (
                    <div
                      key={doc.uuid || doc.id}
                      className="text-sm text-gray-600 flex items-center gap-2"
                    >
                      <span>📄</span>
                      <span>{doc.title || doc.filename || `File ${doc.id}`}</span>
                      <span className="text-xs text-gray-400">
                        ({doc.uuid ? doc.uuid.slice(0, 8) : doc.id})
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {saveStatus && (
            <div
              className={`text-sm p-2 rounded ${
                saveStatus.includes("successfully")
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {saveStatus}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 text-sm font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className={`px-4 py-2 text-sm font-medium rounded ${
                saving
                  ? "bg-blue-300 cursor-not-allowed"
                  : "bg-primary text-white hover:bg-orange-600"
              }`}
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimelineEventModal;
