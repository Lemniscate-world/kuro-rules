-- Hermes Validation Schema
-- Run this in Supabase SQL Editor

-- Enable Row Level Security (RLS)
-- Allow anonymous inserts (for form submissions)
-- Restrict reads to authenticated users (or your specific setup)

CREATE TABLE landing_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Contact
    email TEXT NOT NULL,
    phone TEXT,

    -- Profile
    role TEXT CHECK (role IN ('merchant', 'driver', 'both', 'other')),
    business_type TEXT CHECK (business_type IN ('restaurant', 'bakery', 'pharmacy', 'grocery', 'shop', 'other')),
    zone TEXT,

    -- Usage
    volume TEXT CHECK (volume IN ('lt5_week', '5_20_week', '1_5_day', 'gt5_day')),
    main_problem TEXT CHECK (main_problem IN ('find_driver', 'coordination', 'tracking', 'proof', 'other')),

    -- Business intent
    budget TEXT CHECK (budget IN ('free_only', '5000_15000', '15000_30000', '30000_plus')),
    beta_interest TEXT CHECK (beta_interest IN ('yes', 'maybe', 'no')),

    -- Qualitative
    notes TEXT,

    -- Scoring (computed fields for quick dashboard view)
    qualified BOOLEAN GENERATED ALWAYS AS (
        role = 'merchant' OR role = 'both'
    ) STORED,

    high_volume BOOLEAN GENERATED ALWAYS AS (
        volume IN ('1_5_day', 'gt5_day')
    ) STORED,

    willing_to_pay BOOLEAN GENERATED ALWAYS AS (
        budget != 'free_only'
    ) STORED
);

-- Enable RLS
ALTER TABLE landing_responses ENABLE ROW LEVEL SECURITY;

-- Allow anyone to insert (for the public form)
CREATE POLICY "Allow anonymous inserts" ON landing_responses
    FOR INSERT TO anon
    WITH CHECK (true);

-- Allow anyone to read (for dashboard; restrict in production if needed)
CREATE POLICY "Allow anonymous reads" ON landing_responses
    FOR SELECT TO anon
    USING (true);

-- Create indexes for dashboard queries
CREATE INDEX idx_created_at ON landing_responses(created_at DESC);
CREATE INDEX idx_qualified ON landing_responses(qualified);
CREATE INDEX idx_beta_interest ON landing_responses(beta_interest);

-- View for quick stats
CREATE OR REPLACE VIEW response_stats AS
SELECT
    COUNT(*) as total_responses,
    COUNT(*) FILTER (WHERE qualified) as qualified_merchants,
    COUNT(*) FILTER (WHERE beta_interest = 'yes') as beta_yes,
    COUNT(*) FILTER (WHERE willing_to_pay) as willing_to_pay_count,
    COUNT(*) FILTER (WHERE high_volume) as high_volume_count,
    COUNT(*) FILTER (WHERE main_problem = 'coordination') as problem_coordination,
    COUNT(*) FILTER (WHERE main_problem = 'tracking') as problem_tracking,
    COUNT(*) FILTER (WHERE main_problem = 'proof') as problem_proof,
    COUNT(*) FILTER (WHERE main_problem = 'find_driver') as problem_find_driver
FROM landing_responses;
