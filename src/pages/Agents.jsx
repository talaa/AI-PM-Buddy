import React, { useState } from 'react';
import AgentsTable from '../components/AgentsTable';
import NewAgentModal from '../components/NewAgentModal';
import { Plus } from 'lucide-react';

const Agents = () => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const handleAgentCreated = () => {
        setRefreshTrigger(prev => prev + 1);
        setIsModalOpen(false);
    };

    return (
        <div className="min-h-screen bg-[var(--bg-primary)] p-8 pt-24">
            <div className="max-w-7xl mx-auto container">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-[var(--text-primary)]">AI Agents</h1>
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="btn btn-primary gap-2 flex items-center px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        <Plus size={20} />
                        Create Agent
                    </button>
                </div>

                <AgentsTable key={refreshTrigger} />

                {isModalOpen && (
                    <NewAgentModal
                        onClose={() => setIsModalOpen(false)}
                        onCreated={handleAgentCreated}
                    />
                )}
            </div>
        </div>
    );
};

export default Agents;
