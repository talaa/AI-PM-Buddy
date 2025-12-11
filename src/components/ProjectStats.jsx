import React, { useEffect, useState } from 'react';
import { FolderGit2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const ProjectStats = () => {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const { count, error } = await supabase
          .from('projects')
          .select('*', { count: 'exact', head: true });

        if (error) throw error;
        setCount(count || 0);
      } catch (error) {
        console.error('Error fetching project count:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCount();
  }, []);

  return (
    <div className="glass-card p-6 flex flex-col h-full">
      <h3 className="text-lg font-semibold">Active Projects</h3>
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4 text-[var(--accent-primary)]">
          <FolderGit2 size={32} />
        </div>
        <div className="text-5xl font-bold text-[var(--text-primary)] mb-2">
          {loading ? '-' : count}
        </div>
        <p className="text-sm text-[var(--text-secondary)] text-center">
          Total active projects
        </p>
      </div>
    </div>
  );
};

export default ProjectStats;
