import React, { useState, useEffect } from "react";
import CaseSelector from "./CaseSelector";
import FileTree from "./FileTree";
import AIAssistantChat from "./AIAssistantChat";
import DocumentPreviewModal from "./DocumentPreviewModal";
import ForensicTimeline from "./ForensicTimeline";
import CaseSettingsModal from "./CaseSettingsModal";
import { SourceParty } from "../types/shared";

interface LayoutProps {
  caseId: string;
  userParty: SourceParty;
  onCaseSelect: (caseId: string) => void;
  onEventAdded?: () => void;
}

const Layout: React.FC<LayoutProps> = ({
  caseId,
  userParty,
  onCaseSelect,
  onEventAdded,
}) => {
  const [previewDocUuid, setPreviewDocUuid] = useState<string | null>(null);
  const [leftExpanded, setLeftExpanded] = useState(true);
  const [centerExpanded, setCenterExpanded] = useState(true);
  const [rightExpanded, setRightExpanded] = useState(true);
  const [isFullTimelineOpen, setIsFullTimelineOpen] = useState(false);
  const [isArchiveFullScreen, setIsArchiveFullScreen] = useState(false);
  const [isAIFullScreen, setIsAIFullScreen] = useState(false);
  const [isCaseSettingsOpen, setIsCaseSettingsOpen] = useState(false);
  const [aiSettingsOpen, setAiSettingsOpen] = useState(false);

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
      <main className="flex-1 flex overflow-hidden">
        {/* Panel 1: Timeline (Left) */}
        <div
          className={`${leftExpanded ? "w-1/3 min-w-0" : "w-12"}
            border-r border-gray-200 bg-white flex flex-col transition-all duration-300`}
        >
          {/* Collapsed tab */}
          {!leftExpanded && (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={() => setLeftExpanded(true)}
                className="w-6 h-12 bg-gray-100 rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand Timeline"
              >
                ▶
              </button>
            </div>
          )}

          {leftExpanded && (
            <>
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
                    onClick={() => setLeftExpanded(false)}
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
            </>
          )}
        </div>

        {/* Panel 2: Archive & Canvas (Center) */}
        <div
          className={`${centerExpanded ? "w-1/3 min-w-0" : "w-12"}
            border-r border-gray-200 bg-white flex flex-col transition-all duration-300`}
        >
          {/* Collapsed tab */}
          {!centerExpanded && (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={() => setCenterExpanded(true)}
                className="w-6 h-12 bg-gray-100 rounded-l-lg rounded-r-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand Archive"
              >
                ▶
              </button>
            </div>
          )}

          {centerExpanded && (
            <>
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
                    onClick={() => setCenterExpanded(false)}
                    className="text-xs text-gray-500 hover:text-gray-700"
                    title="Collapse"
                  >
                    ◀
                  </button>
                </div>
              </div>
              <div className="flex-1 flex flex-col overflow-auto">
                {/* Top 40%: File Explorer */}
                <div className="h-[40%] border-b border-gray-200 min-h-0 overflow-auto">
                  <FileTree
                    caseId={caseId}
                    onDocumentSelect={handleDocumentSelect}
                  />
                </div>
                {/* Horizontal divider */}
                <div className="border-t border-gray-200" />
                {/* Bottom 60%: Canvas / Preview */}
                <div className="flex-1 p-4 min-h-0 overflow-auto">
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
          )}
        </div>

        {/* Panel 3: AI Assistant (Right) */}
        <div
          className={`${rightExpanded ? "w-1/3 min-w-0" : "w-12"}
            border-l border-gray-200 bg-white flex flex-col transition-all duration-300`}
        >
          {/* Collapsed tab */}
          {!rightExpanded && (
            <div className="h-full flex items-center justify-center">
              <button
                onClick={() => setRightExpanded(true)}
                className="w-6 h-12 bg-gray-100 rounded-l-lg hover:bg-gray-200 transition-colors flex items-center justify-center text-gray-600 hover:text-gray-800"
                title="Expand AI Assistant"
              >
                ◀
              </button>
            </div>
          )}

          {rightExpanded && (
            <>
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
                    onClick={() => setRightExpanded(false)}
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
            </>
          )}
        </div>
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
    </div>
  );
};

export default Layout;
