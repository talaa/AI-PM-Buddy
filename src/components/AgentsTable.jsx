import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { Bot, FileText, Wrench, Brain, MessageSquare } from 'lucide-react';
import AgentEditModal from './AgentEditModal';

const AgentsTable = () => {
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditOpen, setIsEditOpen] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState(null);

    useEffect(() => {
        fetchAgents();
    }, []);

    const fetchAgents = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('agents')
                .select('*')
                .order('created_at', { ascending: false });

            if (error) throw error;
            setAgents(data);
        } catch (error) {
            console.error('Error fetching agents:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="text-center py-8 text-[var(--text-secondary)]">Loading agents...</div>;
    }

    if (error) {
        return <div className="text-center py-8 text-red-500">Error: {error}</div>;
    }

    if (agents.length === 0) {
        return (
            <div className="glass-card p-12 text-center">
                <Bot size={48} className="mx-auto mb-4 text-[var(--text-secondary)] opacity-50" />
                <h3 className="text-xl font-semibold mb-2">No Agents Found</h3>
                <p className="text-[var(--text-secondary)]">Create your first AI agent to get started.</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
                <div key={agent.id} className="glass-card p-6 hover:border-[var(--accent-primary)] transition-colors border border-[var(--border-color)] rounded-xl">
                    <div className="flex items-start justify-between mb-4">
                        <div className="p-3 rounded-lg bg-blue-500/10 text-[var(--accent-primary)]">
                            <Bot size={24} />
                        </div>
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-color)]">
                            {agent.model || 'Default Model'}
                        </span>
                    </div>

                    <h3 className="text-xl font-bold mb-2 text-[var(--text-primary)]">{agent.name}</h3>
                    <p className="text-[var(--text-secondary)] text-sm mb-4 line-clamp-2">
                        {agent.description || 'No description provided.'}
                    </p>

                    <div className="flex items-center justify-between border-t border-[var(--border-color)] pt-4 mt-auto">
                        <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
                            {agent.tools && agent.tools.length > 0 && (
                                <div className="flex items-center gap-1" title="Tools">
                                    <Wrench size={14} />
                                    <span>{agent.tools.length}</span>
                                </div>
                            )}
                            {agent.knowledge && (
                                <div className="flex items-center gap-1" title="Knowledge Base">
                                    <Brain size={14} />
                                    <span>Know</span>
                                </div>
                            )}
                        </div>
                        <Link to={`/agents/${agent.id}/chat`} className="flex items-center gap-1 text-sm font-medium text-[var(--accent-primary)] hover:underline">Chat <MessageSquare size={14} /></Link>
                        <button onClick={() => { setSelectedAgent(agent); setIsEditOpen(true); }} className="ml-2 text-sm text-[var(--accent-primary)] hover:underline">Edit</button>
                    </div>
                </div>
            ))}
            {isEditOpen && selectedAgent && (
                <AgentEditModal
                    agent={selectedAgent}
                    onClose={() => setIsEditOpen(false)}
                    onSaved={() => { setIsEditOpen(false); fetchAgents(); }}
                />
            )}
        </div>
    );
};

export default AgentsTable;
