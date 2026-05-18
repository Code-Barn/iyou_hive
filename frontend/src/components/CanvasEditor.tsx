import React, { useState, useEffect } from "react";
import archiveApi from "../api/archive";
import { FileNode } from "../types/shared";

interface CanvasEditorProps {
  caseId: string;
  activeDocument: FileNode | null;
}

const CanvasEditor: React.FC<CanvasEditorProps> = ({ caseId, activeDocument }) => {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [loadedContent, setLoadedContent] = useState<string | null>(null);

  useEffect(() => {
    if (activeDocument?.file_details) {
      setTitle(activeDocument.file_details.title || activeDocument.name);
      loadFileContent(activeDocument.file_details);
    } else if (activeDocument) {
      setTitle(activeDocument.name);
      setContent("");
      setLoadedContent(null);
    } else {
      setContent("");
      setTitle("");
      setLoadedContent(null);
    }
  }, [activeDocument?.uuid]);

  const loadFileContent = async (details: { file_type: string; uuid?: string }) => {
    if (!details.uuid) {
      setContent("");
      setLoadedContent(null);
      return;
    }

    try {
      const response = await archiveApi.getDocumentContent(details.uuid);
      if (response.status === 200) {
        setContent(response.data.content || "");
        setLoadedContent(response.data.content || null);
        return;
      }
    } catch {
    }

    setContent("");
    setLoadedContent(null);
  };

  const handleSaveDraft = async () => {
    if (!caseId || !title.trim()) return;
    setIsSaving(true);
    setSaveStatus(null);

    try {
      const blob = new Blob([content], { type: "text/markdown" });
      const file = new File([blob], `${title.replace(/\s+/g, "_")}.md`, {
        type: "text/markdown",
      });
      const formData = new FormData();
      formData.append("file", file);
      formData.append("case_uuid", caseId);
      formData.append("title", title);
      formData.append("folder", "03_Drafts");

      await archiveApi.uploadDocuments(caseId, formData);
      setSaveStatus("Draft saved to Workspace/Drafts");
      setLoadedContent(content);
    } catch (err) {
      setSaveStatus("Failed to save draft");
    } finally {
      setIsSaving(false);
    }
  };

  const handleNewDraft = () => {
    setContent("");
    setTitle("");
    setLoadedContent(null);
    setSaveStatus(null);
  };

  const hasUnsavedChanges =
    loadedContent !== null && content !== loadedContent;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Document title..."
            className="text-sm font-medium bg-transparent border-b border-transparent hover:border-gray-300 focus:border-primary focus:outline-none px-1 py-0.5"
          />
          {hasUnsavedChanges && (
            <span className="text-xs text-orange-500 font-medium">● Unsaved</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex border border-gray-200 rounded overflow-hidden">
            <button
              onClick={() => setMode("edit")}
              className={`px-2 py-1 text-xs font-medium ${
                mode === "edit"
                  ? "bg-primary text-white"
                  : "bg-white text-gray-600 hover:bg-gray-100"
              }`}
            >
              Edit
            </button>
            <button
              onClick={() => setMode("preview")}
              className={`px-2 py-1 text-xs font-medium ${
                mode === "preview"
                  ? "bg-primary text-white"
                  : "bg-white text-gray-600 hover:bg-gray-100"
              }`}
            >
              Preview
            </button>
          </div>
          <button
            onClick={handleNewDraft}
            className="px-2 py-1 text-xs font-medium bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            + New Draft
          </button>
          <button
            onClick={handleSaveDraft}
            disabled={isSaving || !title.trim()}
            className="px-3 py-1 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Draft"}
          </button>
        </div>
      </div>

      {saveStatus && (
        <div
          className={`px-3 py-1 text-xs font-medium ${
            saveStatus.includes("Failed")
              ? "bg-red-100 text-red-700"
              : "bg-green-100 text-green-700"
          }`}
        >
          {saveStatus}
        </div>
      )}

      <div className="flex-1 min-h-0">
        {mode === "edit" ? (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={
              activeDocument
                ? "Edit document content..."
                : "Write a new draft in Markdown...\n\n# Title\n\n## Section\n\nYour content here."
            }
            className="w-full h-full p-4 text-sm font-mono resize-none focus:outline-none bg-white"
          />
        ) : (
          <div className="w-full h-full p-4 overflow-auto bg-white">
            <div className="prose prose-sm max-w-none">
              {content ? (
                content.split("\n").map((line, i) => {
                  if (line.startsWith("# ")) {
                    return <h1 key={i} className="text-xl font-bold mt-4 mb-2">{line.slice(2)}</h1>;
                  }
                  if (line.startsWith("## ")) {
                    return <h2 key={i} className="text-lg font-semibold mt-3 mb-1">{line.slice(3)}</h2>;
                  }
                  if (line.startsWith("### ")) {
                    return <h3 key={i} className="text-base font-medium mt-2 mb-1">{line.slice(4)}</h3>;
                  }
                  if (line.startsWith("| ")) {
                    return <pre key={i} className="text-xs font-mono bg-gray-50 p-1 my-0.5">{line}</pre>;
                  }
                  if (line.trim() === "") {
                    return <br key={i} />;
                  }
                  return <p key={i} className="text-sm text-gray-800 my-0.5">{line}</p>;
                })
              ) : (
                <p className="text-gray-400 text-sm text-center pt-8">
                  {activeDocument
                    ? "File content not available as text"
                    : "Select a document or create a new draft"}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CanvasEditor;
