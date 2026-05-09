import React, { useState, useEffect, useRef } from "react";
import CaseSelector from "./CaseSelector";
import FileTree from "./FileTree";
import AIAssistantChat from "./AIAssistantChat";
import DocumentPreviewModal from "./DocumentPreviewModal";
import ForensicTimeline from "./ForensicTimeline";
import CaseSettingsModal from "./CaseSettingsModal";
import CaseDetailModal from "./CaseDetailModal";
import { SourceParty } from "../types/shared";

// Helper to get CSRF token for POST requests
function getCSRFToken(): string {
  const name = "csrftoken";
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
  }
  return "";
}

// POST Logout handler - Fix 405 Error
const handleLogout = () => {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/accounts/logout/";
  const csrfInput = document.createElement("input");
  csrfInput.type = "hidden";
  csrfInput.name = "csrfmiddlewaretoken";
  csrfInput.value = getCSRFToken() || "";
  form.appendChild(csrfInput);
  document.body.appendChild(form);
  form.submit();
};

interface LayoutProps {
  caseId: string;
  userParty: SourceParty;
  onCaseSelect: (caseId: string) => void;
  onEventAdded?: () => void;
}

// Minimum panel width as percentage
const MIN_PANEL_PERCENT = 10;
// Default panel sizes
const DEFAULT_LEFT = 33;
const DEFAULT_CENTER = 34;
const DEFAULT_RIGHT = 33;
// Default horizontal split in center panel (tree on top)
const DEFAULT_HORIZONTAL_SPLIT = 0.4;

