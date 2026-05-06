import React from "react";
import { TimelineEvent, SourceParty } from "../types/timeline";

interface EventCardProps {
  event: TimelineEvent;
  userParty: SourceParty;
  onContest?: () => void;
  onSaveToCollection?: () => void;
  isContested?: boolean;
}

const statusColors: Record<string, string> = {
  UNDISPUTED: "bg-gray-100 border-gray-300",
  CONTESTED: "bg-yellow-100 border-yellow-400",
  REFUTED: "bg-red-100 border-red-400",
  STIPULATED: "bg-green-100 border-green-400",
  PENDING: "bg-blue-100 border-blue-400",
};

const partyColors: Record<SourceParty, string> = {
  CLIENT: "bg-blue-500",
  OPPOSING: "bg-red-500",
  NEUTRAL: "bg-gray-500",
  COURT: "bg-purple-500",
  WITNESS: "bg-green-500",
};

const EventCard: React.FC<EventCardProps> = ({
  event,
  userParty,
  onContest,
  onSaveToCollection,
  isContested = false,
}) => {
  const statusColor = statusColors[event.status] || "bg-gray-100";
  const partyColor = partyColors[event.source_party] || "bg-gray-500";
  const canContest = userParty !== event.source_party;
  const hasReplacesEvent = event.replaces_event !== null;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div
      className={`border rounded-lg p-4 ${statusColor} ${hasReplacesEvent ? "ring-2 ring-yellow-500" : ""}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-1 text-xs text-white rounded ${partyColor}`}
          >
            {event.source_party}
          </span>
          <span className="font-medium text-gray-800">{event.event}</span>
        </div>
        <div className="flex gap-1">
          {event.has_gold_seal && (
            <span
              className="text-xs bg-yellow-400 text-black px-2 py-1 rounded-full font-bold"
              title="Gold Seal: Court/Neutral Stipulated Fact"
            >
              🏆 Gold Seal
            </span>
          )}
          {hasReplacesEvent && (
            <span
              className="text-xs bg-yellow-500 text-white px-2 py-1 rounded"
              title="This event has a counter-claim"
            >
              Conflict
            </span>
          )}
          {canContest && onContest && (
            <button
              onClick={onContest}
              className="text-xs bg-gray-600 text-white px-2 py-1 rounded hover:bg-gray-700"
            >
              Contest
            </button>
          )}
          {onSaveToCollection && (
            <button
              onClick={onSaveToCollection}
              className="text-xs bg-primary text-white px-2 py-1 rounded hover:opacity-80"
              title="Save to Collection"
            >
              Save
            </button>
          )}
        </div>
      </div>

      <div className="text-sm text-gray-600 mb-2">
        <span>{formatDate(event.date)}</span>
        <span className="mx-2">|</span>
        <span className="capitalize">{event.category}</span>
      </div>

      {event.notes && (
        <div className="text-sm text-gray-700 mb-2">{event.notes}</div>
      )}

      {event.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {event.evidence.slice(0, 3).map((doc) => (
            <a
              key={doc.id}
              href={doc.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-white px-2 py-1 rounded border hover:bg-gray-50"
              title={doc.title}
            >
              📄 {doc.title.slice(0, 20)}
            </a>
          ))}
          {event.evidence.length > 3 && (
            <span className="text-xs text-gray-500">
              +{event.evidence.length - 3} more
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default EventCard;
