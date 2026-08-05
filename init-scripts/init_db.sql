-- Sample e-commerce seed data for the optional `postgres`/`mysql` docker-compose
-- services (docker-compose.yml mounts this directory as
-- /docker-entrypoint-initdb.d for both, so this file must run unmodified under
-- both engines' init mechanism - it deliberately avoids engine-specific syntax
-- like SERIAL or AUTO_INCREMENT and uses explicit integer primary keys instead.
--
-- Matches what the README's "Sample Database" section documents: 10 customers,
-- 17 orders, order_items, and an order_summary view joining the three.

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(255),
    state VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status VARCHAR(255) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE VIEW order_summary AS
SELECT
    o.id AS order_id,
    c.first_name,
    c.last_name,
    c.city,
    c.state,
    o.status,
    o.total_amount
FROM orders o
JOIN customers c ON o.customer_id = c.id;

INSERT INTO customers (id, first_name, last_name, email, city, state) VALUES
    (1, 'John', 'Doe', 'john.doe@email.com', 'New York', 'NY'),
    (2, 'Jane', 'Smith', 'jane.smith@email.com', 'Los Angeles', 'CA'),
    (3, 'Bob', 'Johnson', 'bob.johnson@email.com', 'Chicago', 'IL'),
    (4, 'Alice', 'Brown', 'alice.brown@email.com', 'Houston', 'TX'),
    (5, 'Charlie', 'Wilson', 'charlie.wilson@email.com', 'Phoenix', 'AZ'),
    (6, 'Eva', 'Davis', 'eva.davis@email.com', 'Philadelphia', 'PA'),
    (7, 'Frank', 'Miller', 'frank.miller@email.com', 'San Antonio', 'TX'),
    (8, 'Grace', 'Lee', 'grace.lee@email.com', 'San Diego', 'CA'),
    (9, 'Henry', 'Garcia', 'henry.garcia@email.com', 'Dallas', 'TX'),
    (10, 'Iris', 'Martinez', 'iris.martinez@email.com', 'San Jose', 'CA');

INSERT INTO orders (id, customer_id, status, total_amount) VALUES
    (1, 1, 'completed', 1329.98),
    (2, 2, 'completed', 109.98),
    (3, 3, 'pending', 199.99),
    (4, 4, 'completed', 24.99),
    (5, 5, 'completed', 479.98),
    (6, 6, 'pending', 37.98),
    (7, 7, 'completed', 1315.98),
    (8, 8, 'completed', 14.98),
    (9, 9, 'pending', 399.99),
    (10, 10, 'completed', 15.99),
    (11, 1, 'completed', 79.99),
    (12, 2, 'pending', 29.99),
    (13, 3, 'completed', 200.98),
    (14, 4, 'completed', 12.99),
    (15, 5, 'pending', 1299.99),
    (16, 6, 'completed', 55.98),
    (17, 7, 'pending', 89.97);

INSERT INTO order_items (id, order_id, item_name, quantity, unit_price) VALUES
    (1, 1, 'Laptop Pro', 1, 1299.99),
    (2, 1, 'Wireless Mouse', 1, 29.99),
    (3, 2, 'Mechanical Keyboard', 1, 79.99),
    (4, 2, 'Wireless Mouse', 1, 29.99),
    (5, 3, 'Office Chair', 1, 199.99),
    (6, 4, 'Water Bottle', 1, 24.99),
    (7, 5, 'Standing Desk', 1, 399.99),
    (8, 5, 'Coffee Mug', 1, 12.99),
    (9, 5, 'Notebook', 1, 5.99),
    (10, 5, 'Pen Set', 6, 8.99),
    (11, 6, 'USB Cable', 2, 15.99),
    (12, 6, 'Coffee Mug', 1, 12.99),
    (13, 7, 'Laptop Pro', 1, 1299.99),
    (14, 7, 'Notebook', 2, 5.99),
    (15, 7, 'Pen Set', 1, 8.99),
    (16, 8, 'Coffee Mug', 1, 12.99),
    (17, 9, 'Standing Desk', 1, 399.99),
    (18, 10, 'USB Cable', 1, 15.99),
    (19, 11, 'Mechanical Keyboard', 1, 79.99),
    (20, 12, 'Wireless Mouse', 1, 29.99),
    (21, 13, 'Office Chair', 1, 199.99),
    (22, 13, 'Pen Set', 1, 8.99),
    (23, 14, 'Coffee Mug', 1, 12.99),
    (24, 15, 'Laptop Pro', 1, 1299.99),
    (25, 16, 'Water Bottle', 2, 24.99),
    (26, 16, 'Notebook', 1, 5.99),
    (27, 17, 'Pen Set', 3, 8.99),
    (28, 17, 'Notebook', 4, 5.99),
    (29, 17, 'USB Cable', 2, 15.99);
