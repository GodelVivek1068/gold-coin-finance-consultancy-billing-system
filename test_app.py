"""
Full functionality test for the billing system using Flask test client.
Run with: python test_app.py
"""
import sys
import os

# Change to the project directory so database.db and database.sql resolve correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import app as application

client = application.app.test_client()
application.app.config['TESTING'] = True

# Make sure DB is initialized
application.init_db()

results = []

def check(step, response, expected_status=200, expected_text=None):
    ok  = response.status_code == expected_status
    txt = response.data.decode('utf-8', errors='ignore')
    if expected_text:
        ok = ok and expected_text in txt
    status = "✅ PASS" if ok else "❌ FAIL"
    detail = ""
    if not ok:
        detail = f" | status={response.status_code}"
        if expected_text and expected_text not in txt:
            detail += f" | missing text: '{expected_text}'"
    results.append(f"{status}  {step}{detail}")
    return ok

# ── 1. Home page ──────────────────────────────────────────────────────────────
r = client.get('/')
check("Home page loads", r, 200)

# ── 2. Add customer page renders ──────────────────────────────────────────────
r = client.get('/add_customer')
check("Add customer page renders", r, 200, "Add Customer")

# ── 3. Add a test customer ────────────────────────────────────────────────────
r = client.post('/add_customer', data={
    'name':          'Test Customer',
    'mobile':        '9876543210',
    'email':         'test@test.com',
    'business_name': 'Test Business',
    'village':       'Test Village',
    'bank_name':     'SBI',
    'loan_amount':   '50000',
    'customer_date': '2026-02-22',
}, follow_redirects=True)
check("Add customer (POST)", r, 200, "Test Customer")

# Get customer ID from DB
conn = application.get_db_connection()
customer = conn.execute("SELECT id FROM customers WHERE mobile='9876543210'").fetchone()
conn.close()
assert customer, "Customer not found in DB after insert"
cid = customer['id']

# ── 4. Customer catalog ────────────────────────────────────────────────────────
r = client.get('/customer_catalog')
check("Customer catalog loads", r, 200, "Test Customer")

r = client.get('/customer_catalog?search=Test')
check("Customer catalog search", r, 200, "Test Customer")

# ── 5. Service catalog ────────────────────────────────────────────────────────
r = client.get('/service_catalog')
check("Service catalog loads", r, 200)

# ── 6. Add a custom service to catalog ────────────────────────────────────────
r = client.post('/service_catalog/add', data={
    'service_name':   'Test Service',
    'default_charge': '999',
}, follow_redirects=True)
check("Add service to catalog", r, 200)

# ── 7. API services endpoint ──────────────────────────────────────────────────
r = client.get('/api/services')
check("API /api/services returns JSON", r, 200)

# ── 8. Add services page renders ─────────────────────────────────────────────
r = client.get(f'/add_services/{cid}')
check("Add services page renders", r, 200, "Test Customer")

# ── 9. Add a service to the customer ─────────────────────────────────────────
r = client.post(f'/add_services/{cid}', data={
    'service_name': 'ITR',
    'charge':       '500',
}, follow_redirects=True)
check("Add service ITR (charge 500)", r, 200, "ITR")

r = client.post(f'/add_services/{cid}', data={
    'service_name': 'Xerox',
    'charge':       '200',
}, follow_redirects=True)
check("Add service Xerox (charge 200)", r, 200, "Xerox")

# ── 10. Add payment page renders ──────────────────────────────────────────────
r = client.get(f'/add_payment/{cid}')
check("Add payment page renders", r, 200, "Test Customer")

# ── 11. Add a payment ─────────────────────────────────────────────────────────
r = client.post(f'/add_payment/{cid}', data={
    'date':   '2026-02-22',
    'amount': '300',
}, follow_redirects=True)
check("Add payment Rs.300", r, 200, "300")

# ── 12. Bill page — verify totals ─────────────────────────────────────────────
r = client.get(f'/bill/{cid}')
txt = r.data.decode('utf-8', errors='ignore')
check("Bill page loads",           r, 200)
check("Bill shows total 700",      r, 200, "700")
check("Bill shows payment 300",    r, 200, "300")
check("Bill shows balance 400",    r, 200, "400")

# ── 13. Download PDF ──────────────────────────────────────────────────────────
r = client.get(f'/download_pdf/{cid}')
check("PDF download (content-type)", r, 200)
pdf_ok = b'%PDF' in r.data
results.append(f"{'✅ PASS' if pdf_ok else '❌ FAIL'}  PDF is valid PDF binary")

# ── 14. Delete a service ──────────────────────────────────────────────────────
conn = application.get_db_connection()
svc = conn.execute(f"SELECT id FROM services WHERE customer_id={cid} LIMIT 1").fetchone()
conn.close()
if svc:
    r = client.post(f'/delete_service/{svc["id"]}', follow_redirects=True)
    check("Delete one service", r, 200)

# ── 15. Delete the customer ───────────────────────────────────────────────────
r = client.post(f'/delete_customer/{cid}', follow_redirects=True)
check("Delete customer", r, 200)

conn = application.get_db_connection()
gone = conn.execute(f"SELECT id FROM customers WHERE id={cid}").fetchone()
conn.close()
results.append(f"{'✅ PASS' if not gone else '❌ FAIL'}  Customer removed from DB")

# ── Print report ──────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  BILLING SYSTEM — FULL FUNCTIONALITY TEST REPORT")
print("="*55)
for r in results:
    print(f"  {r}")
print("="*55)
passed = sum(1 for r in results if "PASS" in r)
total  = len(results)
print(f"  Result: {passed}/{total} tests passed")
print("="*55 + "\n")

if passed < total:
    sys.exit(1)
