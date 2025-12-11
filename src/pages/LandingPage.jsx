import React from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import Features from '../components/Features';
import './LandingPage.css';

const LandingPage = () => {
    return (
        <div className="landing-page">
            <Navbar />
            <main>
                <Hero />
                <Features />
            </main>
            <footer className="footer">
                <div className="container">
                    <p>&copy; {new Date().getFullYear()} AI PM Buddy. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;
