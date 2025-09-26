-- Drop the old table if it exists to avoid conflicts.
DROP TABLE IF EXISTS feedback;

-- Create the new table with an added 'corrected_text' column.
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    feedback_text TEXT NOT NULL,
    corrected_text TEXT, -- This new column will store the corrected text.
    department VARCHAR(255) NOT NULL,
    course VARCHAR(255) NOT NULL,
    faculty VARCHAR(255) NOT NULL,
    sentiment_category VARCHAR(50),
    sentiment_score FLOAT,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Insert some sample data to populate the dashboard initially.
INSERT INTO feedback (feedback_text, department, course, faculty, sentiment_category, sentiment_score, source, corrected_text) VALUES
('The professor was amazing and very engaging. Made complex topics easy to understand.', 'Computer Science', 'CS101 - Intro to Programming', 'Dr. Alan Turing', 'Positive', 0.8, 'Manual Entry', 'The professor was amazing and very engaging. Made complex topics easy to understand.'),
('The cafeteria food has been really bad lately. It''s often cold and lacks variety.', 'Campus Services', 'N/A', 'N/A', 'Negative', -0.7, 'LMS Survey', 'The cafeteria food has been really bad lately. It''s often cold and lacks variety.'),
('This course was decent, but the textbook felt very outdated.', 'Computer Science', 'CS202 - Data Structures', 'Dr. Grace Hopper', 'Neutral', 0.1, 'Email', 'This course was decent, but the textbook felt very outdated.'),
('Excellent course on marketing. The case studies were very relevant.', 'Business Administration', 'BA305 - Marketing Principles', 'Dr. Philip Kotler', 'Positive', 0.9, 'Manual Entry', 'Excellent course on marketing. The case studies were very relevant.');

