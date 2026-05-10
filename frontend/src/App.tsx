import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import CaseInitializationModal from "./components/CaseInitializationModal";
import { SourceParty } from "./types/timeline";
import { archiveApi } from "./api/archive";
import { useMutation } from "@tanstack/react-query";

const queryClient = new QueryClient();

const App: React.FC = () => {
  const [caseId, setCaseId] = useState<string>("");
  const [userParty, setUserParty] = useState<SourceParty>("CLIENT");
  const [showInitModal, setShowInitModal] = useState(true);

  const createCaseMutation = useMutation({
    mutationFn: async (data: { name: string; description: string }) => {
      const response = await archiveApi.createCase(data.name, data.description);
      return response.data;
    },
    onSuccess: (data) => {
      const newCaseId = data.id || data.case_id;
      setCaseId(newCaseId);
      setUserParty("CLIENT");
      setShowInitModal(false);
      const timelineApp = document.getElementById("timeline-app");
      if (timelineApp) {
        timelineApp.dataset.caseId = newCaseId;
        timelineApp.dataset.userParty = "CLIENT";
      }
    },
  });

  const handleCaseSelect = (newCaseId: string) => {
    setCaseId(newCaseId);
    const timelineApp = document.getElementById("timeline-app");
    if (timelineApp) {
      timelineApp.dataset.caseId = newCaseId;
    }
  };

  const handleEventAdded = () => {
    queryClient.invalidateQueries({ queryKey: ["events"] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
  };

  return (
    <QueryClientProvider client={queryClient}>
      {showInitModal && !caseId && (
        <CaseInitializationModal
          onCreateCase={async (name, description) => {
            await createCaseMutation.mutateAsync({ name, description });
          }}
        />
      )}
      {caseId && (
        <Layout
          caseId={caseId}
          userParty={userParty}
          onCaseSelect={handleCaseSelect}
          onEventAdded={handleEventAdded}
        />
      )}
    </QueryClientProvider>
  );
};

export default App;
