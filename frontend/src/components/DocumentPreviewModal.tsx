import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import archiveApi from "../api/archive";

interface DocumentPreviewModalProps {
  caseId: string;
  documentUuid: string | null;
  onClose: () => void;
}

const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({
  caseId,
  documentUuid,
  onClose,
}) => {
  const [currentDocUuid, setCurrentDocUuid] = useState<string | null>(documentUuid);

  // Update URL when document changes
  useEffect(() => {
    if (currentDocUuid) {
      const newUrl = `/cases/${caseId}/preview/${currentDocUuid}`;
      window.history.pushState({}, "", newUrl);
    } else {
      const newUrl = `/cases/${caseId}`;
      window.history.pushState({}, "", newUrl);
    }
  }, [currentDocUuid, caseId]);

  // Listen for browser back/forward
  useEffect(() => {
    const handlePopState = () => {
      const match = window.location.pathname.match(
        /\/cases\/([^/]+)\/preview\/([^/]+)/
      );
      if (match) {
        setCurrentDocUuid(match[2]);
      } else {
        onClose();
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [onClose]);

  // Fetch document details
  const { data: document, isLoading } = useQuery({
    queryKey: ["document", currentDocUuid],
    queryFn: () => archiveApi.getDocumentDetails(currentDocUuid!),
    enabled: !!currentDocUuid,
  });

  if (!currentDocUuid) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-11/12 h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold">
            {isLoading ? "Loading..." : document?.title || "Document Preview"}
          </h2>
          <button
            onClick={() => {
              onClose();
              window.history.back();
            }}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Loading document...</p>
            </div>
          ) : document ? (
            <div className="h-full">
              {document.file_type === "pdf" ? (
                <iframe
                  src={`/media/${document.file_path}`}
                  className="w-full h-full"
                  title={document.title}
                />
              ) : (
                <div className="p-4">
                  <pre className="whitespace-pre-wrap">{document.content || "No preview available"}</pre>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-red-500">Document not found</p>
            </div>
          )}
        </div>

        {/* Footer with metadata */}
        {document && (
          <div className="border-t p-4 text-sm text-gray-600">
            <div className="flex gap-4">
              <span>Type: {document.file_type}</span>
              <span>Size: {document.file_size || "Unknown"}</span>
              <span>Created: {new Date(document.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentPreviewModal;
