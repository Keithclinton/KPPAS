-- SQL to create a feedback table for public sentiment
CREATE TABLE IF NOT EXISTS public_feedback (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    county VARCHAR(100),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
