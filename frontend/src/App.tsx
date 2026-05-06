import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DiffView from './components/DiffView';
import SimplifiedView from './components/SimplifiedView';
import { SourceParty } from './types/timeline';

const queryClient = new QueryClient();

const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<'diff' | 'simplified'>('diff');
  const [userParty, setUserParty] = useState<SourceParty>('CLIENT');
  const [caseId, setCaseId] = useState<string>('');

  // In a real app, this would come from:
  // 1. URL params
  // 2. User authentication (which party the user represents)
  // 3. Case selection

  // For demo purposes, we'll use a hardcoded case ID
  useEffect(() => {
    // This would be set from the Django template or URL
    // For now, we'll leave it empty and pass it to child components
  }, []);

  // Get case ID and user party from data attributes (set by Django template)
  useEffect(() => {
    const caseIdAttr = document.getElementById('timeline-app')?.dataset.caseId;
    const userPartyAttr = document.getElementById('timeline-app')?.dataset.userParty as SourceParty;

    if (caseIdAttr) setCaseId(caseIdAttr);
    if (userPartyAttr) setUserParty(userPartyAttr);
  }, []);

  const handleCaseSelect = (caseId: string) => {
    setCaseId(caseId);
  };

  if (!caseId) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>Please select a case to view the timeline.</p>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-full flex flex-col">
        {/* View Mode Toggle */}
        <div className="border-b bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-800">Legal Timeline</h1>
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('diff')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    viewMode === 'diff'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Git-Style Diff
                </button>
                <button
                  onClick={() => setViewMode('simplified')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    viewMode === 'simplified'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Simplified View
                </button>
              </div>
            </div>
            <div className="text-sm text-gray-500">
              <span className="font-medium">User:</span> {userParty}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 max-w-7xl mx-auto w-full p-4">
          {viewMode === 'diff' && (
            <DiffView
              caseId={caseId}
              userParty={userParty}
              leftParty="CLIENT"
              rightParty="OPPOSING"
            />
          )}
          {viewMode === 'simplified' && (
            <SimplifiedView
              caseId={caseId}
              userParty={userParty}
            />
          )}
        </div>
      </div>
    </QueryClientProvider>
  );
};

export default App;
