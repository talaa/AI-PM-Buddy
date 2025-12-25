-- Agents Table Definition (Reference)
create table if not exists agents (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  description text,
  instructions text,
  knowledge text,
  -- Added for RAG/Context
  tools text [],
  model text default 'qwen3:latest',
  created_at timestamp with time zone default timezone('utc'::text, now()),
  modified_at timestamp with time zone default timezone('utc'::text, now())
);
-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;
-- Create a table to store your document chunks
create table if not exists document_chunks (
  id bigserial primary key,
  project_document_id uuid references project_documents(id) on delete cascade,
  content text,
  metadata jsonb,
  embedding vector(768) -- nomic-embed-text uses 768 dimensions
);
-- Create a function to search for documents
create or replace function match_documents (
    query_embedding vector(768),
    match_threshold float,
    match_count int
  ) returns table (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
  ) language plpgsql stable as $$ begin return query
select document_chunks.id,
  document_chunks.content,
  document_chunks.metadata,
  1 - (document_chunks.embedding <=> query_embedding) as similarity
from document_chunks
where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
order by document_chunks.embedding <=> query_embedding
limit match_count;
end;
$$;