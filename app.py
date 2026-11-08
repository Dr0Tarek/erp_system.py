import io
import json
import uuid
import hashlib
import sqlite3
import unicodedata
import warnings
from datetime import date

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError


st.set_page_config(
    page_title="نظام الحسابات والمبيعات",
    layout="wide"
)

DB = "erp_v8.db"
BUILD = "TAREK-EXPENSE-REPORTS-1024"

MONTHS = [
    "يناير", "فبراير", "مارس", "أبريل",
    "مايو", "يونيو", "يوليو", "أغسطس",
    "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
]

ACTIONS = {
    "view": "عرض",
    "add": "إضافة",
    "edit": "تعديل",
    "delete": "حذف",
    "import": "استيراد",
    "export": "تصدير",
    "settle": "سداد",
    "receive": "تغيير الاستلام"
}

# t = نص، n = رقم، d = تاريخ
RAW_TABLES = {
    "customers": """
customer_code|كود العميل|t
customer_name|اسم العميل|t
payment_method|طريقة الدفع|t
due_days|مدة الاستحقاق|n
due_type|نوع الاستحقاق|t
opening_balance|رصيد أول المدة|n
branches_count|عدد الفروع|n
branches|الفروع|t
tax_number|الرقم الضريبي|t
invoice_plus_invoice|تنبيه فاتورة + فاتورة|t
credit_limit|الحد الأقصى للعميل|n
notes|ملاحظات|t
""",
    "sales": """
invoice_no|رقم الفاتورة|t
invoice_date|تاريخ الفاتورة|d
customer_code|كود العميل|t
customer_name|اسم العميل|t
invoice_total|إجمالي الفاتورة|n
before_tax|قيمة قبل الضريبة|n
receipt_status|حالة الاستلام|t
supply_order_no|رقم أمر التوريد|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "returns": """
return_date|تاريخ المرتجع|d
return_no|رقم المرتجع|t
original_invoice_no|رقم الفاتورة الأصلية|t
supply_reference|رقم التوريد أو المرجع|t
customer_code|كود العميل|t
customer_name|اسم العميل|t
return_total|إجمالي المرتجع|n
before_tax|قبل الضريبة|n
reason|سبب المرتجع|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "collections": """
collection_date|تاريخ التحصيل|d
customer_code|كود العميل|t
customer_name|اسم العميل|t
invoice_no|رقم الفاتورة|t
amount|مبلغ التحصيل|n
collection_type|نوع التحصيل|t
collector_name|المحصل|t
month|الشهر|t
year|السنة|n
notes|ملاحظات|t
""",
    "discounts": """
discount_date|تاريخ الخصم|d
customer_code|كود العميل|t
customer_name|اسم العميل|t
invoice_no|رقم الفاتورة|t
discount_type|نوع الخصم|t
discount_percent|نسبة الخصم %|n
fixed_amount|مبلغ الخصم الثابت|n
invoice_total|إجمالي المبلغ|n
before_tax|قبل الضريبة|n
reason|سبب الخصم|t
month|الشهر|t
year|السنة|n
correction|تصحيح|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "contract_discounts": """
customer_code|كود العميل|t
customer_name|اسم العميل|t
discount_type|نوع الخصم|t
percent|النسبة %|n
amount|المبلغ|n
applied_on|على ماذا|t
conditions|الشروط|t
start_date|تاريخ البداية|d
end_date|تاريخ النهاية|d
apply_discount|تطبيق الخصم|t
notes|ملاحظات|t
""",
    "magazines": """
customer_code|كود العميل|t
customer_name|اسم العميل|t
month|الشهر|t
year|السنة|n
discount_value|قيمة خصم المجلة|n
magazine_type|نوع المجلة|t
notes|ملاحظات|t
""",
    "offers": """
customer_code|كود العميل|t
customer_name|اسم العميل|t
description|وصف العرض|t
discount_percent|نسبة الخصم %|n
start_date|تاريخ البداية|d
end_date|تاريخ النهاية|d
notes|ملاحظات|t
""",
    "suppliers": """
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
phone|الهاتف|t
tax_number|الرقم الضريبي|t
opening_balance|رصيد أول المدة|n
notes|ملاحظات|t
""",
    "supplier_invoices": """
invoice_no|رقم الفاتورة|t
invoice_date|تاريخ الفاتورة|d
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
invoice_total|إجمالي الفاتورة|n
before_tax|قبل الضريبة|n
paid_amount|مدفوع مباشر عند تسجيل الفاتورة|n
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "supplier_returns": """
return_date|تاريخ المرتجع|d
return_no|رقم المرتجع|t
original_invoice_no|رقم الفاتورة الأصلية|t
supply_reference|رقم التوريد أو المرجع|t
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
return_total|إجمالي المرتجع|n
before_tax|قبل الضريبة|n
reason|سبب المرتجع|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "supplier_payments": """
payment_date|تاريخ السداد|d
payment_no|رقم السداد|t
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
invoice_no|رقم الفاتورة|t
amount|مبلغ السداد|n
payment_type|طريقة السداد|t
responsible|مسؤول السداد|t
reviewer|المراجع|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "bank_accounts": """
account_name|اسم الحساب|t
bank_name|اسم البنك|t
account_number|رقم الحساب|t
opening_balance|رصيد أول المدة|n
notes|ملاحظات|t
""",
    "bank_transactions": """
transaction_date|تاريخ الحركة|d
account_name|اسم الحساب|t
transaction_type|نوع الحركة|t
amount|المبلغ|n
notes|ملاحظات|t
""",
    "expenses": """
expense_date|التاريخ|d
category|التصنيف|t
description|البيان|t
amount|المبلغ|n
responsible|المسؤول|t
reviewer|المراجع|t
notes|ملاحظات|t
external_link|الرابط الخارجى|t
""",
    "dropdown_options": """
page|الصفحة|t
field|القائمة|t
value|القيمة|t
"""
}

FIELDS = {
    table: [
        tuple(line.strip().split("|"))
        for line in specification.strip().splitlines()
        if line.strip()
    ]
    for table, specification in RAW_TABLES.items()
}

EXTRAS = {
    "sales": {
        "due_date": "TEXT",
        "payment_method": "TEXT",
        "discount_note": "REAL",
        "tax_amount": "REAL"
    },
    "returns": {
        "due_date": "TEXT",
        "tax_amount": "REAL"
    },
    "discounts": {
        "discount_value": "REAL",
        "tax_amount": "REAL"
    },
    "supplier_invoices": {"tax_amount": "REAL"},
    "supplier_returns": {"tax_amount": "REAL"},
    "expenses": {
        "expense_group": "TEXT",
        "expense_type": "TEXT"
    }
}

PAGE_CONFIG = {
    "العملاء": {"table": "customers"},
    "المبيعات": {"table": "sales"},
    "مرتجعات العملاء": {"table": "returns"},
    "التحصيلات": {"table": "collections"},
    "الخصومات": {"table": "discounts"},
    "خصومات العقد": {"table": "contract_discounts"},
    "المجلات": {"table": "magazines"},
    "العروض": {"table": "offers"},
    "الموردين": {"table": "suppliers"},
    "فواتير الموردين": {"table": "supplier_invoices"},
    "مرتجعات الموردين": {"table": "supplier_returns"},
    "مدفوعات الموردين": {"table": "supplier_payments"},
    "حسابات البنوك": {"table": "bank_accounts"},
    "الحركات البنكية": {"table": "bank_transactions"},
    "مصروفات الأستاذ - مصروف": {
        "table": "expenses",
        "fixed": {
            "expense_group": "مصاريف الأستاذ",
            "expense_type": "مصروف"
        }
    },
    "مصروفات الأستاذ - بنزين": {
        "table": "expenses",
        "fixed": {
            "expense_group": "مصاريف الأستاذ",
            "expense_type": "بنزين"
        }
    },
    "الخزينة - وارد": {
        "table": "expenses",
        "fixed": {
            "expense_group": "مصاريف الخزينة",
            "expense_type": "وارد"
        }
    },
    "الخزينة - منصرف": {
        "table": "expenses",
        "fixed": {
            "expense_group": "مصاريف الخزينة",
            "expense_type": "منصرف"
        }
    },
    "المسودة": {"table": "dropdown_options"}
}

GROUPS = {
    "حسابات العملاء والمبيعات": [
        "العملاء", "المبيعات", "مرتجعات العملاء",
        "التحصيلات", "الخصومات", "خصومات العقد",
        "المجلات", "العروض",
        "كشف حساب عميل", "ملخص العملاء"
    ],
    "الموردين": [
        "الموردين", "فواتير الموردين",
        "مرتجعات الموردين", "مدفوعات الموردين",
        "كشف حساب مورد", "ملخص الموردين"
    ],
    "البنوك": [
        "حسابات البنوك", "الحركات البنكية"
    ],
    "مصروفات الأستاذ": [
        "مصروفات الأستاذ - مصروف",
        "مصروفات الأستاذ - بنزين",
        "كشف حساب مصروفات الأستاذ والخزينة",
        "ملخص مصروفات الأستاذ والخزينة"
    ],
    "الخزينة": [
        "الخزينة - وارد", "الخزينة - منصرف",
        "كشف حساب مصروفات الأستاذ والخزينة",
        "ملخص مصروفات الأستاذ والخزينة"
    ],
    "سداد للأفريقية": [
        "الأفريقية - مبيعات",
        "الأفريقية - مشتريات",
        "الأفريقية - شيكات",
        "الأفريقية - بنزين",
        "الأفريقية - تحويلات"
    ],
    "المسودة": ["المسودة"],
    "الإعدادات": [
        "إعدادات السيستم",
        "إدارة المستخدمين",
        "إعدادات الشركة"
    ]
}

GRANTABLE_PAGES = [
    page
    for group_pages in GROUPS.values()
    for page in group_pages
    if page != "إعدادات السيستم"
]

LISTS = {
    "payment_method": [
        "كاش", "آجل", "على المبيع", "فاتورة + فاتورة"
    ],
    "due_type": [
        "يوم من تاريخ الفاتورة",
        "يوم من نهاية شهر الفاتورة",
        "شهر"
    ],
    "receipt_status": [
        "تم الاستلام", "لم يتم الاستلام",
        "مرتجع", "مرتجع جزئى"
    ],
    "invoice_plus_invoice": ["لا", "نعم"],
    "discount_type": ["نسبة مئوية", "مبلغ ثابت"],
    "apply_discount": ["لا", "نعم"],
    "collector_name": [
        "محمد رمضان", "ايمن", "حماده",
        "طارق", "مندوب مبيعات"
    ],
    "month": MONTHS,
    "collection_type": [
        "كاش", "شيك", "تحويل بنكى", "خصم من المديونية"
    ],
    "payment_type": ["كاش", "شيك", "تحويل بنكى"],
    "transaction_type": ["إيداع", "سحب"],
    "conditions": [
        "على المبيعات", "على الشيك", "مره واحده",
        "شهرى", "ربع سنوى", "نصف سنوى", "سنوى"
    ]
}

LEGACY_ALIASES = {
    "مرتجعات العملاء": "المرتجعات",
    "حسابات البنوك": "البنوك",
    "كشف حساب عميل": "كشف الحساب",
    "ملخص العملاء": "الملخص"
}

AFRICA_CUSTOMER_NAME = (
    "الشركة الافريقيه للصادرات المصرية"
)


