"""
Consultancy Billing & Ledger System
Flask web application — PostgreSQL mode (Railway / Supabase compatible)
"""

import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DATABASE_URL = os.getenv('DATABASE_URL', '')



# ── Database helpers ─────────────────────────────────────────────────────────

def get_db_connection():
    """Return a psycopg2 connection with dict-like row access."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def get_cursor(conn):
    """Return a RealDictCursor so rows behave like dicts (same as sqlite3.Row)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """Initialize the PostgreSQL database from database.sql (safe to re-run)."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    with open(os.path.join(os.path.dirname(__file__), 'database.sql'), 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    cur.close()
    conn.close()
    print("[OK] PostgreSQL database initialized / verified")


# ── Routes ────────────────────────────────────────────────────────────────────
# Always initialize the DB (works for both gunicorn and direct python run)
if DATABASE_URL:
    init_db()
else:
    print("[WARNING] DATABASE_URL not set - skipping init_db (set it in Railway Variables)")


@app.route('/health')
def health():
    """Lightweight healthcheck — no DB required."""
    return 'OK', 200


@app.route('/')
def home():
    return "Gold Coin Billing API Running ✅"


@app.route('/dashboard')
def index():
    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute('SELECT * FROM customers ORDER BY created_at DESC')
    customers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', customers=customers)


@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name          = request.form['name']
        mobile        = request.form['mobile']
        email         = request.form.get('email', '')
        business_name = request.form.get('business_name', '')
        village       = request.form.get('village', '')
        bank_name     = request.form.get('bank_name', '')
        loan_amount   = request.form.get('loan_amount', 0) or 0
        customer_date = request.form.get('customer_date') or datetime.now().strftime('%Y-%m-%d')

        conn = get_db_connection()
        cur  = get_cursor(conn)
        cur.execute(
            '''INSERT INTO customers
               (name, mobile, email, business_name, village, bank_name, loan_amount, customer_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (name, mobile, email, business_name, village, bank_name, loan_amount, customer_date)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_customer.html', today=today)


@app.route('/service_catalog')
def service_catalog():
    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute('SELECT * FROM service_catalog ORDER BY service_name')
    services = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('service_catalog.html', services=services)


@app.route('/customer_catalog')
def customer_catalog():
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    cur  = get_cursor(conn)

    if search_query:
        cur.execute(
            "SELECT * FROM customers WHERE name ILIKE %s OR mobile ILIKE %s ORDER BY name",
            (f'%{search_query}%', f'%{search_query}%')
        )
    else:
        cur.execute('SELECT * FROM customers ORDER BY name')

    customers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('customer_catalog.html', customers=customers, search_query=search_query)


@app.route('/service_catalog/add', methods=['POST'])
def add_catalog_service():
    service_name   = request.form['service_name']
    default_charge = request.form.get('default_charge', 0) or 0

    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute(
        'INSERT INTO service_catalog (service_name, default_charge) VALUES (%s, %s)',
        (service_name, default_charge)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('service_catalog'))


@app.route('/service_catalog/edit/<int:service_id>', methods=['POST'])
def edit_catalog_service(service_id):
    default_charge = request.form.get('default_charge', 0) or 0
    is_active      = request.form.get('is_active', 1)

    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute(
        'UPDATE service_catalog SET default_charge = %s, is_active = %s WHERE id = %s',
        (default_charge, is_active, service_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('service_catalog'))


@app.route('/api/services')
def api_services():
    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute('SELECT * FROM service_catalog WHERE is_active = 1 ORDER BY service_name')
    services = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        'id':     s['id'],
        'name':   s['service_name'],
        'charge': s['default_charge']
    } for s in services])


@app.route('/add_services/<int:customer_id>', methods=['GET', 'POST'])
def add_services(customer_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)

    if request.method == 'POST':
        service_name = request.form['service_name']
        charge       = request.form.get('charge', 0) or 0
        cur.execute(
            'INSERT INTO services (customer_id, service_name, charge) VALUES (%s, %s, %s)',
            (customer_id, service_name, charge)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('add_services', customer_id=customer_id))

    cur.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT * FROM services WHERE customer_id = %s', (customer_id,))
    services = cur.fetchall()
    cur.execute('SELECT * FROM service_catalog WHERE is_active = 1 ORDER BY service_name')
    catalog_services = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('add_services.html',
                           customer=customer, services=services, catalog_services=catalog_services)


@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute('SELECT customer_id FROM services WHERE id = %s', (service_id,))
    service = cur.fetchone()

    if service:
        customer_id = service['customer_id']
        cur.execute('DELETE FROM services WHERE id = %s', (service_id,))
        conn.commit()
        cur.close()
        conn.close()
        referrer = request.referrer or ''
        if 'bill' in referrer:
            return redirect(url_for('bill', customer_id=customer_id))
        return redirect(url_for('add_services', customer_id=customer_id))

    cur.close()
    conn.close()
    return "Service not found", 404


@app.route('/delete_multiple_services/<int:customer_id>', methods=['POST'])
def delete_multiple_services(customer_id):
    service_ids = request.form.getlist('service_ids')
    if not service_ids:
        return redirect(url_for('bill', customer_id=customer_id))

    conn = get_db_connection()
    cur  = get_cursor(conn)
    for sid in service_ids:
        cur.execute('DELETE FROM services WHERE id = %s AND customer_id = %s', (sid, customer_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('bill', customer_id=customer_id))


@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)
    cur.execute('SELECT name FROM customers WHERE id = %s', (customer_id,))
    customer = cur.fetchone()

    if customer:
        cur.execute('DELETE FROM customers WHERE id = %s', (customer_id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    cur.close()
    conn.close()
    return "Customer not found", 404


@app.route('/add_payment/<int:customer_id>', methods=['GET', 'POST'])
def add_payment(customer_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)

    if request.method == 'POST':
        date   = request.form['date']
        amount = request.form['amount']
        cur.execute(
            'INSERT INTO payments (customer_id, date, amount) VALUES (%s, %s, %s)',
            (customer_id, date, amount)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('add_payment', customer_id=customer_id))

    cur.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT * FROM payments WHERE customer_id = %s ORDER BY date DESC', (customer_id,))
    payments = cur.fetchall()
    cur.close()
    conn.close()

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_payment.html', customer=customer, payments=payments, today=today)


@app.route('/bill/<int:customer_id>')
def bill(customer_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)

    cur.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT * FROM services WHERE customer_id = %s', (customer_id,))
    services = cur.fetchall()
    cur.execute('SELECT * FROM payments WHERE customer_id = %s ORDER BY date', (customer_id,))
    payments = cur.fetchall()
    cur.close()
    conn.close()

    total_charges  = sum(s['charge'] for s in services)
    total_received = sum(p['amount'] for p in payments)
    balance        = total_charges - total_received
    current_date   = datetime.now().strftime('%d/%m/%Y')

    return render_template('bill.html',
                           customer=customer,
                           services=services,
                           payments=payments,
                           total_charges=total_charges,
                           total_received=total_received,
                           balance=balance,
                           current_date=current_date)


@app.route('/download_pdf/<int:customer_id>')
def download_pdf(customer_id):
    conn = get_db_connection()
    cur  = get_cursor(conn)

    cur.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
    customer = cur.fetchone()
    cur.execute('SELECT * FROM services WHERE customer_id = %s', (customer_id,))
    services = cur.fetchall()
    cur.execute('SELECT * FROM payments WHERE customer_id = %s ORDER BY date', (customer_id,))
    payments = cur.fetchall()
    cur.close()
    conn.close()

    total_charges  = sum(s['charge'] for s in services)
    total_received = sum(p['amount'] for p in payments)
    balance        = total_charges - total_received

    buffer = BytesIO()
    generate_ledger_pdf(buffer, customer, services, payments, total_charges, total_received, balance)
    buffer.seek(0)

    filename = f"Ledger_{customer['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


# ── PDF Generation ────────────────────────────────────────────────────────────

def generate_ledger_pdf(buffer, customer, services, payments, total_charges, total_received, balance):
    """Generate a professional A4 PDF ledger."""
    doc      = SimpleDocTemplate(buffer, pagesize=A4,
                                 rightMargin=30, leftMargin=30,
                                 topMargin=20,  bottomMargin=20)
    elements = []
    styles   = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    # ── Header ────────────────────────────────────────────────────────────────
    elements += [
        Paragraph("GOLD COIN CONSULTANCY FINANCE SERVICES",
                  ps('H', fontSize=24, fontName='Helvetica-Bold',
                     textColor=colors.HexColor('#1F3A5F'), alignment=TA_CENTER, spaceAfter=8)),
        Paragraph("Professional Financial Consultancy",
                  ps('Sub', fontSize=10, fontName='Helvetica-Bold',
                     textColor=colors.HexColor('#C9A227'), alignment=TA_CENTER, spaceAfter=15)),
        Paragraph("LEDGER ACCOUNT",
                  ps('Title', fontSize=18, fontName='Helvetica-Bold',
                     textColor=colors.HexColor('#1F3A5F'), alignment=TA_CENTER,
                     spaceAfter=15, spaceBefore=5,
                     borderWidth=2, borderColor=colors.HexColor('#C9A227'),
                     borderPadding=8, backColor=colors.HexColor('#F8F9FA'))),
        Spacer(1, 15),
    ]

    # ── Customer info table ───────────────────────────────────────────────────
    cdata = [['Customer Name:', customer['name'], 'Date:', datetime.now().strftime('%d/%m/%Y')]]
    if customer['business_name']:
        cdata.append(['Business Name:', customer['business_name'], '', ''])
    cdata += [
        ['Mobile No.:',  customer['mobile'],
         'Village:',     customer['village'] or '-'],
        ['Bank Name:',   customer['bank_name'] or '-',
         'Loan Amount:', f"Rs. {customer['loan_amount']:,.0f}" if customer['loan_amount'] else '-'],
    ]
    ctbl = Table(cdata, colWidths=[1.5*inch, 2.5*inch, 1.3*inch, 1.7*inch])
    ctbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(0,-1), colors.HexColor('#1F3A5F')),
        ('BACKGROUND',   (2,0),(2,-1), colors.HexColor('#1F3A5F')),
        ('BACKGROUND',   (1,0),(1,-1), colors.HexColor('#F8F9FA')),
        ('BACKGROUND',   (3,0),(3,-1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR',    (0,0),(0,-1), colors.white),
        ('TEXTCOLOR',    (2,0),(2,-1), colors.white),
        ('GRID',         (0,0),(-1,-1), 1, colors.HexColor('#1F3A5F')),
        ('FONTNAME',     (0,0),(0,-1), 'Helvetica-Bold'),
        ('FONTNAME',     (2,0),(2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),(-1,-1), 9),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0),(-1,-1), 8),
        ('RIGHTPADDING', (0,0),(-1,-1), 8),
        ('TOPPADDING',   (0,0),(-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1), 6),
    ]))
    elements += [ctbl, Spacer(1, 20)]

    # ── Ledger table ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Transaction Ledger",
                               ps('Sec', fontSize=14, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#1F3A5F'), spaceAfter=10)))

    ldata   = [['Date', 'Particulars', 'Credit (Rs.)', 'Received (Rs.)', 'Balance (Rs.)']]
    running = 0.0

    for s in services:
        running  += s['charge']
        date_str  = str(s['created_at'])[:10] if s['created_at'] else '-'
        ldata.append([date_str, s['service_name'], f"{s['charge']:,.0f}", '-', f"{running:,.0f}"])

    if services:
        ldata.append(['', 'TOTAL CHARGES', f"{total_charges:,.0f}", '-', f"{total_charges:,.0f}"])

    for p in payments:
        running -= p['amount']
        ldata.append([p['date'], 'Payment Received', '-', f"{p['amount']:,.0f}", f"{running:,.0f}"])

    ldata.append(['', 'FINAL BALANCE DUE', '', '', f"Rs. {balance:,.0f}"])

    ltbl    = Table(ldata, colWidths=[1.1*inch, 2.8*inch, 1.3*inch, 1.3*inch, 1.5*inch])
    tstyle  = [
        ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#1F3A5F')),
        ('TEXTCOLOR',     (0,0),(-1,0),  colors.whitesmoke),
        ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,0),  10),
        ('FONTSIZE',      (0,1),(-1,-1), 9),
        ('ALIGN',         (0,0),(-1,-1), 'LEFT'),
        ('ALIGN',         (2,0),(-1,-1), 'RIGHT'),
        ('GRID',          (0,0),(-1,-1), 1, colors.HexColor('#CCCCCC')),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ('TOPPADDING',    (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('ROWBACKGROUNDS',(0,1),(-1,-2), [colors.white, colors.HexColor('#F8F9FA')]),
    ]

    tri = len(services) + 1
    if services:
        tstyle += [
            ('BACKGROUND', (0,tri),(-1,tri), colors.HexColor('#1F3A5F')),
            ('TEXTCOLOR',  (0,tri),(-1,tri), colors.white),
            ('FONTNAME',   (0,tri),(-1,tri), 'Helvetica-Bold'),
        ]

    pstart = tri + 1 if services else 1
    for i in range(len(payments)):
        ri = pstart + i
        tstyle += [
            ('BACKGROUND', (0,ri),(-1,ri), colors.HexColor('#D4EDDA')),
            ('TEXTCOLOR',  (0,ri),(-1,ri), colors.HexColor('#155724')),
        ]

    bri = len(ldata) - 1
    tstyle += [
        ('BACKGROUND', (0,bri),(-1,bri), colors.HexColor('#FFF3CD')),
        ('TEXTCOLOR',  (0,bri),(-1,bri), colors.HexColor('#856404')),
        ('FONTNAME',   (0,bri),(-1,bri), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,bri),(-1,bri), 11),
    ]
    ltbl.setStyle(TableStyle(tstyle))
    elements += [ltbl, Spacer(1, 20)]

    # ── Balance summary ───────────────────────────────────────────────────────
    bal_text = ("ACCOUNT FULLY PAID - Balance: Rs. 0/-" if balance == 0
                else f"Outstanding Balance: Rs. {balance:,.0f}/-")
    elements.append(Paragraph(bal_text,
                               ps('Bal', fontSize=13, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, textColor=colors.HexColor('#1F3A5F'))))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("E. &amp; O.E. (Errors and Omissions Excepted)",
                               ps('Note', fontSize=9, alignment=TA_CENTER, textColor=colors.grey)))
    elements.append(Spacer(1, 20))

    # ── Footer ────────────────────────────────────────────────────────────────
    ft = ps('FT', fontSize=9, textColor=colors.HexColor('#333333'), leading=11)
    fdata = [[
        Paragraph("<b>Gold Coin Consultancy Finance Services</b><br/>"
                  "<font size=8>Laxmi Narayan Nivas Samor,<br/>"
                  "Savarkar Nagar, Vita, Khanapur,<br/>"
                  "Dist. Sangli - 415311</font>", ft),
        Paragraph("<b>Contact Numbers:</b><br/>"
                  "<font size=8>Ravikiran: +91 84216 24116<br/>"
                  "Shriyash: +91 90216 74548</font>", ft),
        Paragraph("<b>Services Offered:</b><br/>"
                  "<font size=8>Personal Loan, Business Loan<br/>"
                  "Mortgage Loan, Home Loan<br/>"
                  "Vehicle Loan, CMEGP/PMEGP<br/>"
                  "Annasaheb Patil Mahamandal Loans</font>", ft),
    ]]
    ftbl = Table(fdata, colWidths=[2.5*inch, 2*inch, 3.5*inch])
    ftbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX',          (0,0),(-1,-1), 2, colors.HexColor('#C9A227')),
        ('GRID',         (0,0),(-1,-1), 1, colors.HexColor('#E0E0E0')),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
        ('TOPPADDING',   (0,0),(-1,-1), 10),
        ('BOTTOMPADDING',(0,0),(-1,-1), 10),
    ]))
    elements.append(ftbl)
    doc.build(elements)
    return buffer


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  Consultancy Billing & Ledger System")
    print("=" * 50)
    print("  Server:   http://localhost:5000")
    print("  Database: PostgreSQL (DATABASE_URL)")
    print("=" * 50 + "\n")

    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1')
    port       = int(os.getenv('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
