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
  // Use documentUuid directly
  const { data: document, isLoading } = useQuery({
    queryKey: ["document", documentUuid],
    queryFn: () => archiveApi.getDocumentMetadata(documentUuid!),
    enabled: !!documentUuid,
  });

  // Handle browser back/forward
  useEffect(() => {
    const handlePopState = () => {
      const match = window.location.pathname.match(
        /\/cases\/([^/]+)\/preview\/([^/]+)/,
      );
      if (!match) {
        onClose();
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [onClose]);

  if (!documentUuid) return null;

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
              <iframe
                src={document.file_url || `/media/${document.path}`}
                className="w-full h-full"
                title={document.title}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-red-500">Document not found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentPreviewModal;
