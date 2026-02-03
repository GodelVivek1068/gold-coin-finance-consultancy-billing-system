-- Consultancy Billing & Ledger System Database Schema
-- SQLite Database for storing customer, service, and payment information

-- Table: customers
-- Stores customer information
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT NOT NULL,
    village TEXT,
    bank_name TEXT,
    loan_amount REAL DEFAULT 0,
    customer_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: service_catalog
-- Master list of all available services with default charges
CREATE TABLE IF NOT EXISTS service_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL UNIQUE,
    default_charge REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: services
-- Stores services provided to customers with charges
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    charge REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Table: payments
-- Stores payment installments made by customers
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    date DATE NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_services_customer ON services(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_service_catalog_active ON service_catalog(is_active);

-- Insert predefined services into catalog
-- These are the standard services offered by the consultancy
INSERT OR IGNORE INTO service_catalog (service_name, default_charge) VALUES
    ('Xerox', 0),
    ('ITR', 0),
    ('Search Report', 0),
    ('Valuation Report', 0),
    ('Plan Design & Estimate', 0),
    ('Rubber Stamp', 0),
    ('Agreement', 0),
    ('Typing', 0),
    ('Data Entry', 0),
    ('Stamp Duty', 0),
    ('Aadhaar-PAN Colour Xerox', 0),
    ('7/12', 0),
    ('Guarantor for Mortgage', 0),
    ('Affidavit', 0),
    ('Vendor Fee', 0),
    ('Dast Xerox', 0),
    ('Consultancy Charge (2%)', 0);
