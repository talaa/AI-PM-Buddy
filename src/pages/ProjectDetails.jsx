import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { ArrowLeft, Calendar, Globe, CreditCard, Users, Briefcase } from 'lucide-react';

const ProjectDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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
        } catch (error) {
            console.error('Error fetching project details:', error);
            setError(error.message);
        } finally {
            setLoading(false);
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
                <button
                    onClick={() => navigate('/dashboard')}
                    className="flex items-center text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors mb-6"
                >
                    <ArrowLeft size={20} className="mr-2" />
                    Back to Dashboard
                </button>

                <div className="glass-card p-8 mb-8">
                    <div className="flex justify-between items-start mb-6">
                        <div>
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
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-[var(--text-secondary)] mb-1">Currency</div>
                            <div className="text-xl font-semibold flex items-center justify-end gap-1">
                                <CreditCard size={20} />
                                {project.currency || 'N/A'}
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                        {/* Dates */}
                        <div className="bg-[var(--bg-secondary)] p-4 rounded-lg">
                            <div className="flex items-center gap-2 mb-2 text-[var(--accent-primary)]">
                                <Calendar size={20} />
                                <h3 className="font-semibold">Timeline</h3>
                            </div>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-secondary)]">Start Date:</span>
                                    <span>{project.forecast_start_date || 'Not set'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-secondary)]">End Date:</span>
                                    <span>{project.forecast_end_date || 'Not set'}</span>
                                </div>
                            </div>
                        </div>

                        {/* Admins */}
                        <div className="bg-[var(--bg-secondary)] p-4 rounded-lg md:col-span-2">
                            <div className="flex items-center gap-2 mb-2 text-[var(--accent-primary)]">
                                <Users size={20} />
                                <h3 className="font-semibold">Project Admins</h3>
                            </div>
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
                        </div>
                    </div>

                    {/* Scope */}
                    <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4 border-b border-[var(--border-color)] pb-2">Project Scope</h3>
                        <div className="prose prose-invert max-w-none text-[var(--text-secondary)] whitespace-pre-wrap">
                            {project.scope || 'No scope definition provided.'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProjectDetails;
