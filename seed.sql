-- Users
INSERT INTO users (username, first_name, last_name, email, password_hash, is_active, has_subscription, created_at, updated_at) VALUES
('john_doe',    'John',    'Doe',     'john@example.com',    'hash1', true,  true,  NOW(), NOW()),
('jane_smith',  'Jane',    'Smith',   'jane@example.com',    'hash2', true,  true,  NOW(), NOW()),
('bob_jones',   'Bob',     'Jones',   'bob@example.com',     'hash3', true,  true,  NOW(), NOW()),
('alice_brown', 'Alice',   'Brown',   'alice@example.com',   'hash4', true,  true,  NOW(), NOW()),
('charlie_w',   'Charlie', 'Wilson',  'charlie@example.com', 'hash5', true,  true,  NOW(), NOW()),
('eve_davis',   'Eve',     'Davis',   'eve@example.com',     'hash6', true,  false, NOW(), NOW()),
('mike_taylor', 'Mike',    'Taylor',  'mike@example.com',    'hash7', true,  true,  NOW(), NOW());

-- Subscription types
INSERT INTO subscription_types (subscription_type_name, price, created_at, updated_at) VALUES
('basic',   9.99,  NOW(), NOW()),
('premium', 19.99, NOW(), NOW()),
('enterprise', 49.99, NOW(), NOW());

-- Subscriptions
INSERT INTO subscriptions (user_id, subscription_type_id, last_paid_time, created_at, updated_at) VALUES
(1, 1, NOW(), NOW(), NOW()),
(2, 2, NOW(), NOW(), NOW()),
(3, 1, NOW(), NOW(), NOW()),
(4, 2, NOW(), NOW(), NOW()),
(5, 1, NOW(), NOW(), NOW()),
(7, 1, NOW(), NOW(), NOW());

-- Priority levels
INSERT INTO priority_levels (priority_level_name) VALUES
('low'),
('medium'),
('high'),
('critical');

-- Chat statuses
INSERT INTO chat_statuses (chat_status_name, created_at, updated_at) VALUES
('open',     NOW(), NOW()),
('pending',  NOW(), NOW()),
('resolved', NOW(), NOW()),
('closed',   NOW(), NOW());

-- Anomalies
INSERT INTO anomalies (anomaly_name, anomaly_description, first_message) VALUES
('duplicate_subscription_charge',
 'Two or more subscription charge events for the same user within 60 seconds or consecutively in the log stream.',
 'Ми виявили підозріле подвійне списання коштів з вашого рахунку. Будь ласка, перевірте деталі.'),
('multiple_failed_logins',
 'Five or more consecutive failed login attempts for the same user within 60 seconds.',
 'Зафіксовано декілька невдалих спроб входу до вашого акаунту. Чи це були ви?');

-- Actions
INSERT INTO actions (action_name, action_description, is_allowed, created_at, updated_at) VALUES
('reset_password',   'Send password reset link to the user',      true,  NOW(), NOW()),
('refund_charge',    'Initiate a refund for a duplicate charge',   true,  NOW(), NOW()),
('block_account',    'Temporarily block a suspicious account',     false, NOW(), NOW()),
('notify_user',      'Send email notification to the user',        true,  NOW(), NOW());

-- Logs (sample data with anomalies)
INSERT INTO logs (user_id, log_message, log_type, created_at, updated_at) VALUES
(1, 'User logged in',                          'AUTH',       '2024-01-15 10:00:01', '2024-01-15 10:00:01'),
(1, 'User viewed subscription page',           'NAVIGATION', '2024-01-15 10:00:30', '2024-01-15 10:00:30'),
(1, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:01:00', '2024-01-15 10:01:00'),
(1, 'User logged out',                         'AUTH',       '2024-01-15 10:05:00', '2024-01-15 10:05:00'),

(2, 'User logged in',                          'AUTH',       '2024-01-15 10:02:00', '2024-01-15 10:02:00'),
(2, 'Subscription charge: 19.99 plan=premium', 'BILLING',    '2024-01-15 10:02:45', '2024-01-15 10:02:45'),
(2, 'User logged out',                         'AUTH',       '2024-01-15 10:10:00', '2024-01-15 10:10:00'),

-- ANOMALY: duplicate charge for user 3
(3, 'User logged in',                          'AUTH',       '2024-01-15 10:15:00', '2024-01-15 10:15:00'),
(3, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:15:30', '2024-01-15 10:15:30'),
(3, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:15:33', '2024-01-15 10:15:33'),
(3, 'User logged out',                         'AUTH',       '2024-01-15 10:20:00', '2024-01-15 10:20:00'),

(4, 'User logged in',                          'AUTH',       '2024-01-15 10:22:00', '2024-01-15 10:22:00'),
(4, 'Subscription charge: 19.99 plan=premium', 'BILLING',    '2024-01-15 10:22:30', '2024-01-15 10:22:30'),
(4, 'User logged out',                         'AUTH',       '2024-01-15 10:25:00', '2024-01-15 10:25:00'),

-- ANOMALY: triple charge for user 5
(5, 'User logged in',                          'AUTH',       '2024-01-15 10:30:00', '2024-01-15 10:30:00'),
(5, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:30:20', '2024-01-15 10:30:20'),
(5, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:30:23', '2024-01-15 10:30:23'),
(5, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:30:26', '2024-01-15 10:30:26'),
(5, 'User logged out',                         'AUTH',       '2024-01-15 10:35:00', '2024-01-15 10:35:00'),

-- ANOMALY: multiple failed logins for user 6
(6, 'Login failed: invalid password',          'AUTH_ERROR', '2024-01-15 10:40:00', '2024-01-15 10:40:00'),
(6, 'Login failed: invalid password',          'AUTH_ERROR', '2024-01-15 10:40:05', '2024-01-15 10:40:05'),
(6, 'Login failed: invalid password',          'AUTH_ERROR', '2024-01-15 10:40:10', '2024-01-15 10:40:10'),
(6, 'Login failed: invalid password',          'AUTH_ERROR', '2024-01-15 10:40:15', '2024-01-15 10:40:15'),
(6, 'Login failed: invalid password',          'AUTH_ERROR', '2024-01-15 10:40:20', '2024-01-15 10:40:20'),

(7, 'User logged in',                          'AUTH',       '2024-01-15 10:45:00', '2024-01-15 10:45:00'),
(7, 'Subscription charge: 9.99 plan=basic',    'BILLING',    '2024-01-15 10:46:00', '2024-01-15 10:46:00'),
(7, 'User logged out',                         'AUTH',       '2024-01-15 10:50:00', '2024-01-15 10:50:00');
