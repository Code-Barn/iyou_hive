import React, { useState, useRef, useEffect } from "react";
import { aiApi, ChatMessage } from "../api/ai";

interface AIAssistantChatProps {
  caseId: string;
  showSettings?: boolean;
  onToggleSettings?: () => void;
}

interface Message extends ChatMessage {
  id: string;
  timestamp: string;
}

const AIAssistantChat: React.FC<AIAssistantChatProps> = ({
  caseId,
  showSettings = false,
  onToggleSettings,
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

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check API configuration on mount
  useEffect(() => {
    setApiConfigured(true);
  }, []);

  // Clear chat when case changes
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
      const response = await aiApi.queryTimeline(inputValue.trim(), caseId);

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

  return (
    <div className="flex flex-col h-full">
      {/* Settings Panel - controlled by parent via showSettings prop */}
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

      {/* Chat History */}
      <div
        className={`flex-1 p-3 overflow-auto bg-gray-50 ${showSettings ? "" : "min-h-0"}`}
      >
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
                <span className="text-xs opacity-60 mt-1 block">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
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
  );
};

export default AIAssistantChat;