def db():
    connection = sqlite3.connect(DB, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def read(sql, arguments=()):
    connection = db()
    try:
        return pd.read_sql_query(
            sql, connection, params=arguments
        )
    finally:
        connection.close()


def write(sql, arguments=()):
    connection = db()
    try:
        with connection:
            connection.execute(sql, arguments)
    finally:
        connection.close()


def txt(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def num(value):
    return float(txt(value).replace(",", "") or 0)


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def normalize_mode(value):
    value = " ".join(txt(value).split())
    value = value.replace("اجل", "آجل")
    value = value.replace("أجل", "آجل")
    value = value.replace("فاتورة+فاتورة", "فاتورة + فاتورة")
    value = value.replace("على البيع", "على المبيع")
    return value


def normalized_text(value):
    value = unicodedata.normalize("NFKC", txt(value))

    for character in [
        "\u200b", "\u200c", "\u200d",
        "\u200e", "\u200f", "\ufeff"
    ]:
        value = value.replace(character, "")

    return " ".join(value.split())


def africa_text(value):
    value = normalized_text(value)

    for source, replacement in [
        ("أ", "ا"), ("إ", "ا"), ("آ", "ا"),
        ("ة", "ه"), ("ى", "ي"), ("ـ", "")
    ]:
        value = value.replace(source, replacement)

    return "".join(
        character
        for character in value
        if unicodedata.category(character) != "Mn"
    )


def is_africa_note(value):
    value = africa_text(value)
    return (
        "سداد للافريقيه" in value
        or "سداد الافريقيه" in value
    )


def is_africa_customer(value):
    return africa_text(value) == africa_text(
        AFRICA_CUSTOMER_NAME
    )


def initialize():
    connection = db()

    try:
        with connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    full_name TEXT,
                    role TEXT,
                    company_id INTEGER,
                    permissions TEXT,
                    is_active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS companies(
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    system_name TEXT,
                    language TEXT,
                    logo_path TEXT,
                    logo_data BLOB
                );

                CREATE TABLE IF NOT EXISTS page_permissions(
                    user_id INTEGER,
                    page TEXT,
                    action TEXT,
                    allowed INTEGER,
                    PRIMARY KEY(user_id, page, action)
                );

                CREATE TABLE IF NOT EXISTS audit_events(
                    id INTEGER PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT
                );

                CREATE TABLE IF NOT EXISTS system_settings(
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    owner_user_id INTEGER NOT NULL,
                    system_name TEXT NOT NULL,
                    login_title TEXT NOT NULL,
                    logo_data BLOB
                );
            """)

            company_columns = {
                row["name"]
                for row in connection.execute(
                    'PRAGMA table_info("companies")'
                )
            }

            for column, sql_type in {
                "name": "TEXT",
                "system_name": "TEXT",
                "language": "TEXT",
                "logo_path": "TEXT",
                "logo_data": "BLOB"
            }.items():
                if column not in company_columns:
                    connection.execute(
                        f'ALTER TABLE companies '
                        f'ADD COLUMN "{column}" {sql_type}'
                    )

            for table, fields in FIELDS.items():
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{table}"(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER
                    )
                    """
                )

                existing = {
                    row["name"]
                    for row in connection.execute(
                        f'PRAGMA table_info("{table}")'
                    )
                }

                definitions = {
                    name: "REAL" if kind == "n" else "TEXT"
                    for name, label, kind in fields
                }

                definitions["company_id"] = "INTEGER"
                definitions.update(EXTRAS.get(table, {}))

                for name, sql_type in definitions.items():
                    if name not in existing:
                        connection.execute(
                            f'ALTER TABLE "{table}" '
                            f'ADD COLUMN "{name}" {sql_type}'
                        )

            connection.execute(
                """
                INSERT OR IGNORE INTO companies(
                    id, name, system_name, language
                )
                VALUES(1, ?, ?, ?)
                """,
                (
                    "الشركة الرئيسية",
                    "نظام الحسابات والمبيعات",
                    "العربية"
                )
            )

            tarek = connection.execute(
                """
                SELECT id FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                ("tarek",)
            ).fetchone()

            if tarek is None:
                cursor = connection.execute(
                    """
                    INSERT INTO users(
                        username, password_hash, full_name,
                        role, company_id, permissions, is_active
                    )
                    VALUES(?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        "tarek", digest("159019"),
                        "طارق", "super_admin", 1, "ALL"
                    )
                )
                owner_id_value = int(cursor.lastrowid)
            else:
                owner_id_value = int(tarek["id"])

            connection.execute(
                """
                INSERT OR IGNORE INTO system_settings(
                    id, owner_user_id,
                    system_name, login_title, logo_data
                )
                VALUES(1, ?, ?, ?, NULL)
                """,
                (
                    owner_id_value,
                    "نظام الحسابات والمبيعات",
                    "تسجيل الدخول"
                )
            )

    finally:
        connection.close()


def system_settings_row():
    return read(
        "SELECT * FROM system_settings WHERE id = 1"
    ).iloc[0]


def owner_id():
    row = read(
        """
        SELECT owner_user_id
        FROM system_settings
        WHERE id = 1
        """
    )
    return int(row.iloc[0]["owner_user_id"])


def is_owner():
    user = st.session_state.get("user")

    if not user:
        return False

    current = read(
        """
        SELECT id, is_active
        FROM users
        WHERE id = ?
        """,
        (int(user["id"]),)
    )

    return (
        not current.empty
        and bool(current.iloc[0]["is_active"])
        and int(current.iloc[0]["id"]) == owner_id()
    )


def admin():
    return (
        is_owner()
        or st.session_state.user["role"] == "super_admin"
    )


def can(page, action):
    if page == "إعدادات السيستم":
        return is_owner()

    if admin():
        return True

    user_id = int(st.session_state.user["id"])

    result = read(
        """
        SELECT allowed FROM page_permissions
        WHERE user_id = ? AND page = ? AND action = ?
        """,
        (user_id, page, action)
    )

    if not result.empty:
        return bool(result.iloc[0]["allowed"])

    alias = LEGACY_ALIASES.get(page)

    if alias:
        result = read(
            """
            SELECT allowed FROM page_permissions
            WHERE user_id = ? AND page = ? AND action = ?
            """,
            (user_id, alias, action)
        )

        if not result.empty:
            return bool(result.iloc[0]["allowed"])

    return False


def require(page, action):
    if not can(page, "view") or not can(page, action):
        raise ValueError(
            "ليس لديك صلاحية تنفيذ هذه العملية"
        )


def require_owner():
    if not is_owner():
        raise ValueError(
            "هذه العملية متاحة لمالك السيستم فقط."
        )


def audit(connection, action, details):
    connection.execute(
        """
        INSERT INTO audit_events(user_id, action, details)
        VALUES(?, ?, ?)
        """,
        (
            int(st.session_state.user["id"]),
            action,
            json.dumps(details, ensure_ascii=False)
        )
    )


def table_data(table):
    return read(
        f"""
        SELECT * FROM "{table}"
        WHERE company_id = 1
        ORDER BY id DESC
        """
    )


def page_data(page):
    configuration = PAGE_CONFIG[page]
    frame = table_data(configuration["table"])

    for column, value in configuration.get("fixed", {}).items():
        frame = frame[
            frame[column].fillna("").astype(str) == value
        ]

    return frame


def party_details(table):
    if table in {
        "sales", "returns", "collections", "discounts",
        "contract_discounts", "magazines", "offers"
    }:
        return (
            "customers", "customer_code", "customer_name",
            "كود العميل", "اسم العميل"
        )

    if table in {
        "supplier_invoices",
        "supplier_returns",
        "supplier_payments"
    }:
        return (
            "suppliers", "supplier_code", "supplier_name",
            "كود المورد", "اسم المورد"
        )

    return None


def party_picker(
    prefix,
    master_table,
    code_column,
    name_column,
    code_label,
    name_label,
    initial=""
):
    master = table_data(master_table)

    mapping = {
        str(row[code_column]): str(row[name_column])
        for _, row in master.iterrows()
    }

    code_key = prefix + "_code"
    name_key = prefix + "_name"

    if code_key not in st.session_state:
        st.session_state[code_key] = (
            initial if initial in mapping else ""
        )

    if st.session_state[code_key] not in mapping:
        st.session_state[code_key] = ""

    if (
        name_key not in st.session_state
        or st.session_state[name_key] not in mapping
    ):
        st.session_state[name_key] = st.session_state[code_key]

    def sync(source, target):
        st.session_state[target] = st.session_state[source]

    left, right = st.columns(2)

    left.selectbox(
        code_label,
        [""] + list(mapping),
        key=code_key,
        on_change=sync,
        args=(code_key, name_key)
    )

    right.selectbox(
        name_label,
        [""] + list(mapping),
        format_func=lambda value: (
            f"{mapping[value]} — {value}"
            if value else "اختر"
        ),
        key=name_key,
        on_change=sync,
        args=(name_key, code_key)
    )

    code = st.session_state[code_key]
    return code, mapping.get(code, "")


def choices(name, label):
    found = read(
        """
        SELECT DISTINCT value
        FROM dropdown_options
        WHERE company_id = 1 AND field IN (?, ?)
        ORDER BY id
        """,
        (name, label)
    )

    if not found.empty:
        return found["value"].dropna().astype(str).tolist()

    return list(LISTS.get(name, []))


def normalize_customer_values(values):
    values = dict(values)
    method = normalize_mode(values.get("payment_method"))
    duration_mode = normalize_mode(values.get("due_days"))

    if duration_mode in LISTS["payment_method"]:
        if method and method != duration_mode:
            raise ValueError(
                "طريقة الدفع تتعارض مع النص الموجود "
                "في مدة الاستحقاق."
            )

        method = duration_mode
        values["due_days"] = 0

    if method in {
        "كاش", "على المبيع", "فاتورة + فاتورة"
    }:
        values["due_days"] = 0

    values["payment_method"] = method
    return values


def customer_due(customer, invoice_date):
    method = normalize_mode(customer["payment_method"])
    duration_mode = normalize_mode(customer["due_days"])

    if not method and duration_mode in LISTS["payment_method"]:
        method = duration_mode

    if method in ("على المبيع", "فاتورة + فاتورة"):
        return method, method

    invoice_date = pd.Timestamp(invoice_date)

    if method == "كاش":
        return (
            str((invoice_date + pd.Timedelta(days=1)).date()),
            method
        )

    try:
        duration = num(customer["due_days"])
    except (ValueError, TypeError):
        raise ValueError(
            f"مدة الاستحقاق غير رقمية للعميل "
            f"{customer['customer_code']}"
        ) from None

    if duration < 0 or not duration.is_integer():
        raise ValueError(
            "مدة الاستحقاق يجب أن تكون عدداً صحيحاً غير سالب"
        )

    duration = int(duration)
    due_type = txt(customer["due_type"])

    if "نهاية" in due_type:
        due = (
            invoice_date.replace(day=1)
            + pd.DateOffset(months=1)
            + pd.Timedelta(days=duration)
        )
    elif due_type == "شهر":
        due = invoice_date + pd.DateOffset(months=duration)
    else:
        due = invoice_date + pd.Timedelta(days=duration)

    return str(due.date()), method


def invoice_remaining(connection, invoice):
    returned = connection.execute(
        """
        SELECT COALESCE(SUM(return_total), 0)
        FROM returns
        WHERE company_id = 1
          AND original_invoice_no = ?
          AND customer_code = ?
        """,
        (
            invoice["invoice_no"],
            invoice["customer_code"]
        )
    ).fetchone()[0]

    collected = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM collections
        WHERE company_id = 1
          AND invoice_no = ?
          AND customer_code = ?
        """,
        (
            invoice["invoice_no"],
            invoice["customer_code"]
        )
    ).fetchone()[0]

    return max(
        num(invoice["invoice_total"])
        - num(returned)
        - num(collected),
        0
    )


def supplier_invoice_remaining(connection, invoice):
    returned = connection.execute(
        """
        SELECT COALESCE(SUM(return_total), 0)
        FROM supplier_returns
        WHERE company_id = 1
          AND original_invoice_no = ?
          AND supplier_code = ?
        """,
        (
            invoice["invoice_no"],
            invoice["supplier_code"]
        )
    ).fetchone()[0]

    payments = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM supplier_payments
        WHERE company_id = 1
          AND invoice_no = ?
          AND supplier_code = ?
        """,
        (
            invoice["invoice_no"],
            invoice["supplier_code"]
        )
    ).fetchone()[0]

    return max(
        num(invoice["invoice_total"])
        - num(invoice["paid_amount"])
        - num(returned)
        - num(payments),
        0
    )


