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
import { diffApi } from "../api/timeline";
import {
  DiffViewData,
  TimelineEvent,
  SourceParty,
  ContestedPair,
} from "../types/timeline";
import EventCard from "./EventCard";
import ConflictResolverModal from "./ConflictResolverModal";
import { TimelineToolbar } from "./TimelineToolbar";

interface DiffViewProps {
  caseId: string;
  userParty: SourceParty;
  leftParty?: SourceParty;
  rightParty?: SourceParty;
}

const DiffView: React.FC<DiffViewProps> = ({
  caseId,
  userParty,
  leftParty = "CLIENT",
  rightParty = "OPPOSING",
}) => {
  const [selectedConflict, setSelectedConflict] =
    useState<ContestedPair | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(
    null,
  );

  const { data, isLoading, error, refetch } = useQuery<DiffViewData>({
    queryKey: ["diffView", caseId, leftParty, rightParty],
    queryFn: () =>
      diffApi
        .getDiffView(caseId, leftParty, rightParty)
        .then((res) => res.data),
  });

  const handleContest = (event: TimelineEvent) => {
    // Create counter-claim
    console.log("Contesting event:", event.id);
    // API call would go here
  };

  const handleSaveToCollection = (event: TimelineEvent) => {
    console.log("Saving event to collection:", event.id);
    // Open collection dropdown or add to selected collection
  };

  const handleResolve = (resolution: any) => {
    console.log("Resolving conflict with resolution:", resolution);
    setSelectedConflict(null);
    refetch();
  };

  const handleOpenCollectionDropdown = (
    e: React.MouseEvent,
    event: TimelineEvent,
  ) => {
    e.stopPropagation();
    // Open dropdown logic would go here
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
        Error loading diff view: {(error as Error).message}
      </div>
    );
  }

  if (!data) {
    return <div className="p-4">No data available</div>;
  }

  // Count stats
  const totalEvents =
    data.shared.length +
    data.left_only.length +
    data.right_only.length +
    Object.keys(data.contested).length * 2;

  return (
    <div className="flex flex-col h-full">
      {/* Timeline Toolbar */}
      <TimelineToolbar caseId={caseId} onEventAdded={refetch} />

      {/* Header */}
      <div className="border-b p-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">
          Legal Diff: {data.left_party} vs {data.right_party}
        </h2>
        <div className="text-sm text-gray-500">
          <span className="font-medium text-gray-700">{totalEvents}</span> total
          events |
          <span className="text-yellow-600">
            {Object.keys(data.contested).length} contested
          </span>{" "}
          |<span className="text-blue-600">{data.shared.length} shared</span> |
          <span className="text-green-600">
            {data.left_only.length} {data.left_party}
          </span>{" "}
          |
          <span className="text-red-600">
            {data.right_only.length} {data.right_party}
          </span>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column: Client */}
        <div className="flex-1 overflow-y-auto p-4 border-r">
          <h3 className="font-semibold text-lg mb-4 text-blue-600">
            {data.left_party} Only
          </h3>
          <div className="space-y-4">
            {data.left_only.length === 0 && (
              <div className="text-gray-400 text-center py-8">
                No events unique to {data.left_party}
              </div>
            )}
            {data.left_only.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                userParty={userParty}
                onContest={() => handleContest(event)}
                onSaveToCollection={() => handleSaveToCollection(event)}
              />
            ))}
          </div>
        </div>

        {/* Center Column: Shared/Undisputed */}
        <div className="flex-1 overflow-y-auto p-4 border-r">
          <h3 className="font-semibold text-lg mb-4 text-gray-700">
            Shared / Undisputed
          </h3>
          <div className="space-y-4">
            {data.shared.length === 0 && (
              <div className="text-gray-400 text-center py-8">
                No shared events
              </div>
            )}
            {data.shared.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                userParty={userParty}
                onSaveToCollection={() => handleSaveToCollection(event)}
              />
            ))}
          </div>
        </div>

        {/* Right Column: Opposing */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="font-semibold text-lg mb-4 text-red-600">
            {data.right_party} Only
          </h3>
          <div className="space-y-4">
            {data.right_only.length === 0 && (
              <div className="text-gray-400 text-center py-8">
                No events unique to {data.right_party}
              </div>
            )}
            {data.right_only.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                userParty={userParty}
                onContest={() => handleContest(event)}
                onSaveToCollection={() => handleSaveToCollection(event)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Contested Events Section */}
      {Object.keys(data.contested).length > 0 && (
        <div className="border-t p-4">
          <h3 className="font-semibold text-lg mb-4 text-yellow-600">
            Contested Events ({Object.keys(data.contested).length})
          </h3>
          <div className="space-y-4">
            {Object.entries(data.contested).map(([key, pair]) => (
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
                      {data.left_party} Version
                    </div>
                    <EventCard
                      event={pair.left}
                      userParty={userParty}
                      isContested={true}
                    />
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">
                      {data.right_party} Version
                    </div>
                    <EventCard
                      event={pair.right}
                      userParty={userParty}
                      isContested={true}
                    />
                  </div>
                </div>
                <div className="mt-2 text-xs text-gray-600">
                  Differences:
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

      {/* Conflict Resolver Modal */}
      {selectedConflict && (
        <ConflictResolverModal
          conflict={selectedConflict}
          leftParty={data.left_party}
          rightParty={data.right_party}
          onClose={() => setSelectedConflict(null)}
          onResolve={handleResolve}
        />
      )}
    </div>
  );
};

export default DiffView;
