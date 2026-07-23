-- Phase C: Parent-Child Chunking Migration
-- Adds parent-child relationship columns to document_chunks table.
-- Non-destructive: existing rows remain valid with NULL parent columns.

-- Add parent-child columns
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS parent_id VARCHAR;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS is_parent BOOLEAN DEFAULT false;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS parent_text TEXT;

-- Index for fast parent lookups (only on rows that have a parent)
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_id
    ON document_chunks (parent_id) WHERE parent_id IS NOT NULL;

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'Phase C migration complete: parent_id, is_parent, parent_text columns added to document_chunks';
END $$;