def invoice_warning(customer_code, exclude_id=None):
    invoices = read(
        """
        SELECT * FROM sales
        WHERE company_id = 1
          AND customer_code = ?
          AND id <> ?
        ORDER BY invoice_date, id
        """,
        (
            str(customer_code),
            int(exclude_id or -1)
        )
    )

    unpaid = []
    connection = db()

    try:
        for _, invoice in invoices.iterrows():
            amount = invoice_remaining(connection, invoice)
            if amount > 0.005:
                unpaid.append(
                    (txt(invoice["invoice_no"]), amount)
                )
    finally:
        connection.close()

    if not unpaid:
        return ""

    total = sum(amount for number, amount in unpaid)
    numbers = "، ".join(
        number for number, amount in unpaid[:10]
    )

    return (
        "تنبيه فاتورة + فاتورة: "
        f"يوجد {len(unpaid)} فاتورة سابقة "
        f"بمتبقي {total:,.2f}. "
        f"الفواتير: {numbers}. "
        "لم يسجل النظام سداداً تلقائياً."
    )


def prepare(page, values, record_id=None):
    configuration = PAGE_CONFIG[page]
    table = configuration["table"]
    values = dict(values)
    messages = []

    if table == "customers":
        values = normalize_customer_values(values)

    if table in ("returns", "supplier_returns"):
        if not txt(values.get("return_no")):
            prefix = "CR" if table == "returns" else "SR"
            values["return_no"] = (
                prefix + "-" + uuid.uuid4().hex[:16].upper()
            )
            messages.append(
                "تم إنشاء رقم داخلي للمرتجع: "
                + values["return_no"]
            )

    if table == "supplier_payments":
        if not txt(values.get("payment_no")):
            values["payment_no"] = (
                "SP-" + uuid.uuid4().hex[:16].upper()
            )
            messages.append(
                "تم إنشاء رقم داخلي للسداد: "
                + values["payment_no"]
            )

    for name, label, kind in FIELDS[table]:
        value = values.get(name)

        if kind == "n":
            try:
                values[name] = num(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"{label}: يجب إدخال رقم، "
                    f"وليس {txt(value)!r}"
                ) from None

        elif kind == "d":
            if not txt(value):
                raise ValueError(
                    f"{label}: التاريخ مطلوب"
                )
            values[name] = str(pd.Timestamp(value).date())

        else:
            values[name] = txt(value)

    values.update(configuration.get("fixed", {}))

    unique_field = {
        "customers": "customer_code",
        "sales": "invoice_no",
        "returns": "return_no",
        "suppliers": "supplier_code",
        "supplier_invoices": "invoice_no",
        "supplier_returns": "return_no",
        "supplier_payments": "payment_no"
    }.get(table)

    if unique_field:
        if not values[unique_field]:
            raise ValueError(
                "الكود أو رقم المستند مطلوب"
            )

        duplicate = read(
            f"""
            SELECT * FROM "{table}"
            WHERE company_id = 1
              AND "{unique_field}" = ?
              AND id <> ?
            """,
            (
                values[unique_field],
                int(record_id or -1)
            )
        )

        if not duplicate.empty:
            old = duplicate.iloc[0]
            raise ValueError(
                f"القيمة {values[unique_field]!r} "
                f"موجودة بالسجل رقم {old['id']}."
            )

    if table == "customers" and not values["customer_name"]:
        raise ValueError("اسم العميل مطلوب")

    if table == "suppliers" and not values["supplier_name"]:
        raise ValueError("اسم المورد مطلوب")

    details = party_details(table)
    party = None

    if details:
        master_table, code_col, name_col, _, _ = details
        master = table_data(master_table)

        code = values[code_col]
        name = values[name_col]

        if code:
            matches = master[
                master[code_col].astype(str) == code
            ]
        else:
            matches = master[
                master[name_col].map(normalized_text)
                == normalized_text(name)
            ]

        if len(matches) != 1:
            raise ValueError(
                "الكود غير موجود أو الاسم متكرر؛ "
                "استخدم الكود المسجل."
            )

        party = matches.iloc[0]

        if (
            name
            and normalized_text(name)
            != normalized_text(party[name_col])
        ):
            raise ValueError(
                f"الاسم لا يطابق الكود {code!r}. "
                f"اسم الملف: {name!r}. "
                f"اسم النظام: {txt(party[name_col])!r}."
            )

        values[code_col] = str(party[code_col])
        values[name_col] = str(party[name_col])

    if table == "sales":
        due, method = customer_due(
            party, values["invoice_date"]
        )

        values.update(
            due_date=due,
            payment_method=method,
            tax_amount=(
                values["invoice_total"] - values["before_tax"]
            ),
            discount_note=values["before_tax"] * 0.01
        )

        if (
            method == "فاتورة + فاتورة"
            or txt(party["invoice_plus_invoice"]) == "نعم"
        ):
            warning = invoice_warning(
                values["customer_code"], record_id
            )
            if warning:
                messages.append(warning)

    if table in (
        "returns", "collections", "discounts",
        "supplier_returns", "supplier_payments"
    ):
        supplier_side = table in {
            "supplier_returns", "supplier_payments"
        }

        master_invoice_table = (
            "supplier_invoices" if supplier_side else "sales"
        )

        code_column = (
            "supplier_code" if supplier_side else "customer_code"
        )

        return_side = table in {
            "returns", "supplier_returns"
        }

        invoice_column = (
            "original_invoice_no" if return_side else "invoice_no"
        )

        invoice_number = txt(values.get(invoice_column))

        if invoice_number:
            found = read(
                f"""
                SELECT id FROM "{master_invoice_table}"
                WHERE company_id = 1
                  AND invoice_no = ?
                  AND "{code_column}" = ?
                """,
                (
                    invoice_number,
                    values[code_column]
                )
            )

            if found.empty:
                if return_side:
                    references = [
                        txt(values.get("supply_reference")),
                        invoice_number
                    ]

                    values["supply_reference"] = " | ".join(
                        dict.fromkeys(
                            value for value in references if value
                        )
                    )
                    values["original_invoice_no"] = ""

                    messages.append(
                        f"تم حفظ {invoice_number!r} "
                        "كمرجع خارجي؛ المرتجع على الحساب العام."
                    )
                else:
                    raise ValueError(
                        "رقم الفاتورة غير مسجل لهذا الحساب."
                    )

        elif table == "collections":
            raise ValueError(
                "رقم الفاتورة مطلوب للتحصيل."
            )

    if table == "returns":
        values["due_date"] = str(
            (
                pd.Timestamp(values["return_date"])
                + pd.Timedelta(days=1)
            ).date()
        )

    if table in ("returns", "supplier_returns"):
        values["tax_amount"] = (
            values["return_total"] - values["before_tax"]
        )

    if table == "supplier_invoices":
        values["tax_amount"] = (
            values["invoice_total"] - values["before_tax"]
        )

    if table == "discounts":
        values["discount_value"] = (
            values["invoice_total"]
            * values["discount_percent"] / 100
            if values["discount_type"] == "نسبة مئوية"
            else values["fixed_amount"]
        )

        values["tax_amount"] = (
            values["invoice_total"] - values["before_tax"]
        )

    if table in ("offers", "contract_discounts"):
        if values["end_date"] < values["start_date"]:
            raise ValueError(
                "تاريخ النهاية يسبق البداية."
            )

    if table == "expenses" and values["amount"] < 0:
        raise ValueError(
            "المبلغ يجب أن يكون موجباً؛ "
            "اختر صفحة الوارد أو المنصرف المناسبة."
        )

    return values, messages


def save(page, values, record_id=None, importing=False):
    action = (
        "import" if importing
        else "edit" if record_id
        else "add"
    )

    require(page, action)

    values, messages = prepare(
        page, values, record_id
    )

    table = PAGE_CONFIG[page]["table"]
    connection = db()

    try:
        with connection:
            if record_id:
                assignments = ", ".join(
                    f'"{name}" = ?' for name in values
                )

                connection.execute(
                    f"""
                    UPDATE "{table}"
                    SET {assignments}
                    WHERE company_id = 1 AND id = ?
                    """,
                    list(values.values()) + [int(record_id)]
                )

            else:
                names = ", ".join(
                    f'"{name}"' for name in values
                )
                placeholders = ", ".join(
                    "?" for _ in values
                )

                connection.execute(
                    f"""
                    INSERT INTO "{table}"(
                        company_id, {names}
                    )
                    VALUES(1, {placeholders})
                    """,
                    list(values.values())
                )

            audit(
                connection,
                action,
                {
                    "page": page,
                    "table": table,
                    "id": record_id
                }
            )
    finally:
        connection.close()

    return messages


def refresh():
    st.session_state["revision"] = (
        st.session_state.get("revision", 0) + 1
    )
    st.session_state.pop("editing", None)
    st.rerun()


