import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import ProjectForm from '../components/ProjectForm';

const ProjectDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();

    // --- Project Data State ---
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({});
    const [saving, setSaving] = useState(false);
    const [isCollapsed, setIsCollapsed] = useState(true);
    const [showAddSourceModal, setShowAddSourceModal] = useState(false);

    // --- Upload / Documents State ---
    const [documents, setDocuments] = useState([]);
    const [openCategories, setOpenCategories] = useState({});
    const [selectedFile, setSelectedFile] = useState(null);
    const [sourceData, setSourceData] = useState({
        category: 'Contracts',
        status: 'Draft',
    });
    const [tags, setTags] = useState([]);
    const [tagInput, setTagInput] = useState('');
    const [uploading, setUploading] = useState(false);

    const fileInputRef = useRef(null);

    // --- A2A / Chat State ---
    const [availableAgents, setAvailableAgents] = useState([]);
    const [selectedAgents, setSelectedAgents] = useState([]);
    const [selectedDocuments, setSelectedDocuments] = useState([]); // Array of IDs
    const [chatHistory, setChatHistory] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [projectSessions, setProjectSessions] = useState([]);
    const chatEndRef = useRef(null);

    // --- Initialization ---
    useEffect(() => {
        fetchProjectDetails();
        fetchDocuments();
        fetchAgents();
        fetchProjectSessions();
    }, [id]);

    // Fetch messages when active session changes
    useEffect(() => {
        if (activeSessionId) {
            fetchSessionMessages(activeSessionId);
        } else {
            setChatHistory([]); // Clear if no session
        }
    }, [activeSessionId]);

    useEffect(() => {
        scrollToBottom();
    }, [chatHistory]);

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // --- Fetchers ---
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
            setFormData(data);
        } catch (error) {
            console.error('Error fetching project details:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const fetchDocuments = async () => {
        const { data, error } = await supabase
            .from('project_documents')
            .select('*')
            .eq('project_id', id)
            .order('created_at', { ascending: false });

        if (error) {
            console.error('Error fetching documents:', error);
        } else {
            setDocuments(data || []);
            // Initialize all categories as open by default
            const cats = {};
            (data || []).forEach(d => cats[d.category] = true);
            setOpenCategories(cats);
        }
    };

    const fetchAgents = async () => {
        try {
            const { data, error } = await supabase
                .from('agents')
                .select('*');
            if (error) throw error;
            setAvailableAgents(data || []);
        } catch (err) {
            console.error("Error fetching agents:", err);
        }
    };

    const fetchProjectSessions = async () => {
        try {
            const response = await fetch(`http://localhost:8000/api/projects/${id}/sessions`);
            if (response.ok) {
                const data = await response.json();
                setProjectSessions(data);
                // Auto-select latest session if exists
                if (data && data.length > 0 && !activeSessionId) {
                    setActiveSessionId(data[0].id);
                }
            }
        } catch (error) {
            console.error("Error fetching sessions:", error);
        }
    };

    const fetchSessionMessages = async (sessionId) => {
        try {
            const response = await fetch(`http://localhost:8000/api/sessions/${sessionId}/messages`);
            if (response.ok) {
                const data = await response.json();
                setChatHistory(data);
            }
        } catch (error) {
            console.error("Error fetching messages:", error);
        }
    };

    const createNewSession = () => {
        setActiveSessionId(null);
        setChatHistory([]);
    };

    // --- Helpers ---
    const groupedDocuments = documents.reduce((acc, doc) => {
        const cat = doc.category || 'Uncategorized';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(doc);
        return acc;
    }, {});

    const formatFileSize = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const getFileIcon = (filename) => {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext === 'pdf') return { icon: 'picture_as_pdf', color: 'text-red-500', label: 'PDF' };
        if (['doc', 'docx'].includes(ext)) return { icon: 'description', color: 'text-blue-500', label: 'DOCX' };
        if (['xls', 'xlsx', 'csv'].includes(ext)) return { icon: 'table_view', color: 'text-green-500', label: 'XLSX' };
        return { icon: 'insert_drive_file', color: 'text-slate-400', label: ext.toUpperCase() };
    };

    const toggleCategory = (cat) => {
        setOpenCategories(prev => ({
            ...prev,
            [cat]: !prev[cat]
        }));
    };

    const toggleDocumentSelection = (docId) => {
        setSelectedDocuments(prev =>
            prev.includes(docId)
                ? prev.filter(id => id !== docId)
                : [...prev, docId]
        );
    };

    const toggleAgentSelection = (agentId) => {
        setSelectedAgents(prev =>
            prev.includes(agentId)
                ? prev.filter(id => id !== agentId)
                : [...prev, agentId]
        );
    };

    const handleSendMessage = async () => {
        if (!chatInput.trim()) return;
        if (selectedAgents.length === 0) {
            alert("Please select at least one agent to chat with.");
            return;
        }

        const userMsg = { role: 'user', content: chatInput, name: 'You' };
        setChatHistory(prev => [...prev, userMsg]);
        const currentMessage = chatInput;
        setChatInput('');
        setIsProcessing(true);

        try {
            const payload = {
                project_id: id,
                agent_ids: selectedAgents,
                document_ids: selectedDocuments,
                message: currentMessage,
                session_id: activeSessionId
            };

            const response = await fetch('http://localhost:8000/api/a2a/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Chat failed");
            }

            const data = await response.json();

            // Store the session ID returned by backend if we started a new one
            if (data.session_id && data.session_id !== activeSessionId) {
                setActiveSessionId(data.session_id);
                // Also refresh session list to show title
                fetchProjectSessions();
            }

            // The backend returns the PARTIAL interaction log for this turn.
            // append it to history
            // Wait, if it returns partial, we should append.
            setChatHistory(prev => {
                // If we are appending to existing
                return [...prev, ...data.messages];
            });

            // Re-fetch full history to be safe and perfectly synced?
            // Actually let's trust the return for smoother UI, but maybe fetch in background

        } catch (error) {
            console.error("Chat error:", error);
            setChatHistory(prev => [...prev, { role: 'system', content: `Error: ${error.message}`, name: 'System' }]);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleChatKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // --- Project Editing Handlers ---
    const handleEdit = () => {
        setIsEditing(true);
        // We don't need to manually set formData here as ProjectForm takes project as initialData
    };

    const handleCancel = () => {
        setIsEditing(false);
    };

    const handleEditSubmit = async (data) => {
        try {
            setSaving(true);
            const updates = {
                ...data,
                admins: typeof data.admins === 'string'
                    ? data.admins.split(',').map(a => a.trim()).filter(Boolean)
                    : data.admins,
                updated_at: new Date().toISOString()
            };

            const { error } = await supabase
                .from('projects')
                .update(updates)
                .eq('id', id);

            if (error) throw error;

            setProject(updates);
            setFormData(updates); // Update local formData too just in case
            setIsEditing(false);
        } catch (error) {
            console.error('Error updating project:', error);
            alert('Error updating project: ' + error.message);
        } finally {
            setSaving(false);
        }
    };

    // --- Upload Handlers ---
    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
        }
    };

    const handleRemoveFile = () => {
        setSelectedFile(null);
    };

    const handleTagKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = tagInput.trim();
            if (val && !tags.includes(val)) {
                setTags([...tags, val]);
                setTagInput('');
            }
        }
    };

    const removeTag = (tagToRemove) => {
        setTags(tags.filter(tag => tag !== tagToRemove));
    };

    const handleAddSource = async () => {
        if (!selectedFile) {
            alert("Please select a file first.");
            return;
        }

        try {
            setUploading(true);

            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                alert("You must be logged in to upload files.");
                return;
            }

            const uploadFormData = new FormData();
            uploadFormData.append('file', selectedFile);
            uploadFormData.append('project_id', id);
            uploadFormData.append('user_id', user.id);
            uploadFormData.append('category', sourceData.category);
            uploadFormData.append('status', sourceData.status);
            uploadFormData.append('tags', tags.join(', '));

            const response = await fetch('http://localhost:8000/api/documents/upload', {
                method: 'POST',
                body: uploadFormData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const result = await response.json();
            console.log("Upload success:", result);
            alert("File uploaded successfully!");

            setSelectedFile(null);
            setTags([]);
            setTagInput('');
            setShowAddSourceModal(false);
            fetchDocuments(); // Refresh list

        } catch (error) {
            console.error("Upload error:", error);
            alert("Error uploading file: " + error.message);
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteDocument = async (docId, e) => {
        e.stopPropagation(); // Prevent triggering the row click

        if (!window.confirm("Are you sure you want to delete this document? This will remove it from the database and your local folder.")) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/api/documents/${docId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Delete failed');
            }

            console.log("Delete success");
            // Optimistically update or re-fetch
            fetchDocuments();

        } catch (error) {
            console.error("Delete error:", error);
            alert("Error deleting file: " + error.message);
        }
    };

    if (loading) return <div className="p-8 text-center text-slate-500">Loading...</div>;
    if (error) return <div className="p-8 text-center text-red-500">Error: {error}</div>;
    if (!project) return <div className="p-8 text-center text-slate-500">Project not found</div>;

    if (isEditing) {
        return (
            <div className="min-h-screen bg-background-light p-8">
                <div className="max-w-5xl mx-auto">
                    <h1 className="text-3xl font-bold mb-8 text-slate-900">Edit Project: {project.project_name}</h1>
                    <ProjectForm
                        initialData={project}
                        onSubmit={handleEditSubmit}
                        onCancel={handleCancel}
                        isEditing={true}
                        loading={saving}
                    />
                </div>
            </div>
        );
    }

    return (
        <div className="bg-background-light text-slate-900 font-display flex flex-col h-[calc(100vh-64px)] overflow-hidden">
            {/* Project Details Header Section */}
            <div className={`bg-background-light px-6 pt-4 pb-2 shrink-0 transition-all duration-300 ${isCollapsed ? '' : 'overflow-y-auto max-h-[45vh]'}`}>
                <button
                    onClick={() => navigate('/dashboard')}
                    className="flex items-center gap-2 text-slate-500 hover:text-slate-800 transition-colors text-sm font-medium mb-3 ml-1"
                >
                    <span className="material-symbols-outlined text-[20px]">arrow_back</span>
                    Back to Dashboard
                </button>

                <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm transition-all duration-300">
                    <div className="flex justify-between items-start">
                        <div className="flex-1 mr-8">
                            <h1 className="text-3xl font-bold text-slate-900">{project.project_name}</h1>
                        </div>

                        <div className="flex items-center gap-6">
                            <button
                                onClick={handleEdit}
                                className="flex items-center gap-1 text-slate-400  hover:text-primary transition-colors"
                                title="Edit Project"
                            >
                                <span className="material-symbols-outlined text-[20px]">edit</span>
                            </button>

                            <div className="text-right">
                                <div className="flex items-center justify-end gap-1.5 font-bold text-xl text-slate-900">
                                    <div className="text-[10px] text-slate-400 font-normal uppercase tracking-wider mr-1">Currency</div>
                                    <span className="material-symbols-outlined text-[24px]">credit_card</span>
                                    {project.currency || 'N/A'}
                                </div>
                            </div>

                            <button
                                onClick={() => setIsCollapsed(!isCollapsed)}
                                className="text-slate-400 hover:text-slate-600 transition-colors"
                            >
                                <span className="material-symbols-outlined text-[24px]">
                                    {isCollapsed ? 'keyboard_arrow_down' : 'keyboard_arrow_up'}
                                </span>
                            </button>
                        </div>
                    </div>

                    {!isCollapsed && (
                        <div className="mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
                            <div className="mb-6">
                                <div className="flex items-center gap-4 text-slate-500 text-sm">
                                    <div className="flex items-center gap-1.5">
                                        <span className="material-symbols-outlined text-[18px]">globe</span>
                                        {project.country}
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <span className="material-symbols-outlined text-[18px]">business_center</span>
                                        {project.ct_name || 'No CT Name'}
                                    </div>
                                </div>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-5 gap-4">
                                {/* Timeline */}
                                <div className="bg-slate-50 rounded-lg p-4 col-span-1 border border-slate-100 hover:border-blue-100 hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-2 mb-3 text-primary font-semibold">
                                        <span className="material-symbols-outlined">calendar_today</span>
                                        Timeline
                                    </div>
                                    <div className="space-y-3">
                                        <div>
                                            <div className="text-slate-500 text-xs mb-0.5">Start Date</div>
                                            <div className="font-medium text-slate-900 text-sm">{project.forecast_start_date || 'N/A'}</div>
                                        </div>
                                        <div>
                                            <div className="text-slate-500 text-xs mb-0.5">End Date</div>
                                            <div className="font-medium text-slate-900 text-sm">{project.forecast_end_date || 'N/A'}</div>
                                        </div>
                                    </div>
                                </div>

                                {/* Admins */}
                                <div className="bg-slate-50 rounded-lg p-4 col-span-1 border border-slate-100 hover:border-blue-100 hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-2 mb-3 text-primary font-semibold">
                                        <span className="material-symbols-outlined">group</span>
                                        Admins
                                    </div>
                                    <div>
                                        {(project.admins || []).map((admin, i) => (
                                            <span key={i} className="inline-block w-full text-center px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-700 truncate mb-1" title={admin}>
                                                {admin}
                                            </span>
                                        ))}
                                        {(!project.admins || project.admins.length === 0) && (
                                            <span className="text-slate-400 text-xs italic">No admins</span>
                                        )}
                                    </div>
                                </div>

                                {/* Cost */}
                                <div className="bg-slate-50 rounded-lg p-4 col-span-1 border border-slate-100 hover:border-blue-100 hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-2 mb-3 text-primary font-semibold">
                                        <span className="material-symbols-outlined">attach_money</span>
                                        Cost
                                    </div>
                                    <div className="space-y-3">
                                        <div>
                                            <div className="text-slate-500 text-xs mb-0.5">Total Budget</div>
                                            <div className="font-medium text-slate-900 text-sm">$2,450,000</div>
                                        </div>
                                        <div>
                                            <div className="text-slate-500 text-xs mb-0.5">Spent</div>
                                            <div className="font-medium text-slate-900 text-sm flex items-center justify-between">
                                                $840,000
                                                <span className="text-xs text-green-600 font-normal">34%</span>
                                            </div>
                                            <div className="w-full bg-slate-200 rounded-full h-1.5 mt-1">
                                                <div className="bg-green-500 h-1.5 rounded-full" style={{ width: '34%' }}></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Roll-out */}
                                <div className="bg-slate-50 rounded-lg p-4 col-span-1 border border-slate-100 hover:border-blue-100 hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-2 mb-3 text-primary font-semibold">
                                        <span className="material-symbols-outlined">rocket_launch</span>
                                        Roll-out
                                    </div>
                                    <div className="flex flex-col items-center justify-center h-[calc(100%-2rem)]">
                                        <div className="relative size-16 mb-2">
                                            <svg className="size-full" viewBox="0 0 36 36">
                                                <path className="text-slate-200" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                                                <path className="text-primary" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray="62, 100" strokeWidth="3"></path>
                                            </svg>
                                            <div className="absolute inset-0 flex items-center justify-center flex-col">
                                                <span className="text-sm font-bold text-slate-900">62%</span>
                                            </div>
                                        </div>
                                        <div className="text-xs text-slate-500">Completion</div>
                                    </div>
                                </div>

                                {/* Health */}
                                <div className="bg-slate-50 rounded-lg p-4 col-span-1 border border-slate-100 hover:border-blue-100 hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-2 mb-3 text-primary font-semibold">
                                        <span className="material-symbols-outlined">health_and_safety</span>
                                        Health
                                    </div>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-slate-500">Overall</span>
                                            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-bold uppercase">Good</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-slate-500">Risks</span>
                                            <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-[10px] font-bold uppercase">Medium</span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-slate-500">Quality</span>
                                            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-bold uppercase">High</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <main className="flex-1 flex overflow-hidden p-4 gap-4 pt-2">
                {/* Sources Sidebar */}
                <aside className="flex flex-col w-[320px] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden shrink-0">
                    <div className="p-4 border-b border-slate-100">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-bold text-slate-800 text-lg">Sources</h3>
                            <button
                                onClick={() => setShowAddSourceModal(true)}
                                className="flex items-center justify-center size-8 rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                            >
                                <span className="material-symbols-outlined text-[20px]">add</span>
                            </button>
                        </div>
                        <div className="relative">
                            <span className="material-symbols-outlined absolute left-2.5 top-2 text-slate-400 text-[18px]">search</span>
                            <input className="w-full bg-slate-50 text-sm text-slate-900 rounded-lg pl-9 pr-3 py-2 border-none ring-1 ring-slate-200 focus:ring-2 focus:ring-primary placeholder-slate-400 outline-none" placeholder="Search sources..." type="text" />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {Object.keys(groupedDocuments).length === 0 ? (
                            <div className="text-center py-8 text-slate-400 text-sm">
                                No documents yet.
                            </div>
                        ) : (
                            Object.entries(groupedDocuments).map(([category, docs]) => (
                                <div key={category} className="mb-2">
                                    <div
                                        onClick={() => toggleCategory(category)}
                                        className="flex items-center justify-between px-2 py-2 cursor-pointer hover:bg-slate-50 rounded text-xs font-semibold text-slate-500 uppercase tracking-wider"
                                    >
                                        <span>{category}</span>
                                        <span className="material-symbols-outlined text-[16px]">
                                            {openCategories[category] !== false ? 'expand_more' : 'chevron_right'}
                                        </span>
                                    </div>

                                    {openCategories[category] !== false && (
                                        <div className="space-y-1">
                                            {docs.map((doc, i) => {
                                                const fileInfo = getFileIcon(doc.filename);
                                                return (
                                                    <div key={doc.id || i} className="group flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors border border-transparent hover:border-slate-200">
                                                        <div className="mt-0.5">
                                                            <input
                                                                type="checkbox"
                                                                className="rounded border-slate-300 bg-transparent text-primary focus:ring-primary focus:ring-offset-0 size-4"
                                                                checked={selectedDocuments.includes(doc.id)}
                                                                onChange={(e) => { e.stopPropagation(); toggleDocumentSelection(doc.id); }}
                                                                onClick={(e) => e.stopPropagation()}
                                                            />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2 mb-0.5">
                                                                <span className={`material-symbols-outlined text-[18px] ${fileInfo.color}`}>{fileInfo.icon}</span>
                                                                <span className="text-sm font-medium text-slate-700 truncate" title={doc.filename}>{doc.filename}</span>
                                                            </div>
                                                            <div className="flex items-center gap-2 flex-wrap">
                                                                <span className="px-1.5 py-0.5 bg-slate-100 text-[10px] rounded text-slate-500 font-medium">{fileInfo.label}</span>
                                                                <span className="text-[10px] text-slate-400">{formatFileSize(doc.file_size)}</span>
                                                                {doc.status === 'Final / Signed' && (
                                                                    <span className="text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded border border-green-100">Signed</span>
                                                                )}
                                                                {(doc.tags || []).map((tag, tIndex) => (
                                                                    <span key={tIndex} className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">{tag}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                                                            className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-all"
                                                            title="Delete Source"
                                                        >
                                                            <span className="material-symbols-outlined text-[18px]">delete</span>
                                                        </button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    <div className="p-3 border-t border-slate-100 text-center">
                        <p className="text-xs text-slate-500">{documents.length} sources total</p>
                    </div>
                </aside>

                {/* Chat Interface */}
                <section className="flex-1 flex flex-col min-w-0 bg-white rounded-xl border border-slate-200 shadow-sm relative overflow-hidden">
                    <div className="h-16 bg-white/90 backdrop-blur-md border-b border-slate-100 px-6 flex items-center justify-between shrink-0 z-10">
                        <div className="flex flex-col">
                            <div className="flex items-center gap-2 text-xs font-medium mb-1">
                                <a className="text-slate-500 hover:text-primary transition-colors" href="#">Projects</a>
                                <span className="text-slate-400">/</span>
                                <span className="text-slate-900">{project.project_name}</span>
                            </div>
                            <h1 className="text-lg font-bold text-slate-900 tracking-tight">{project.project_name} Construction</h1>
                        </div>
                        <div className="flex items-center gap-3">
                            <button className="p-2 text-slate-400 hover:text-primary transition-colors rounded-full hover:bg-slate-100">
                                <span className="material-symbols-outlined text-[20px]">ios_share</span>
                            </button>
                            <button
                                onClick={createNewSession}
                                className="p-2 text-slate-400 hover:text-green-600 transition-colors rounded-full hover:bg-green-50"
                                title="New Chat Session"
                            >
                                <span className="material-symbols-outlined text-[20px]">add_comment</span>
                            </button>

                            <select
                                className="bg-slate-50 border-none text-xs rounded-lg max-w-[150px] truncate outline-none focus:ring-1 focus:ring-primary"
                                value={activeSessionId || ""}
                                onChange={(e) => setActiveSessionId(e.target.value || null)}
                            >
                                <option value="">New Chat</option>
                                {projectSessions.map(s => (
                                    <option key={s.id} value={s.id}>
                                        {new Date(s.updated_at).toLocaleDateString()} - {s.title}
                                    </option>
                                ))}
                            </select>

                            <button className="p-2 text-slate-400 hover:text-primary transition-colors rounded-full hover:bg-slate-100">
                                <span className="material-symbols-outlined text-[20px]">more_vert</span>
                            </button>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 sm:px-8 md:px-16 lg:px-24">
                        {chatHistory.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-center text-slate-400">
                                <span className="material-symbols-outlined text-[48px] mb-2 opacity-50">forum</span>
                                <p className="text-sm">Select agents on the right, documents on the left,<br />and start chatting!</p>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {chatHistory.map((msg, idx) => {
                                    // Handle System/Thought messages differently
                                    if (msg.role === 'system' || msg.role === 'function' || msg.name === 'Supervisor') {
                                        return (
                                            <div key={idx} className="flex justify-center my-2">
                                                <div className="bg-slate-50 text-slate-500 text-xs px-3 py-1.5 rounded-full border border-slate-200 flex items-center gap-2 max-w-[80%]">
                                                    <span className="material-symbols-outlined text-[14px]">
                                                        {msg.name === 'Supervisor' ? 'alt_route' : 'settings'}
                                                    </span>
                                                    <span className="font-semibold">{msg.name}:</span>
                                                    <span className="truncate">{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</span>
                                                </div>
                                            </div>
                                        );
                                    }

                                    return (
                                        <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                            <div className={`size-8 rounded-full shrink-0 flex items-center justify-center shadow-md ${msg.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-gradient-to-br from-primary to-blue-400 text-white'}`}>
                                                <span className="material-symbols-outlined text-[18px]">
                                                    {msg.role === 'user' ? 'person' : 'smart_toy'}
                                                </span>
                                            </div>
                                            <div className={`flex-1 space-y-1 ${msg.role === 'user' ? 'text-right' : ''}`}>
                                                <div className={`flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                                                    <span className="text-sm font-bold text-slate-900">{msg.name || (msg.role === 'user' ? 'You' : 'Agent')}</span>
                                                </div>
                                                <div className={`inline-block text-slate-700 leading-relaxed text-[15px] p-3 rounded-lg ${msg.role === 'user' ? 'bg-slate-100' : 'bg-white border border-slate-100 shadow-sm text-left'}`}>
                                                    <div className="whitespace-pre-wrap">{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                                {isProcessing && (
                                    <div className="flex gap-4">
                                        <div className="size-8 rounded-full bg-slate-100 shrink-0 flex items-center justify-center animate-pulse">
                                            <span className="material-symbols-outlined text-[18px] text-slate-400">more_horiz</span>
                                        </div>
                                        <div className="text-sm text-slate-400 mt-1.5 flex items-center gap-2">
                                            Agents are working...
                                            <span className="size-2 bg-primary rounded-full animate-bounce"></span>
                                        </div>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>
                        )}
                    </div>

                    <div className="p-4 bg-white border-t border-slate-100 shrink-0">
                        <div className="max-w-4xl mx-auto relative group">
                            <div className="bg-white border border-slate-200 rounded-2xl shadow-lg flex flex-col transition-all focus-within:ring-2 focus-within:ring-primary/50">
                                <textarea
                                    className="w-full bg-transparent border-none text-slate-900 placeholder-slate-400 p-4 resize-none focus:ring-0 max-h-32 text-[15px]"
                                    placeholder={selectedAgents.length === 0 ? "Select agents to start chatting..." : "Ask your team..."}
                                    rows="1"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyDown={handleChatKeyDown}
                                    disabled={isProcessing}
                                ></textarea>
                                <div className="flex justify-between items-center px-2 pb-2">
                                    <div className="flex gap-1">
                                        <button className="p-2 text-slate-400 hover:text-primary hover:bg-slate-100 rounded-lg transition-colors">
                                            <span className="material-symbols-outlined text-[20px]">attach_file</span>
                                        </button>
                                        <button className="p-2 text-slate-400 hover:text-primary hover:bg-slate-100 rounded-lg transition-colors">
                                            <span className="material-symbols-outlined text-[20px]">mic</span>
                                        </button>
                                    </div>
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={!chatInput.trim() || isProcessing}
                                        className="flex items-center justify-center size-9 bg-primary hover:bg-blue-600 text-white rounded-xl shadow-md shadow-primary/20 transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <span className="material-symbols-outlined text-[20px]">arrow_upward</span>
                                    </button>
                                </div>
                            </div>
                            <div className="text-center mt-2">
                                <p className="text-[10px] text-slate-400">AI agents can make mistakes. Verify important information.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Agents Sidebar */}
                <aside className="flex flex-col w-[300px] gap-4 shrink-0">
                    <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="font-bold text-slate-800 text-lg">Agents & Tools</h3>
                            <button className="text-slate-400 hover:text-primary transition-colors">
                                <span className="material-symbols-outlined text-[20px]">grid_view</span>
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-3 space-y-3">
                            {availableAgents.length === 0 ? (
                                <div className="text-center py-4 text-slate-400 text-xs">No agents found. Create one in Agents page.</div>
                            ) : (
                                availableAgents.map(agent => (
                                    <div
                                        key={agent.id}
                                        onClick={() => toggleAgentSelection(agent.id)}
                                        className={`bg-slate-50 p-3 rounded-xl border relative cursor-pointer transition-colors ${selectedAgents.includes(agent.id) ? 'border-primary ring-1 ring-primary' : 'border-slate-200 hover:border-slate-300'}`}
                                    >
                                        <div className="absolute top-3 right-3 flex gap-2">
                                            {selectedAgents.includes(agent.id) && (
                                                <div className="flex items-center justify-center size-5 bg-primary text-white rounded-full">
                                                    <span className="material-symbols-outlined text-[14px]">check</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="size-10 rounded-lg bg-white shadow-sm flex items-center justify-center text-primary border border-slate-100">
                                                <span className="material-symbols-outlined">smart_toy</span>
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-bold text-slate-900">{agent.name}</h4>
                                                <p className="text-xs text-slate-500 truncate max-w-[120px]">{agent.description || "AI Assistant"}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </aside>
            </main>

            {/* Add Source Modal */}
            {showAddSourceModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                            <h2 className="text-xl font-bold text-slate-900">Add New Source</h2>
                            <button
                                onClick={() => setShowAddSourceModal(false)}
                                className="text-slate-400 hover:text-slate-600 transition-colors rounded-full p-1 hover:bg-slate-100"
                            >
                                <span className="material-symbols-outlined text-[24px]">close</span>
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            {/* Hidden File Input */}
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                className="hidden"
                                accept=".pdf,.docx,.xlsx,.eml"
                            />

                            {/* Drop Zone */}
                            <div
                                onClick={handleUploadClick}
                                onDragOver={handleDragOver}
                                onDrop={handleDrop}
                                className="border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-primary/50 hover:bg-slate-50 transition-colors cursor-pointer group mb-6"
                            >
                                <div className="size-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mb-3 group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                    <span className="material-symbols-outlined text-[24px]">cloud_upload</span>
                                </div>
                                <h3 className="font-semibold text-slate-900 mb-1">
                                    {selectedFile ? 'Change File' : 'Click to upload or drag and drop'}
                                </h3>
                                <p className="text-sm text-slate-500">PDF, DOCX, XLSX, or EML (max. 10MB)</p>
                            </div>

                            <div className="space-y-4">
                                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">Document Details</h3>

                                {selectedFile && (
                                    <div className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
                                        <div className="size-10 flex items-center justify-center bg-white rounded border border-slate-200 text-red-500">
                                            <span className="material-symbols-outlined">
                                                {selectedFile.type.includes('pdf') ? 'picture_as_pdf' : 'description'}
                                            </span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium text-slate-900 truncate">{selectedFile.name}</div>
                                            <div className="text-xs text-slate-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB • Ready to tag</div>
                                        </div>
                                        <button
                                            onClick={handleRemoveFile}
                                            className="text-slate-400 hover:text-red-500"
                                        >
                                            <span className="material-symbols-outlined text-[20px]">delete</span>
                                        </button>
                                    </div>
                                )}

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-1.5">Category (Genre)</label>
                                        <select
                                            name="category"
                                            value={sourceData.category}
                                            onChange={(e) => setSourceData({ ...sourceData, category: e.target.value })}
                                            className="w-full rounded-lg border-slate-200 text-sm focus:border-primary focus:ring-primary text-slate-700"
                                        >
                                            <option value="Contracts">Contracts</option>
                                            <option value="Financials">Financials</option>
                                            <option value="Technical Specs">Technical Specs</option>
                                            <option value="Correspondence">Correspondence</option>
                                            <option value="Safety & Compliance">Safety & Compliance</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-1.5">Document Status</label>
                                        <select
                                            name="status"
                                            value={sourceData.status}
                                            onChange={(e) => setSourceData({ ...sourceData, status: e.target.value })}
                                            className="w-full rounded-lg border-slate-200 text-sm focus:border-primary focus:ring-primary text-slate-700"
                                        >
                                            <option>Draft</option>
                                            <option>Under Review</option>
                                            <option>Final / Signed</option>
                                            <option>Archived</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Tags</label>
                                    <div className="flex flex-wrap gap-2 p-2 border border-slate-200 rounded-lg min-h-[42px] focus-within:ring-1 focus-within:ring-primary focus-within:border-primary bg-white">
                                        {tags.map((tag, index) => (
                                            <span key={index} className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 text-xs font-medium text-slate-700">
                                                {tag}
                                                <button
                                                    onClick={() => removeTag(tag)}
                                                    className="hover:text-red-500"
                                                >
                                                    <span className="material-symbols-outlined text-[14px]">close</span>
                                                </button>
                                            </span>
                                        ))}
                                        <input
                                            className="border-none p-0 focus:ring-0 text-sm w-24 placeholder-slate-400"
                                            placeholder="Add tag..."
                                            type="text"
                                            value={tagInput}
                                            onChange={(e) => setTagInput(e.target.value)}
                                            onKeyDown={handleTagKeyDown}
                                        />
                                    </div>
                                    <p className="text-xs text-slate-500 mt-1.5">Press Enter to add a tag</p>
                                </div>
                            </div>
                        </div>
                        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
                            <button
                                onClick={() => setShowAddSourceModal(false)}
                                className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-200 transition-colors"
                                disabled={uploading}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddSource}
                                disabled={uploading || !selectedFile}
                                className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-primary bg-blue-600 hover:bg-blue-700 transition-colors shadow-sm shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {uploading ? 'Uploading...' : 'Add Source'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProjectDetails;