const Layout: React.FC<LayoutProps> = ({
  caseId,
  userParty,
  onCaseSelect,
  onEventAdded,
}) => {
  const mainRef = useRef<HTMLDivElement>(null);
  const [previewDocUuid, setPreviewDocUuid] = useState<string | null>(null);
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);

  // Panel expanded/collapsed state
  const [leftExpanded, setLeftExpanded] = useState(true);
  const [centerExpanded, setCenterExpanded] = useState(true);
  const [rightExpanded, setRightExpanded] = useState(true);

  // Panel width percentages (stored for restoration when re-expanded)
  const [panelSizes, setPanelSizes] = useState({
    left: DEFAULT_LEFT,
    center: DEFAULT_CENTER,
    right: DEFAULT_RIGHT,
  });

  // Horizontal split ratio in center panel (tree on top, canvas on bottom)
  const [horizontalSplit, setHorizontalSplit] = useState(
    DEFAULT_HORIZONTAL_SPLIT,
  );

  // Track which panels are currently being dragged
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);
  const [isDraggingHorizontal, setIsDraggingHorizontal] = useState(false);

  // Modal states
  const [isFullTimelineOpen, setIsFullTimelineOpen] = useState(false);
  const [isArchiveFullScreen, setIsArchiveFullScreen] = useState(false);
  const [isAIFullScreen, setIsAIFullScreen] = useState(false);
  const [isCaseSettingsOpen, setIsCaseSettingsOpen] = useState(false);
  const [aiSettingsOpen, setAiSettingsOpen] = useState(false);
  const [isCaseDetailOpen, setIsCaseDetailOpen] = useState(false);

  // Load saved panel sizes from localStorage
  useEffect(() => {
    if (!caseId) return;

    try {
      const savedSizes = localStorage.getItem(`panel-sizes-${caseId}`);
      if (savedSizes) {
        setPanelSizes(JSON.parse(savedSizes));
      }

      const savedSplit = localStorage.getItem(`panel-horizontal-${caseId}`);
      if (savedSplit) {
        setHorizontalSplit(parseFloat(savedSplit));
      }
    } catch {
      // ignore
    }
  }, [caseId]);

  // Save panel sizes to localStorage
  useEffect(() => {
    if (!caseId) return;

    try {
      localStorage.setItem(`panel-sizes-${caseId}`, JSON.stringify(panelSizes));
      localStorage.setItem(
        `panel-horizontal-${caseId}`,
        horizontalSplit.toString(),
      );
    } catch {
      // ignore
    }
  }, [panelSizes, horizontalSplit, caseId]);

  // Handle URL routing for document preview
  useEffect(() => {
    const match = window.location.pathname.match(
      /\/cases\/([^\/]+)\/preview\/([^\/]+)/,
    );
    if (match && match[1] === caseId) {
      setPreviewDocUuid(match[2]);
    }
  }, [caseId]);

  // Handle document selection from FileTree
  const handleDocumentSelect = (docUuid: string) => {
    setPreviewDocUuid(docUuid);
    const newUrl = `/cases/${caseId}/preview/${docUuid}`;
    window.history.pushState({}, "", newUrl);
  };

  const handleClosePreview = () => {
    setPreviewDocUuid(null);
    window.history.pushState({}, "", `/cases/${caseId}`);
  };

  // Handle left divider drag
  const handleLeftDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingLeft(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!mainRef.current) return;

      const containerWidth = mainRef.current.offsetWidth;
      const containerRect = mainRef.current.getBoundingClientRect();
      const x = moveEvent.clientX - containerRect.left;

      // Calculate new left width percentage
      const newLeftPercent = (x / containerWidth) * 100;

      // Ensure minimum widths
      if (newLeftPercent < MIN_PANEL_PERCENT) return;
      const remaining = 100 - newLeftPercent;
      if (remaining < MIN_PANEL_PERCENT * 2) return;

      // Distribute remaining between center and right proportionally
      const ratio = panelSizes.center / (panelSizes.center + panelSizes.right);
      const newCenterPercent = ratio * remaining;
      const newRightPercent = remaining - newCenterPercent;

      setPanelSizes({
        left: newLeftPercent,
        center: newCenterPercent,
        right: newRightPercent,
      });
    };

    const handleMouseUp = () => {
      setIsDraggingLeft(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  // Handle right divider drag
  const handleRightDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingRight(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!mainRef.current) return;

      const containerWidth = mainRef.current.offsetWidth;
      const containerRect = mainRef.current.getBoundingClientRect();
      const x = moveEvent.clientX - containerRect.left;

      // Calculate new right width based on mouse position
      const newRightPercent = ((containerWidth - x) / containerWidth) * 100;

      // Ensure minimum widths
      if (newRightPercent < MIN_PANEL_PERCENT) return;
      const remaining = 100 - newRightPercent;
      if (remaining < MIN_PANEL_PERCENT * 2) return;

      // Distribute remaining between left and center proportionally
      const ratio = panelSizes.left / (panelSizes.left + panelSizes.center);
      const newLeftPercent = ratio * remaining;
      const newCenterPercent = remaining - newLeftPercent;

      setPanelSizes({
        left: newLeftPercent,
        center: newCenterPercent,
        right: newRightPercent,
      });
    };

    const handleMouseUp = () => {
      setIsDraggingRight(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  // Handle horizontal divider drag (in center panel)
  const handleHorizontalDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingHorizontal(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!mainRef.current) return;

      const centerPanel = mainRef.current.querySelector(".center-panel");
      if (!centerPanel) return;

      const centerRect = centerPanel.getBoundingClientRect();
      const y = moveEvent.clientY - centerRect.top;
      const centerHeight = centerRect.height;

      // Calculate new ratio (clamped between 0.1 and 0.9)
      const newRatio = Math.max(0.1, Math.min(0.9, y / centerHeight));
      setHorizontalSplit(newRatio);
    };

    const handleMouseUp = () => {
      setIsDraggingHorizontal(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  // Toggle panel collapse/expand
  const toggleLeft = () => setLeftExpanded(!leftExpanded);
  const toggleCenter = () => setCenterExpanded(!centerExpanded);
  const toggleRight = () => setRightExpanded(!rightExpanded);

  // Calculate panel styles based on expanded state
  // When panels are collapsed, use flex-grow for elastic behavior
  const getPanelStyle = (panel: "left" | "center" | "right") => {
    const expandedCount =
      (leftExpanded ? 1 : 0) +
      (centerExpanded ? 1 : 0) +
      (rightExpanded ? 1 : 0);

    if (!centerExpanded) {
      // Center is the anchor - if it's collapsed, show collapsed tab
      return { width: "12px" };
    }

    if (panel === "center") {
      // Center panel: use flex-grow when side panels are collapsed
      if (expandedCount === 1) {
        // Only center is expanded
        return { flex: "1 1 100%", minWidth: 0 };
      } else if (expandedCount === 2 && !leftExpanded) {
        // Center and right expanded
        const centerPercent =
          panelSizes.center / (panelSizes.center + panelSizes.right);
        return { flex: `1 1 ${centerPercent * 100}%`, minWidth: 0 };
      } else if (expandedCount === 2 && !rightExpanded) {
        // Left and center expanded
        const centerPercent =
          panelSizes.center / (panelSizes.left + panelSizes.center);
        return { flex: `1 1 ${centerPercent * 100}%`, minWidth: 0 };
      } else {
        // All three expanded
        return { flex: `1 1 ${panelSizes.center}%`, minWidth: 0 };
      }
    }

    if (panel === "left" && leftExpanded) {
      if (expandedCount === 1) {
        return { width: "12px" };
      } else if (expandedCount === 2 && !rightExpanded) {
        const leftPercent =
          panelSizes.left / (panelSizes.left + panelSizes.center);
        return { width: `${leftPercent * 100}%`, minWidth: 0 };
      } else {
        return { width: `${panelSizes.left}%`, minWidth: 0 };
      }
    }

    if (panel === "right" && rightExpanded) {
      if (expandedCount === 1) {
        return { width: "12px" };
      } else if (expandedCount === 2 && !leftExpanded) {
        const rightPercent =
          panelSizes.right / (panelSizes.center + panelSizes.right);
        return { width: `${rightPercent * 100}%`, minWidth: 0 };
      } else {
        return { width: `${panelSizes.right}%`, minWidth: 0 };
      }
    }

    return { width: "12px" };
  };

  return (
    <div className="h-screen flex flex-col bg-white text-gray-900">
      {/* Top Navigation Bar - Hiver Light Theme */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 shadow-sm">
        <div className="flex items-center justify-between max-w-full">
          <div className="flex items-center gap-4">
            <img
              src="/static/core/images/logos/light_mode_LOGO.png"
              alt="Hiver Logo"
              className="h-8 w-auto"
            />
            <CaseSelector currentCaseId={caseId} onCaseSelect={onCaseSelect} />
            <button
              onClick={() => setIsCaseDetailOpen(true)}
              className="px-3 py-1.5 bg-primary text-white rounded text-sm font-medium hover:bg-orange-600"
              title="Case Info - Forensic Cockpit"
            >
              Case Info
            </button>
            {/* Case Cockpit Entry Point - Info Icon */}
            <button
              onClick={() => setIsCaseDetailOpen(true)}
              className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded"
              title="Case Cockpit"
            >
              ⓘ
            </button>
            <button
              onClick={() => setIsCaseSettingsOpen(true)}
              className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded"
              title="Case Settings"
            >
              ⚙️
            </button>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Party:{" "}
              <span className="font-medium text-gray-800">{userParty}</span>
            </span>
            {/* Logout POST handler - Fix 405 Error */}
            <button
              onClick={handleLogout}
              className="text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600 cursor-pointer"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* 3-Panel Content Area - Elastic Layout with flex */}
      <main ref={mainRef} className="flex-1 flex overflow-hidden relative">
        {/* Panel 1: Timeline (Left) */}
        <div
          className="bg-white flex flex-col border-r border-gray-200 min-w-0 transition-all duration-300"
          style={getPanelStyle("left")}
        >
          {leftExpanded ? (
            <>
              <div className="p-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <span>🕰️</span>
                  <h2 className="font-semibold text-gray-800 truncate">
                    Timeline
                  </h2>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setIsFullTimelineOpen(true)}
                    className="text-gray-600 hover:text-blue-600 p-1 rounded-md hover:bg-gray-100"
                    title="Full Screen"
                  >
                    ⛶
                  </button>
                  <button
                    onClick={toggleLeft}
                    className="text-gray-600 hover:text-blue-600 p-1 rounded-md hover:bg-gray-100"
                    title="Collapse"
                  >
                    ◀
                  </button>
                </div>
              </div>
              <div className="flex-1 flex flex-col overflow-auto">
                <ForensicTimeline
                  caseId={caseId}
                  userParty={userParty}
                  onEventAdded={onEventAdded}
                />
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={toggleLeft}
                className="w-6 h-12 bg-gray-100 rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand Timeline"
              >
                ▶
              </button>
            </div>
          )}
        </div>

        {/* Left Divider */}
        {leftExpanded && centerExpanded && (
          <div
            className="w-1 bg-gray-200 cursor-col-resize hover:bg-primary transition-colors"
            onMouseDown={handleLeftDragStart}
          />
        )}

        {/* Panel 2: Archive & Canvas (Center) - ELASTIC ANCHOR */}
        <div
          className="center-panel bg-white flex flex-col border-r border-gray-200 min-w-0 relative transition-all duration-300"
          style={getPanelStyle("center")}
        >
          {centerExpanded ? (
            <>
              <div className="p-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <span>📁</span>
                  <h2 className="font-semibold text-gray-800 truncate">
                    Archive & Canvas
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  {/* Archive Ingestion Interface */}
                  <button
                    onClick={() => setIsIngestModalOpen(true)}
                    className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
                    title="Ingest Document"
                  >
                    Ingest Document
                  </button>
                  <button
                    onClick={() => setIsArchiveFullScreen(true)}
                    className="text-gray-600 hover:text-blue-600 p-1 rounded-md hover:bg-gray-100"
                    title="Full Screen"
                  >
                    ⛶
                  </button>
                  <button
                    onClick={toggleCenter}
                    className="text-gray-600 hover:text-blue-600 p-1 rounded-md hover:bg-gray-100"
                    title="Collapse"
                  >
                    ◀
                  </button>
                </div>
              </div>
              <div className="flex-1 flex flex-col overflow-auto center-panel-inner">
                <div
                  className="min-h-0 overflow-auto border-b border-gray-200"
                  style={{ height: `${horizontalSplit * 100}%` }}
                >
                  <FileTree
                    caseId={caseId}
                    onDocumentSelect={handleDocumentSelect}
                  />
                </div>

                <div
                  className="h-1 bg-gray-200 cursor-row-resize hover:bg-primary transition-colors relative"
                  onMouseDown={handleHorizontalDragStart}
                >
                  <div className="absolute top-0 left-0 right-0 bottom-0 flex items-center justify-center">
                    <div className="w-6 h-1 bg-primary opacity-50" />
                  </div>
                </div>

                <div
                  className="flex-1 p-4 min-h-0 overflow-auto"
                  style={{ height: `${(1 - horizontalSplit) * 100}%` }}
                >
                  {previewDocUuid ? (
                    <DocumentPreviewModal
                      caseId={caseId}
                      documentUuid={previewDocUuid}
                      onClose={handleClosePreview}
                    />
                  ) : (
                    <p className="text-gray-400 text-sm text-center pt-8">
                      Select a document to preview
                    </p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={toggleCenter}
                className="w-6 h-12 bg-gray-100 rounded-l-lg rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand Archive"
              >
                ▶
              </button>
            </div>
          )}
        </div>

        {/* Right Divider */}
        {centerExpanded && rightExpanded && (
          <div
            className="w-1 bg-gray-200 cursor-col-resize hover:bg-primary transition-colors"
            onMouseDown={handleRightDragStart}
          />
        )}

        {/* Panel 3: AI Assistant (Right) */}
        <div
          className="bg-white flex flex-col border-l border-gray-200 min-w-0 transition-all duration-300"
          style={getPanelStyle("right")}
        >
          {rightExpanded ? (
            <>
              <div className="p-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <span>✨</span>
                  <h2 className="font-semibold text-gray-800 truncate">
                    AI Assistant
                  </h2>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setAiSettingsOpen(!aiSettingsOpen)}
                    className="text-blue-600 bg-blue-50 border border-blue-100 p-1 rounded-md hover:bg-blue-100"
                    title="AI Settings"
                  >
                    ⚙️
                  </button>
                  <button
                    onClick={() => setIsAIFullScreen(true)}
                    className="text-blue-600 bg-blue-50 border border-blue-100 p-1 rounded-md hover:bg-blue-100"
                    title="Full Screen"
                  >
                    ⛶
                  </button>
                  <button
                    onClick={toggleRight}
                    className="text-blue-600 bg-blue-50 border border-blue-100 p-1 rounded-md hover:bg-blue-100"
                    title="Collapse"
                  >
                    ▶
                  </button>
                </div>
              </div>
              <div className="flex-1 min-h-0">
                <AIAssistantChat
                  caseId={caseId}
                  showSettings={aiSettingsOpen}
                  onToggleSettings={() => setAiSettingsOpen(false)}
                />
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={toggleRight}
                className="w-6 h-12 bg-gray-100 rounded-l-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand AI Assistant"
              >
                ◀
              </button>
            </div>
          )}
        </div>

        {/* Drag Overlay */}
        {(isDraggingLeft || isDraggingRight) && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-0 right-0 bottom-0 border-l border-r border-transparent" />
          </div>
        )}
        {isDraggingHorizontal && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-0 right-0 bottom-0 border-t border-b border-transparent" />
          </div>
        )}
      </main>

      {/* Full Timeline Modal - WITH SCROLLING */}
      {isFullTimelineOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white overflow-y-auto">
          <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between shadow-lg">
            <h2 className="text-lg font-semibold">Full Timeline View</h2>
            <button
              onClick={() => setIsFullTimelineOpen(false)}
              className="text-2xl hover:text-gray-300"
              title="Close"
            >
              ×
            </button>
          </div>
          <div className="flex-1 flex flex-col min-h-0">
            <ForensicTimeline
              caseId={caseId}
              userParty={userParty}
              onEventAdded={onEventAdded}
              isFullScreen={true}
            />
          </div>
        </div>
      )}

      {/* Archive Full Screen Modal */}
      {isArchiveFullScreen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white">
          <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between shadow-lg">
            <h2 className="text-lg font-semibold">
              Archive & Canvas - Full Screen
            </h2>
            <button
              onClick={() => setIsArchiveFullScreen(false)}
              className="text-2xl hover:text-gray-300"
              title="Close"
            >
              ×
            </button>
          </div>
          <div className="flex-1 flex flex-col overflow-auto">
            <div className="h-[40%] border-b border-gray-200 p-4 overflow-auto">
              <FileTree
                caseId={caseId}
                onDocumentSelect={handleDocumentSelect}
              />
            </div>
            <div className="border-t border-gray-200" />
            <div className="flex-1 p-4 overflow-auto">
              {previewDocUuid ? (
                <DocumentPreviewModal
                  caseId={caseId}
                  documentUuid={previewDocUuid}
                  onClose={handleClosePreview}
                />
              ) : (
                <p className="text-gray-400 text-sm text-center pt-8">
                  Select a document to preview
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant Full Screen Modal */}
      {isAIFullScreen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white">
          <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between shadow-lg">
            <h2 className="text-lg font-semibold truncate">
              AI Assistant - Full Screen
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAiSettingsOpen(!aiSettingsOpen)}
                className="text-xl hover:text-gray-300"
                title="AI Settings"
              >
                ⚙️
              </button>
              <button
                onClick={() => setIsAIFullScreen(false)}
                className="text-2xl hover:text-gray-300"
                title="Close"
              >
                ×
              </button>
            </div>
          </div>
          <div className="flex-1 flex flex-col">
            <AIAssistantChat
              caseId={caseId}
              showSettings={aiSettingsOpen}
              onToggleSettings={() => setAiSettingsOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Case Settings Modal */}
      {isCaseSettingsOpen && (
        <CaseSettingsModal
          caseId={caseId}
          onClose={() => setIsCaseSettingsOpen(false)}
          onEventAdded={onEventAdded}
        />
      )}

      {/* Case Detail Modal - Forensic Cockpit */}
      {isCaseDetailOpen && (
        <CaseDetailModal
          caseId={caseId}
          onClose={() => setIsCaseDetailOpen(false)}
          onEventAdded={onEventAdded}
        />
      )}

      {/* Smart Ingestion Modal (triggered from Archive header) */}
      {isIngestModalOpen && (
        <CaseDetailModal
          caseId={caseId}
          onClose={() => setIsIngestModalOpen(false)}
          onEventAdded={onEventAdded}
        />
      )}
    </div>
  );
};

export default Layout;
