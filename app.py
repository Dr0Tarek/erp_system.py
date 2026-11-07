import io
import json
import hashlib
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(page_title="حسابات طارق",layout="wide")
DB="erp_v8.db"
BUILD="TAREK-SINGLE-227"
MONTHS=["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
ACTIONS={"view":"عرض","add":"إضافة","edit":"تعديل","delete":"حذف","import":"استيراد","export":"تصدير","settle":"سداد","receive":"تغيير الاستلام"}
RAW={
"العملاء":("customers","customer_code:كود العميل:t;customer_name:اسم العميل:t;payment_method:طريقة الدفع:t;due_days:مدة الاستحقاق:n;due_type:نوع الاستحقاق:t;opening_balance:رصيد أول المدة:n;branches_count:عدد الفروع:n;branches:الفروع:t;tax_number:الرقم الضريبي:t;invoice_plus_invoice:تنبيه فاتورة + فاتورة:t;credit_limit:الحد الأقصى للعميل:n"),
"المبيعات":("sales","invoice_no:رقم الفاتورة:t;invoice_date:تاريخ الفاتورة:d;customer_code:كود العميل:t;customer_name:اسم العميل:t;invoice_total:إجمالي الفاتورة:n;before_tax:قيمة قبل الضريبة:n;receipt_status:حالة الاستلام:t;supply_order_no:رقم أمر التوريد:t;external_link:الرابط الخارجى:t"),
"المرتجعات":("returns","return_date:تاريخ المرتجع:d;return_no:رقم المرتجع:t;original_invoice_no:رقم الفاتورة الأصلية:t;customer_code:كود العميل:t;customer_name:اسم العميل:t;return_total:إجمالي المرتجع:n;before_tax:قبل الضريبة:n;reason:سبب المرتجع:t;external_link:الرابط الخارجى:t"),
"التحصيلات":("collections","collection_date:تاريخ التحصيل:d;customer_code:كود العميل:t;customer_name:اسم العميل:t;invoice_no:رقم الفاتورة:t;amount:مبلغ التحصيل:n;collector_name:المحصل:t;month:الشهر:t;year:السنة:n;notes:ملاحظات:t"),
"الخصومات":("discounts","discount_date:تاريخ الخصم:d;customer_code:كود العميل:t;customer_name:اسم العميل:t;invoice_no:رقم الفاتورة:t;discount_type:نوع الخصم:t;discount_percent:نسبة الخصم %:n;fixed_amount:مبلغ الخصم الثابت:n;invoice_total:إجمالي المبلغ:n;before_tax:قبل الضريبة:n;reason:سبب الخصم:t;month:الشهر:t;year:السنة:n;correction:تصحيح:t;notes:ملاحظات:t;external_link:الرابط الخارجى:t"),
"خصومات العقد":("contract_discounts","customer_code:كود العميل:t;customer_name:اسم العميل:t;discount_type:نوع الخصم:t;percent:النسبة %:n;amount:المبلغ:n;applied_on:على ماذا:t;conditions:الشروط:t;start_date:تاريخ البداية:d;end_date:تاريخ النهاية:d;apply_discount:تطبيق الخصم:t"),
"المجلات":("magazines","customer_code:كود العميل:t;customer_name:اسم العميل:t;month:الشهر:t;year:السنة:n;discount_value:قيمة خصم المجلة:n;magazine_type:نوع المجلة:t;notes:ملاحظات:t"),
"العروض":("offers","customer_code:كود العميل:t;customer_name:اسم العميل:t;description:وصف العرض:t;discount_percent:نسبة الخصم %:n;start_date:تاريخ البداية:d;end_date:تاريخ النهاية:d"),
"الموردين":("suppliers","supplier_code:كود المورد:t;supplier_name:اسم المورد:t;phone:الهاتف:t;tax_number:الرقم الضريبي:t;opening_balance:رصيد أول المدة:n;notes:ملاحظات:t"),
"فواتير الموردين":("supplier_invoices","invoice_no:رقم الفاتورة:t;invoice_date:تاريخ الفاتورة:d;supplier_code:كود المورد:t;supplier_name:اسم المورد:t;invoice_total:إجمالي الفاتورة:n;paid_amount:المدفوع:n;notes:ملاحظات:t"),
"البنوك":("bank_accounts","account_name:اسم الحساب:t;bank_name:اسم البنك:t;account_number:رقم الحساب:t;opening_balance:رصيد أول المدة:n"),
"الحركات البنكية":("bank_transactions","transaction_date:تاريخ الحركة:d;account_name:اسم الحساب:t;transaction_type:نوع الحركة:t;amount:المبلغ:n;notes:ملاحظات:t"),
"المصروفات":("expenses","expense_date:تاريخ المصروف:d;expense_group:نوع المصروف:t;expense_type:تفصيل المصروف:t;amount:المبلغ:n;notes:ملاحظات:t"),
"المسودة":("dropdown_options","page:الصفحة:t;field:القائمة:t;value:القيمة:t")}
CONFIG={p:(t,[tuple(f.split(':')) for f in fs.split(';')]) for p,(t,fs) in RAW.items()}
CLIENT_PAGES=list(CONFIG)[1:8]
PAGES=list(CONFIG)+["كشف الحساب","الملخص","إدارة المستخدمين","إعدادات الشركة"]
GROUPS={"حسابات العملاء والمبيعات":list(CONFIG)[:8]+["كشف الحساب","الملخص"],"الموردين":["الموردين","فواتير الموردين"],"البنوك":["البنوك","الحركات البنكية"],"المصروفات":["المصروفات"],"المسودة":["المسودة"],"الإعدادات":["إدارة المستخدمين","إعدادات الشركة"]}
LISTS={"payment_method":["كاش","آجل","على المبيع","فاتورة + فاتورة"],"due_type":["يوم من تاريخ الفاتورة","يوم من نهاية شهر الفاتورة","شهر"],"receipt_status":["تم الاستلام","لم يتم الاستلام","مرتجع","مرتجع جزئى"],"invoice_plus_invoice":["لا","نعم"],"discount_type":["نسبة مئوية","مبلغ ثابت"],"apply_discount":["لا","نعم"],"collector_name":["محمد رمضان","ايمن","حماده","طارق","مندوب مبيعات"],"month":MONTHS,"expense_group":["مصاريف الأستاذ","مصاريف الخزينة","سداد الافريقية"],"expense_type":["بنزين","مصاريف","سداد الافريقية","وارد","منصرف"],"transaction_type":["إيداع","سحب"]}
EXTRAS={"sales":{"due_date":"TEXT","payment_method":"TEXT","discount_note":"REAL","tax_amount":"REAL"},"returns":{"due_date":"TEXT","tax_amount":"REAL"},"discounts":{"discount_value":"REAL","tax_amount":"REAL"}}

def db():
    c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row; return c

def read(sql,args=()):
    c=db()
    try: return pd.read_sql_query(sql,c,params=args)
    finally: c.close()

def write(sql,args=()):
    c=db()
    try:
        with c: c.execute(sql,args)
    finally: c.close()

def txt(v): return '' if v is None or pd.isna(v) else str(v).strip()
def num(v): return float(txt(v).replace(',','') or 0)
def digest(v): return hashlib.sha256(str(v).encode()).hexdigest()

def initialize():
    c=db()
    try:
        with c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT,full_name TEXT,role TEXT,company_id INTEGER,permissions TEXT,is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY,name TEXT,system_name TEXT,language TEXT,logo_path TEXT);
