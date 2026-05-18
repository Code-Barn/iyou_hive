import React, { useState } from "react";

interface CaseInitializationModalProps {
  onCreateCase: (name: string, description: string, clientLegalName: string, opposingLegalName: string) => Promise<void>;
}

const CaseInitializationModal: React.FC<CaseInitializationModalProps> = ({
  onCreateCase,
}) => {
  const [name, setName] = useState("");
  const [clientLegalName, setClientLegalName] = useState("");
  const [opposingLegalName, setOpposingLegalName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsCreating(true);
    setError(null);

    try {
      await onCreateCase(name.trim(), description.trim(), clientLegalName.trim(), opposingLegalName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Welcome to Hiver</h2>
          <p className="text-sm text-gray-600 mt-1">
            Create a case to get started with forensic timeline analysis.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Case Reference Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Byers v. Donatello"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Client Filing Legal Name
            </label>
            <input
              type="text"
              value={clientLegalName}
              onChange={(e) => setClientLegalName(e.target.value)}
              placeholder="e.g. David Byers"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Opposing Party Legal Name
            </label>
            <input
              type="text"
              value={opposingLegalName}
              onChange={(e) => setOpposingLegalName(e.target.value)}
              placeholder="e.g. Pauletta Donatello"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the case..."
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-100 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isCreating || !name.trim()}
            className="w-full bg-primary text-white py-2 rounded-lg text-sm font-medium hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isCreating ? "Creating Case..." : "Create Case"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default CaseInitializationModal;
