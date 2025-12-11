import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, MoreHorizontal } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import './ProjectsTable.css';

const ProjectsTable = () => {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('projects')
                .select('*')
                .order('created_at', { ascending: false });

            if (error) throw error;
            setProjects(data);
        } catch (error) {
            console.error('Error fetching projects:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="projects-section glass-card p-8 flex justify-center items-center">
                <div className="text-[var(--text-secondary)]">Loading projects...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="projects-section glass-card p-8 flex justify-center items-center">
                <div className="text-red-500">Error loading projects: {error}</div>
            </div>
        );
    }

    return (
        <div className="projects-section glass-card">
            <div className="projects-header">
                <h3 className="text-lg font-semibold">Active Projects</h3>
                <Link to="/new-project" className="btn btn-primary btn-sm gap-2">
                    <Plus size={16} /> New Project
                </Link>
            </div>

            <div className="table-container">
                {projects.length === 0 ? (
                    <div className="p-8 text-center text-[var(--text-secondary)]">
                        No projects found. Create your first project!
                    </div>
                ) : (
                    <table className="projects-table">
                        <thead>
                            <tr>
                                <th>Project Name</th>
                                <th>Country</th>
                                <th>Scope</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projects.map((project) => (
                                <tr key={project.id}>
                                    <td className="font-medium">
                                        <Link to={`/project/${project.id}`} className="hover:text-[var(--accent-primary)] hover:underline">
                                            {project.project_name}
                                        </Link>
                                    </td>
                                    <td>{project.country}</td>
                                    <td className="scope-cell">
                                        <div className="line-clamp-2" title={project.scope}>
                                            {project.scope}
                                        </div>
                                    </td>
                                    <td>
                                        <button className="icon-btn">
                                            <MoreHorizontal size={18} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default ProjectsTable;