CREATE TABLE IF NOT EXISTS page_permissions(user_id INTEGER,page TEXT,action TEXT,allowed INTEGER,PRIMARY KEY(user_id,page,action));
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY,created_at TEXT DEFAULT CURRENT_TIMESTAMP,user_id INTEGER,action TEXT,details TEXT);
''')
            for p,(t,fs) in CONFIG.items():
                c.execute(f'CREATE TABLE IF NOT EXISTS "{t}"(id INTEGER PRIMARY KEY AUTOINCREMENT,company_id INTEGER)')
                existing={r['name'] for r in c.execute(f'PRAGMA table_info("{t}")')}
                columns={n:'REAL' if k=='n' else 'TEXT' for n,l,k in fs}; columns['company_id']='INTEGER'; columns.update(EXTRAS.get(t,{}))
                for n,k in columns.items():
                    if n not in existing: c.execute(f'ALTER TABLE "{t}" ADD COLUMN "{n}" {k}')
            c.execute('INSERT OR IGNORE INTO companies(id,name,system_name,language) VALUES(1,?,?,?)',('الشركة الرئيسية','نظام الحسابات والمبيعات','العربية'))
            if c.execute('SELECT id FROM users WHERE username=? COLLATE NOCASE',('tarek',)).fetchone() is None:
                c.execute('INSERT INTO users(username,password_hash,full_name,role,company_id,permissions,is_active) VALUES(?,?,?,?,?,?,1)',('tarek',digest('159019'),'طارق','super_admin',1,'ALL'))
    finally: c.close()

def admin(): return st.session_state.user['role']=='super_admin'
def can(p,a):
    if admin(): return True
    result=read('SELECT allowed FROM page_permissions WHERE user_id=? AND page=? AND action=?',(int(st.session_state.user['id']),p,a))
    return not result.empty and bool(result.iloc[0]['allowed'])
def require(p,a):
    if not can(p,'view') or not can(p,a): raise ValueError('ليس لديك صلاحية هذه العملية')
def data(p): return read(f'SELECT * FROM "{CONFIG[p][0]}" WHERE company_id=1 ORDER BY id DESC')
def log(c,a,details): c.execute('INSERT INTO audit_events(user_id,action,details) VALUES(?,?,?)',(int(st.session_state.user['id']),a,json.dumps(details,ensure_ascii=False)))

def choices(n,l):
    found=read('SELECT DISTINCT value FROM dropdown_options WHERE company_id=1 AND field IN (?,?) ORDER BY id',(n,l))
    return found.value.dropna().astype(str).tolist() if not found.empty else LISTS.get(n,[])

def picker(prefix,initial=''):
    cs=data('العملاء'); mapping={str(r.customer_code):str(r.customer_name) for r in cs.itertuples()}
    ck,nk=prefix+'_code',prefix+'_name'
    if st.session_state.get(ck,'') not in mapping: st.session_state[ck]=''
    if ck not in st.session_state: st.session_state[ck]=initial if initial in mapping else ''
    if nk not in st.session_state or st.session_state[nk] not in mapping: st.session_state[nk]=st.session_state.get(ck,'')
    def sync(a,b): st.session_state[b]=st.session_state[a]
    left,right=st.columns(2)
    left.selectbox('كود العميل',['']+list(mapping),key=ck,on_change=sync,args=(ck,nk))
    right.selectbox('اسم العميل',['']+list(mapping),format_func=lambda x:f'{mapping[x]} — {x}' if x else 'اختر العميل',key=nk,on_change=sync,args=(nk,ck))
    return st.session_state[ck],mapping.get(st.session_state[ck],'')

def prepare(p,v,rid=None):
    v=dict(v)
    for n,l,k in CONFIG[p][1]:
        if k=='n': v[n]=num(v.get(n))
        elif k=='d':
            if not txt(v.get(n)): raise ValueError(l+' مطلوب')
            v[n]=str(pd.Timestamp(v[n]).date())
        else: v[n]=txt(v.get(n))
    unique={'العملاء':'customer_code','المبيعات':'invoice_no','المرتجعات':'return_no','الموردين':'supplier_code','فواتير الموردين':'invoice_no'}.get(p)
    if unique:
        if not v[unique]: raise ValueError('الكود أو رقم المستند مطلوب')
        duplicate=read(f'SELECT id FROM "{CONFIG[p][0]}" WHERE company_id=1 AND "{unique}"=? AND id<>?',(v[unique],int(rid or -1)))
        if not duplicate.empty: raise ValueError('الكود أو رقم المستند موجود بالفعل')
    if p=='العملاء' and not v['customer_name']: raise ValueError('اسم العميل مطلوب')
    if p in CLIENT_PAGES:
        cs=data('العملاء'); matches=cs[cs.customer_code.astype(str)==v['customer_code']] if v['customer_code'] else cs[cs.customer_name.astype(str)==v['customer_name']]
        if len(matches)!=1: raise ValueError('العميل غير موجود أو الاسم متكرر؛ استخدم الكود')
        customer=matches.iloc[0]
        if v['customer_name'] and v['customer_name']!=txt(customer.customer_name): raise ValueError('اسم العميل لا يطابق الكود')
        v.update(customer_code=str(customer.customer_code),customer_name=str(customer.customer_name))
        if p=='المبيعات':
            d=pd.Timestamp(v['invoice
