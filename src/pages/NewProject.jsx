import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import './NewProject.css';

const NewProject = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        project_name: '',
        ct_name: '',
        country: '',
        forecast_start_date: '',
        forecast_end_date: '',
        currency: '',
        scope: '',
        admins: '',
        sharepoint_folder_path: ''
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                alert('You must be logged in to create a project');
                return;
            }

            // Convert admins string to array
            const adminsArray = formData.admins.split(',').map(admin => admin.trim()).filter(Boolean);

            const { error } = await supabase
                .from('projects')
                .insert([
                    {
                        project_name: formData.project_name,
                        ct_name: formData.ct_name,
                        country: formData.country,
                        forecast_start_date: formData.forecast_start_date,
                        forecast_end_date: formData.forecast_end_date,
                        currency: formData.currency,
                        scope: formData.scope,
                        admins: adminsArray,
                        sharepoint_folder_path: formData.sharepoint_folder_path,
                        user_id: user.id
                    }
                ]);

            if (error) throw error;

            if (error) throw error;

            console.log("Supabase entry created, attempting backend folder creation...");

            // Create Folders via Backend if path is provided
            if (formData.sharepoint_folder_path) {
                try {
                    const response = await fetch('http://localhost:8000/api/folders/create', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            path: formData.sharepoint_folder_path
                        }),
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to create folders');
                    }

                    alert('Project and local folders created successfully!');
                } catch (folderError) {
                    console.error("Folder Creation Error:", folderError);
                    alert('Project created in DB, but folder creation failed: ' + folderError.message);
                }
            } else {
                alert('Project created successfully (No folder path provided).');
            }

            navigate('/dashboard');
        } catch (error) {
            console.error('Error creating project:', error);
            alert('Error creating project: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="new-project-page">
            <div className="new-project-container">
                <h1 className="text-3xl font-bold mb-8 text-[var(--text-primary)]">Create New Project</h1>

                <form onSubmit={handleSubmit} className="glass-card p-8 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Project Name */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                Project Name
                            </label>
                            <input
                                type="text"
                                name="project_name"
                                value={formData.project_name}
                                onChange={handleChange}
                                required
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                                placeholder="Enter project name"
                            />
                        </div>

                        {/* CT Name */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                CT Name
                            </label>
                            <input
                                type="text"
                                name="ct_name"
                                value={formData.ct_name}
                                onChange={handleChange}
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                                placeholder="Enter CT name"
                            />
                        </div>

                        {/* Country */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                Country
                            </label>
                            <input
                                type="text"
                                name="country"
                                value={formData.country}
                                onChange={handleChange}
                                required
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                                placeholder="Enter country"
                            />
                        </div>

                        {/* Currency */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                Currency
                            </label>
                            <input
                                type="text"
                                name="currency"
                                value={formData.currency}
                                onChange={handleChange}
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                                placeholder="USD, EUR, etc."
                            />
                        </div>

                        {/* Forecast Start Date */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                Forecast Start Date
                            </label>
                            <input
                                type="date"
                                name="forecast_start_date"
                                value={formData.forecast_start_date}
                                onChange={handleChange}
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            />
                        </div>

                        {/* Forecast End Date */}
                        <div>
                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                Forecast End Date
                            </label>
                            <input
                                type="date"
                                name="forecast_end_date"
                                value={formData.forecast_end_date}
                                onChange={handleChange}
                                className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            />
                        </div>
                    </div>

                    {/* Admins */}
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            Admins (comma separated)
                        </label>
                        <input
                            type="text"
                            name="admins"
                            value={formData.admins}
                            onChange={handleChange}
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="admin1@example.com, admin2@example.com"
                        />
                    </div>

                    {/* Local Project Path */}
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            Local Project Path
                        </label>
                        <input
                            type="text"
                            name="sharepoint_folder_path"
                            value={formData.sharepoint_folder_path}
                            onChange={handleChange}
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="C:\Users\YourName\OneDrive\ProjectFolder"
                        />
                        <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md flex items-start gap-2 text-yellow-800 text-sm">
                            <span className="font-semibold">Note:</span>
                            <span>Please Sync this local Path with your Sharepoint Folder Path.</span>
                        </div>
                    </div>

                    {/* Scope */}
                    <div>
                        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            Scope
                        </label>
                        <textarea
                            name="scope"
                            value={formData.scope}
                            onChange={handleChange}
                            rows="4"
                            className="w-full px-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
                            placeholder="Enter project scope details..."
                        ></textarea>
                    </div>

                    {/* Submit Button */}
                    <div className="flex justify-end pt-4">
                        <button
                            type="button"
                            onClick={() => navigate('/dashboard')}
                            className="mr-4 px-6 py-2 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-6 py-2 rounded-lg bg-[var(--accent-primary)] text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50"
                        >
                            {loading ? 'Creating...' : 'Create Project'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default NewProject;
