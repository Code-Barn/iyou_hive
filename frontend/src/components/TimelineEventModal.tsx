import React, { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
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
  const queryClient = useQueryClient();
  const [editedEvent, setEditedEvent] = useState<TimelineEvent>({ ...event });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
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

      const response = await timelineApi.updateEvent(
        caseId,
        editedEvent.id,
        changes,
      );
      onEventUpdated(response.data);
      setSaveStatus("Saved successfully!");
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["diffView"] });

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

  const handleDelete = async () => {
    if (!event.id) return;

    const confirmed = window.confirm(
      "Are you sure? This will remove this claim from the truth graph.",
    );
    if (!confirmed) return;

    setDeleting(true);
    setSaveStatus(null);

    try {
      await timelineApi.deleteEvent(caseId, event.id);
      setSaveStatus("Event deleted successfully!");
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["diffView"] });

      setTimeout(() => {
        onClose();
        onEventUpdated(event); // Trigger parent refresh
      }, 1000);
    } catch (error: any) {
      const message =
        error.response?.data?.error ||
        error.response?.data?.message ||
        "Failed to delete event";
      console.error("Delete failed:", error.response?.data || error);
      setSaveStatus(message);
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-auto">
        {/* Header: Date and Event Title */}
        <div className="bg-gray-800 text-white px-6 py-4 flex items-center justify-between rounded-t-lg">
          <div className="flex-1 min-w-0">
            <div className="text-sm text-gray-300">
              {formatDate(event.date)}
            </div>
            <h2 className="text-xl font-semibold truncate">{event.event}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-2xl hover:text-gray-300 ml-4"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Body Section 1: Context - Event Text and Notes */}
          <div className="border-b pb-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              Context
            </h3>

            {/* Event Text - Large readable display */}
            <div className="mb-4">
              <label className="text-sm font-medium text-gray-600 block mb-1">
                Event Description
              </label>
              <div className="p-4 border border-gray-200 rounded bg-gray-50 whitespace-pre-wrap text-gray-800">
                {event.event || "No description"}
              </div>
            </div>

            {/* Notes */}
            {event.notes && (
              <div>
                <label className="text-sm font-medium text-gray-600 block mb-1">
                  Notes
                </label>
                <div className="p-4 border border-gray-200 rounded bg-gray-50 whitespace-pre-wrap text-gray-700">
                  {event.notes}
                </div>
              </div>
            )}
          </div>

          {/* Body Section 2: Evidence - Linked Documents */}
          <div className="border-b pb-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              Evidence Links
            </h3>
            {event.evidence && event.evidence.length > 0 ? (
              <div className="space-y-2">
                {(event.evidence as any[]).map((doc) => (
                  <button
                    key={doc.uuid || doc.id}
                    onClick={() => {
                      // Open document in Archive Preview
                      // This would need to be handled by the parent Layout
                      // For now, just log the document UUID
                      console.log("Open document:", doc.uuid || doc.id);
                    }}
                    className="w-full flex items-center gap-3 p-3 border border-gray-200 rounded hover:bg-gray-50 transition-colors text-left"
                  >
                    <span>📄</span>
                    <span className="text-sm text-gray-800 flex-1">
                      {doc.title || doc.filename || `Document ${doc.id}`}
                    </span>
                    <span className="text-xs text-gray-500">
                      {doc.path
                        ? doc.path.split("/").slice(-2).join("/")
                        : doc.uuid?.slice(0, 8)}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                No evidence linked to this event
              </p>
            )}
          </div>

          {/* Edit Controls: Source Party and Status */}
          <div className="border-b pb-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Edit</h3>
            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700 block">
                  Source Party
                </label>
                <select
                  value={editedEvent.source_party || ""}
                  onChange={(e) =>
                    handleFieldChange(
                      "source_party",
                      e.target.value as SourceParty,
                    )
                  }
                  className="w-full p-2 border border-gray-300 rounded bg-white"
                >
                  {partyOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700 block">
                  Status
                </label>
                <select
                  value={editedEvent.status || ""}
                  onChange={(e) =>
                    handleFieldChange("status", e.target.value as Status)
                  }
                  className="w-full p-2 border border-gray-300 rounded bg-white"
                >
                  {statusOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Status Message */}
          {saveStatus && (
            <div
              className={`text-sm p-3 rounded ${
                saveStatus.includes("successfully")
                  ? "bg-green-50 text-green-700"
                  : "bg-red-50 text-red-700"
              }`}
            >
              {saveStatus}
            </div>
          )}

          {/* Action Buttons: Save and Delete */}
          <div className="flex justify-between items-center gap-4 pt-4">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-sm font-medium text-red-600 border border-red-200 bg-red-50 hover:bg-red-100 px-4 py-2 rounded transition-colors"
            >
              {deleting ? "Deleting..." : "Delete Event"}
            </button>
            <div className="flex gap-3">
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
    </div>
  );
};

export default TimelineEventModal;