def record_form(page, row=None):
    table = PAGE_CONFIG[page]["table"]
    record_id = int(row["id"]) if row is not None else None
    prefix = f"{page}_{record_id or 'new'}"
    values = {}

    details = party_details(table)

    if details:
        master, code_col, name_col, code_label, name_label = details

        code, name = party_picker(
            prefix,
            master,
            code_col,
            name_col,
            code_label,
            name_label,
            txt(row[code_col]) if record_id else ""
        )

        values[code_col] = code
        values[name_col] = name

        if table == "sales" and code:
            clients = table_data("customers")
            matched = clients[
                clients["customer_code"].astype(str) == code
            ]

            if not matched.empty:
                client = matched.iloc[0]

                if (
                    normalize_mode(
                        client["payment_method"]
                    ) == "فاتورة + فاتورة"
                    or txt(
                        client["invoice_plus_invoice"]
                    ) == "نعم"
                ):
                    message = invoice_warning(
                        code, record_id
                    )
                    if message:
                        st.warning(message)

    if table in ("returns", "supplier_returns"):
        st.info(
            "رقم الفاتورة والمرجع اختياريان. "
            "رقم المرتجع الفارغ يحصل على رقم داخلي. "
            "المرتجع العام يخصم من الحساب."
        )

    if table == "supplier_invoices":
        st.warning(
            "المدفوع المباشر يُخصم من رصيد المورد؛ "
            "لا تسجله مرة ثانية في مدفوعات الموردين."
        )

    if table == "supplier_payments":
        st.caption(
            "رقم الفاتورة اختياري. "
            "السداد بدون فاتورة يخصم من الحساب العام."
        )

    with st.form("form_" + prefix):
        columns = st.columns(3)

        for index, (name, label, kind) in enumerate(FIELDS[table]):
            if name in values:
                continue

            old = row.get(name) if record_id else None
            box = columns[index % 3]
            key = prefix + "_" + name

            if table == "customers" and name == "due_days":
                values[name] = box.text_input(
                    label, value=txt(old), key=key
                )

            elif kind == "n":
                try:
                    initial = num(old)
                except (ValueError, TypeError):
                    initial = 0.0
                    box.warning(
                        f"راجع القيمة القديمة: {txt(old)}"
                    )

                if name == "year" and not txt(old):
                    initial = float(date.today().year)

                values[name] = box.number_input(
                    label, value=initial, key=key
                )

            elif kind == "d":
                try:
                    initial = (
                        pd.Timestamp(old).date()
                        if txt(old) else date.today()
                    )
                except (ValueError, TypeError):
                    initial = date.today()

                values[name] = str(
                    box.date_input(
                        label, value=initial, key=key
                    )
                )

            else:
                options = (
                    choices(name, label)
                    if table != "dropdown_options"
                    else []
                )

                if (
                    table == "customers"
                    and name == "payment_method"
                ):
                    options = [""] + [
                        option for option in options if option
                    ]

                if options:
                    old_text = txt(old)

                    if old_text and old_text not in options:
                        options = [old_text] + options

                    values[name] = box.selectbox(
                        label,
                        options,
                        index=(
                            options.index(old_text)
                            if old_text in options else 0
                        ),
                        key=key
                    )
                else:
                    values[name] = box.text_input(
                        label, value=txt(old), key=key
                    )

        submitted = st.form_submit_button(
            "حفظ التعديل" if record_id else "إضافة"
        )

    if submitted:
        try:
            messages = save(page, values, record_id)
        except (
            ValueError, TypeError, sqlite3.Error
        ) as error:
            st.error(str(error))
        else:
            st.session_state["save_messages"] = (
                ["تم الحفظ بنجاح"] + messages
            )
            refresh()


def excel_bytes(frame):
    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer, engine="xlsxwriter"
    ) as writer:
        frame.to_excel(
            writer, index=False, sheet_name="Data"
        )

        sheet = writer.sheets["Data"]
        sheet.right_to_left()
        sheet.freeze_panes(1, 0)
        sheet.set_column(
            0, max(len(frame.columns) - 1, 0), 24
        )

    return buffer.getvalue()


def download(frame, key):
    st.download_button(
        "تحميل Excel",
        data=excel_bytes(frame),
        file_name=key + ".xlsx",
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        key="download_" + key
    )


def import_page(page):
    table = PAGE_CONFIG[page]["table"]
    fields = FIELDS[table]
    headers = [label for name, label, kind in fields]

    if can(page, "export"):
        download(
            pd.DataFrame(columns=headers),
            "template_" + page
        )

    if not can(page, "import"):
        return

    if table == "expenses":
        st.caption(
            "نوع الحركة يتحدد من صفحة المصروفات "
            "أو الوارد أو المنصرف التي ترفع الملف داخلها."
        )

    if table in {
        "returns", "supplier_returns", "supplier_payments"
    }:
        st.warning(
            "الحركات بدون رقم تحصل على رقم داخلي جديد. "
            "لا تعِد استيراد الصفوف المحفوظة."
        )

    uploaded = st.file_uploader(
        "رفع Excel",
        type=["xlsx"],
        key="file_" + page
    )

    if uploaded is None:
        return

    try:
        incoming = pd.read_excel(
            uploaded, dtype=str
        ).fillna("")

        incoming.columns = [
            str(column).strip()
            for column in incoming.columns
        ]
    except Exception as error:
        st.error(f"تعذرت قراءة الملف: {error}")
        return

    if incoming.columns.duplicated().any():
        st.error("يوجد عنوان عمود مكرر.")
        return

    optional_columns = {
        "notes", "external_link",
        "supply_reference", "collection_type"
    }

    if table in ("returns", "supplier_returns"):
        optional_columns.update(
            {"return_no", "original_invoice_no"}
        )

    if table == "supplier_payments":
        optional_columns.update(
            {"payment_no", "invoice_no"}
        )

    if table == "supplier_invoices":
        optional_columns.update(
            {"before_tax", "paid_amount"}
        )

    for name, label, kind in fields:
        if (
            name in optional_columns
            and label not in incoming.columns
        ):
            incoming[label] = ""

    if set(incoming.columns) != set(headers):
        st.error(
            "الأعمدة لا تطابق قالب هذه الصفحة."
        )

        missing = set(headers) - set(incoming.columns)
        extra = set(incoming.columns) - set(headers)

        if missing:
            st.write("أعمدة ناقصة:", sorted(missing))
        if extra:
            st.write("أعمدة إضافية:", sorted(extra))
        return

    st.dataframe(
        incoming.head(20),
        use_container_width=True
    )

    if st.button(
        "استيراد فعلي", key="import_" + page
    ):
        saved_count = 0
        errors = []
        messages_report = []

        for index, row in incoming.iterrows():
            if all(txt(value) == "" for value in row):
                continue

            try:
                values = {
                    name: row[label]
                    for name, label, kind in fields
                }

                messages = save(
                    page, values, importing=True
                )
                saved_count += 1

                for message in messages:
                    messages_report.append(
                        {
                            "صف Excel": index + 2,
                            "التنبيه": message
                        }
                    )

            except (
                ValueError, TypeError, sqlite3.Error
            ) as error:
                errors.append(
                    {
                        "صف Excel": index + 2,
                        "السبب": str(error)
                    }
                )

        st.success(
            f"تم حفظ {saved_count} صف فعلياً"
        )

        if errors:
            error_frame = pd.DataFrame(errors)
            st.warning(
                f"لم يتم حفظ {len(errors)} صف"
            )
            st.dataframe(
                error_frame, use_container_width=True
            )
            download(
                error_frame, "import_errors_" + page
            )

        if messages_report:
            message_frame = pd.DataFrame(
                messages_report
            )
            st.info(
                "هذه تنبيهات لصفوف تم حفظها؛ "
                "لا تعِد رفعها بسبب التنبيه."
            )
            st.dataframe(
                message_frame, use_container_width=True
            )
            download(
                message_frame, "import_messages_" + page
            )


def bulk_action(page, record_ids, action, options=None):
    require(page, action)
    options = options or {}
    table = PAGE_CONFIG[page]["table"]
    connection = db()

    try:
        with connection:
            for record_id in record_ids:
                row = connection.execute(
                    f"""
                    SELECT * FROM "{table}"
                    WHERE company_id = 1 AND id = ?
                    """,
                    (int(record_id),)
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "أحد السجلات لم يعد موجوداً."
                    )

                for key, value in PAGE_CONFIG[page].get(
                    "fixed", {}
                ).items():
                    if txt(row[key]) != value:
                        raise ValueError(
                            "السجل لا ينتمي لهذه الصفحة."
                        )

                if action == "delete":
                    if table in ("customers", "suppliers"):
                        supplier_side = table == "suppliers"
                        code_column = (
                            "supplier_code"
                            if supplier_side
                            else "customer_code"
                        )

                        children = (
                            [
                                "supplier_invoices",
                                "supplier_returns",
                                "supplier_payments"
                            ]
                            if supplier_side
                            else [
                                "sales", "returns", "collections",
                                "discounts", "magazines",
                                "offers", "contract_discounts"
                            ]
                        )

                        for child in children:
                            linked = connection.execute(
                                f"""
                                SELECT id FROM "{child}"
                                WHERE company_id = 1
                                  AND "{code_column}" = ?
                                LIMIT 1
                                """,
                                (row[code_column],)
                            ).fetchone()

                            if linked:
                                raise ValueError(
                                    "الحساب مرتبط بحركات؛ "
                                    "عالجها أولاً."
                                )

                    if table in (
                        "sales", "supplier_invoices"
                    ):
                        supplier_side = (
                            table == "supplier_invoices"
                        )
                        code_column = (
                            "supplier_code"
                            if supplier_side
                            else "customer_code"
                        )

                        links = (
                            [
                                (
                                    "supplier_returns",
                                    "original_invoice_no"
                                ),
                                (
                                    "supplier_payments",
                                    "invoice_no"
                                )
                            ]
                            if supplier_side
                            else [
                                ("returns", "original_invoice_no"),
                                ("collections", "invoice_no"),
                                ("discounts", "invoice_no")
                            ]
                        )

                        for child, invoice_column in links:
                            linked = connection.execute(
                                f"""
                                SELECT id FROM "{child}"
                                WHERE company_id = 1
                                  AND "{invoice_column}" = ?
                                  AND "{code_column}" = ?
                                LIMIT 1
                                """,
                                (
                                    row["invoice_no"],
                                    row[code_column]
                                )
                            ).fetchone()

                            if linked:
                                raise ValueError(
                                    "الفاتورة مرتبطة بحركات؛ "
                                    "عالجها أولاً."
                                )

                    connection.execute(
                        f"""
                        DELETE FROM "{table}"
                        WHERE company_id = 1 AND id = ?
                        """,
                        (int(record_id),)
                    )

                elif (
                    action == "receive"
                    and table == "sales"
                ):
                    connection.execute(
                        """
                        UPDATE sales
                        SET receipt_status = ?
                        WHERE company_id = 1 AND id = ?
                        """,
                        (
                            options["status"],
                            int(record_id)
                        )
                    )

                elif (
                    action == "settle"
                    and table == "sales"
                ):
                    require("التحصيلات", "add")

                    unallocated = connection.execute(
                        """
                        SELECT COUNT(*) FROM returns
                        WHERE company_id = 1
                          AND customer_code = ?
                          AND TRIM(
                              COALESCE(original_invoice_no, '')
                          ) = ''
                          AND COALESCE(return_total, 0) <> 0
                        """,
                        (row["customer_code"],)
                    ).fetchone()[0]

                    if unallocated:
                        raise ValueError(
                            "العميل لديه إشعارات دائنة عامة. "
                            "راجع كشف حسابه وسجل التحصيل يدوياً."
                        )

                    amount = invoice_remaining(
                        connection, row
                    )
                    payment_date = options["date"]

                    if amount > 0.005:
                        connection.execute(
                            """
                            INSERT INTO collections(
                                company_id, collection_date,
                                customer_code, customer_name,
                                invoice_no, amount,
                                collection_type, collector_name,
                                month, year, notes
                            )
                            VALUES(
                                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                            """,
                            (
                                str(payment_date),
                                row["customer_code"],
                                row["customer_name"],
                                row["invoice_no"],
                                amount,
                                options["collection_type"],
                                options["collector"],
                                MONTHS[payment_date.month - 1],
                                payment_date.year,
                                "سداد جماعي"
                            )
                        )
                else:
                    raise ValueError(
                        "الإجراء غير متاح لهذه الصفحة."
                    )

            audit(
                connection,
                action,
                {
                    "page": page,
                    "ids": [
                        int(value) for value in record_ids
                    ]
                }
            )
    finally:
        connection.close()


