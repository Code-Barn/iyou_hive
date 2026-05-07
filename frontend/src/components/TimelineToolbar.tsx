import React, { useState } from 'react';
import { timelineApi } from '../api/timeline';
import { archiveApi } from '../api/archive';

interface TimelineToolbarProps {
  caseId: string;
  onEventAdded: () => void;
}

export const TimelineToolbar: React.FC<TimelineToolbarProps> = ({ caseId, onEventAdded }) => {
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAddEventModalOpen, setIsAddEventModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [uploadError, setUploadError] = useState<string>('');

  // Event form state
  const [eventDate, setEventDate] = useState('');
  const [eventTitle, setEventTitle] = useState('');
  const [eventCategory, setEventCategory] = useState('verified');
  const [eventSourceParty, setEventSourceParty] = useState<'CLIENT' | 'OPPOSING' | 'NEUTRAL'>('CLIENT');
  const [eventNotes, setEventNotes] = useState('');
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([]);
  const [availableDocuments, setAvailableDocuments] = useState<Array<{uuid: string; title: string}>>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [addEventStatus, setAddEventStatus] = useState<'idle' | 'adding' | 'success' | 'error'>('idle');
  const [addEventError, setAddEventError] = useState<string>('');

  // Load available documents for evidence linking
  const loadDocuments = async () => {
    try {
      setIsLoadingDocuments(true);
      const response = await archiveApi.getDirectoryTree();

      // Extract documents from the tree
      const documents: Array<{uuid: string; title: string}> = [];

      // Helper function to traverse tree and extract documents
      const traverseTree = (nodes: any[]) => {
        for (const node of nodes) {
          if (!node.is_folder && node.file_details) {
            documents.push({
              uuid: node.file_details.uuid,
              title: node.file_details.title
            });
          }
          if (node.children) {
            traverseTree(node.children);
          }
        }
      };

      if (response.data && Array.isArray(response.data)) {
        traverseTree(response.data);
      }

      setAvailableDocuments(documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setAvailableDocuments([]);
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  // Handle file upload for timeline markdown
  const handleFileUpload = async () => {
    if (!uploadFile || !caseId) return;

    setUploadStatus('uploading');
    setUploadError('');

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('case_uuid', caseId);

      // Call the timeline upload API
      const response = await timelineApi.uploadTimeline(caseId, formData);

      if (response.data.status === 'success') {
        setUploadStatus('success');
        onEventAdded(); // Refresh timeline
        setTimeout(() => {
          setIsUploadModalOpen(false);
          setUploadStatus('idle');
          setUploadFile(null);
        }, 2000);
      } else {
        setUploadStatus('error');
        setUploadError(response.data.error || 'Failed to upload timeline');
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus('error');
      setUploadError('Failed to upload timeline. Please try again.');
    }
  };

  // Handle manual event creation
  const handleAddEvent = async () => {
    if (!caseId) return;

    setAddEventStatus('adding');
    setAddEventError('');

    try {
      const eventData = {
        date: eventDate,
        event: eventTitle,
        category: eventCategory,
        source_party: eventSourceParty,
        notes: eventNotes,
        evidence_ids: selectedEvidence
      };

      const response = await timelineApi.createEvent(caseId, eventData);

      if (response.data.status === 'success') {
        setAddEventStatus('success');
        onEventAdded(); // Refresh timeline

        // Reset form
        setEventDate('');
        setEventTitle('');
        setEventCategory('verified');
        setEventSourceParty('CLIENT');
        setEventNotes('');
        setSelectedEvidence([]);

        setTimeout(() => {
          setIsAddEventModalOpen(false);
          setAddEventStatus('idle');
        }, 2000);
      } else {
        setAddEventStatus('error');
        setAddEventError(response.data.error || 'Failed to add event');
      }
    } catch (error) {
      console.error('Add event failed:', error);
      setAddEventStatus('error');
      setAddEventError('Failed to add event. Please try again.');
    }
  };

  // Handle PDF generation
  const handlePrintPDF = async () => {
    if (!caseId) return;

    try {
      // Call the PDF generation API
      const response = await timelineApi.generatePdf(caseId);

      if (response.data.status === 'success' && response.data.pdf_url) {
        // Open the PDF in a new tab
        window.open(response.data.pdf_url, '_blank');
      } else {
        console.error('PDF generation failed:', response.data.error);
        alert('Failed to generate PDF. Please try again.');
      }
    } catch (error) {
      console.error('PDF generation failed:', error);
      alert('Failed to generate PDF. Please try again.');
    }
  };

  // Toggle evidence selection
  const toggleEvidence = (documentUuid: string) => {
    setSelectedEvidence(prev =>
      prev.includes(documentUuid)
        ? prev.filter(id => id !== documentUuid)
        : [...prev, documentUuid]
    );
  };

  return (
    <div className="timeline-toolbar bg-white border-b border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-800">Legal Timeline</h1>
        </div>

        <div className="flex items-center gap-2">
          {/* Upload Timeline Button */}
          <button
            onClick={() => {
              setIsUploadModalOpen(true);
              loadDocuments();
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <span>📄</span> Upload Timeline
          </button>

          {/* Add Event Button */}
          <button
            onClick={() => {
              setIsAddEventModalOpen(true);
              loadDocuments();
            }}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <span>➕</span> Add Event
          </button>

          {/* Print PDF Button */}
          <button
            onClick={handlePrintPDF}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
          >
            <span>📄</span> Print PDF
          </button>
        </div>
      </div>

      {/* Upload Timeline Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Upload Timeline File</h2>
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setUploadStatus('idle');
                  setUploadError('');
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="mb-4">
              <p className="text-gray-600 mb-2">Upload a 5-column Markdown timeline file</p>
              <input
                type="file"
                accept=".md,.markdown"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="w-full border border-gray-300 rounded-lg p-2"
              />
            </div>

            {uploadStatus === 'uploading' && (
              <div className="mb-4 p-3 bg-blue-100 rounded-lg">
                <p className="text-blue-700">Uploading and processing timeline...</p>
              </div>
            )}

            {uploadStatus === 'success' && (
              <div className="mb-4 p-3 bg-green-100 rounded-lg">
                <p className="text-green-700">Timeline uploaded successfully!</p>
              </div>
            )}

            {uploadStatus === 'error' && uploadError && (
              <div className="mb-4 p-3 bg-red-100 rounded-lg">
                <p className="text-red-700">Error: {uploadError}</p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsUploadModalOpen(false);
                  setUploadStatus('idle');
                  setUploadError('');
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleFileUpload}
                disabled={uploadStatus === 'uploading' || !uploadFile}
                className={`px-4 py-2 ${uploadStatus === 'uploading' || !uploadFile ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg transition-colors`}
              >
                {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Event Modal */}
      {isAddEventModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Add Timeline Event</h2>
              <button
                onClick={() => {
                  setIsAddEventModalOpen(false);
                  setAddEventStatus('idle');
                  setAddEventError('');
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg p-2"
                  required
                />
              </div>

              {/* Event Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Event/Incident *</label>
                <input
                  type="text"
                  value={eventTitle}
                  onChange={(e) => setEventTitle(e.target.value)}
                  placeholder="Event title"
                  className="w-full border border-gray-300 rounded-lg p-2"
                  required
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={eventCategory}
                  onChange={(e) => setEventCategory(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg p-2"
                >
                  <option value="verified">Verified</option>
                  <option value="contested">Contested</option>
                  <option value="refuted">Refuted</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Source Party */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source Party</label>
                <select
                  value={eventSourceParty}
                  onChange={(e) => setEventSourceParty(e.target.value as 'CLIENT' | 'OPPOSING' | 'NEUTRAL')}
                  className="w-full border border-gray-300 rounded-lg p-2"
                >
                  <option value="CLIENT">Client</option>
                  <option value="OPPOSING">Opposing Party</option>
                  <option value="NEUTRAL">Neutral (Court/Judge)</option>
                </select>
              </div>

              {/* Notes */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={eventNotes}
                  onChange={(e) => setEventNotes(e.target.value)}
                  placeholder="Additional notes about this event"
                  className="w-full border border-gray-300 rounded-lg p-2 h-24"
                />
              </div>

              {/* Evidence Documents */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Supporting Documents</label>
                <p className="text-sm text-gray-500 mb-2">Link evidence from your archive</p>

                {isLoadingDocuments ? (
                  <p className="text-gray-500">Loading documents...</p>
                ) : availableDocuments.length === 0 ? (
                  <p className="text-gray-500">No documents available in your archive.</p>
                ) : (
                  <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-2">
                    {availableDocuments.map(doc => (
                      <div key={doc.uuid} className="flex items-center p-2 hover:bg-gray-50">
                        <input
                          type="checkbox"
                          id={`doc-${doc.uuid}`}
                          checked={selectedEvidence.includes(doc.uuid)}
                          onChange={() => toggleEvidence(doc.uuid)}
                          className="mr-2"
                        />
                        <label htmlFor={`doc-${doc.uuid}`} className="text-sm">
                          {doc.title}
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {addEventStatus === 'adding' && (
              <div className="mb-4 p-3 bg-blue-100 rounded-lg">
                <p className="text-blue-700">Adding event...</p>
              </div>
            )}

            {addEventStatus === 'success' && (
              <div className="mb-4 p-3 bg-green-100 rounded-lg">
                <p className="text-green-700">Event added successfully!</p>
              </div>
            )}

            {addEventStatus === 'error' && addEventError && (
              <div className="mb-4 p-3 bg-red-100 rounded-lg">
                <p className="text-red-700">Error: {addEventError}</p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsAddEventModalOpen(false);
                  setAddEventStatus('idle');
                  setAddEventError('');
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleAddEvent}
                disabled={addEventStatus === 'adding' || !eventDate || !eventTitle}
                className={`px-4 py-2 ${addEventStatus === 'adding' || !eventDate || !eventTitle ? 'bg-green-300' : 'bg-green-600 hover:bg-green-700'} text-white rounded-lg transition-colors`}
              >
                {addEventStatus === 'adding' ? 'Adding...' : 'Add Event'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
