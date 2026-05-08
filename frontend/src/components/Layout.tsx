import React, { useState, useEffect, useRef, useCallback } from "react";
import CaseSelector from "./CaseSelector";
import FileTree from "./FileTree";
import AIAssistantChat from "./AIAssistantChat";
import DocumentPreviewModal from "./DocumentPreviewModal";
import ForensicTimeline from "./ForensicTimeline";
import CaseSettingsModal from "./CaseSettingsModal";
import CaseDetailModal from "./CaseDetailModal";
import { SourceParty } from "../types/shared";

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
      if (remaining < MIN_PANEL_PERCENT * 2) return; // Need room for both center and right

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
      if (remaining < MIN_PANEL_PERCENT * 2) return; // Need room for both left and center

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

  // Reset panels to default sizes
  const resetPanels = () => {
    setPanelSizes({
      left: DEFAULT_LEFT,
      center: DEFAULT_CENTER,
      right: DEFAULT_RIGHT,
    });
    setHorizontalSplit(DEFAULT_HORIZONTAL_SPLIT);
  };

  // Calculate actual pixel widths based on percentages
  const getPanelWidths = () => {
    if (!mainRef.current) {
      return { left: 0, center: 0, right: 0 };
    }

    const containerWidth = mainRef.current.offsetWidth;
    return {
      left: (panelSizes.left / 100) * containerWidth,
      center: (panelSizes.center / 100) * containerWidth,
      right: (panelSizes.right / 100) * containerWidth,
    };
  };

  const panelWidths = getPanelWidths();

  // Toggle panel collapse/expand with size restoration
  const toggleLeft = () => {
    if (leftExpanded) {
      setLeftExpanded(false);
    } else {
      setLeftExpanded(true);
    }
  };

  const toggleCenter = () => {
    if (centerExpanded) {
      setCenterExpanded(false);
    } else {
      setCenterExpanded(true);
    }
  };

  const toggleRight = () => {
    if (rightExpanded) {
      setRightExpanded(false);
    } else {
      setRightExpanded(true);
    }
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
            <button
              onClick={() => setIsCaseSettingsOpen(true)}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
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
            <a
              href="/accounts/logout/"
              className="text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
            >
              Logout
            </a>
          </div>
        </div>
      </header>

      {/* 3-Panel Content Area */}
      <main ref={mainRef} className="flex-1 flex overflow-hidden relative">
        {/* Panel 1: Timeline (Left) */}
        {leftExpanded ? (
          <div
            className="bg-white flex flex-col border-r border-gray-200 min-w-0"
            style={{ width: panelWidths.left }}
          >
            {/* Standardized Header: [Icon] [Title] | [Full Screen] [Collapse] */}
            <div className="p-3 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2 truncate">
                <span>🕰️</span>
                <h2 className="font-semibold text-gray-800 truncate">
                  Timeline
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsFullTimelineOpen(true)}
                  className="text-xs bg-primary text-white px-2 py-1 rounded hover:bg-orange-600"
                  title="Full Screen"
                >
                  ⛶
                </button>
                <button
                  onClick={toggleLeft}
                  className="text-xs text-gray-500 hover:text-gray-700"
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
          </div>
        ) : (
          <div className="w-12 border-r border-gray-200 bg-white flex items-center justify-center">
            <button
              onClick={toggleLeft}
              className="w-6 h-12 bg-gray-100 rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
              title="Expand Timeline"
            >
              ▶
            </button>
          </div>
        )}

        {/* Left Divider (between Timeline and Archive) */}
        {leftExpanded && centerExpanded && (
          <div
            className="w-1 bg-gray-200 cursor-col-resize hover:bg-primary transition-colors"
            onMouseDown={handleLeftDragStart}
          />
        )}

        {/* Panel 2: Archive & Canvas (Center) */}
        {centerExpanded ? (
          <div
            className="center-panel bg-white flex flex-col border-r border-gray-200 min-w-0 relative"
            style={{ width: panelWidths.center }}
          >
            {/* Standardized Header: [Icon] [Title] | [Full Screen] [Collapse] */}
            <div className="p-3 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2 truncate">
                <span>📁</span>
                <h2 className="font-semibold text-gray-800 truncate">
                  Archive & Canvas
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsArchiveFullScreen(true)}
                  className="text-xs bg-accent text-white px-2 py-1 rounded hover:bg-blue-700"
                  title="Full Screen"
                >
                  ⛶
                </button>
                <button
                  onClick={toggleCenter}
                  className="text-xs text-gray-500 hover:text-gray-700"
                  title="Collapse"
                >
                  ◀
                </button>
              </div>
            </div>
            <div className="flex-1 flex flex-col overflow-auto center-panel-inner">
              {/* Top: File Explorer (Tree) */}
              <div
                className="min-h-0 overflow-auto border-b border-gray-200"
                style={{ height: `${horizontalSplit * 100}%` }}
              >
                <FileTree
                  caseId={caseId}
                  onDocumentSelect={handleDocumentSelect}
                />
              </div>

              {/* Horizontal Divider (between Tree and Canvas) */}
              <div
                className="h-1 bg-gray-200 cursor-row-resize hover:bg-primary transition-colors relative"
                onMouseDown={handleHorizontalDragStart}
              >
                <div className="absolute top-0 left-0 right-0 bottom-0 flex items-center justify-center">
                  <div className="w-6 h-1 bg-primary opacity-50" />
                </div>
              </div>

              {/* Bottom: Canvas / Preview */}
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
          </div>
        ) : (
          <div className="w-12 border-r border-gray-200 bg-white flex items-center justify-center">
            <button
              onClick={toggleCenter}
              className="w-6 h-12 bg-gray-100 rounded-l-lg rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
              title="Expand Archive"
            >
              ▶
            </button>
          </div>
        )}

        {/* Right Divider (between Archive and AI) */}
        {centerExpanded && rightExpanded && (
          <div
            className="w-1 bg-gray-200 cursor-col-resize hover:bg-primary transition-colors"
            onMouseDown={handleRightDragStart}
          />
        )}

        {/* Panel 3: AI Assistant (Right) */}
        {rightExpanded ? (
          <div
            className="bg-white flex flex-col border-l border-gray-200 min-w-0"
            style={{ width: panelWidths.right }}
          >
            {/* Standardized Header: [Icon] [Title] | [⚙️ Settings] [⛶ Full Screen] [▶ Collapse] */}
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
                  className="text-xs text-gray-500 hover:text-gray-700 p-1"
                  title="AI Settings"
                >
                  ⚙️
                </button>
                <button
                  onClick={() => setIsAIFullScreen(true)}
                  className="text-xs bg-brand-purple text-white px-2 py-1 rounded hover:bg-purple-700"
                  title="Full Screen"
                >
                  ⛶
                </button>
                <button
                  onClick={toggleRight}
                  className="text-xs text-gray-500 hover:text-gray-700"
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
          </div>
        ) : (
          <div className="w-12 border-l border-gray-200 bg-white flex items-center justify-center">
            <button
              onClick={toggleRight}
              className="w-6 h-12 bg-gray-100 rounded-l-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
              title="Expand AI Assistant"
            >
              ◀
            </button>
          </div>
        )}

        {/* Drag Overlay (visual feedback during drag) */}
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

      {/* Full Timeline Modal - Uses ForensicTimeline */}
      {isFullTimelineOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white">
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
          <div className="flex-1 flex flex-col">
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
    </div>
  );
};

export default Layout;
