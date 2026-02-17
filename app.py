"""
Consultancy Billing & Ledger System
A Flask-based web application for managing customer billing, services, and payments
Enhanced with Service Catalog, PDF Generation, and PostgreSQL Support
"""

import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)

# Database Configuration - Auto-detect PostgreSQL or use SQLite
DATABASE_URL = os.getenv('DATABASE_URL')
USE_POSTGRESQL = DATABASE_URL is not None

if USE_POSTGRESQL:
    # Fix Render's postgres:// to postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    try:
        import psycopg2
        import psycopg2.extras
        print("✓ Using PostgreSQL database (Production Mode)")
    except ImportError:
        print("⚠️ psycopg2 not installed, falling back to SQLite")
        USE_POSTGRESQL = False
else:
    print("✓ Using SQLite database (Development Mode)")

app.config['DATABASE'] = 'database.db'

# Database helper functions
def get_db_connection():
    """Get database connection - PostgreSQL or SQLite"""
    if USE_POSTGRESQL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        # Use RealDictCursor for dict-like access similar to sqlite3.Row
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        # SQLite for local development
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn

def init_db():
    """Initialize database from schema file"""
    if USE_POSTGRESQL:
        # PostgreSQL initialization
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Read and execute database schema for PostgreSQL
            with open('database.sql', 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
                # Convert SQLite syntax to PostgreSQL
                sql_content = sql_content.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
                sql_content = sql_content.replace('REAL', 'NUMERIC')
                sql_content = sql_content.replace('INSERT OR IGNORE', 'INSERT')
                sql_content = sql_content.replace('IF NOT EXISTS', '')  # PostgreSQL handles this differently
                
                # Split into individual statements and execute
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        # Execute statement - errors will propagate for debugging
                        cursor.execute(statement)
                
                conn.commit()
                print("✓ PostgreSQL database initialized successfully")
                
        except Exception as e:
            conn.rollback()
            # Re-raise the exception so you can see the full error details
            raise
        finally:
            cursor.close()
            conn.close()
            
    else:
        # SQLite initialization (original logic)
        if not os.path.exists(app.config['DATABASE']):
            conn = get_db_connection()
            with open('database.sql', 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            print("✓ Database initialized successfully")
        else:
            # Migrate existing database to add new tables/columns
            conn = get_db_connection()
            try:
                # Check if service_catalog table exists
                result = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='service_catalog'"
                ).fetchone()
                
                if not result:
                    print("🔄 Migrating database to add service catalog...")
                    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS service_catalog (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            service_name TEXT NOT NULL UNIQUE,
                            default_charge REAL DEFAULT 0,
                            is_active INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_service_catalog_active ON service_catalog(is_active);
                        
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
                    """)
                    conn.commit()
                    print("✓ Service catalog added successfully")
                
                # Check if customer_date column exists
                cursor = conn.execute("PRAGMA table_info(customers)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'customer_date' not in columns:
                    print("🔄 Adding customer_date column...")
                    conn.execute("ALTER TABLE customers ADD COLUMN customer_date DATE")
                    conn.commit()
                    print("✓ Customer date field added successfully")
                
                # Check if business_name column exists
                cursor = conn.execute("PRAGMA table_info(customers)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'business_name' not in columns:
                    print("🔄 Adding business_name column...")
                    conn.execute("ALTER TABLE customers ADD COLUMN business_name TEXT")
                    conn.commit()
                    print("✓ Business name field added successfully")
                
                # Check if email column exists
                cursor = conn.execute("PRAGMA table_info(customers)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'email' not in columns:
                    print("🔄 Adding email column...")
                    conn.execute("ALTER TABLE customers ADD COLUMN email TEXT")
                    conn.commit()
                    print("✓ Email field added successfully")
                
                # Add indexes for customer search performance
                print("🔄 Adding customer search indexes...")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_mobile ON customers(mobile)")
                conn.commit()
                print("✓ Customer search indexes added successfully")
            finally:
                conn.close()

# Routes

@app.route('/')
def index():
    """Home page - Display all customers"""
    conn = get_db_connection()
    customers = conn.execute('SELECT * FROM customers ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('index.html', customers=customers)

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    """Add new customer"""
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form.get('email', '')
        business_name = request.form.get('business_name', '')
        village = request.form.get('village', '')
        bank_name = request.form.get('bank_name', '')
        loan_amount = request.form.get('loan_amount', 0)
        customer_date = request.form.get('customer_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Insert into database
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO customers (name, mobile, email, business_name, village, bank_name, loan_amount, customer_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (name, mobile, email, business_name, village, bank_name, loan_amount, customer_date)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
    
    # Get today's date for default value
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_customer.html', today=today)

@app.route('/service_catalog')
def service_catalog():
    """View and manage service catalog"""
    conn = get_db_connection()
    services = conn.execute(
        'SELECT * FROM service_catalog ORDER BY service_name'
    ).fetchall()
    conn.close()
    return render_template('service_catalog.html', services=services)

@app.route('/customer_catalog')
def customer_catalog():
    """View customer catalog with search capability"""
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    if search_query:
        # Search by name or mobile (partial match)
        customers = conn.execute(
            '''SELECT * FROM customers 
               WHERE name LIKE ? OR mobile LIKE ? 
               ORDER BY name''',
            (f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        # Show all customers
        customers = conn.execute(
            'SELECT * FROM customers ORDER BY name'
        ).fetchall()
    conn.close()
    
    return render_template('customer_catalog.html', customers=customers, search_query=search_query)

@app.route('/service_catalog/add', methods=['POST'])
def add_catalog_service():
    """Add new service to catalog"""
    service_name = request.form['service_name']
    default_charge = request.form.get('default_charge', 0)
    
    conn = get_db_connection()
    # No error suppression - let IntegrityError propagate if service name is duplicate
    conn.execute(
        'INSERT INTO service_catalog (service_name, default_charge) VALUES (?, ?)',
        (service_name, default_charge)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('service_catalog'))

@app.route('/service_catalog/edit/<int:service_id>', methods=['POST'])
def edit_catalog_service(service_id):
    """Edit service in catalog"""
    default_charge = request.form.get('default_charge', 0)
    is_active = request.form.get('is_active', 1)
    
    conn = get_db_connection()
    conn.execute(
        'UPDATE service_catalog SET default_charge = ?, is_active = ? WHERE id = ?',
        (default_charge, is_active, service_id)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('service_catalog'))

@app.route('/api/services')
def api_services():
    """JSON API to get all active services"""
    conn = get_db_connection()
    services = conn.execute(
        'SELECT * FROM service_catalog WHERE is_active = 1 ORDER BY service_name'
    ).fetchall()
    conn.close()
    
    return jsonify([{
        'id': s['id'],
        'name': s['service_name'],
        'charge': s['default_charge']
    } for s in services])

@app.route('/add_services/<int:customer_id>', methods=['GET', 'POST'])
def add_services(customer_id):
    """Add services for a customer"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        service_name = request.form['service_name']
        charge = request.form.get('charge', 0)
        
        # Insert service
        conn.execute(
            'INSERT INTO services (customer_id, service_name, charge) VALUES (?, ?, ?)',
            (customer_id, service_name, charge)
        )
        conn.commit()
        
        # Redirect back to the same page to add more services
        return redirect(url_for('add_services', customer_id=customer_id))
    
    # Get customer info and existing services
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    services = conn.execute('SELECT * FROM services WHERE customer_id = ?', (customer_id,)).fetchall()
    
    # Get service catalog for dropdown
    catalog_services = conn.execute(
        'SELECT * FROM service_catalog WHERE is_active = 1 ORDER BY service_name'
    ).fetchall()
    
    conn.close()
    
    return render_template('add_services.html', customer=customer, services=services, catalog_services=catalog_services)

@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    """Delete a service from customer's ledger"""
    conn = get_db_connection()
    
    # Get customer_id before deleting
    service = conn.execute('SELECT customer_id FROM services WHERE id = ?', (service_id,)).fetchone()
    
    if service:
        customer_id = service['customer_id']
        # Delete the service
        conn.execute('DELETE FROM services WHERE id = ?', (service_id,))
        conn.commit()
        conn.close()
        
        # Check referrer to redirect back to the correct page
        referrer = request.referrer or ''
        if 'bill' in referrer:
            return redirect(url_for('bill', customer_id=customer_id))
        else:
            return redirect(url_for('add_services', customer_id=customer_id))
    else:
        conn.close()
        return "Service not found", 404

@app.route('/delete_multiple_services/<int:customer_id>', methods=['POST'])
def delete_multiple_services(customer_id):
    """Delete multiple services from customer's ledger"""
    service_ids = request.form.getlist('service_ids')
    
    if not service_ids:
        # No services selected, redirect back
        return redirect(url_for('bill', customer_id=customer_id))
    
    conn = get_db_connection()
    
    # Delete each selected service
    for service_id in service_ids:
        conn.execute('DELETE FROM services WHERE id = ? AND customer_id = ?', (service_id, customer_id))
    
    conn.commit()
    conn.close()
    
    # Redirect back to bill page
    return redirect(url_for('bill', customer_id=customer_id))

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    """Delete a customer and all associated services and payments"""
    conn = get_db_connection()
    
    # Get customer name for confirmation message
    customer = conn.execute('SELECT name FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if customer:
        # Delete the customer (CASCADE will delete associated services and payments)
        conn.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        conn.close()
        
        # Redirect to home page
        return redirect(url_for('index'))
    else:
        conn.close()
        return "Customer not found", 404


@app.route('/add_payment/<int:customer_id>', methods=['GET', 'POST'])
def add_payment(customer_id):
    """Add payment for a customer"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        
        # Insert payment
        conn.execute(
            'INSERT INTO payments (customer_id, date, amount) VALUES (?, ?, ?)',
            (customer_id, date, amount)
        )
        conn.commit()
        
        # Redirect back to the same page to add more payments
        return redirect(url_for('add_payment', customer_id=customer_id))
    
    # Get customer info and existing payments
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    payments = conn.execute('SELECT * FROM payments WHERE customer_id = ? ORDER BY date DESC', (customer_id,)).fetchall()
    conn.close()
    
    # Get today's date for default value
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('add_payment.html', customer=customer, payments=payments, today=today)

@app.route('/bill/<int:customer_id>')
def bill(customer_id):
    """Generate and display bill for a customer"""
    conn = get_db_connection()
    
    # Get customer details
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    # Get all services
    services = conn.execute('SELECT * FROM services WHERE customer_id = ?', (customer_id,)).fetchall()
    
    # Get all payments
    payments = conn.execute('SELECT * FROM payments WHERE customer_id = ? ORDER BY date', (customer_id,)).fetchall()
    
    conn.close()
    
    # Calculate totals
    total_charges = sum(service['charge'] for service in services)
    total_received = sum(payment['amount'] for payment in payments)
    balance = total_charges - total_received
    
    # Get current date
    current_date = datetime.now().strftime('%d/%m/%Y')
    
    return render_template(
        'bill.html',
        customer=customer,
        services=services,
        payments=payments,
        total_charges=total_charges,
        total_received=total_received,
        balance=balance,
        current_date=current_date
    )

@app.route('/download_pdf/<int:customer_id>')
def download_pdf(customer_id):
    """Generate and download PDF ledger for a customer"""
    conn = get_db_connection()
    
    # Get customer details
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    # Get all services
    services = conn.execute('SELECT * FROM services WHERE customer_id = ?', (customer_id,)).fetchall()
    
    # Get all payments
    payments = conn.execute('SELECT * FROM payments WHERE customer_id = ? ORDER BY date', (customer_id,)).fetchall()
    
    conn.close()
    
    # Calculate totals
    total_charges = sum(service['charge'] for service in services)
    total_received = sum(payment['amount'] for payment in payments)
    balance = total_charges - total_received
    
    # Generate PDF
    buffer = BytesIO()
    pdf = generate_ledger_pdf(buffer, customer, services, payments, total_charges, total_received, balance)
    buffer.seek(0)
    
    # Send PDF file
    filename = f"Ledger_{customer['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

def generate_ledger_pdf(buffer, customer, services, payments, total_charges, total_received, balance):
    """Generate professional PDF ledger with complete company branding"""
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=20, bottomMargin=20)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Company Header with Branding
    company_header_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1F3A5F'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    company_subtitle_style = ParagraphStyle(
        'CompanySubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#C9A227'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Add company branding
    company_name = Paragraph("GOLD COIN CONSULTANCY FINANCE SERVICES", company_header_style)
    elements.append(company_name)
    company_tagline = Paragraph("Professional Financial Consultancy", company_subtitle_style)
    elements.append(company_tagline)
    
    # Ledger title
    ledger_title_style = ParagraphStyle(
        'LedgerTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1F3A5F'),
        spaceAfter=15,
        spaceBefore=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        borderWidth=2,
        borderColor=colors.HexColor('#C9A227'),
        borderPadding=8,
        backColor=colors.HexColor('#F8F9FA')
    )
    
    title = Paragraph("LEDGER ACCOUNT", ledger_title_style)
    elements.append(title)
    elements.append(Spacer(1, 15))
    
    # Customer info table with enhanced styling
    customer_data = [
        ['Customer Name:', customer['name'], 'Date:', datetime.now().strftime('%d/%m/%Y')],
    ]
    
    # Add business name row if present
    if customer.get('business_name'):
        customer_data.append(['Business Name:', customer['business_name'], '', ''])
    
    customer_data.extend([
        ['Mobile No.:', customer['mobile'], 'Village:', customer['village'] or '-'],
        ['Bank Name:', customer['bank_name'] or '-', 'Loan Amount:', f"Rs. {customer['loan_amount']:,.0f}" if customer['loan_amount'] else '-']
    ])
    
    # Adjust column widths based on number of rows
    customer_table = Table(customer_data, colWidths=[1.5*inch, 2.5*inch, 1.3*inch, 1.7*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1F3A5F')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#1F3A5F')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#F8F9FA')),
        ('BACKGROUND', (3, 0), (3, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1F3A5F')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(customer_table)
    elements.append(Spacer(1, 20))
    
    # Section title for ledger
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1F3A5F'),
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    section_title = Paragraph("Transaction Ledger", section_style)
    elements.append(section_title)
    
    # Ledger table with all transaction details
    ledger_data = [['Date', 'Particulars', 'Credit (Rs.)', 'Received (Rs.)', 'Balance (Rs.)']]
    
    running_balance = 0
    
    # Add services with dates
    for service in services:
        running_balance += service['charge']
        date_str = service['created_at'][:10] if service['created_at'] else '-'
        ledger_data.append([
            date_str,
            service['service_name'],
            f"{service['charge']:,.0f}",
            '-',
            f"{running_balance:,.0f}"
        ])
    
    # Add total charges row if services exist
    if services:
        ledger_data.append([
            '', 
            'TOTAL CHARGES', 
            f"{total_charges:,.0f}",
            '-', 
            f"{total_charges:,.0f}"
        ])
    
    # Add payments
    for payment in payments:
        running_balance -= payment['amount']
        ledger_data.append([
            payment['date'],
            'Payment Received',
            '-',
            f"{payment['amount']:,.0f}",
            f"{running_balance:,.0f}"
        ])
    
    # Add final balance row
    ledger_data.append([
        '', 
        'FINAL BALANCE DUE', 
        '',
        '',
        f"Rs. {balance:,.0f}"
    ])
    
    ledger_table = Table(ledger_data, colWidths=[1.1*inch, 2.8*inch, 1.3*inch, 1.3*inch, 1.5*inch])
    
    # Style for ledger table
    table_style = [
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3A5F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        # Alternate row colors for transactions
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8F9FA')]),
    ]
    
    # Highlight total charges row if services exist
    total_row_index = len(services) + 1 if services else 1
    if services:
        table_style.extend([
            ('BACKGROUND', (0, total_row_index), (-1, total_row_index), colors.HexColor('#1F3A5F')),
            ('TEXTCOLOR', (0, total_row_index), (-1, total_row_index), colors.white),
            ('FONTNAME', (0, total_row_index), (-1, total_row_index), 'Helvetica-Bold'),
        ])
    
    # Highlight payments in green
    payment_start = total_row_index + 1 if services else 1
    payment_end = payment_start + len(payments) - 1
    if payments:
        for i in range(len(payments)):
            row_idx = payment_start + i
            table_style.extend([
                ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#D4EDDA')),
                ('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.HexColor('#155724')),
            ])
    
    # Highlight final balance row
    balance_row_index = len(ledger_data) - 1
    table_style.extend([
        ('BACKGROUND', (0, balance_row_index), (-1, balance_row_index), colors.HexColor('#FFF3CD')),
        ('TEXTCOLOR', (0, balance_row_index), (-1, balance_row_index), colors.HexColor('#856404')),
        ('FONTNAME', (0, balance_row_index), (-1, balance_row_index), 'Helvetica-Bold'),
        ('FONTSIZE', (0, balance_row_index), (-1, balance_row_index), 11),
    ])
    
    ledger_table.setStyle(TableStyle(table_style))
    
    elements.append(ledger_table)
    elements.append(Spacer(1, 20))
    
    # Balance summary text
    balance_style = ParagraphStyle(
        'BalanceStyle',
        parent=styles['Normal'],
        fontSize=13,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1F3A5F'),
    )
    
    if balance == 0:
        balance_text = Paragraph("ACCOUNT FULLY PAID - Balance: Rs. 0/-", balance_style)
    else:
        balance_text = Paragraph(f"Outstanding Balance: Rs. {balance:,.0f}/-", balance_style)
    
    elements.append(balance_text)
    elements.append(Spacer(1, 8))
    
    # Note
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Italic'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    note = Paragraph("E. &amp; O.E. (Errors and Omissions Excepted)", note_style)
    elements.append(note)
    elements.append(Spacer(1, 20))
    
    # Company Footer with complete contact details
    footer_title_style = ParagraphStyle(
        'FooterTitle',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1F3A5F'),
        spaceAfter=5
    )
    
    footer_text_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=9,  # Increased from 8 for better readability
        textColor=colors.HexColor('#333333'),
        leading=11
    )
    
    # Company footer information
    footer_data = [
        [
            Paragraph("<b>Gold Coin Consultancy Finance Services</b><br/><font size=8>Laxmi Narayan Nivas Samor,<br/>Savarkar Nagar, Vita, Khanapur,<br/>Dist. Sangli - 415311</font>", footer_text_style),
            Paragraph("<b>Contact Numbers:</b><br/><font size=8>Ravikiran: +91 84216 24116<br/>Shriyash: +91 90216 74548</font>", footer_text_style),
            Paragraph("<b>Services Offered:</b><br/><font size=8>Personal Loan, Business Loan<br/>Mortgage Loan, Home Loan<br/>Vehicle Loan, CMEGP/PMEGP<br/>Annasaheb Patil Mahamandal Loans</font>", footer_text_style),
        ]
    ]
    
    footer_table = Table(footer_data, colWidths=[2.5*inch, 2*inch, 3.5*inch])
    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#C9A227')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
    ]))
    
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    
    return buffer

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    init_db()
    
    # Run the Flask app
    print("\n" + "="*50)
    print("🏢 Consultancy Billing & Ledger System")
    print("="*50)
    print("📍 Server: http://localhost:5000")
    print("="*50 + "\n")
    
    # Debug mode enabled by default for error visibility
    # Set FLASK_DEBUG=False in production environment
    debug_mode = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    # Get PORT from environment (for Render deployment) or default to 5000
    port = int(os.getenv('PORT', 5000))
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