def grid(page):
    configuration = PAGE_CONFIG[page]
    table = configuration["table"]
    frame = page_data(page)

    search = st.text_input(
        "بحث", key="search_" + page
    )

    if search:
        mask = frame.astype(str).apply(
            lambda column: column.str.contains(
                search,
                regex=False,
                case=False,
                na=False
            )
        ).any(axis=1)
        frame = frame[mask]

    labels = {
        name: label
        for name, label, kind in FIELDS[table]
    }

    labels.update(
        {
            "id": "م",
            "due_date": "تاريخ الاستحقاق",
            "payment_method": "طريقة الدفع",
            "tax_amount": "مبلغ الضريبة",
            "discount_note": "إشعار خصم 1%",
            "discount_value": "قيمة الخصم",
            "expense_group": "مجموعة المصروف",
            "expense_type": "نوع الحركة"
        }
    )

    shown = frame.drop(
        columns=["company_id"], errors="ignore"
    ).rename(columns=labels)

    if table in ("sales", "supplier_invoices"):
        connection = db()
        try:
            calculator = (
                invoice_remaining
                if table == "sales"
                else supplier_invoice_remaining
            )

            if not frame.empty:
                shown["متبقي الفاتورة"] = [
                    calculator(connection, row)
                    for _, row in frame.iterrows()
                ]
        finally:
            connection.close()

        st.caption(
            "متبقي الفاتورة يشمل الحركات المرتبطة بها فقط. "
            "الحركات العامة تظهر في كشف الحساب والملخص."
        )

    if (
        table in ("returns", "supplier_returns")
        and not frame.empty
    ):
        shown["نوع الربط"] = [
            "مرتبط بفاتورة" if txt(value)
            else "على الحساب العام"
            for value in frame["original_invoice_no"]
        ]

    if can(page, "export"):
        download(shown, "data_" + page)

    if frame.empty:
        st.info("لا توجد بيانات")
        return

    state = st.session_state.setdefault(
        "select_" + page,
        {
            "ids": [],
            "manual": [],
            "phase": 0,
            "revision": 0
        }
    )

    cycle_labels = [
        "تحديد الكل (نتائج البحث)",
        "العودة للتحديد السابق",
        "إلغاء جميع التحديد"
    ]

    if st.button(
        cycle_labels[state["phase"]],
        key="cycle_" + page
    ):
        if state["phase"] == 0:
            state["manual"] = state["ids"][:]
            state["ids"] = [
                int(value) for value in frame["id"]
            ]
            state["phase"] = 1
        elif state["phase"] == 1:
            state["ids"] = state["manual"][:]
            state["phase"] = 2
        else:
            state.update(ids=[], manual=[], phase=0)

        state["revision"] += 1

    model = shown.copy()

    model.insert(
        0,
        "تحديد",
        frame["id"].astype(int).isin(
            state["ids"]
        ).to_numpy()
    )

    model["إجراء"] = ""

    row_options = [""]
    if can(page, "edit"):
        row_options.append("تعديل")
    if can(page, "delete"):
        row_options.append("حذف")

    edited = st.data_editor(
        model,
        hide_index=True,
        use_container_width=True,
        disabled=[
            column for column in model.columns
            if column not in ("تحديد", "إجراء")
        ],
        column_config={
            "تحديد": st.column_config.CheckboxColumn(
                "تحديد"
            ),
            "إجراء": st.column_config.SelectboxColumn(
                "إجراء", options=row_options
            )
        },
        key=(
            f"grid_{page}_{state['revision']}_"
            f"{st.session_state.get('revision', 0)}"
        )
    )

    state["ids"] = [
        int(value)
        for value in edited.loc[
            edited["تحديد"], "م"
        ]
    ]

    requested = edited[
        edited["إجراء"] != ""
    ]

    if len(requested) > 1:
        st.info(
            "اختر إجراء صف واحد أو استخدم الإجراءات الجماعية."
        )

    elif len(requested) == 1:
        item = requested.iloc[0]
        record_id = int(item["م"])

        if item["إجراء"] == "تعديل":
            st.session_state.editing = (
                page, record_id
            )

        elif st.button(
            f"تأكيد حذف السجل {record_id}",
            key="row_delete_" + page
        ):
            try:
                bulk_action(
                    page, [record_id], "delete"
                )
            except (
                ValueError, sqlite3.Error
            ) as error:
                st.error(str(error))
            else:
                state["revision"] += 1
                refresh()

    editing = st.session_state.get(
        "editing", (None, None)
    )

    if editing[0] == page:
        match = frame[
            frame["id"] == editing[1]
        ]

        if not match.empty:
            st.subheader(
                f"تعديل السجل {editing[1]}"
            )
            record_form(page, match.iloc[0])

            if st.button(
                "إلغاء التعديل", key="cancel_" + page
            ):
                state["revision"] += 1
                refresh()

    selected_ids = state["ids"]

    if not selected_ids:
        return

    with st.expander(
        f"إجراءات المحدد — {len(selected_ids)} سجل",
        expanded=True
    ):
        operations = {}
        details = {}

        if can(page, "delete"):
            operations["حذف المحدد"] = "delete"

        if table == "sales" and can(page, "receive"):
            operations[
                "تغيير حالة الاستلام"
            ] = "receive"

        if (
            table == "sales"
            and can(page, "settle")
            and can("التحصيلات", "add")
        ):
            operations[
                "سداد كامل المتبقي"
            ] = "settle"

        if not operations:
            st.info(
                "لا توجد إجراءات جماعية مصرح بها."
            )
            return

        title = st.selectbox(
            "الإجراء",
            list(operations),
            key="bulk_operation_" + page
        )
        action = operations[title]

        if action == "receive":
            details["status"] = st.selectbox(
                "حالة الاستلام الجديدة",
                LISTS["receipt_status"]
            )

        if action == "settle":
            details["date"] = st.date_input(
                "تاريخ السداد"
            )
            details["collector"] = st.text_input(
                "المحصل", value="طارق"
            )
            details["collection_type"] = st.selectbox(
                "نوع التحصيل",
                LISTS["collection_type"]
            )
            st.caption(
                "يسجل تحصيلات فعلية. "
                "لا يخصص الخصومات والمجلات تلقائياً."
            )

        confirmed = st.checkbox(
            f"أوافق على {title} "
            f"لعدد {len(selected_ids)} سجل",
            key="bulk_confirm_" + page
        )

        if st.button(
            "تنفيذ",
            disabled=not confirmed,
            key="execute_" + page
        ):
            try:
                bulk_action(
                    page, selected_ids, action, details
                )
            except (
                ValueError, sqlite3.Error
            ) as error:
                st.error(str(error))
            else:
                state.update(
                    ids=[],
                    manual=[],
                    phase=0,
                    revision=state["revision"] + 1
                )
                refresh()


def account_summary(supplier_side):
    if supplier_side:
        master_table = "suppliers"
        code_column = "supplier_code"
        name_column = "supplier_name"

        definitions = [
            (
                "supplier_invoices", "invoice_total",
                "إجمالي المشتريات", 1
            ),
            (
                "supplier_invoices", "paid_amount",
                "مدفوع مباشر", -1
            ),
            (
                "supplier_returns", "return_total",
                "إجمالي المرتجعات", -1
            ),
            (
                "supplier_payments", "amount",
                "إجمالي المدفوعات", -1
            )
        ]
    else:
        master_table = "customers"
        code_column = "customer_code"
        name_column = "customer_name"

        definitions = [
            ("sales", "invoice_total", "المبيعات", 1),
            ("returns", "return_total", "المرتجعات", -1),
            ("collections", "amount", "التحصيلات", -1),
            ("discounts", "discount_value", "الخصومات", -1),
            ("magazines", "discount_value", "المجلات", -1)
        ]

    master = table_data(master_table)

    result = master[
        [code_column, name_column, "opening_balance"]
    ].copy()

    balance = pd.to_numeric(
        result["opening_balance"],
        errors="coerce"
    ).fillna(0)

    for table, amount_column, label, sign in definitions:
        frame = table_data(table)

        frame[amount_column] = pd.to_numeric(
            frame[amount_column], errors="coerce"
        ).fillna(0)

        totals = frame.groupby(
            code_column
        )[amount_column].sum()

        result[label] = (
            result[code_column].map(totals).fillna(0)
        )

        balance = balance + sign * result[label]

    result[
        "المستحق للمورد"
        if supplier_side
        else "المستحق على العميل"
    ] = balance

    return result, code_column, name_column


