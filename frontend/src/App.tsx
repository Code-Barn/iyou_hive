import React, { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import { SourceParty } from "./types/timeline";

const queryClient = new QueryClient();

const App: React.FC = () => {
  const [userParty, setUserParty] = useState<SourceParty>("CLIENT");
  const [caseId, setCaseId] = useState<string>("");

  // Initialize caseId from DOM attributes (set by Django template)
  useEffect(() => {
    const timelineApp = document.getElementById("timeline-app");
    const caseIdAttr = timelineApp?.dataset.caseId || "";
    const userPartyAttr = timelineApp?.dataset.userParty as SourceParty;

    console.log("App: Initializing with caseId:", caseIdAttr);
    setCaseId(caseIdAttr);
    if (userPartyAttr) setUserParty(userPartyAttr);
  }, []);

  const handleCaseSelect = (newCaseId: string) => {
    setCaseId(newCaseId);
    // Update the DOM attribute so Django template is aware
    const timelineApp = document.getElementById("timeline-app");
    if (timelineApp) {
      timelineApp.dataset.caseId = newCaseId;
    }
    // Stay on dashboard - no navigation needed
  };

  // Function to invalidate timeline queries
  const handleEventAdded = () => {
    queryClient.invalidateQueries({ queryKey: ["events"] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
  };

  return (
    <QueryClientProvider client={queryClient}>
      {/* Always render the 3-panel dashboard on / */}
      <Layout
        caseId={caseId}
        userParty={userParty}
        onCaseSelect={handleCaseSelect}
        onToggleFullTimeline={() => {
          // Optional: track if full timeline modal is open
          console.log("Full timeline toggled");
        }}
        onEventAdded={handleEventAdded}
      />
    </QueryClientProvider>
  );
};

export default App;
