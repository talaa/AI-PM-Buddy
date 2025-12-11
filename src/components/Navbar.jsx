import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot, User, Settings, LogOut, Plus, LayoutDashboard } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import './Navbar.css';

const Navbar = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [showProfileMenu, setShowProfileMenu] = useState(false);

    useEffect(() => {
        // Check active session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setUser(session?.user ?? null);
        });

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
            setUser(session?.user ?? null);
        });

        return () => subscription.unsubscribe();
    }, []);

    const handleLogout = async () => {
        await supabase.auth.signOut();
        navigate('/');
        setShowProfileMenu(false);
    };

    return (
        <nav className="navbar">
            <div className="container navbar-content">
                <Link to={user ? "/dashboard" : "/"} className="logo">
                    <Bot className="logo-icon" />
                    <span>AI PM Buddy</span>
                </Link>

                <div className="nav-links">
                    {user ? (
                        <>
                            <Link to="/dashboard" className="nav-link flex items-center gap-2">
                                <LayoutDashboard size={18} />
                                <span>Dashboard</span>
                            </Link>
                            <Link to="/agents" className="nav-link flex items-center gap-2">
                                <Bot size={18} />
                                <span>Agents</span>
                            </Link>
                            <Link to="/new-project" className="nav-link flex items-center gap-2">
                                <Plus size={18} />
                                <span>New Project</span>
                            </Link>

                            <div className="relative">
                                <button
                                    className="flex items-center gap-2 nav-link"
                                    onClick={() => setShowProfileMenu(!showProfileMenu)}
                                >
                                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-[var(--accent-primary)]">
                                        <User size={18} />
                                    </div>
                                </button>

                                {showProfileMenu && (
                                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-[var(--border-color)] py-1 z-50">
                                        <Link
                                            to="/profile"
                                            className="flex items-center gap-2 px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] hover:text-[var(--text-primary)] transition-colors"
                                            onClick={() => setShowProfileMenu(false)}
                                        >
                                            <Settings size={16} />
                                            <span>Settings</span>
                                        </Link>
                                        <button
                                            onClick={handleLogout}
                                            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-50 transition-colors"
                                        >
                                            <LogOut size={16} />
                                            <span>Logout</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="nav-link">
                                Log in
                            </Link>
                            <Link to="/signup" className="btn btn-primary">
                                Sign up
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;