def reports(page):
    if page in {
        "كشف حساب مصروفات الأستاذ والخزينة",
        "ملخص مصروفات الأستاذ والخزينة"
    }:
        expense_report(page)
        return

    supplier_side = page in {
        "كشف حساب مورد", "ملخص الموردين"
    }

    source_pages = (
        [
            "الموردين", "فواتير الموردين",
            "مرتجعات الموردين", "مدفوعات الموردين"
        ]
        if supplier_side
        else [
            "العملاء", "المبيعات", "مرتجعات العملاء",
            "التحصيلات", "الخصومات", "المجلات"
        ]
    )

    if not all(
        can(source, "view") for source in source_pages
    ):
        st.warning(
            "التقرير يحتاج صلاحية عرض جميع مصادره."
        )
        return

    if page in {"ملخص العملاء", "ملخص الموردين"}:
        search = st.text_input(
            "اكتب الكل أو الاسم أو الكود"
        )

        if not search.strip():
            st.info("مخفي")
            return

        report, code_column, name_column = account_summary(
            supplier_side
        )

        if search.strip() != "الكل":
            mask = report[
                [code_column, name_column]
            ].astype(str).apply(
                lambda column: column.str.contains(
                    search, regex=False, na=False
                )
            ).any(axis=1)

            report = report[mask]

        report = report.rename(
            columns={
                "supplier_code": "كود المورد",
                "supplier_name": "اسم المورد",
                "customer_code": "كود العميل",
                "customer_name": "اسم العميل",
                "opening_balance": "رصيد أول المدة"
            }
        )

    else:
        master_table = (
            "suppliers" if supplier_side else "customers"
        )
        code_column = (
            "supplier_code" if supplier_side else "customer_code"
        )
        name_column = (
            "supplier_name" if supplier_side else "customer_name"
        )

        code, name = party_picker(
            "report_" + page,
            master_table,
            code_column,
            name_column,
            "الكود",
            "الاسم"
        )

        if not code:
            return

        left, right = st.columns(2)

        start = left.date_input(
            "من تاريخ", value=date(2024, 1, 1)
        )
        end = right.date_input(
            "إلى تاريخ", value=date.today()
        )

        if end < start:
            st.error("الفترة غير صحيحة")
            return

        master = table_data(master_table)
        account = master[
            master[code_column].astype(str) == code
        ].iloc[0]

        balance = num(account["opening_balance"])
        movements = []

        definitions = (
            [
                (
                    "supplier_invoices", "invoice_date",
                    "invoice_total", 1, "مشتريات", "invoice_no"
                ),
                (
                    "supplier_returns", "return_date",
                    "return_total", -1, "مرتجع مورد", "return_no"
                ),
                (
                    "supplier_payments", "payment_date",
                    "amount", -1, "سداد مورد", "payment_no"
                )
            ]
            if supplier_side
            else [
                (
                    "sales", "invoice_date",
                    "invoice_total", 1, "مبيعات", "invoice_no"
                ),
                (
                    "returns", "return_date",
                    "return_total", -1, "إشعار دائن", "return_no"
                ),
                (
                    "collections", "collection_date",
                    "amount", -1, "تحصيل", "invoice_no"
                ),
                (
                    "discounts", "discount_date",
                    "discount_value", -1, "خصم", "invoice_no"
                )
            ]
        )

        for (
            table, date_column, amount_column,
            sign, kind, reference_column
        ) in definitions:
            frame = table_data(table)
            frame = frame[
                frame[code_column].astype(str) == code
            ]

            for _, row in frame.iterrows():
                parsed = pd.to_datetime(
                    row[date_column], errors="coerce"
                )

                if pd.isna(parsed):
                    continue

                movements.append(
                    {
                        "date": parsed.date(),
                        "type": kind,
                        "reference": txt(row.get(reference_column)),
                        "notes": txt(row.get("notes")),
                        "value": sign * num(row.get(amount_column))
                    }
                )

                if table == "supplier_invoices":
                    direct = num(row.get("paid_amount"))

                    if direct:
                        movements.append(
                            {
                                "date": parsed.date(),
                                "type": "مدفوع مباشر بالفاتورة",
                                "reference": txt(row["invoice_no"]),
                                "notes": "مدفوع داخل فاتورة المشتريات",
                                "value": -direct
                            }
                        )

        if not supplier_side:
            magazines = table_data("magazines")
            magazines = magazines[
                magazines["customer_code"].astype(str) == code
            ]

            for _, row in magazines.iterrows():
                month = txt(row["month"])
                year = int(num(row["year"]))

                if month in MONTHS and year:
                    movements.append(
                        {
                            "date": date(
                                year, MONTHS.index(month) + 1, 1
                            ),
                            "type": "خصم مجلة",
                            "reference": txt(row["magazine_type"]),
                            "notes": txt(row["notes"]),
                            "value": -num(row["discount_value"])
                        }
                    )

        balance += sum(
            movement["value"]
            for movement in movements
            if movement["date"] < start
        )

        output = [
            {
                "التاريخ": str(start),
                "النوع": "رصيد بداية الفترة",
                "المستند": "",
                "زيادة المستحق": 0,
                "تخفيض المستحق": 0,
                "الرصيد": balance,
                "ملاحظات": ""
            }
        ]

        for movement in sorted(
            movements, key=lambda value: value["date"]
        ):
            if not (
                start <= movement["date"] <= end
            ):
                continue

            value = movement["value"]
            balance += value

            output.append(
                {
                    "التاريخ": str(movement["date"]),
                    "النوع": movement["type"],
                    "المستند": movement["reference"],
                    "زيادة المستحق": max(value, 0),
                    "تخفيض المستحق": max(-value, 0),
                    "الرصيد": balance,
                    "ملاحظات": movement["notes"]
                }
            )

        report = pd.DataFrame(output)
        st.subheader(f"{name} — {code}")

        st.caption(
            "الرصيد الموجب مستحق للمورد."
            if supplier_side
            else (
                "الرصيد الموجب مستحق على العميل. "
                "خصم المجلة مؤرخ بأول يوم من شهره."
            )
        )

    st.dataframe(
        report, use_container_width=True
    )

    if can(page, "export"):
        download(report, "report_" + page)


def expense_report(page):
    source_pages = [
        "مصروفات الأستاذ - مصروف",
        "مصروفات الأستاذ - بنزين",
        "الخزينة - وارد",
        "الخزينة - منصرف"
    ]

    allowed_sources = [
        source
        for source in source_pages
        if can(source, "view")
    ]

    if not allowed_sources:
        st.warning(
            "لا توجد صلاحية عرض على أي مصدر من المصروفات "
            "أو الخزينة."
        )
        return

    frame = table_data("expenses")

    allowed_mask = pd.Series(
        False, index=frame.index
    )

    for source in allowed_sources:
        configuration = PAGE_CONFIG[source]
        source_mask = pd.Series(
            True, index=frame.index
        )

        for column, value in configuration.get(
            "fixed", {}
        ).items():
            source_mask &= (
                frame[column].fillna("").astype(str)
                == value
            )

        allowed_mask |= source_mask

    frame = frame[allowed_mask]

    frame["التاريخ"] = pd.to_datetime(
        frame["expense_date"],
        errors="coerce"
    ).dt.date

    left, right = st.columns(2)

    start = left.date_input(
        "من تاريخ",
        value=date(date.today().year, 1, 1)
    )

    end = right.date_input(
        "إلى تاريخ",
        value=date.today()
    )

    if end < start:
        st.error("الفترة غير صحيحة")
        return

    frame = frame[
        (frame["التاريخ"] >= start)
        & (frame["التاريخ"] <= end)
    ]

    with st.expander("الفلاتر", expanded=True):
        columns = st.columns(3)

        responsible_options = ["الكل"] + sorted(
            frame["responsible"].dropna().astype(str).unique()
        )

        reviewer_options = ["الكل"] + sorted(
            frame["reviewer"].dropna().astype(str).unique()
        )

        category_options = ["الكل"] + sorted(
            frame["category"].dropna().astype(str).unique()
        )

        description_options = ["الكل"] + sorted(
            frame["description"].dropna().astype(str).unique()
        )

        movement_options = ["الكل"] + sorted(
            frame["expense_type"].dropna().astype(str).unique()
        )

        group_options = ["الكل"] + sorted(
            frame["expense_group"].dropna().astype(str).unique()
        )

        responsible = columns[0].selectbox(
            "المسؤول",
            responsible_options,
            key="expense_responsible"
        )

        reviewer = columns[1].selectbox(
            "المراجع",
            reviewer_options,
            key="expense_reviewer"
        )

        category = columns[2].selectbox(
            "التصنيف",
            category_options,
            key="expense_category"
        )

        description = columns[0].selectbox(
            "البيان",
            description_options,
            key="expense_description"
        )

        movement_type = columns[1].selectbox(
            "نوع الحركة",
            movement_options,
            key="expense_movement_type"
        )

        expense_group = columns[2].selectbox(
            "مجموعة المصروف",
            group_options,
            key="expense_group_filter"
        )

        search = st.text_input(
            "بحث في كل الحقول",
            key="expense_search"
        )

    filters = {
        "responsible": responsible,
        "reviewer": reviewer,
        "category": category,
        "description": description,
        "expense_type": movement_type,
        "expense_group": expense_group
    }

    for column, selected in filters.items():
        if selected != "الكل":
            frame = frame[
                frame[column].fillna("").astype(str)
                == selected
            ]

    if search.strip():
        mask = frame.astype(str).apply(
            lambda column: column.str.contains(
                search.strip(),
                regex=False,
                case=False,
                na=False
            )
        ).any(axis=1)
        frame = frame[mask]

    labels = {
        "id": "م",
        "expense_date": "التاريخ",
        "category": "التصنيف",
        "description": "البيان",
        "amount": "المبلغ",
        "responsible": "المسؤول",
        "reviewer": "المراجع",
        "notes": "ملاحظات",
        "external_link": "الرابط الخارجى",
        "expense_group": "مجموعة المصروف",
        "expense_type": "نوع الحركة"
    }

    report = frame.drop(
        columns=["company_id"],
        errors="ignore"
    ).rename(columns=labels)

    if page == "كشف حساب مصروفات الأستاذ والخزينة":
        report = report.sort_values(
            "التاريخ", ascending=True
        )

        running = 0.0
        balances = []

        for _, row in report.iterrows():
            amount = num(row["المبلغ"])
            movement = txt(row["نوع الحركة"])

            if movement == "وارد":
                running += amount
            elif movement == "منصرف":
                running -= amount
            else:
                running -= amount

            balances.append(running)

        report["الرصيد التراكمي"] = balances

        st.caption(
            "المصروف والمنصرف يقللان الرصيد، "
            "والوارد يزيده. "
            "الرصيد التراكمي يبدأ من صفر داخل الفترة المحددة."
        )

    else:
        if report.empty:
            st.info("لا توجد بيانات")
            return

        summary = report.groupby(
            [
                "مجموعة المصروف",
                "نوع الحركة",
                "التصنيف",
                "المسؤول",
                "المراجع"
            ],
            as_index=False,
            dropna=False
        ).agg(
            {
                "المبلغ": "sum",
                "البيان": lambda values: " | ".join(
                    sorted(
                        set(
                            txt(value)
                            for value in values
                            if txt(value)
                        )
                    )
                ),
                "م": "count"
            }
        ).rename(
            columns={
                "م": "عدد الحركات",
                "المبلغ": "إجمالي المبلغ"
            }
        )

        report = summary.sort_values(
            [
                "مجموعة المصروف",
                "نوع الحركة",
                "التصنيف",
                "المسؤول"
            ],
            ascending=True
        )

        st.caption(
            "الملخص يجمع الحركات المتشابهة "
            "حسب المجموعة ونوع الحركة والتصنيف "
            "والمسؤول والمراجع."
        )

    if report.empty:
        st.info("لا توجد بيانات")
        return

    st.dataframe(
        report, use_container_width=True
    )

    if can(page, "export"):
        download(
            report,
            "expense_" + page
        )


