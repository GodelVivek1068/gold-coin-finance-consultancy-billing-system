-- Consultancy Billing & Ledger System — PostgreSQL Schema

-- Table: customers
CREATE TABLE IF NOT EXISTS customers (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    mobile        TEXT NOT NULL,
    email         TEXT,
    business_name TEXT,
    village       TEXT,
    bank_name     TEXT,
    loan_amount   NUMERIC DEFAULT 0,
    customer_date DATE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: service_catalog
CREATE TABLE IF NOT EXISTS service_catalog (
    id             SERIAL PRIMARY KEY,
    service_name   TEXT NOT NULL UNIQUE,
    default_charge NUMERIC DEFAULT 0,
    is_active      INTEGER DEFAULT 1,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: services
CREATE TABLE IF NOT EXISTS services (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    charge       NUMERIC NOT NULL DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: payments
CREATE TABLE IF NOT EXISTS payments (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    amount      NUMERIC NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_services_customer      ON services(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer      ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_service_catalog_active ON service_catalog(is_active);
CREATE INDEX IF NOT EXISTS idx_customers_name         ON customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_mobile       ON customers(mobile);

-- Seed service catalog (skip duplicates)
INSERT INTO service_catalog (service_name, default_charge) VALUES
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
    ('Consultancy Charge (2%)', 0)
ON CONFLICT (service_name) DO NOTHING;
