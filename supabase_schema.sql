-- Create projects table
create table public.projects (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default now(),
  project_name text not null,
  ct_name text,
  country text,
  forecast_start_date date,
  forecast_end_date date,
  currency text,
  scope text,
  admins text[], -- Array of strings for admin names/emails
  user_id uuid references auth.users not null
);

-- Enable Row Level Security (RLS)
alter table public.projects enable row level security;

-- Create policies
create policy "Users can view their own projects"
  on public.projects for select
  using (auth.uid() = user_id);

create policy "Users can insert their own projects"
  on public.projects for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own projects"
  on public.projects for update
  using (auth.uid() = user_id);

create policy "Users can delete their own projects"
  on public.projects for delete
  using (auth.uid() = user_id);
