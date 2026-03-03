# Consultancy Billing & Ledger System

A simple, beginner-friendly web-based billing system built with Flask to manage customer billing, services, and payments.

## 📋 Features

- ✅ Add and manage customers
- ✅ Add multiple services per customer
- ✅ Record partial payments (installments)
- ✅ Automatic balance calculations
- ✅ Print-ready bills with Marathi support
- ✅ Clean professional UI
- ✅ No authentication required (single-user system)
- ✅ **PostgreSQL integration** via environment variables
- ✅ Deployment-ready via Gunicorn
- ✅ Supports gap year logic and certificate uploads for academic records

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Database:** PostgreSQL (Production) / SQLite (Fallback, if applicable)
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Server:** Gunicorn

## 📂 Project Structure

```
billing-system/
│
├── app.py                  # Main Flask application logic
├── requirements.txt        # Python dependencies (Flask, psycopg2, gunicorn, etc)
├── README.md               # Project documentation
├── DEPLOYMENT.md           # Instructions for deployment (Railway, etc.)
├── .env                    # Environment variables (DATABASE_URL configured here)
│
├── database.sql            # Schema commands for PostgreSQL
├── updation.txt            # Roadmap and pending improvements
│
├── templates/              # HTML Templates (Jinja2)
│   ├── base.html           # Base template
│   ├── index.html          # Dashboard (customer list)
│   ├── add_customer.html   # Add customer form
│   ├── add_services.html   # Add services form
│   ├── add_payment.html    # Add payment form
│   ├── edit.html           # Edit details & handle gap year certificates
│   └── bill.html           # Print-optimized billing layout
│
└── static/
    ├── style.css           # Styling
    └── uploads/            # Directories for user-uploaded certificates
```

## 🚀 Setup & Installation

### Prerequisites

- Python 3.7+
- PostgreSQL (if running postgres locally, otherwise use remote DB URL)

### Steps to Run

1. **Navigate to the project directory/Clone:**
   ```bash
   cd "gold-coin-finance-consultancy-billing-system"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file in the root directory mapping the database. For example:
   ```env
   DATABASE_URL=postgresql://user:password@hostname:port/dbname
   ```

4. **Run the application:**
   Using the Flask Dev server:
   ```bash
   python app.py
   ```
   Or using Gunicorn (production mode):
   ```bash
   gunicorn -w 1 -b 0.0.0.0:5000 app:app
   ```

5. **Open your browser:**
   Navigate to `http://localhost:5000`

## 📖 How to Use

### 1. Add a Customer
- Click "Add New Customer" from the home page.
- Fill in customer details (name, mobile, village, bank info) and track gap years & upload certificates.
- Click "Save Customer".

### 2. Add Services
- From the customer list, click "Add Services" for a customer.
- Enter service name and charge amount.
- Click "Done" when finished.

### 3. Record Payments
- Set the payment date and enter the respective amount.

### 4. View & Print Bill
- Provides complete history of details, including overall balance.
- Standard Marathi notes available ("चुकभूल क्षमस्व").
- Click "Print Bill" for an optimized layout.

## 💾 Database 

The system utilizes PostgreSQL for a robust, persistent data layer ideal for production environments like Railway.

**Connection Mechanism:** 
The application connects automatically if it detects a `DATABASE_URL` environment variable via `psycopg2`.

## 🔧 Deployment Summary

This project can be easily pushed to platforms like Railway or Render:
- Add a PostgreSQL instance plugin.
- Add `DATABASE_URL` to variables and watch it configure via `.env`.
- Ensure the start command is `gunicorn app:app`.

*(For comprehensive steps, refer to `DEPLOYMENT.md`)*

## 📝 Roadmap & V2 Updates

Refinements for subsequent upgrades are listed in `updation.txt`, such as:
- Dashboard statistical calculation cards.
- Search bar directly accessible on the main dashboard index.
- Modal confirmations for delete actions instead of browser alerts.

---

**Developed as a simple consultancy billing solution** 🏢
