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
import { Case } from "../types/timeline";

interface CaseSelectorProps {
  currentCaseId: string;
  onCaseSelect: (caseId: string) => void;
}

const CaseSelector: React.FC<CaseSelectorProps> = ({
  currentCaseId,
  onCaseSelect,
}) => {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCaseName, setNewCaseName] = useState("");

  const fetchCases = () => {
    setLoading(true);
    fetch("/core/api/cases/", {
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) {
          setCases([]);
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        // API returns { cases: [...] } so we need to extract the array
        const casesArray = data.cases || data;
        // Defensive guard: ensure data is an array
        setCases(Array.isArray(casesArray) ? casesArray : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch cases:", err);
        setError("Failed to load cases");
        setCases([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleCreateCase = async () => {
    if (!newCaseName.trim()) return;

    try {
      const res = await fetch("/core/api/cases/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        credentials: "include",
        body: JSON.stringify({ name: newCaseName }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const responseData = await res.json();
      // API returns { status: 'success', case: {...} } for POST
      const newCase = responseData.case || responseData;

      if (newCase && newCase.id) {
        // Defensive guard: ensure cases is an array before spreading
        setCases(Array.isArray(cases) ? [...cases, newCase] : [newCase]);
        setNewCaseName("");
        setShowCreateForm(false);
        onCaseSelect(newCase.id); // Update global caseId state
        fetchCases(); // Re-fetch to ensure sync
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err) {
      console.error("Failed to create case:", err);
      setError("Failed to create case");
    }
  };

  const getCSRFToken = (): string | null => {
    const name = "hive_csrftoken";
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  };

  // Defensive guard: ensure cases is an array before calling .find()
  const currentCase = Array.isArray(cases)
    ? cases.find((c) => c.id === currentCaseId)
    : null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg border"
      >
        <span className="font-medium">
          {loading
            ? "Loading..."
            : currentCase
              ? currentCase.name
              : "Select Case"}
        </span>
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-1 w-64 bg-white border rounded-lg shadow-lg z-50">
          {loading && (
            <div className="p-3 text-sm text-gray-500">Loading cases...</div>
          )}
          {error && <div className="p-3 text-sm text-red-500">{error}</div>}
          {!loading && !error && cases.length === 0 && (
            <div className="p-3 text-sm text-gray-500">
              No cases found. Create one below.
            </div>
          )}
          {Array.isArray(cases) &&
            cases.map((caseItem) => (
              <button
                key={caseItem.id}
                onClick={() => {
                  onCaseSelect(caseItem.id);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 ${
                  caseItem.id === currentCaseId
                    ? "bg-blue-50 text-blue-700"
                    : ""
                }`}
              >
                {caseItem.name}
              </button>
            ))}
          <div className="border-t">
            {!showCreateForm ? (
              <button
                onClick={() => setShowCreateForm(true)}
                className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50"
              >
                + Create New Case
              </button>
            ) : (
              <div className="p-3">
                <input
                  type="text"
                  value={newCaseName}
                  onChange={(e) => setNewCaseName(e.target.value)}
                  placeholder="Case name..."
                  className="w-full px-2 py-1 text-sm border rounded"
                  autoFocus
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={handleCreateCase}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Create
                  </button>
                  <button
                    onClick={() => setShowCreateForm(false)}
                    className="px-3 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseSelector;