def africa_page(page):
    if page == "الأفريقية - مبيعات":
        sources = [
            (
                "المبيعات", "sales", "invoice_date",
                "invoice_no", "customer_name",
                "invoice_total", "مبيعات", 1.0
            )
        ]

    elif page == "الأفريقية - مشتريات":
        sources = [
            (
                "فواتير الموردين", "supplier_invoices",
                "invoice_date", "invoice_no",
                "supplier_name", "invoice_total",
                "فاتورة مشتريات", 1.0
            ),
            (
                "مرتجعات الموردين", "supplier_returns",
                "return_date", "return_no",
                "supplier_name", "return_total",
                "مرتجع مورد", 1.0
            ),
            (
                "مدفوعات الموردين", "supplier_payments",
                "payment_date", "payment_no",
                "supplier_name", "amount",
                "سداد مورد", 1.0
            )
        ]

    elif page == "الأفريقية - شيكات":
        sources = [
            (
                "التحصيلات", "collections",
                "collection_date", "invoice_no",
                "customer_name", "amount", "تحصيل", 1.0
            )
        ]

    elif page == "الأفريقية - بنزين":
        sources = [
            (
                "مصروفات الأستاذ - بنزين", "expenses",
                "expense_date", "id",
                "responsible", "amount",
                "بنزين", 0.5
            )
        ]

    else:
        sources = [
            (
                "مصروفات الأستاذ - مصروف", "expenses",
                "expense_date", "id",
                "responsible", "amount",
                "حركة مصروفات", 1.0
            )
        ]

    output = []
    hidden_sources = []

    for (
        source_page, table, date_column,
        reference_column, party_column,
        amount_column, kind, multiplier
    ) in sources:
        if not can(source_page, "view"):
            hidden_sources.append(source_page)
            continue

        frame = table_data(table)

        if table == "expenses":
            configuration = PAGE_CONFIG[source_page]

            for column, value in configuration.get(
                "fixed", {}
            ).items():
                frame = frame[
                    frame[column].fillna("").astype(str)
                    == value
                ]

        if table == "sales":
            customer_mask = frame["customer_name"].map(
                is_africa_customer
            )

            notes_mask = frame["notes"].map(
                is_africa_note
            )

            frame = frame[
                customer_mask | notes_mask
            ]

        for _, row in frame.iterrows():
            direction = ""
            description = ""

            if table == "expenses":
                direction = (
                    txt(row.get("expense_group"))
                    + " / "
                    + txt(row.get("expense_type"))
                )
                description = txt(row.get("description"))

            elif table == "collections":
                direction = txt(row.get("collection_type"))

            elif table == "supplier_payments":
                direction = txt(row.get("payment_type"))

            output.append(
                {
                    "المصدر": kind,
                    "رقم السجل بالمصدر": int(row["id"]),
                    "التاريخ": txt(row[date_column]),
                    "رقم المستند": txt(row[reference_column]),
                    "الحساب أو المسؤول": txt(row[party_column]),
                    "نوع الحركة": direction,
                    "البيان": description,
                    "المبلغ الأصلي": num(row[amount_column]),
                    "المبلغ في الأفريقية": (
                        num(row[amount_column]) * multiplier
                    ),
                    "ملاحظات": txt(row["notes"])
                }
            )

    st.info(
        "هذه شاشة تجميع من المصادر ولا تنشئ حركة مالية جديدة. "
        "التعديل والحذف يتمان من المصدر."
    )

    if page == "الأفريقية - مبيعات":
        st.caption(
            "تظهر فقط فواتير العميل: "
            + AFRICA_CUSTOMER_NAME
            + "، أو الفواتير التي تحتوي الملاحظات على "
            + "«سداد للأفريقية». "
            + "باقي فواتير المبيعات لا تظهر هنا."
        )

    if page == "الأفريقية - بنزين":
        st.caption(
            "يظهر بنصف قيمة قيد البنزين المسجل في "
            "مصروفات الأستاذ - بنزين. "
            "القيد الأصلي يظل كما هو."
        )

    if page == "الأفريقية - مشتريات":
        st.caption(
            "المشتريات والمرتجعات والمدفوعات تظهر منفصلة "
            "ولا تعامل كمشتريات صافية."
        )

    if page == "الأفريقية - شيكات":
        st.caption(
            "تجمع التحصيلات الموسومة بسداد للأفريقية "
            "بغض النظر عن طريقة التحصيل."
        )

    if hidden_sources:
        st.warning(
            "مصادر غير ظاهرة لعدم وجود صلاحية عرض: "
            + "، ".join(hidden_sources)
        )

    result = pd.DataFrame(
        output,
        columns=[
            "المصدر", "رقم السجل بالمصدر",
            "التاريخ", "رقم المستند",
            "الحساب أو المسؤول", "نوع الحركة",
            "البيان", "المبلغ الأصلي",
            "المبلغ في الأفريقية", "ملاحظات"
        ]
    )

    search = st.text_input(
        "بحث", key="africa_search_" + page
    )

    if search and not result.empty:
        mask = result.astype(str).apply(
            lambda column: column.str.contains(
                search, regex=False, na=False
            )
        ).any(axis=1)
        result = result[mask]

    st.dataframe(
        result, use_container_width=True
    )

    if not result.empty:
        st.subheader("إجمالي حسب نوع المصدر")

        summary = result.groupby(
            "المصدر", as_index=False
        ).agg(
            {
                "المبلغ الأصلي": "sum",
                "المبلغ في الأفريقية": "sum"
            }
        )

        st.dataframe(
            summary, use_container_width=True
        )

    if can(page, "export"):
        download(result, "africa_" + page)

    st.caption(
        "لرفع Excel: ارفعه في صفحة المصدر، "
        "واكتب في الملاحظات: سداد للأفريقية."
    )


def users_page():
    if not admin():
        st.error(
            "إدارة المستخدمين للحساب الأساسي أو المدير المصرح."
        )
        return

    users = read(
        """
        SELECT id, username, full_name, role, is_active
        FROM users ORDER BY id
        """
    )
    st.dataframe(
        users, use_container_width=True
    )

    with st.form("new_user"):
        username = st.text_input("اسم المستخدم الجديد")
        full_name = st.text_input("الاسم الكامل")
        password = st.text_input(
            "كلمة المرور", type="password"
        )
        submitted = st.form_submit_button(
            "إنشاء حساب بلا صلاحيات"
        )

    if submitted:
        if not username.strip() or not password:
            st.error(
                "اسم المستخدم وكلمة المرور مطلوبان."
            )

        elif not read(
            """
            SELECT id FROM users
            WHERE username = ? COLLATE NOCASE
            """,
            (username.strip(),)
        ).empty:
            st.error("اسم المستخدم موجود.")

        else:
            write(
                """
                INSERT INTO users(
                    username, password_hash, full_name,
                    role, company_id, permissions, is_active
                )
                VALUES(?, ?, ?, ?, 1, ?, 1)
                """,
                (
                    username.strip(), digest(password),
                    full_name, "user", ""
                )
            )
            refresh()

    user_id = st.selectbox(
        "الحساب لتعديل صلاحياته",
        users["id"].tolist(),
        format_func=lambda value: str(
            users.loc[
                users["id"] == value, "username"
            ].iloc[0]
        )
    )

    user = users[
        users["id"] == user_id
    ].iloc[0]

    target_is_owner = int(user_id) == owner_id()

    if target_is_owner:
        st.info(
            "هذا حساب مالك السيستم. "
            "لا يمكن حذف أو تعطيل الحساب "
            "أو تغيير ملكيته من هنا."
        )

        if not is_owner():
            st.warning(
                "بيانات مالك السيستم لا يعدلها حساب آخر."
            )
            return

        with st.form("owner_password"):
            replacement = st.text_input(
                "كلمة مرور جديدة للحساب الأساسي",
                type="password"
            )
            submitted = st.form_submit_button(
                "تغيير كلمة المرور"
            )

        if submitted:
            require_owner()

            if replacement:
                write(
                    """
                    UPDATE users SET password_hash = ?
                    WHERE id = ?
                    """,
                    (
                        digest(replacement),
                        owner_id()
                    )
                )
                st.success("تم تغيير كلمة المرور.")
            else:
                st.error("أدخل كلمة المرور الجديدة.")

        return

    if user["role"] == "super_admin":
        st.info(
            "هذا حساب مدير شامل. لا تمنحه صفحة إعدادات "
            "السيستم؛ تظل خاصة بالمالك فقط."
        )

    saved = read(
        """
        SELECT * FROM page_permissions
        WHERE user_id = ?
        """,
        (int(user_id),)
    )

    lookup = {
        (row.page, row.action): bool(row.allowed)
        for row in saved.itertuples()
    }

    matrix = pd.DataFrame(
        [
            {
                "الصفحة": page,
                **{
                    label: lookup.get(
                        (page, action),
                        lookup.get(
                            (
                                LEGACY_ALIASES.get(page),
                                action
                            ),
                            False
                        )
                    )
                    for action, label in ACTIONS.items()
                }
            }
            for page in GRANTABLE_PAGES
        ]
    )

    st.caption(
        "إعدادات السيستم غير موجودة هنا لأنها لا تُمنح "
        "لمستخدم آخر. إلغاء عرض يمنع كل عمليات الصفحة."
    )

    edited = st.data_editor(
        matrix,
        disabled=["الصفحة"],
        hide_index=True,
        use_container_width=True,
        key=f"permissions_{user_id}"
    )

    active = st.checkbox(
        "حساب مفعّل",
        value=bool(user["is_active"]),
        key=f"active_{user_id}"
    )

    replacement = st.text_input(
        "كلمة مرور بديلة (اختياري)",
        type="password",
        key=f"password_{user_id}"
    )

    if st.button("حفظ الصلاحيات"):
        if int(user_id) == owner_id():
            raise ValueError(
                "لا يجوز تعديل صلاحيات المالك بهذه الطريقة."
            )

        connection = db()

        try:
            with connection:
                for _, row in edited.iterrows():
                    if row["الصفحة"] not in GRANTABLE_PAGES:
                        raise ValueError("صفحة غير مسموحة.")

                    for action, label in ACTIONS.items():
                        permitted = (
                            bool(row[label])
                            and bool(row["عرض"])
                        )

                        connection.execute(
                            """
                            INSERT OR REPLACE INTO
                            page_permissions(
                                user_id, page, action, allowed
                            )
                            VALUES(?, ?, ?, ?)
                            """,
                            (
                                int(user_id),
                                row["الصفحة"],
                                action,
                                int(permitted)
                            )
                        )

                connection.execute(
                    """
                    UPDATE users SET is_active = ?
                    WHERE id = ?
                    """,
                    (int(active), int(user_id))
                )

                if replacement:
                    connection.execute(
                        """
                        UPDATE users SET password_hash = ?
                        WHERE id = ?
                        """,
                        (
                            digest(replacement),
                            int(user_id)
                        )
                    )

                audit(
                    connection,
                    "permissions",
                    {"user_id": int(user_id)}
                )
        finally:
            connection.close()

        st.success("تم حفظ الصلاحيات.")

    confirm_delete = st.checkbox(
        "تأكيد حذف هذا المستخدم",
        key=f"delete_user_confirm_{user_id}"
    )

    if st.button(
        "حذف المستخدم",
        disabled=not confirm_delete
    ):
        if int(user_id) == owner_id():
            raise ValueError("لا يمكن حذف مالك السيستم.")

        if int(user_id) == int(st.session_state.user["id"]):
            st.error(
                "لا تحذف الحساب الذي تستخدمه حالياً."
            )
            return

        connection = db()

        try:
            with connection:
                connection.execute(
                    """
                    DELETE FROM page_permissions
                    WHERE user_id = ?
                    """,
                    (int(user_id),)
                )
                connection.execute(
                    "DELETE FROM users WHERE id = ?",
                    (int(user_id),)
                )
        finally:
            connection.close()

        refresh()


def prepare_logo(uploaded):
    raw = uploaded.getvalue()

    if not raw:
        raise ValueError("ملف الصورة فارغ.")

    if len(raw) > 5242880:
        raise ValueError(
            "حجم اللوجو يجب ألا يتجاوز 5 ميجابايت."
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error", Image.DecompressionBombWarning
            )

            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {
                    "PNG", "JPEG", "WEBP"
                }:
                    raise ValueError(
                        "الصيغ المدعومة: PNG وJPG وWEBP."
                    )

                pixels = image.width * image.height

                if pixels > 20000000:
                    raise ValueError(
                        "أبعاد الصورة كبيرة جداً. "
                        "استخدم صورة أصغر."
                    )

                image.verify()

            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                image = image.convert("RGBA")

                image.thumbnail(
                    (1200, 1200),
                    Image.Resampling.LANCZOS
                )

                output = io.BytesIO()
                image.save(
                    output,
                    format="PNG",
                    optimize=True
                )

                return output.getvalue()

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning
    ) as error:
        raise ValueError(
            "تعذرت قراءة اللوجو. "
            "اختر صورة PNG أو JPG أو WEBP سليمة."
        ) from error


def valid_logo_blob(value):
    return (
        isinstance(value, (bytes, bytearray, memoryview))
        and len(value) > 0
    )


def display_logo(value, width=140):
    if not valid_logo_blob(value):
        return False

    try:
        st.image(
            io.BytesIO(bytes(value)),
            width=width
        )
        return True
    except Exception:
        st.caption("تعذر عرض الصورة المحفوظة.")
        return False


