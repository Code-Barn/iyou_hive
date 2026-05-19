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
import { useQuery } from "@tanstack/react-query";
import { timelineApi, collectionApi } from "../api/timeline";
import {
  TimelineEvent,
  TimelineCollection,
  TimelineFilters,
  SourceParty,
  Status,
  Category,
} from "../types/timeline";
import EventCard from "./EventCard";

interface SimplifiedViewProps {
  caseId: string;
  userParty: SourceParty;
  onEventAdded?: () => void;
}

const statusOptions: { value: Status; label: string; color: string }[] = [
  { value: "UNDISPUTED", label: "Undisputed", color: "bg-gray-100" },
  { value: "CONTESTED", label: "Contested", color: "bg-yellow-100" },
  { value: "REFUTED", label: "Refuted", color: "bg-red-100" },
  { value: "STIPULATED", label: "Stipulated", color: "bg-green-100" },
  { value: "PENDING", label: "Pending", color: "bg-blue-100" },
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

const SimplifiedView: React.FC<SimplifiedViewProps> = ({
  caseId,
  userParty,
}) => {
  const [filters, setFilters] = useState<TimelineFilters>({});
  const [selectedCollection, setSelectedCollection] = useState<string | null>(
    null,
  );
  const [collections, setCollections] = useState<TimelineCollection[]>([]);

  // Fetch collections for this case
  const { data: collectionsData } = useQuery<TimelineCollection[]>({
    queryKey: ["collections", caseId],
    enabled: !!caseId && caseId !== "",
    queryFn: async () => {
      try {
        const res = await collectionApi.getCollections(caseId);
        const data = res.data;
        // Defensive guard: ensure data is an array
        return Array.isArray(data) ? data : [];
      } catch (err) {
        console.error("Failed to fetch collections:", err);
        return []; // Return empty array on error
      }
    },
  });

  useEffect(() => {
    if (collectionsData) {
      setCollections(collectionsData);
    }
  }, [collectionsData]);

  // Fetch events with filters
  const {
    data: eventsData,
    isLoading,
    error,
    refetch,
  } = useQuery<TimelineEvent[]>({
    queryKey: ["events", caseId, filters, selectedCollection],
    enabled: !!caseId && caseId !== "",
    queryFn: async () => {
      try {
        let data = await timelineApi
          .getEvents(caseId, filters)
          .then((res) => res.data);

        // Defensive guard: ensure data is an array
        if (!Array.isArray(data)) {
          data = [];
        }

        // If a collection is selected, filter to only those events
        if (
          selectedCollection &&
          collectionsData &&
          Array.isArray(collectionsData)
        ) {
          const selected = collectionsData.find(
            (c) => c.id === selectedCollection,
          );
          if (selected && Array.isArray(selected.events)) {
            const collectionEventIds = new Set(
              selected.events.map((e) => e.id),
            );
            data = data.filter((e: TimelineEvent) =>
              collectionEventIds.has(e.id),
            );
          }
        }

        return data;
      } catch (err) {
        console.error("Failed to fetch events:", err);
        return []; // Return empty array on error
      }
    },
  });

  // No need for special handling - onEventAdded is called by parent
  // which will trigger queryClient.invalidateQueries
  // The useQuery will auto-refetch when invalidated

  const handleFilterChange = (
    key: keyof TimelineFilters,
    value: string | boolean | undefined,
  ) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleContest = (event: TimelineEvent) => {
    console.log("Contesting event:", event.id);
    // API call to contest the event
  };

  const handleSaveToCollection = (event: TimelineEvent) => {
    console.log("Saving event to collection:", event.id);
    // This would open a modal to select which collection
  };

  const clearFilters = () => {
    setFilters({});
    setSelectedCollection(null);
  };

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
        Error loading events: {(error as Error).message}
      </div>
    );
  }

  const events = eventsData || [];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-4">
        <h2 className="text-xl font-bold text-gray-800 mb-2">Timeline</h2>

        {/* Filter Bar */}
        <div className="bg-gray-50 p-3 rounded-lg mb-4">
          <div className="text-sm text-gray-600 mb-2">Filters:</div>
          <div className="flex flex-wrap gap-3 items-center">
            {/* Party Filter */}
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

            {/* Status Filter */}
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

            {/* Category Filter */}
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

            {/* Collection Filter */}
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

        <div className="text-sm text-gray-500">
          Showing{" "}
          <span className="font-medium text-gray-700">{events.length}</span>{" "}
          events
        </div>
      </div>

      {/* Events List - 3-Column Git Diff Layout */}
      <div className="flex-1 overflow-y-auto p-4">
        {!events || events.length === 0 ? (
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
                {Array.isArray(events) &&
                  events.map((event) => (
                    <tr
                      key={event.id}
                      className="border-b border-gray-100 hover:bg-gray-50"
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
                      <td className="p-2 text-gray-600 max-w-[400px] truncate">
                        {event.notes || "No details"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimplifiedView;
