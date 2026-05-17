import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "./components/Layout";
import CaseInitializationModal from "./components/CaseInitializationModal";
import { SourceParty } from "./types/timeline";
import { archiveApi } from "./api/archive";

const root = document.getElementById("timeline-app");
const rawCaseId = root?.dataset?.caseId || "";
const bootCaseId =
  rawCaseId && rawCaseId !== "None" && rawCaseId !== "null" ? rawCaseId : "";

const App: React.FC = () => {
  const queryClient = useQueryClient();
  const [caseId, setCaseId] = useState<string>(bootCaseId);
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
    <>
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
    </>
  );
};

export default App;
