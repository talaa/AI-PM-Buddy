-- Create agents table
create table public.agents (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default now(),
  modified_at timestamp with time zone default now(),
  name text not null,
  description text,
  instructions text,
  model text,
  tools text[], -- Array of strings for tool names
  knowledge text,
  user_id uuid references auth.users not null
);

-- Enable RLS
alter table public.agents enable row level security;

-- Policies
create policy "Users can view their own agents"
  on public.agents for select
  using (auth.uid() = user_id);

create policy "Users can insert their own agents"
  on public.agents for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own agents"
  on public.agents for update
  using (auth.uid() = user_id);

create policy "Users can delete their own agents"
  on public.agents for delete
  using (auth.uid() = user_id);
