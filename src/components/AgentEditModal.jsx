import React, { useState } from 'react';
import { X } from 'lucide-react';

const AgentEditModal = ({ agent, onClose, onSaved }) => {
    const [formData, setFormData] = useState({
        name: agent.name || '',
        description: agent.description || '',
        instructions: agent.instructions || '',
        knowledge: agent.knowledge || '',
        tools: agent.tools ? agent.tools.join(', ') : '',
        model: agent.model || '',
        //temperature: agent.temperature || 0.7,
        //max_tokens: agent.max_tokens || 2000,
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        // Prepare payload, converting tools string back to array
        const payload = {
            ...formData,
            tools: formData.tools ? formData.tools.split(',').map((t) => t.trim()) : [],
        };
        try {
            const response = await fetch(`${process.env.VITE_BACKEND_URL || ''}/api/agents/${agent.id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to update agent');
            }
            onSaved();
        } catch (err) {
            console.error('Error updating agent:', err);
            alert(err.message);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="relative bg-[var(--bg-primary)] rounded-xl shadow-2xl w-full max-w-2xl mx-4 p-8 glass-card">
                <h2 className="text-2xl font-bold mb-6 text-[var(--text-primary)] text-center">Edit Agent</h2>
                <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Name</label>
                            <input name="name" value={formData.name} onChange={handleChange} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" required />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Model</label>
                            <input name="model" value={formData.model} onChange={handleChange} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" required />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Description</label>
                        <input name="description" value={formData.description} onChange={handleChange} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Instructions</label>
                        <textarea name="instructions" value={formData.instructions} onChange={handleChange} rows={3} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Tools (comma separated)</label>
                        <input name="tools" value={formData.tools} onChange={handleChange} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Knowledge</label>
                        <input name="knowledge" value={formData.knowledge} onChange={handleChange} className="w-full border border-[var(--border-color)] rounded-md px-3 py-2 bg-[var(--bg-secondary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]" />
                    </div>
                    <div className="flex justify-end space-x-3 pt-4">
                        <button type="button" onClick={onClose} className="px-5 py-2 bg-[var(--bg-secondary)] text-[var(--text-secondary)] rounded-md hover:bg-[var(--bg-primary)] transition-colors">Cancel</button>
                        <button type="submit" className="px-5 py-2 bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white rounded-md hover:opacity-90 transition-opacity">Save Changes</button>
                    </div>
                </form>
                <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors"><X size={20} /></button>
            </div>
        </div>
    );
};

export default AgentEditModal;
