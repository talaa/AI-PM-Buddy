import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import ProjectForm from '../components/ProjectForm';
import './NewProject.css';

const NewProject = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);

    const handleCreateProject = async (data) => {
        setLoading(true);

        try {
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                alert('You must be logged in to create a project');
                return;
            }

            // Convert admins string to array
            const adminsArray = data.admins.split(',').map(admin => admin.trim()).filter(Boolean);

            const { error } = await supabase
                .from('projects')
                .insert([
                    {
                        project_name: data.project_name,
                        ct_name: data.ct_name,
                        country: data.country,
                        forecast_start_date: data.forecast_start_date,
                        forecast_end_date: data.forecast_end_date,
                        currency: data.currency,
                        scope: data.scope,
                        admins: adminsArray,
                        sharepoint_folder_path: data.sharepoint_folder_path,
                        user_id: user.id
                    }
                ]);

            if (error) throw error;

            console.log("Supabase entry created, attempting backend folder creation...");

            // Create Folders via Backend if path is provided
            if (data.sharepoint_folder_path) {
                try {
                    const response = await fetch('http://localhost:8000/api/folders/create', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            path: data.sharepoint_folder_path
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

                <ProjectForm
                    onSubmit={handleCreateProject}
                    onCancel={() => navigate('/dashboard')}
                    loading={loading}
                />
            </div>
        </div>
    );
};

export default NewProject;
