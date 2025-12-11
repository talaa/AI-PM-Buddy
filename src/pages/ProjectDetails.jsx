import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { ArrowLeft, Calendar, Globe, CreditCard, Users, Briefcase, Pencil, Save, X } from 'lucide-react';

const ProjectDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({});
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchProjectDetails();
    }, [id]);

    const fetchProjectDetails = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('projects')
                .select('*')
                .eq('id', id)
                .single();

            if (error) throw error;
            setProject(data);
            setFormData(data); // Initialize form data
        } catch (error) {
            console.error('Error fetching project details:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = () => {
        setIsEditing(true);
        // Ensure formData is fresh (in case of background updates, though unlikely with current flow)
        setFormData({
            ...project,
            // Convert admins array back to string for editing if it's an array
            admins: Array.isArray(project.admins) ? project.admins.join(', ') : (project.admins || '')
        });
    };

    const handleCancel = () => {
        setIsEditing(false);
        setFormData(project);
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSave = async () => {
        try {
            setSaving(true);

            // Prepare data for update
            const updates = {
                ...formData,
                // Convert admins string back to array
                admins: typeof formData.admins === 'string'
                    ? formData.admins.split(',').map(a => a.trim()).filter(Boolean)
                    : formData.admins,
                updated_at: new Date().toISOString()
            };

            const { error } = await supabase
                .from('projects')
                .update(updates)
                .eq('id', id);

            if (error) throw error;

            // Update local state
            setProject(updates);
            setIsEditing(false);
            alert('Project updated successfully!');
        } catch (error) {
            console.error('Error updating project:', error);
            alert('Error updating project: ' + error.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
                <div className="text-[var(--text-secondary)]">Loading project details...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
                <div className="text-red-500">Error: {error}</div>
            </div>
        );
    }

    if (!project) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
                <div className="text-[var(--text-secondary)]">Project not found</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] p-8 pt-24">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors"
                    >
                        <ArrowLeft size={20} className="mr-2" />
                        Back to Dashboard
                    </button>

                    <div className="flex gap-2">
                        {isEditing ? (
                            <>
                                <button
                                    onClick={handleCancel}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-gray-700 transition-colors"
                                    disabled={saving}
                                >
                                    <X size={18} /> Cancel
                                </button>
                                <button
                                    onClick={handleSave}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-primary)] text-white hover:opacity-90 transition-colors"
                                    disabled={saving}
                                >
                                    <Save size={18} /> {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                            </>
                        ) : (
                            <button
                                onClick={handleEdit}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-secondary)] text-[var(--accent-primary)] hover:bg-gray-700 transition-colors"
                            >
                                <Pencil size={18} /> Edit Project
                            </button>
                        )}
                    </div>
                </div>

                <div className="glass-card p-8 mb-8">
                    <div className="flex justify-between items-start mb-6">
                        <div className="flex-1 mr-8">
                            {isEditing ? (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs text-[var(--text-secondary)] mb-1">Project Name</label>
                                        <input
                                            type="text"
                                            name="project_name"
                                            value={formData.project_name || ''}
                                            onChange={handleChange}
                                            className="w-full text-3xl font-bold bg-[var(--bg-secondary)] border-b border-[var(--accent-primary)] focus:outline-none text-[var(--text-primary)] px-2 py-1 rounded-t"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs text-[var(--text-secondary)] mb-1">Country</label>
                                            <input
                                                type="text"
                                                name="country"
                                                value={formData.country || ''}
                                                onChange={handleChange}
                                                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs text-[var(--text-secondary)] mb-1">CT Name</label>
                                            <input
                                                type="text"
                                                name="ct_name"
                                                value={formData.ct_name || ''}
                                                onChange={handleChange}
                                                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)]"
                                            />
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <h1 className="text-4xl font-bold mb-2">{project.project_name}</h1>
                                    <div className="flex items-center text-[var(--text-secondary)] gap-4">
                                        <span className="flex items-center gap-1">
                                            <Globe size={16} />
                                            {project.country}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Briefcase size={16} />
                                            {project.ct_name || 'No CT Name'}
                                        </span>
                                    </div>
                                </>
                            )}
                        </div>

                        <div className="text-right min-w-[150px]">
                            <div className="text-sm text-[var(--text-secondary)] mb-1">Currency</div>
                            {isEditing ? (
                                <input
                                    type="text"
                                    name="currency"
                                    value={formData.currency || ''}
                                    onChange={handleChange}
                                    className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)] text-right"
                                    placeholder="USD"
                                />
                            ) : (
                                <div className="text-xl font-semibold flex items-center justify-end gap-1">
                                    <CreditCard size={20} />
                                    {project.currency || 'N/A'}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                        {/* Dates */}
                        <div className="bg-[var(--bg-secondary)] p-4 rounded-lg">
                            <div className="flex items-center gap-2 mb-2 text-[var(--accent-primary)]">
                                <Calendar size={20} />
                                <h3 className="font-semibold">Timeline</h3>
                            </div>
                            <div className="space-y-4 text-sm">
                                <div className="flex flex-col">
                                    <span className="text-[var(--text-secondary)] mb-1">Start Date:</span>
                                    {isEditing ? (
                                        <input
                                            type="date"
                                            name="forecast_start_date"
                                            value={formData.forecast_start_date || ''}
                                            onChange={handleChange}
                                            className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-2 py-1 text-[var(--text-primary)]"
                                        />
                                    ) : (
                                        <span>{project.forecast_start_date || 'Not set'}</span>
                                    )}
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-[var(--text-secondary)] mb-1">End Date:</span>
                                    {isEditing ? (
                                        <input
                                            type="date"
                                            name="forecast_end_date"
                                            value={formData.forecast_end_date || ''}
                                            onChange={handleChange}
                                            className="bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-2 py-1 text-[var(--text-primary)]"
                                        />
                                    ) : (
                                        <span>{project.forecast_end_date || 'Not set'}</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Admins */}
                        <div className="bg-[var(--bg-secondary)] p-4 rounded-lg md:col-span-2">
                            <div className="flex items-center gap-2 mb-2 text-[var(--accent-primary)]">
                                <Users size={20} />
                                <h3 className="font-semibold">Project Admins</h3>
                            </div>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="text"
                                        name="admins"
                                        value={formData.admins || ''}
                                        onChange={handleChange}
                                        className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-[var(--text-primary)]"
                                        placeholder="admin1@example.com, admin2@example.com"
                                    />
                                    <p className="text-xs text-[var(--text-secondary)] mt-1">Separate multiple emails with commas</p>
                                </div>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {project.admins && project.admins.length > 0 ? (
                                        project.admins.map((admin, index) => (
                                            <span key={index} className="px-3 py-1 bg-[var(--bg-primary)] rounded-full text-sm border border-[var(--border-color)]">
                                                {admin}
                                            </span>
                                        ))
                                    ) : (
                                        <span className="text-[var(--text-secondary)] text-sm">No admins assigned</span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Scope */}
                    <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4 border-b border-[var(--border-color)] pb-2">Project Scope</h3>
                        {isEditing ? (
                            <textarea
                                name="scope"
                                value={formData.scope || ''}
                                onChange={handleChange}
                                rows="6"
                                className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
                                placeholder="Enter project scope details..."
                            ></textarea>
                        ) : (
                            <div className="prose prose-invert max-w-none text-[var(--text-secondary)] whitespace-pre-wrap">
                                {project.scope || 'No scope definition provided.'}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProjectDetails;
