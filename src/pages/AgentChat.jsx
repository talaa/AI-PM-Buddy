import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { Send, Bot, User, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const AgentChat = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [agent, setAgent] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        fetchAgent();
    }, [id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchAgent = async () => {
        try {
            setLoading(true);
            const { data, error } = await supabase
                .from('agents')
                .select('*')
                .eq('id', id)
                .single();

            if (error) throw error;
            setAgent(data);
        } catch (error) {
            console.error('Error fetching agent:', error);
            setError('Agent not found');
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || sending) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setSending(true);

        try {
            // Convert history to format expected by backend backend
            // Backend expects list of {role, content}
            const history = messages.map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            const response = await fetch('http://localhost:8000/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agent_id: id,
                    message: userMessage.content,
                    history: history
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to send message');
            }

            const data = await response.json();
            const agentMessage = { role: 'assistant', content: data.response };
            setMessages(prev => [...prev, agentMessage]);

        } catch (error) {
            console.error('Error sending message:', error);
            setMessages(prev => [...prev, {
                role: 'system',
                content: `Error: ${error.message}. Is the backend server running?`
            }]);
        } finally {
            setSending(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center pt-24">
                <Loader2 className="animate-spin text-[var(--accent-primary)]" size={32} />
            </div>
        );
    }

    if (error || !agent) {
        return (
            <div className="min-h-screen bg-[var(--bg-primary)] pt-24 p-8 flex flex-col items-center">
                <AlertCircle className="text-red-500 mb-4" size={48} />
                <h2 className="text-2xl font-bold mb-2">Error</h2>
                <p className="text-[var(--text-secondary)] mb-6">{error || 'Agent not found'}</p>
                <button
                    onClick={() => navigate('/agents')}
                    className="px-4 py-2 bg-[var(--bg-secondary)] rounded-lg hover:bg-[var(--border-color)] transition-colors"
                >
                    Back to Agents
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--bg-primary)] pt-20 flex flex-col">
            {/* Header */}
            <div className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] p-4 shadow-sm z-10">
                <div className="max-w-4xl mx-auto flex items-center gap-4">
                    <button
                        onClick={() => navigate('/agents')}
                        className="p-2 hover:bg-[var(--bg-primary)] rounded-full transition-colors text-[var(--text-secondary)]"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div className="w-10 h-10 rounded-lg bg-[var(--accent-primary)]/10 flex items-center justify-center text-[var(--accent-primary)]">
                        <Bot size={24} />
                    </div>
                    <div>
                        <h1 className="font-bold text-[var(--text-primary)]">{agent.name}</h1>
                        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                            <span className="px-1.5 py-0.5 rounded bg-[var(--bg-primary)] border border-[var(--border-color)]">{agent.model}</span>
                            <span>•</span>
                            <span>{agent.tools?.length || 0} Tools</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 scroll-smooth">
                <div className="max-w-3xl mx-auto space-y-6">
                    {messages.length === 0 && (
                        <div className="text-center py-20 opacity-50">
                            <Bot size={48} className="mx-auto mb-4" />
                            <p>Start a conversation with {agent.name}</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role !== 'user' && (
                                <div className="w-8 h-8 rounded-full bg-[var(--accent-primary)]/10 flex items-center justify-center text-[var(--accent-primary)] shrink-0 mt-1">
                                    <Bot size={16} />
                                </div>
                            )}

                            <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${msg.role === 'user'
                                    ? 'bg-[var(--accent-primary)] text-white'
                                    : msg.role === 'system'
                                        ? 'bg-red-500/10 text-red-500 border border-red-500/20'
                                        : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] border border-[var(--border-color)]'
                                }`}>
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <div
                                        dangerouslySetInnerHTML={{
                                            __html: DOMPurify.sanitize(
                                                (msg.content || '') ? marked.parse(msg.content || '') : ''
                                            ),
                                        }}
                                    />
                                </div>
                            </div>

                            {msg.role === 'user' && (
                                <div className="w-8 h-8 rounded-full bg-[var(--text-primary)] text-[var(--bg-primary)] flex items-center justify-center shrink-0 mt-1">
                                    <User size={16} />
                                </div>
                            )}
                        </div>
                    ))}

                    {sending && (
                        <div className="flex gap-4 justify-start">
                            <div className="w-8 h-8 rounded-full bg-[var(--accent-primary)]/10 flex items-center justify-center text-[var(--accent-primary)] shrink-0 mt-1">
                                <Bot size={16} />
                            </div>
                            <div className="bg-[var(--bg-secondary)] rounded-2xl px-5 py-3 border border-[var(--border-color)] flex items-center gap-2">
                                <span className="w-2 h-2 bg-[var(--text-secondary)] rounded-full animate-bounce"></span>
                                <span className="w-2 h-2 bg-[var(--text-secondary)] rounded-full animate-bounce delay-100"></span>
                                <span className="w-2 h-2 bg-[var(--text-secondary)] rounded-full animate-bounce delay-200"></span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="p-4 bg-[var(--bg-primary)] border-t border-[var(--border-color)]">
                <div className="max-w-3xl mx-auto">
                    <form onSubmit={handleSend} className="relative flex items-end gap-2">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={`Message ${agent.name}...`}
                            className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] resize-none"
                            disabled={sending}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || sending}
                            className="absolute right-2 bottom-2 p-2 bg-[var(--accent-primary)] text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:hover:bg-[var(--accent-primary)] transition-colors"
                        >
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AgentChat;
