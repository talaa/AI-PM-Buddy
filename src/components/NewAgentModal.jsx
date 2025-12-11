import React, { useState } from 'react';
import { supabase } from '../lib/supabaseClient';
import { X, Upload, Check } from 'lucide-react';

const NewAgentModal = ({ onClose, onCreated }) => {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        instructions: '',
        model: 'llama3',
        tools: [],
        knowledge: ''
    });

    const AVAILABLE_TOOLS = ['Web Search', 'Data Analysis', 'Image Generation', 'Code Interpreter'];

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleToolToggle = (tool) => {
        setFormData(prev => {
            const tools = prev.tools.includes(tool)
                ? prev.tools.filter(t => t !== tool)
                : [...prev.tools, tool];
            return { ...prev, tools };
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error('User not authenticated');

            // Create agent record
            const { error: insertError } = await supabase
                .from('agents')
                .insert([{
                    name: formData.name,
                    description: formData.description,
                    instructions: formData.instructions,
                    model: formData.model,
                    tools: formData.tools,
                    knowledge_path: formData.knowledge,
                    user_id: user.id
                }]);

            if (insertError) throw insertError;

            onCreated();
        } catch (error) {
            console.error('Error creating agent:', error);
            alert('Error creating agent: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center p-6 border-b border-[var(--border-color)]">
                    <h2 className="text-2xl font-bold">Create New Agent</h2>
                    <button onClick={onClose} className="p-2 hover:bg-[var(--bg-secondary)] rounded-full transition-colors">
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    <div>
                        <label className="block text-sm font-medium mb-2">Agent Name</label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            required
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="e.g., Strategic Planner"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Description</label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows="2"
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="Briefly describe what this agent does..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Instructions (System Prompt)</label>
                        <textarea
                            name="instructions"
                            value={formData.instructions}
                            onChange={handleChange}
                            required
                            rows="4"
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="You are a helpful assistant that specializes in..."
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium mb-2">Model</label>
                            <select
                                name="model"
                                value={formData.model}
                                onChange={handleChange}
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            >
                                <option value="llama3">Llama 3</option>
                                <option value="mistral">Mistral</option>
                                <option value="gemma">Gemma</option>
                                <option value="phi3">Phi-3</option>
                                <option value="llama2">Llama 2</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Knowledge Base (Context)</label>
                            <textarea
                                name="knowledge"
                                value={formData.knowledge}
                                onChange={handleChange}
                                rows="5"
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                                placeholder="Paste any context or knowledge base text here..."
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">Capabilities / Tools</label>
                        <div className="grid grid-cols-2 gap-3">
                            {AVAILABLE_TOOLS.map(tool => (
                                <button
                                    key={tool}
                                    type="button"
                                    onClick={() => handleToolToggle(tool)}
                                    className={`flex items-center gap-2 px-4 py-3 rounded-lg border text-sm transition-all ${formData.tools.includes(tool)
                                        ? 'bg-blue-500/10 border-[var(--accent-primary)] text-[var(--accent-primary)]'
                                        : 'border-[var(--border-color)] hover:bg-[var(--bg-secondary)]'
                                        }`}
                                >
                                    <div className={`w-4 h-4 rounded border flex items-center justify-center ${formData.tools.includes(tool) ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-gray-400'
                                        }`}>
                                        {formData.tools.includes(tool) && <Check size={12} className="text-white" />}
                                    </div>
                                    {tool}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-end pt-4 border-t border-[var(--border-color)]">
                        <button
                            type="button"
                            onClick={onClose}
                            className="mr-4 px-6 py-2 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-6 py-2 rounded-lg bg-[var(--accent-primary)] text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? 'Creating...' : 'Create Agent'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default NewAgentModal;
