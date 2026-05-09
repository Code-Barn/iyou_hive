import React, { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { timelineApi, collectionApi, diffApi } from "../api/timeline";
import {
  TimelineEvent,
  TimelineCollection,
  TimelineFilters,
  SourceParty,
  Status,
  Category,
  DiffViewData,
  ContestedPair,
} from "../types/timeline";
import EventCard from "./EventCard";
import ConflictResolverModal from "./ConflictResolverModal";
import TimelineEventModal from "./TimelineEventModal";
import { TimelineToolbar } from "./TimelineToolbar";

interface ForensicTimelineProps {
  caseId: string;
  userParty: SourceParty;
  onEventAdded?: () => void;
  isFullScreen?: boolean;
}

type ViewMode = "standard" | "diff";

const statusOptions: { value: Status; label: string }[] = [
  { value: "UNDISPUTED", label: "Undisputed" },
  { value: "CONTESTED", label: "Contested" },
  { value: "REFUTED", label: "Refuted" },
  { value: "STIPULATED", label: "Stipulated" },
  { value: "PENDING", label: "Pending" },
];

const categoryOptions: { value: Category; label: string }[] = [
  { value: "contract", label: "Contract" },
  { value: "email", label: "Email" },
  { value: "court_filing", label: "Court Filing" },
  { value: "communication", label: "Communication" },
  { value: "meeting", label: "Meeting" },
  { value: "deadline", label: "Deadline" },
  { value: "other", label: "Other" },
];

const partyOptions: { value: SourceParty; label: string; color: string }[] = [
  { value: "CLIENT", label: "Client", color: "bg-blue-500" },
  { value: "OPPOSING", label: "Opposing", color: "bg-red-500" },
  { value: "NEUTRAL", label: "Neutral", color: "bg-gray-500" },
  { value: "COURT", label: "Court", color: "bg-purple-500" },
  { value: "WITNESS", label: "Witness", color: "bg-green-500" },
];

const ForensicTimeline: React.FC<ForensicTimelineProps> = ({
  caseId,
  userParty,
  onEventAdded,
  isFullScreen = false,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("standard");
  const [filters, setFilters] = useState<TimelineFilters>({});
  const [selectedCollection, setSelectedCollection] = useState<string | null>(
    null,
  );
  const [collections, setCollections] = useState<TimelineCollection[]>([]);
  const [selectedConflict, setSelectedConflict] =
    useState<ContestedPair | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(
    null,
  );
  const [leftParty, setLeftParty] = useState<SourceParty>("CLIENT");
  const [rightParty, setRightParty] = useState<SourceParty>("OPPOSING");
  const queryClient = useQueryClient();

  // Fetch collections
  const { data: collectionsData } = useQuery<TimelineCollection[]>({
    queryKey: ["collections", caseId],
    enabled: !!caseId && caseId !== "",
    queryFn: async () => {
      try {
        const res = await collectionApi.getCollections(caseId);
        return Array.isArray(res.data) ? res.data : [];
      } catch {
        return [];
      }
    },
  });

  useEffect(() => {
    if (collectionsData) setCollections(collectionsData);
  }, [collectionsData]);

  // Fetch events (single source of truth)
  const {
    data: eventsData,
    isLoading: eventsLoading,
    error: eventsError,
    refetch: refetchEvents,
  } = useQuery<TimelineEvent[]>({
    queryKey: ["events", caseId, viewMode, filters, selectedCollection],
    enabled: !!caseId && caseId !== "",
    queryFn: async () => {
      try {
        // In Standard mode, show ALL events - no filters, no collection filtering
        // In Diff mode, apply filters
        const apiFilters = viewMode === "standard" ? {} : filters;
        // Add page_size=1000 to always display the entire dataset
        const fetchFilters = { ...apiFilters, page_size: 1000 };
        let data = await timelineApi
          .getEvents(caseId, fetchFilters)
          .then((res) => res.data);
        // Handle paginated response from DRF
        if (data && data.results && Array.isArray(data.results)) {
          data = data.results;
        } else if (!Array.isArray(data)) {
          data = [];
        }
        console.log("Raw Timeline Data:", data);
        // In Standard mode, don't filter by collection - show all events
        if (
          viewMode !== "standard" &&
          selectedCollection &&
          Array.isArray(collectionsData)
        ) {
          const selected = collectionsData.find(
            (c) => c.id === selectedCollection,
          );
          if (selected && Array.isArray(selected.events)) {
            const ids = new Set(selected.events.map((e) => e.id));
            data = data.filter((e: TimelineEvent) => ids.has(e.id));
          }
        }
        return data;
      } catch {
        return [];
      }
    },
  });

  // Fetch diff view data
  const {
    data: diffData,
    isLoading: diffLoading,
    error: diffError,
    refetch: refetchDiff,
  } = useQuery<DiffViewData>({
    queryKey: ["diffView", caseId, leftParty, rightParty],
    enabled: viewMode === "diff" && !!caseId && caseId !== "",
    queryFn: async () => {
      const res = await diffApi.getDiffView(caseId, leftParty, rightParty);
      return res.data;
    },
  });

  const handleEventAdded = () => {
    refetchEvents();
    if (viewMode === "diff") refetchDiff();
    onEventAdded?.();
  };

  const handleFilterChange = (
    key: keyof TimelineFilters,
    value: string | boolean | undefined,
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResolve = (resolution: any) => {
    setSelectedConflict(null);
    refetchEvents();
    refetchDiff();
  };

  const clearFilters = () => {
    setFilters({});
    setSelectedCollection(null);
  };

  const isLoading = viewMode === "standard" ? eventsLoading : diffLoading;
  const error = viewMode === "standard" ? eventsError : diffError;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 p-4">
        Error loading timeline: {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Timeline Toolbar - always visible at top */}
      <TimelineToolbar caseId={caseId} onEventAdded={handleEventAdded} />

      {/* View Toggle */}
      <div className="px-4 pb-2 flex items-center gap-2 border-b border-gray-200 bg-white">
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode("standard")}
            className={`px-3 py-1 text-sm rounded transition-colors ${
              viewMode === "standard"
                ? "bg-white text-gray-800 shadow"
                : "text-gray-600 hover:bg-gray-200"
            }`}
          >
            Standard
          </button>
          <button
            onClick={() => setViewMode("diff")}
            className={`px-3 py-1 text-sm rounded transition-colors ${
              viewMode === "diff"
                ? "bg-white text-gray-800 shadow"
                : "text-gray-600 hover:bg-gray-200"
            }`}
          >
            Git Diff
          </button>
        </div>

        {viewMode === "diff" && (
          <div className="flex gap-2 ml-4">
            <select
              value={leftParty}
              onChange={(e) => setLeftParty(e.target.value as SourceParty)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              {partyOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <span className="text-gray-400">vs</span>
            <select
              value={rightParty}
              onChange={(e) => setRightParty(e.target.value as SourceParty)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              {partyOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Standard View - 3-Column Table */}
      {viewMode === "standard" && (
        <>
          {/* Filter Bar */}
          <div className="bg-gray-50 p-3 border-b border-gray-200">
            <div className="text-sm text-gray-600 mb-2">
              Showing{" "}
              <span className="font-medium text-gray-800">
                {(eventsData || []).length}
              </span>{" "}
              events
            </div>
            <div className="flex flex-wrap gap-3 items-center">
              <select
                value={filters.party || ""}
                onChange={(e) =>
                  handleFilterChange(
                    "party",
                    (e.target.value as SourceParty) || undefined,
                  )
                }
                className="p-2 border rounded text-sm"
              >
                <option value="">All Parties</option>
                {partyOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={filters.status || ""}
                onChange={(e) =>
                  handleFilterChange(
                    "status",
                    (e.target.value as Status) || undefined,
                  )
                }
                className="p-2 border rounded text-sm"
              >
                <option value="">All Statuses</option>
                {statusOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={filters.category || ""}
                onChange={(e) =>
                  handleFilterChange(
                    "category",
                    (e.target.value as Category) || undefined,
                  )
                }
                className="p-2 border rounded text-sm"
              >
                <option value="">All Categories</option>
                {categoryOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={selectedCollection || ""}
                onChange={(e) => setSelectedCollection(e.target.value || null)}
                className="p-2 border rounded text-sm"
              >
                <option value="">All Events</option>
                {Array.isArray(collections) &&
                  collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.name} ({col.event_count})
                    </option>
                  ))}
              </select>
              <button
                onClick={clearFilters}
                className="text-sm bg-gray-300 text-gray-700 px-3 py-2 rounded hover:bg-gray-400"
              >
                Clear Filters
              </button>
            </div>
          </div>

          {/* Events List - 3-Column Table */}
          <div className="flex-1 overflow-y-auto p-4 bg-white">
            {(eventsData || []).length === 0 ? (
              <div className="text-gray-400 text-center py-8">
                No events match the current filters
              </div>
            ) : (
              <div className="w-full overflow-x-auto">
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="p-2 font-semibold text-gray-600 w-[120px]">
                        Date
                      </th>
                      <th className="p-2 font-semibold text-gray-600">
                        Event/Incident
                      </th>
                      <th className="p-2 font-semibold text-gray-600">
                        Change/Details
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(eventsData || []).map((event) => (
                      <tr
                        key={event.id}
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                        onClick={() => setSelectedEvent(event)}
                      >
                        <td className="p-2 whitespace-nowrap">
                          {event.date
                            ? new Date(event.date).toLocaleDateString()
                            : "N/A"}
                        </td>
                        <td className="p-2 font-medium">
                          {event.event}
                          {event.category && (
                            <span className="ml-2 text-xs bg-gray-100 px-2 py-1 rounded">
                              {event.category}
                            </span>
                          )}
                        </td>
                        {/* Notes column - responsive truncation */}
                        <td
                          className={`p-2 text-gray-600 ${isFullScreen ? "max-w-[400px]" : "max-w-[200px] truncate"}`}
                        >
                          {event.notes || "No details"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Diff View - Three Columns */}
      {viewMode === "diff" && diffData && (
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          <div className="border-b p-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              Legal Diff: {diffData.left_party} vs {diffData.right_party}
            </h2>
            <div className="text-sm text-gray-500">
              <span className="font-medium text-gray-700">
                {diffData.shared.length +
                  diffData.left_only.length +
                  diffData.right_only.length +
                  Object.keys(diffData.contested).length * 2}
              </span>{" "}
              total events |
              <span className="text-yellow-600">
                {Object.keys(diffData.contested).length} contested
              </span>{" "}
              |
              <span className="text-blue-600">
                {diffData.shared.length} shared
              </span>{" "}
              |
              <span className="text-green-600">
                {diffData.left_only.length} {diffData.left_party}
              </span>{" "}
              |
              <span className="text-red-600">
                {diffData.right_only.length} {diffData.right_party}
              </span>
            </div>
          </div>

          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 border-r">
              <h3 className="font-semibold text-lg mb-4 text-blue-600">
                {diffData.left_party} Only
              </h3>
              <div className="space-y-4">
                {diffData.left_only.length === 0 ? (
                  <div className="text-gray-400 text-center py-8">
                    No events unique to {diffData.left_party}
                  </div>
                ) : (
                  diffData.left_only.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      userParty={userParty}
                      onClick={() => setSelectedEvent(event)}
                    />
                  ))
                )}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 border-r">
              <h3 className="font-semibold text-lg mb-4 text-gray-700">
                Shared / Undisputed
              </h3>
              <div className="space-y-4">
                {diffData.shared.length === 0 ? (
                  <div className="text-gray-400 text-center py-8">
                    No shared events
                  </div>
                ) : (
                  diffData.shared.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      userParty={userParty}
                      onClick={() => setSelectedEvent(event)}
                    />
                  ))
                )}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="font-semibold text-lg mb-4 text-red-600">
                {diffData.right_party} Only
              </h3>
              <div className="space-y-4">
                {diffData.right_only.length === 0 ? (
                  <div className="text-gray-400 text-center py-8">
                    No events unique to {diffData.right_party}
                  </div>
                ) : (
                  diffData.right_only.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      userParty={userParty}
                      onClick={() => setSelectedEvent(event)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {Object.keys(diffData.contested).length > 0 && (
            <div className="border-t p-4">
              <h3 className="font-semibold text-lg mb-4 text-yellow-600">
                Contested Events ({Object.keys(diffData.contested).length})
              </h3>
              <div className="space-y-4">
                {Object.entries(diffData.contested).map(([key, pair]) => (
                  <div
                    key={key}
                    className="border border-yellow-300 rounded-lg p-4 bg-yellow-50"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-yellow-800">
                        {pair.left.event} - {pair.left.date}
                      </span>
                      <button
                        onClick={() => setSelectedConflict(pair)}
                        className="text-xs bg-yellow-600 text-white px-3 py-1 rounded hover:bg-yellow-700"
                      >
                        Resolve Conflict
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-gray-500 mb-1">
                          {diffData.left_party} Version
                        </div>
                        <EventCard
                          event={pair.left}
                          userParty={userParty}
                          isContested={true}
                          onClick={() => setSelectedEvent(pair.left)}
                        />
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 mb-1">
                          {diffData.right_party} Version
                        </div>
                        <EventCard
                          event={pair.right}
                          userParty={userParty}
                          isContested={true}
                          onClick={() => setSelectedEvent(pair.right)}
                        />
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-gray-600">
                      Differences:{" "}
                      {Object.entries(pair.diff)
                        .filter(([_, diff]) => diff)
                        .map(([field]) => field)
                        .join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Event Inspector Modal */}
      {selectedEvent && (
        <TimelineEventModal
          event={selectedEvent}
          caseId={caseId}
          onClose={() => setSelectedEvent(null)}
          onEventUpdated={(updated) => {
            setSelectedEvent(null);
            refetchEvents();
            if (viewMode === "diff") refetchDiff();
            queryClient.invalidateQueries({ queryKey: ["events"] });
            queryClient.invalidateQueries({ queryKey: ["directory"] });
            onEventAdded?.();
          }}
        />
      )}

      {/* Conflict Resolver Modal */}
      {selectedConflict && (
        <ConflictResolverModal
          conflict={selectedConflict}
          leftParty={leftParty}
          rightParty={rightParty}
          onClose={() => setSelectedConflict(null)}
          onResolve={handleResolve}
        />
      )}
    </div>
  );
};

export default ForensicTimeline;
