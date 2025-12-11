import React from 'react';
import WorldMap from '../components/WorldMap';
import ProjectStats from '../components/ProjectStats';
import ProjectsTable from '../components/ProjectsTable.jsx';
import './Dashboard.css';

const Dashboard = () => {
    return (
        <div className="dashboard-page">
            <div className="container">
                <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
                <div className="dashboard-grid">
                    <div className="stats-column">
                        <ProjectStats />
                    </div>
                    <div className="map-column">
                        <WorldMap />
                    </div>
                </div>
                <ProjectsTable />
            </div>
        </div>
    );
};

export default Dashboard;
