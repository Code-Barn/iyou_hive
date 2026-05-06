import React, { useState } from 'react';
import { ContestedPair, SourceParty } from '../types/timeline';

interface ConflictResolverModalProps {
  conflict: ContestedPair;
  leftParty: SourceParty;
  rightParty: SourceParty;
  onClose: () => void;
  onResolve: (resolution: any) => void;
}

const ConflictResolverModal: React.FC<ConflictResolverModalProps> = ({
  conflict,
  leftParty,
  rightParty,
  onClose,
  onResolve
}) => {
  const [activeTab, setActiveTab] = useState<'resolve' | 'merge'>('resolve');
  const [mergedData, setMergedData] = useState({
    date: conflict.left.date,
    event: conflict.left.event,
    category: conflict.left.category,
    notes: conflict.left.notes || '',
    citation: conflict.left.citation || '',
    evidence_ids: [] as string[],
  });

  const handleResolve = (action: string) => {
    onResolve({ action, ...mergedData });
  };

  const getFieldDiff = (field: keyof typeof conflict.diff) => {
    return conflict.diff[field] ? 'bg-yellow-100' : 'bg-green-50';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b p-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">
            Resolve Conflict: {conflict.left.event}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            &times;
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b flex">
          <button
            onClick={() => setActiveTab('resolve')}
            className={`px-4 py-2 text-sm font-medium ${activeTab === 'resolve' ? 'bg-white text-primary border-b-2 border-primary' : 'bg-gray-50 text-gray-500'}`}
          >
            Quick Resolve
          </button>
          <button
            onClick={() => setActiveTab('merge')}
            className={`px-4 py-2 text-sm font-medium ${activeTab === 'merge' ? 'bg-white text-primary border-b-2 border-primary' : 'bg-gray-50 text-gray-500'}`}
          >
            Merge Versions
          </button>
        </div>

        <div className="p-4">
          {/* Comparison View */}
          <div className="mb-6">
            <h3 className="font-semibold mb-4">Comparison</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="bg-blue-50 p-3 rounded-lg mb-2">
                  <div className="font-medium text-blue-700">{leftParty}</div>
                  <div className="text-xs text-gray-500">Version by: {conflict.left.created_by_username}</div>
                </div>
                <div className="space-y-2">
                  <div className={`p-2 rounded ${getFieldDiff('date')}`}>
                    <div className="text-xs text-gray-500">Date</div>
                    <div>{conflict.left.date}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('event')}`}>
                    <div className="text-xs text-gray-500">Event</div>
                    <div>{conflict.left.event}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('category')}`}>
                    <div className="text-xs text-gray-500">Category</div>
                    <div className="capitalize">{conflict.left.category}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('notes')}`}>
                    <div className="text-xs text-gray-500">Notes</div>
                    <div>{conflict.left.notes || '(none)'}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('evidence')}`}>
                    <div className="text-xs text-gray-500">Evidence ({conflict.left.evidence.length})</div>
                    <div className="flex flex-wrap gap-1">
                      {conflict.left.evidence.slice(0, 3).map(doc => (
                        <span key={doc.id} className="text-xs bg-gray-200 px-2 py-1 rounded">
                          {doc.title}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="bg-red-50 p-3 rounded-lg mb-2">
                  <div className="font-medium text-red-700">{rightParty}</div>
                  <div className="text-xs text-gray-500">Version by: {conflict.right.created_by_username}</div>
                </div>
                <div className="space-y-2">
                  <div className={`p-2 rounded ${getFieldDiff('date')}`}>
                    <div className="text-xs text-gray-500">Date</div>
                    <div>{conflict.right.date}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('event')}`}>
                    <div className="text-xs text-gray-500">Event</div>
                    <div>{conflict.right.event}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('category')}`}>
                    <div className="text-xs text-gray-500">Category</div>
                    <div className="capitalize">{conflict.right.category}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('notes')}`}>
                    <div className="text-xs text-gray-500">Notes</div>
                    <div>{conflict.right.notes || '(none)'}</div>
                  </div>
                  <div className={`p-2 rounded ${getFieldDiff('evidence')}`}>
                    <div className="text-xs text-gray-500">Evidence ({conflict.right.evidence.length})</div>
                    <div className="flex flex-wrap gap-1">
                      {conflict.right.evidence.slice(0, 3).map(doc => (
                        <span key={doc.id} className="text-xs bg-gray-200 px-2 py-1 rounded">
                          {doc.title}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Resolution Options */}
          {activeTab === 'resolve' && (
            <div className="space-y-4">
              <h3 className="font-semibold">Quick Resolution</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => handleResolve('ACCEPT_LEFT')}
                  className="bg-blue-500 text-white py-3 px-4 rounded-lg hover:bg-blue-600 transition-colors"
                >
                  ✓ Accept {leftParty}'s Version
                </button>
                <button
                  onClick={() => handleResolve('ACCEPT_RIGHT')}
                  className="bg-red-500 text-white py-3 px-4 rounded-lg hover:bg-red-600 transition-colors"
                >
                  ✓ Accept {rightParty}'s Version
                </button>
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => handleResolve('STIPULATED')}
                  className="bg-green-500 text-white py-3 px-4 rounded-lg hover:bg-green-600 transition-colors flex-1"
                >
                  ✓ Create Stipulated Version
                </button>
                <button
                  onClick={() => setActiveTab('merge')}
                  className="bg-gray-500 text-white py-3 px-4 rounded-lg hover:bg-gray-600 transition-colors flex-1"
                >
                  Merge Versions
                </button>
              </div>
            </div>
          )}

          {activeTab === 'merge' && (
            <div className="space-y-4">
              <h3 className="font-semibold">Merge Versions</h3>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input
                    type="date"
                    value={mergedData.date}
                    onChange={(e) => setMergedData({...mergedData, date: e.target.value})}
                    className="w-full p-2 border rounded"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Event Title</label>
                  <input
                    type="text"
                    value={mergedData.event}
                    onChange={(e) => setMergedData({...mergedData, event: e.target.value})}
                    className="w-full p-2 border rounded"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={mergedData.category}
                    onChange={(e) => setMergedData({...mergedData, category: e.target.value as any})}
                    className="w-full p-2 border rounded"
                  >
                    <option value="contract">Contract</option>
                    <option value="email">Email</option>
                    <option value="court_filing">Court Filing</option>
                    <option value="communication">Communication</option>
                    <option value="meeting">Meeting</option>
                    <option value="deadline">Deadline</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <textarea
                    value={mergedData.notes}
                    onChange={(e) => setMergedData({...mergedData, notes: e.target.value})}
                    rows={4}
                    className="w-full p-2 border rounded"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Citation</label>
                  <input
                    type="text"
                    value={mergedData.citation}
                    onChange={(e) => setMergedData({...mergedData, citation: e.target.value})}
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>

              <div className="flex gap-4 pt-4">
                <button
                  onClick={() => handleResolve('MERGE')}
                  className="bg-primary text-white py-2 px-6 rounded-lg hover:opacity-80 transition-opacity flex-1"
                >
                  Create Merged Version
                </button>
                <button
                  onClick={() => setActiveTab('resolve')}
                  className="bg-gray-300 text-gray-700 py-2 px-6 rounded-lg hover:bg-gray-400 transition-colors flex-1"
                >
                  Back
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConflictResolverModal;