def system_settings_page():
    require_owner()
    settings = system_settings_row()

    st.info(
        "هذه إعدادات عامة للسيستم ومستقلة عن الشركة. "
        "لا تظهر الصفحة ولا تُمنح صلاحيتها لأي حساب آخر."
    )

    st.write("لوجو السيستم الحالي")
    if not display_logo(settings["logo_data"], width=180):
        st.caption("لا يوجد لوجو عام محفوظ.")

    with st.form("system_settings_form"):
        system_name = st.text_input(
            "اسم السيستم العام",
            value=txt(settings["system_name"])
        )

        login_title = st.text_input(
            "عنوان شاشة تسجيل الدخول",
            value=txt(settings["login_title"])
        )

        uploaded_logo = st.file_uploader(
            "رفع لوجو السيستم",
            type=["png", "jpg", "jpeg", "webp"],
            help=(
                "يظهر قبل تسجيل الدخول. "
                "الحد الأقصى 5 ميجابايت."
            )
        )

        delete_logo = st.checkbox(
            "حذف لوجو السيستم الحالي"
        )

        submitted = st.form_submit_button(
            "حفظ إعدادات السيستم"
        )

    prepared_logo = None

    if uploaded_logo is not None:
        try:
            prepared_logo = prepare_logo(uploaded_logo)
        except ValueError as error:
            st.error(str(error))
            if submitted:
                return
        else:
            st.write("معاينة اللوجو الجديد")
            display_logo(prepared_logo, width=180)

    if not submitted:
        return

    require_owner()

    if not system_name.strip():
        st.error("اسم السيستم مطلوب.")
        return

    if not login_title.strip():
        st.error("عنوان شاشة الدخول مطلوب.")
        return

    if delete_logo and uploaded_logo is not None:
        st.error(
            "اختر حذف اللوجو أو رفع لوجو جديد، "
            "وليس الاثنين معاً."
        )
        return

    connection = db()

    try:
        with connection:
            stored_owner = connection.execute(
                """
                SELECT owner_user_id
                FROM system_settings
                WHERE id = 1
                """
            ).fetchone()

            if (
                stored_owner is None
                or int(stored_owner["owner_user_id"])
                != int(st.session_state.user["id"])
            ):
                raise ValueError(
                    "غير مصرح بتعديل إعدادات السيستم."
                )

            connection.execute(
                """
                UPDATE system_settings
                SET system_name = ?, login_title = ?
                WHERE id = 1
                """,
                (
                    system_name.strip(),
                    login_title.strip()
                )
            )

            if delete_logo:
                connection.execute(
                    """
                    UPDATE system_settings
                    SET logo_data = NULL
                    WHERE id = 1
                    """
                )

            elif prepared_logo is not None:
                connection.execute(
                    """
                    UPDATE system_settings
                    SET logo_data = ?
                    WHERE id = 1
                    """,
                    (sqlite3.Binary(prepared_logo),)
                )

            audit(
                connection,
                "system_settings",
                {
                    "logo_action": (
                        "delete"
                        if delete_logo
                        else "replace"
                        if prepared_logo is not None
                        else "unchanged"
                    )
                }
            )

    except (ValueError, sqlite3.Error) as error:
        st.error(str(error))
        return

    finally:
        connection.close()

    st.session_state["save_messages"] = [
        "تم حفظ إعدادات السيستم."
    ]
    refresh()


def company_settings(company):
    st.write("لوجو الشركة الحالي")

    if not display_logo(company.get("logo_data"), width=180):
        st.caption("لا يوجد لوجو شركة محفوظ.")

    allowed_to_edit = can("إعدادات الشركة", "edit")

    with st.form("company_settings_form"):
        company_name = st.text_input(
            "اسم الشركة",
            value=txt(company["name"]),
            disabled=not allowed_to_edit
        )

        company_system_name = st.text_input(
            "اسم النظام داخل الشركة",
            value=txt(company["system_name"]),
            disabled=not allowed_to_edit
        )

        uploaded_logo = st.file_uploader(
            "رفع لوجو الشركة",
            type=["png", "jpg", "jpeg", "webp"],
            disabled=not allowed_to_edit
        )

        delete_logo = st.checkbox(
            "حذف لوجو الشركة الحالي",
            disabled=not allowed_to_edit
        )

        submitted = st.form_submit_button(
            "حفظ إعدادات الشركة",
            disabled=not allowed_to_edit
        )

    prepared_logo = None

    if uploaded_logo is not None:
        try:
            prepared_logo = prepare_logo(uploaded_logo)
        except ValueError as error:
            st.error(str(error))
            if submitted:
                return
        else:
            st.write("معاينة لوجو الشركة الجديد")
            display_logo(prepared_logo, width=180)

    if not submitted:
        return

    require("إعدادات الشركة", "edit")

    if not company_name.strip():
        st.error("اسم الشركة مطلوب.")
        return

    if delete_logo and uploaded_logo is not None:
        st.error(
            "اختر حذف اللوجو أو رفع لوجو جديد."
        )
        return

    connection = db()

    try:
        with connection:
            connection.execute(
                """
                UPDATE companies
                SET name = ?, system_name = ?
                WHERE id = 1
                """,
                (
                    company_name.strip(),
                    company_system_name.strip()
                )
            )

            if delete_logo:
                connection.execute(
                    """
                    UPDATE companies
                    SET logo_data = NULL, logo_path = NULL
                    WHERE id = 1
                    """
                )
            elif prepared_logo is not None:
                connection.execute(
                    """
                    UPDATE companies
                    SET logo_data = ?, logo_path = NULL
                    WHERE id = 1
                    """,
                    (sqlite3.Binary(prepared_logo),)
                )

            audit(
                connection,
                "company_settings",
                {
                    "company_id": 1,
                    "logo_action": (
                        "delete"
                        if delete_logo
                        else "replace"
                        if prepared_logo is not None
                        else "unchanged"
                    )
                }
            )

    except sqlite3.Error:
        st.error(
            "تعذر حفظ إعدادات الشركة. راجع سجل التشغيل."
        )
        return
    finally:
        connection.close()

    st.session_state["save_messages"] = [
        "تم حفظ إعدادات الشركة."
    ]
    refresh()


def show_system_brand(settings):
    logo = settings.get("logo_data")
    title = (
        txt(settings["system_name"])
        or "نظام الحسابات والمبيعات"
    )

    if valid_logo_blob(logo):
        logo_column, title_column = st.columns([1, 7])

        with logo_column:
            display_logo(logo, width=100)

        with title_column:
            st.title(title)
    else:
        st.title(title)


def show_authenticated_header(settings, company):
    show_system_brand(settings)

    if valid_logo_blob(company.get("logo_data")):
        logo_column, details_column = st.columns([1, 7])

        with logo_column:
            display_logo(
                company["logo_data"],
                width=85
            )

        with details_column:
            st.subheader(txt(company["name"]))
            st.caption(
                txt(company["system_name"])
            )
    else:
        st.subheader(txt(company["name"]))

    st.caption(
        f"{st.session_state.user['full_name']} | "
        f"{date.today()}"
    )


def navigate(group):
    st.session_state.group = group
    st.session_state.pop("page", None)
    st.session_state.pop("editing", None)


def login_screen(settings):
    show_system_brand(settings)

    st.subheader(
        txt(settings["login_title"])
        or "تسجيل الدخول"
    )

    with st.form("login"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input(
            "كلمة المرور", type="password"
        )
        submitted = st.form_submit_button("دخول")

    if not submitted:
        return

    if not username.strip() or not password:
        st.error(
            "أدخل اسم المستخدم وكلمة المرور."
        )
        return

    found = read(
        """
        SELECT * FROM users
        WHERE username = ? COLLATE NOCASE
          AND is_active = 1
        """,
        (username.strip(),)
    )

    if (
        not found.empty
        and found.iloc[0]["password_hash"]
        == digest(password)
    ):
        st.session_state.user = (
            found.iloc[0].to_dict()
        )
        st.session_state.group = "الرئيسية"
        st.rerun()
    else:
        st.error(
            "اسم المستخدم أو كلمة المرور غير صحيحة "
            "أو الحساب غير مفعّل."
        )


def main():
    st.caption("نسخة التشغيل: " + BUILD)

    try:
        initialize()
    except sqlite3.Error as error:
        st.error(
            "تعذر تجهيز قاعدة البيانات. "
            "راجع سجل التشغيل ولا تحذف البيانات."
        )
        st.write(
            "نوع الخطأ:", type(error).__name__
        )
        return

    settings = system_settings_row()

    st.session_state.setdefault("user", None)

    if st.session_state.user is None:
        login_screen(settings)
        return

    found = read(
        """
        SELECT * FROM users
        WHERE id = ? AND is_active = 1
        """,
        (int(st.session_state.user["id"]),)
    )

    if found.empty:
        st.session_state.clear()
        st.rerun()

    st.session_state.user = (
        found.iloc[0].to_dict()
    )

    company = read(
        "SELECT * FROM companies WHERE id = 1"
    ).iloc[0]

    show_authenticated_header(
        settings, company
    )

    messages = st.session_state.pop(
        "save_messages", []
    )

    for index, message in enumerate(messages):
        if index == 0:
            st.success(message)
        else:
            st.warning(message)

    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.clear()
        st.rerun()

    group = st.session_state.get(
        "group", "الرئيسية"
    )

    if group == "الرئيسية":
        st.subheader("الأقسام الرئيسية")
        columns = st.columns(3)
        visible = 0

        for group_name, pages in GROUPS.items():
            if not any(
                can(page, "view") for page in pages
            ):
                continue

            columns[visible % 3].button(
                group_name,
                on_click=navigate,
                args=(group_name,),
                use_container_width=True
            )
            visible += 1

        if not visible:
            st.warning(
                "لا توجد صفحات مصرح بها. "
                "اطلب من طارق ضبط صلاحياتك."
            )
        return

    st.sidebar.button(
        "العودة للرئيسية",
        on_click=navigate,
        args=("الرئيسية",)
    )

    pages = [
        page
        for page in GROUPS.get(group, [])
        if can(page, "view")
    ]

    if not pages:
        st.warning("لا توجد صفحات مصرح بها.")
        return

    page = st.sidebar.radio(
        group, pages, key="page"
    )
    st.subheader(page)

    if page in PAGE_CONFIG:
        operations = ["عرض"]

        if can(page, "add"):
            operations.append("إضافة")

        if (
            can(page, "import")
            or can(page, "export")
        ):
            operations.append("قالب واستيراد")

        operation = st.radio(
            "العملية",
            operations,
            horizontal=True,
            key="operation_" + page
        )

        if operation == "عرض":
            grid(page)
        elif operation == "إضافة":
            record_form(page)
        else:
            import_page(page)

    elif page in {
        "كشف حساب عميل",
        "ملخص العملاء",
        "كشف حساب مورد",
        "ملخص الموردين",
        "كشف حساب مصروفات الأستاذ والخزينة",
        "ملخص مصروفات الأستاذ والخزينة"
    }:
        reports(page)

    elif page.startswith("الأفريقية -"):
        africa_page(page)

    elif page == "إدارة المستخدمين":
        users_page()

    elif page == "إعدادات الشركة":
        company_settings(company)

    elif page == "إعدادات السيستم":
        system_settings_page()


if __name__ == "__main__":
    main()

# END OF APP
