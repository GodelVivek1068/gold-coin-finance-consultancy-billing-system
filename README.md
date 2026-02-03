# Consultancy Billing & Ledger System

A simple, beginner-friendly web-based billing system built with Flask and SQLite to manage customer billing, services, and payments.

## 📋 Features

- ✅ Add and manage customers
- ✅ Add multiple services per customer
- ✅ Record partial payments (installments)
- ✅ Automatic balance calculations
- ✅ Print-ready bills with Marathi support
- ✅ Clean professional UI
- ✅ No authentication required (single-user system)

## 🛠️ Tech Stack

- **Backend:** Python (Flask)
- **Database:** SQLite
- **Frontend:** HTML5, CSS3 (No JavaScript frameworks)

## 📂 Project Structure

```
billing-system/
│
├── app.py                  # Flask application
├── database.db            # SQLite database (auto-created)
├── database.sql           # Database schema
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── templates/
│   ├── base.html         # Base template
│   ├── index.html        # Home page (customer list)
│   ├── add_customer.html # Add customer form
│   ├── add_services.html # Add services form
│   ├── add_payment.html  # Add payment form
│   └── bill.html         # Bill/invoice page
│
└── static/
    └── style.css         # Stylesheet
```

## 🚀 Setup & Installation

### Prerequisites

- Python 3.7 or higher installed on your system

### Steps to Run

1. **Navigate to the project directory:**
   ```bash
   cd "c:\01 Pratik\CLG\Projects\BILL SYSTEM\billing-system"
   ```

2. **Install Flask:**
   ```bash
   pip install flask
   ```
   
   Or using requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:5000`

The database will be created automatically on first run.

## 📖 How to Use

### 1. Add a Customer
- Click "Add New Customer" from the home page
- Fill in customer details (name, mobile, village, bank info)
- Click "Save Customer"

### 2. Add Services
- From the customer list, click "Add Services" for a customer
- Enter service name and charge amount
- Click "Add Service" (you can add multiple services)
- Click "Done" when finished

### 3. Record Payments
- From the customer list, click "Add Payment" for a customer
- Select payment date (defaults to today)
- Enter payment amount
- Click "Record Payment"
- You can add multiple payments as installments

### 4. View & Print Bill
- From the customer list, click "View Bill" for a customer
- Review the complete bill with:
  - Customer details
  - Services provided
  - Payment history
  - Total charges, received amount, and balance
- Click "Print Bill" to print

## 🧮 Business Logic

```
Total Charges = SUM(all service charges)
Total Received = SUM(all payments)
Balance = Total Charges - Total Received

If Balance == 0:
  Display: "एकूण येणे बाकी = 0/-"
```

## 📄 Bill Format

The bill includes:
- Consultancy header with date
- Customer information (name, mobile, village, bank, loan amount)
- Services table with itemized charges
- Payment history table
- Summary section with totals and balance
- Marathi note: "चुकभूल क्षमस्व"
- Print button

## 🎨 UI Features

- Clean white background with professional styling
- Table-based layouts for easy reading
- Print-optimized CSS (hides navigation/buttons when printing)
- Responsive design
- Color-coded balance (green for paid, red for pending)

## 💾 Database Schema

### customers
- id (Primary Key)
- name
- mobile
- village
- bank_name
- loan_amount

### services
- id (Primary Key)
- customer_id (Foreign Key)
- service_name
- charge

### payments
- id (Primary Key)
- customer_id (Foreign Key)
- date
- amount

## 🔧 Troubleshooting

**Issue:** Flask not found
- **Solution:** Run `pip install flask`

**Issue:** Database error
- **Solution:** Delete `database.db` file and restart the application

**Issue:** Port 5000 already in use
- **Solution:** Change port in `app.py` (line: `app.run(port=5000)`)

## 📝 Notes

- This is a beginner-friendly, single-user system
- No authentication or user management
- Data is stored locally in SQLite database
- All code is well-commented for learning purposes

## 👨‍💻 For Developers

The code follows a simple MVC-like pattern:
- **Model:** SQLite database (database.sql)
- **View:** HTML templates (templates/)
- **Controller:** Flask routes (app.py)

Each file contains detailed comments explaining the functionality.

---

**Developed as a simple consultancy billing solution** 🏢
