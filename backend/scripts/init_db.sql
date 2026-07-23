-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions loaded
DO $$
BEGIN
  RAISE NOTICE 'Extensions loaded: vector, uuid-ossp';
END $$;
