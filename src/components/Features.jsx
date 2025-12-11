import React from 'react';
import { Zap, Shield, BarChart3, Users } from 'lucide-react';
import './Features.css';

const features = [
    {
        icon: <Zap size={24} />,
        title: "Instant Analysis",
        description: "Get real-time insights on your product metrics and user behavior with AI-driven analytics."
    },
    {
        icon: <Shield size={24} />,
        title: "Secure & Private",
        description: "Enterprise-grade security ensures your data remains protected and compliant at all times."
    },
    {
        icon: <BarChart3 size={24} />,
        title: "Predictive Growth",
        description: "Forecast trends and identify growth opportunities before they happen with advanced modeling."
    },
    {
        icon: <Users size={24} />,
        title: "Team Collaboration",
        description: "Seamlessly share insights and collaborate with your team in a unified workspace."
    }
];

const Features = () => {
    return (
        <section className="features">
            <div className="container">
                <div className="features-grid">
                    {features.map((feature, index) => (
                        <div key={index} className="feature-card glass-card">
                            <div className="feature-icon">{feature.icon}</div>
                            <h3 className="feature-title">{feature.title}</h3>
                            <p className="feature-description">{feature.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default Features;
