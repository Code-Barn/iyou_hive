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

import React, { useState, useRef, useEffect } from "react";
import { aiApi, ChatMessage } from "../api/ai";
import { timelineApi, MaterializePayload } from "../api/timeline";
import archiveApi from "../api/archive";
import { FileNode } from "../types/shared";
import { PerspectiveMode } from "../types/timeline";
import { InspectorPanel } from "./InspectorPanel";

interface AIAssistantChatProps {
  caseId: string;
  showSettings?: boolean;
  onToggleSettings?: () => void;
  activeDocument?: FileNode | null;
  onEventAdded?: () => void;
}

interface Message extends ChatMessage {
  id: string;
  timestamp: string;
}

interface CommitModalState {
  isOpen: boolean;
  messageId: string | null;
  date: string;
  event: string;
  category: string;
  notes: string;
  source_party: string;
  isSubmitting: boolean;
}

const AIAssistantChat: React.FC<AIAssistantChatProps> = ({
  caseId,
  showSettings = false,
  onToggleSettings,
  activeDocument,
  onEventAdded,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I'm your AI Research Assistant. I can help you analyze documents, query your timeline, and generate insights for your case. All my responses are scoped to your current case and filtered by case_uuid.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState({
    mistral_api_key: "",
    gemini_api_key: "",
    preferred_provider: "mistral" as "mistral" | "gemini",
  });
  const [apiConfigured, setApiConfigured] = useState<boolean | null>(null);
  const [showInspector, setShowInspector] = useState(false);
  const [documentContent, setDocumentContent] = useState<string>("");
  const [commitModal, setCommitModal] = useState<CommitModalState>({
    isOpen: false,
    messageId: null,
    date: new Date().toISOString().split("T")[0],
    event: "",
    category: "other",
    notes: "",
    source_party: "CLIENT",
    isSubmitting: false,
  });

  const [perspectiveMode, setPerspectiveMode] = useState<PerspectiveMode>(() => {
    const saved = localStorage.getItem("hiver_ai_perspective");
    if (saved === "CLIENT" || saved === "NEUTRAL" || saved === "OPPOSING") return saved;
    return "NEUTRAL";
  });

  useEffect(() => {
    localStorage.setItem("hiver_ai_perspective", perspectiveMode);
  }, [perspectiveMode]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setApiConfigured(true);
  }, []);

  useEffect(() => {
    if (caseId) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content:
            "Hello! I'm your AI Research Assistant. I can help you analyze documents, query your timeline, and generate insights for your case. All my responses are scoped to your current case and filtered by case_uuid.",
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  }, [caseId]);

  useEffect(() => {
    if (!activeDocument?.file_details?.uuid) {
      setDocumentContent("");
      return;
    }
    const loadContent = async () => {
      try {
        const resp = await archiveApi.getDocumentContent(activeDocument.file_details!.uuid!);
        if (resp.status === 200 && resp.data.content) {
          setDocumentContent(resp.data.content);
          return;
        }
      } catch {}
      setDocumentContent("");
    };
    loadContent();
  }, [activeDocument?.uuid]);

  const parseEventSuggestion = (text: string): { date: string; event: string; category: string } | null => {
    const dateMatch = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
    const date = dateMatch ? dateMatch[1] : new Date().toISOString().split("T")[0];

    const categoryKeywords: Record<string, string[]> = {
      contract: ["contract", "agreement", "signed", "executed"],
      email: ["email", "correspondence"],
      court_filing: ["court", "filing", "filed", "motion", "order"],
      communication: ["call", "meeting", "spoke", "discussed", "communication"],
      meeting: ["meeting", "conference", "appointment"],
      deadline: ["deadline", "due", "expir"],
      financial: ["payment", "invoice", "bill", "financial", "fee", "settlement"],
      legal: ["legal", "litigation", "claim", "allegation"],
      medical: ["medical", "health", "doctor", "hospital"],
      personal: ["personal", "family", "marriage", "divorce"],
      education: ["school", "education", "class", "course"],
    };

    let category = "other";
    const textLower = text.toLowerCase();
    for (const [cat, keywords] of Object.entries(categoryKeywords)) {
      if (keywords.some((kw) => textLower.includes(kw))) {
        category = cat;
        break;
      }
    }

    const lines = text.split("\n").filter((l) => l.trim());
    const eventLine = lines.find(
      (l) => l.match(/^[-*]\s+\d/) || l.match(/^[\d:]/) || l.match(/^[A-Z]/)
    );

    const event = eventLine
      ? eventLine.replace(/^[-*\s]+/, "").replace(/^\d{4}-\d{2}-\d{2}\s*/, "").substring(0, 200)
      : text.substring(0, 200);

    return { date, event, category };
  };

  const handleCommitToTimeline = (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message) return;

    const parsed = parseEventSuggestion(message.content);
    setCommitModal({
      isOpen: true,
      messageId,
      date: parsed?.date || new Date().toISOString().split("T")[0],
      event: parsed?.event || message.content.substring(0, 200),
      category: parsed?.category || "other",
      notes: message.content.substring(0, 500),
      source_party: "CLIENT",
      isSubmitting: false,
    });
  };

  const handleCommitSubmit = async () => {
    if (!caseId || !commitModal.event.trim()) return;

    setCommitModal((prev) => ({ ...prev, isSubmitting: true }));

    try {
      const payload: MaterializePayload = {
        date: commitModal.date,
        event: commitModal.event,
        category: commitModal.category,
        notes: commitModal.notes,
        source_party: commitModal.source_party,
        source_type: "AI_GENERATED",
        status: "PENDING",
        trust_level: 2,
      };

      await timelineApi.materializeEvent(caseId, payload);

      const confirmMsg: Message = {
        id: `commit-${Date.now()}`,
        role: "assistant",
        content: `✅ Event materialized: **${commitModal.event}** (${commitModal.date}) — saved to Timeline.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, confirmMsg]);
      setCommitModal((prev) => ({ ...prev, isOpen: false }));
      onEventAdded?.();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Failed to materialize event";
      setCommitModal((prev) => ({ ...prev, isOpen: false }));
      setError(errorMsg);
    } finally {
      setCommitModal((prev) => ({ ...prev, isSubmitting: false }));
    }
  };

  const closeCommitModal = () => {
    setCommitModal((prev) => ({ ...prev, isOpen: false }));
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading || !caseId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await aiApi.queryTimeline(
        inputValue.trim(),
        caseId,
        documentContent || undefined,
        perspectiveMode,
      );

      if (response.data && response.data.status === "success") {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: response.data.response || "No response from AI",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else if (response.data && response.data.analysis) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: response.data.analysis,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error(response.data?.error || "Unknown error");
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to get AI response";
      setError(errorMessage);
      const errorMessageObj: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessageObj]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await aiApi.saveApiKey({
        mistral_api_key: settings.mistral_api_key || undefined,
        gemini_api_key: settings.gemini_api_key || undefined,
        preferred_provider: settings.preferred_provider,
      });
      setApiConfigured(true);
      onToggleSettings?.();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to save settings";
      setError(errorMessage);
    }
  };

  const handleToggleSettingsInternal = () => {
    onToggleSettings?.();
  };

  const isApiConfigured =
    apiConfigured !== false &&
    (settings.mistral_api_key || settings.gemini_api_key || apiConfigured);

  const hasDate = (text: string) => /\b\d{4}-\d{2}-\d{2}\b/.test(text);

  return (
    <div className="flex flex-col h-full">
      {/* Settings Panel */}
      {showSettings && (
        <div className="p-3 border-b border-gray-200 bg-gray-50">
          <h3 className="font-semibold text-gray-700 mb-2">AI Settings</h3>
          <form onSubmit={handleSaveSettings} className="space-y-2">
            <div className="flex gap-2">
              <select
                value={settings.preferred_provider}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    preferred_provider: e.target.value as "mistral" | "gemini",
                  })
                }
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="mistral">Mistral AI</option>
                <option value="gemini">Google Gemini</option>
              </select>
            </div>
            <div className="space-y-1">
              <input
                type="password"
                placeholder="Mistral API Key"
                value={settings.mistral_api_key}
                onChange={(e) =>
                  setSettings({ ...settings, mistral_api_key: e.target.value })
                }
                className="w-full text-sm border border-gray-300 rounded px-2 py-1"
              />
              <input
                type="password"
                placeholder="Gemini API Key"
                value={settings.gemini_api_key}
                onChange={(e) =>
                  setSettings({ ...settings, gemini_api_key: e.target.value })
                }
                className="w-full text-sm border border-gray-300 rounded px-2 py-1"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                className="text-xs bg-primary text-white px-3 py-1 rounded hover:bg-orange-600"
              >
                Save
              </button>
              <button
                type="button"
                onClick={handleToggleSettingsInternal}
                className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </form>
          <p className="text-xs text-gray-500 mt-1">
            Keys are saved to your user profile. Get free keys at{" "}
            <a href="https://mistral.ai" className="text-primary underline">
              Mistral
            </a>{" "}
            or{" "}
            <a
              href="https://aistudio.google.com"
              className="text-primary underline"
            >
              Gemini
            </a>
            .
          </p>
        </div>
      )}

      {/* Inspector Toggle Bar */}
      {activeDocument && (
        <div className="flex items-center justify-between px-3 py-1 border-b border-gray-200 bg-gray-50">
          <span className="text-xs text-gray-500 truncate">
            Active: {activeDocument.name}
          </span>
          <button
            onClick={() => setShowInspector(!showInspector)}
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              showInspector
                ? "bg-primary text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {showInspector ? "Hide Inspector" : "Inspect"}
          </button>
        </div>
      )}

      {/* Perspective Toggle — fixed at top of AI panel */}
      <div className="flex-none px-3 py-1.5 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-center gap-0">
          {(["CLIENT", "NEUTRAL", "OPPOSING"] as PerspectiveMode[]).map((mode) => {
            const isActive = perspectiveMode === mode;
            const activeStyles: Record<PerspectiveMode, string> = {
              CLIENT:
                "bg-indigo-100 text-indigo-700 border-indigo-300 shadow-sm",
              NEUTRAL:
                "bg-gray-100 text-gray-700 border-gray-300 shadow-sm",
              OPPOSING:
                "bg-amber-100 text-amber-700 border-amber-300 shadow-sm",
            };
            return (
              <button
                key={mode}
                onClick={() => setPerspectiveMode(mode)}
                className={`text-xs font-medium tracking-wide px-3 py-1 border transition-all duration-150 first:rounded-l-md last:rounded-r-md -ml-px first:ml-0 focus:outline-none ${
                  isActive
                    ? activeStyles[mode]
                    : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {mode}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Main Chat Area */}
        <div className={`flex flex-col ${showInspector ? "w-1/2" : "w-full"} border-r border-gray-200`}>
          {/* Chat History */}
          <div className="flex-1 p-3 overflow-auto bg-gray-50">
            {!isApiConfigured && messages.length === 1 && (
              <div className="mb-3 p-3 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-sm">
                Configure your API keys in Settings to enable AI assistance.
              </div>
            )}

            <div className="space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                      message.role === "user"
                        ? "bg-primary text-white"
                        : "bg-white border border-gray-200 text-gray-800"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs opacity-60">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                      {message.role === "assistant" && message.id !== "welcome" && hasDate(message.content) && (
                        <button
                          onClick={() => handleCommitToTimeline(message.id)}
                          className="ml-2 text-xs font-medium bg-green-100 text-green-700 px-2 py-0.5 rounded hover:bg-green-200 transition-colors"
                        >
                          + Commit to Timeline
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600">
                    AI is thinking...
                  </div>
                </div>
              )}

              {error && (
                <div className="flex justify-center">
                  <div className="bg-red-100 border border-red-300 rounded px-3 py-2 text-sm text-red-700">
                    {error}
                  </div>
                </div>
              )}
            </div>

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="p-3 border-t border-gray-200 bg-white">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={
                  isApiConfigured
                    ? "Ask a question..."
                    : "Configure API keys to chat"
                }
                disabled={!isApiConfigured || isLoading || !caseId}
                className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={
                  !inputValue.trim() || isLoading || !isApiConfigured || !caseId
                }
                className="bg-primary text-white px-4 py-2 rounded text-sm font-medium hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                Send
              </button>
            </form>
            <p className="text-xs text-gray-400 mt-1">
              All responses filtered by case_uuid:{" "}
              {caseId ? caseId.substring(0, 8) + "..." : "None"}
            </p>
          </div>
        </div>

        {/* Inspector Panel (conditional) */}
        {showInspector && (
          <div className="w-1/2 overflow-auto">
            <InspectorPanel selectedFile={activeDocument || null} />
          </div>
        )}
      </div>

      {/* Commit to Timeline Modal */}
      {commitModal.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-lg mx-4 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-800">
                Commit to Timeline
              </h3>
              <button
                onClick={closeCommitModal}
                className="text-gray-400 hover:text-gray-600 text-xl"
              >
                ✕
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Date
                </label>
                <input
                  type="date"
                  value={commitModal.date}
                  onChange={(e) =>
                    setCommitModal((prev) => ({ ...prev, date: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Event *
                </label>
                <input
                  type="text"
                  value={commitModal.event}
                  onChange={(e) =>
                    setCommitModal((prev) => ({ ...prev, event: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Category
                </label>
                <select
                  value={commitModal.category}
                  onChange={(e) =>
                    setCommitModal((prev) => ({ ...prev, category: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="contract">Contract</option>
                  <option value="email">Email</option>
                  <option value="court_filing">Court Filing</option>
                  <option value="communication">Communication</option>
                  <option value="meeting">Meeting</option>
                  <option value="deadline">Deadline</option>
                  <option value="financial">Financial</option>
                  <option value="legal">Legal</option>
                  <option value="medical">Medical</option>
                  <option value="personal">Personal</option>
                  <option value="education">Education</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Source Party
                </label>
                <select
                  value={commitModal.source_party}
                  onChange={(e) =>
                    setCommitModal((prev) => ({ ...prev, source_party: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="CLIENT">Client</option>
                  <option value="OPPOSING">Opposing</option>
                  <option value="NEUTRAL">Neutral</option>
                  <option value="COURT">Court</option>
                  <option value="WITNESS">Witness</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Notes
                </label>
                <textarea
                  value={commitModal.notes}
                  onChange={(e) =>
                    setCommitModal((prev) => ({ ...prev, notes: e.target.value }))
                  }
                  rows={3}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-gray-200">
              <button
                onClick={closeCommitModal}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCommitSubmit}
                disabled={commitModal.isSubmitting || !commitModal.event.trim()}
                className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
              >
                {commitModal.isSubmitting ? "Creating..." : "Commit to Timeline"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAssistantChat;
