"""
Consultancy Billing & Ledger System
A Flask-based web application for managing customer billing, services, and payments
Enhanced with Service Catalog and PDF Generation
"""

import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.config['DATABASE'] = 'database.db'

# Database helper functions
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initialize database from schema file"""
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
                
        except Exception as e:
            print(f"⚠️  Migration note: {e}")
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
        village = request.form.get('village', '')
        bank_name = request.form.get('bank_name', '')
        loan_amount = request.form.get('loan_amount', 0)
        customer_date = request.form.get('customer_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Insert into database
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO customers (name, mobile, village, bank_name, loan_amount, customer_date) VALUES (?, ?, ?, ?, ?, ?)',
            (name, mobile, village, bank_name, loan_amount, customer_date)
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

@app.route('/service_catalog/add', methods=['POST'])
def add_catalog_service():
    """Add new service to catalog"""
    service_name = request.form['service_name']
    default_charge = request.form.get('default_charge', 0)
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO service_catalog (service_name, default_charge) VALUES (?, ?)',
            (service_name, default_charge)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Service already exists
        pass
    finally:
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
    """Generate professional PDF ledger"""
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Add title
    title = Paragraph("LEDGER ACCOUNT", header_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Customer info table
    customer_data = [
        ['Customer Name:', customer['name'], 'Date:', datetime.now().strftime('%d/%m/%Y')],
        ['Mobile No:', customer['mobile'], 'Village:', customer['village'] or '-'],
        ['Bank Name:', customer['bank_name'] or '-', 'Loan Amount:', f"₹{customer['loan_amount']:.0f}" if customer['loan_amount'] else '-']
    ]
    
    customer_table = Table(customer_data, colWidths=[1.5*inch, 2.5*inch, 1.3*inch, 1.7*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
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
    
    # Ledger table
    ledger_data = [['Date', 'Particulars', 'Credit (₹)', 'Received (₹)', 'Balance (₹)']]
    
    running_balance = 0
    
    # Add services
    for service in services:
        running_balance += service['charge']
        date_str = service['created_at'][:10] if service['created_at'] else '-'
        ledger_data.append([
            date_str,
            service['service_name'],
            f"{service['charge']:.0f}",
            '',
            f"{running_balance:.0f}"
        ])
    
    # Add total row if services exist
    if services:
        ledger_data.append([
            '', 'Total', '', '', f"{total_charges:.0f}"
        ])
    
    # Add payments
    for payment in payments:
        running_balance -= payment['amount']
        ledger_data.append([
            payment['date'],
            'Payment',
            '0',
            f"{payment['amount']:.0f}",
            f"{running_balance:.0f}"
        ])
    
    # Add final balance
    ledger_data.append([
        '', 'Balance', '', '', f"{balance:.0f}"
    ])
    
    ledger_table = Table(ledger_data, colWidths=[1.2*inch, 3*inch, 1.2*inch, 1.3*inch, 1.3*inch])
    
    # Style for ledger table
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    
    # Highlight total and balance rows
    total_row_index = len(services) + 1 if services else 1
    balance_row_index = len(ledger_data) - 1
    
    if services:
        table_style.extend([
            ('BACKGROUND', (0, total_row_index), (-1, total_row_index), colors.HexColor('#f9f9f9')),
            ('FONTNAME', (0, total_row_index), (-1, total_row_index), 'Helvetica-Bold'),
        ])
    
    table_style.extend([
        ('BACKGROUND', (0, balance_row_index), (-1, balance_row_index), colors.HexColor('#fff3cd')),
        ('FONTNAME', (0, balance_row_index), (-1, balance_row_index), 'Helvetica-Bold'),
    ])
    
    ledger_table.setStyle(TableStyle(table_style))
    
    elements.append(ledger_table)
    elements.append(Spacer(1, 20))
    
    # Balance text
    balance_style = ParagraphStyle(
        'BalanceStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )
    
    if balance == 0:
        balance_text = Paragraph("एकूण येणे बाकी = 0/-", balance_style)
    else:
        balance_text = Paragraph(f"Balance Due: ₹{balance:.0f}/-", balance_style)
    
    elements.append(balance_text)
    elements.append(Spacer(1, 10))
    
    # Marathi note
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Italic'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    note = Paragraph("चुकभूल क्षमस्व", note_style)
    elements.append(note)
    
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
    
    app.run(debug=True, host='0.0.0.0', port=5000)
