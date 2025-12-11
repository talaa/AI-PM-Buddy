import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import './Hero.css';

const Hero = () => {
    return (
        <section className="hero">
            <div className="container hero-content">
                <div className="hero-badge">
                    <Sparkles size={16} />
                    <span>AI-Powered Product Management</span>
                </div>

                <h1 className="hero-title">
                    Your Intelligent <br />
                    <span className="gradient-text">Product Companion</span>
                </h1>

                <p className="hero-subtitle">
                    Streamline your workflow, generate insights, and manage products with the power of advanced AI. The future of product management is here.
                </p>

                <div className="hero-actions">
                    <Link to="/signup" className="btn btn-primary btn-lg">
                        Get Started <ArrowRight size={20} />
                    </Link>
                    <Link to="/login" className="btn btn-outline btn-lg">
                        Live Demo
                    </Link>
                </div>
            </div>
        </section>
    );
};

export default Hero;
