-- SQL script to create the user activity log table
CREATE TABLE user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    activity_description TEXT NOT NULL,
    activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
