import io
import json
import hashlib
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="نظام الحسابات والمبيعات",
    layout="wide"
)

DB = "erp_v8.db"
BUILD = "TAREK-RETURNS-OPTIONAL-INVOICE-417"

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

# أنواع الحقول:
# t = نص
# n = رقم
# d = تاريخ

RAW = {
    "العملاء": (
        "customers",
        """
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
"""
    ),
    "المبيعات": (
        "sales",
        """
invoice_no|رقم الفاتورة|t
invoice_date|تاريخ الفاتورة|d
customer_code|كود العميل|t
customer_name|اسم العميل|t
invoice_total|إجمالي الفاتورة|n
before_tax|قيمة قبل الضريبة|n
receipt_status|حالة الاستلام|t
supply_order_no|رقم أمر التوريد|t
external_link|الرابط الخارجى|t
"""
    ),
    "المرتجعات": (
        "returns",
        """
return_date|تاريخ المرتجع|d
return_no|رقم المرتجع|t
original_invoice_no|رقم الفاتورة الأصلية|t
supply_reference|رقم التوريد أو المرجع|t
customer_code|كود العميل|t
customer_name|اسم العميل|t
return_total|إجمالي المرتجع|n
before_tax|قبل الضريبة|n
reason|سبب المرتجع|t
external_link|الرابط الخارجى|t
"""
    ),
    "التحصيلات": (
        "collections",
        """
collection_date|تاريخ التحصيل|d
customer_code|كود العميل|t
customer_name|اسم العميل|t
invoice_no|رقم الفاتورة|t
amount|مبلغ التحصيل|n
collector_name|المحصل|t
month|الشهر|t
year|السنة|n
notes|ملاحظات|t
"""
    ),
    "الخصومات": (
        "discounts",
        """
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
"""
    ),
    "خصومات العقد": (
        "contract_discounts",
        """
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
"""
    ),
    "المجلات": (
        "magazines",
        """
customer_code|كود العميل|t
customer_name|اسم العميل|t
month|الشهر|t
year|السنة|n
discount_value|قيمة خصم المجلة|n
magazine_type|نوع المجلة|t
notes|ملاحظات|t
"""
    ),
    "العروض": (
        "offers",
        """
customer_code|كود العميل|t
customer_name|اسم العميل|t
description|وصف العرض|t
discount_percent|نسبة الخصم %|n
start_date|تاريخ البداية|d
end_date|تاريخ النهاية|d
"""
    ),
    "الموردين": (
        "suppliers",
        """
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
phone|الهاتف|t
tax_number|الرقم الضريبي|t
opening_balance|رصيد أول المدة|n
notes|ملاحظات|t
"""
    ),
    "فواتير الموردين": (
        "supplier_invoices",
        """
invoice_no|رقم الفاتورة|t
invoice_date|تاريخ الفاتورة|d
supplier_code|كود المورد|t
supplier_name|اسم المورد|t
invoice_total|إجمالي الفاتورة|n
paid_amount|المدفوع|n
notes|ملاحظات|t
"""
    ),
    "البنوك": (
        "bank_accounts",
        """
account_name|اسم الحساب|t
bank_name|اسم البنك|t
account_number|رقم الحساب|t
opening_balance|رصيد أول المدة|n
"""
    ),
    "الحركات البنكية": (
        "bank_transactions",
        """
transaction_date|تاريخ الحركة|d
account_name|اسم الحساب|t
transaction_type|نوع الحركة|t
amount|المبلغ|n
notes|ملاحظات|t
"""
    ),
    "المصروفات": (
        "expenses",
        """
expense_date|تاريخ المصروف|d
expense_group|نوع المصروف|t
expense_type|تفصيل المصروف|t
amount|المبلغ|n
notes|ملاحظات|t
"""
    ),
    "المسودة": (
        "dropdown_options",
        """
page|الصفحة|t
field|القائمة|t
value|القيمة|t
"""
    )
}

CONFIG = {}

for page_name, specification in RAW.items():
    table_name, fields_text = specification
    CONFIG[page_name] = (
        table_name,
        [
            tuple(line.strip().split("|"))
            for line in fields_text.strip().splitlines()
            if line.strip()
        ]
    )

CLIENT_PAGES = [
    "المبيعات",
    "المرتجعات",
    "التحصيلات",
    "الخصومات",
    "خصومات العقد",
    "المجلات",
    "العروض"
]

PAGES = list(CONFIG) + [
    "كشف الحساب",
    "الملخص",
    "إدارة المستخدمين",
    "إعدادات الشركة"
]

GROUPS = {
    "حسابات العملاء والمبيعات": [
        "العملاء",
        "المبيعات",
        "المرتجعات",
        "التحصيلات",
        "الخصومات",
        "خصومات العقد",
        "المجلات",
        "العروض",
        "كشف الحساب",
        "الملخص"
    ],
    "الموردين": [
        "الموردين",
        "فواتير الموردين"
    ],
    "البنوك": [
        "البنوك",
        "الحركات البنكية"
    ],
    "المصروفات": ["المصروفات"],
    "المسودة": ["المسودة"],
    "الإعدادات": [
        "إدارة المستخدمين",
        "إعدادات الشركة"
    ]
}

LISTS = {
    "payment_method": [
        "كاش",
        "آجل",
        "على المبيع",
        "فاتورة + فاتورة"
    ],
    "due_type": [
        "يوم من تاريخ الفاتورة",
        "يوم من نهاية شهر الفاتورة",
        "شهر"
    ],
    "receipt_status": [
        "تم الاستلام",
        "لم يتم الاستلام",
        "مرتجع",
        "مرتجع جزئى"
    ],
    "invoice_plus_invoice": ["لا", "نعم"],
    "discount_type": ["نسبة مئوية", "مبلغ ثابت"],
    "apply_discount": ["لا", "نعم"],
    "collector_name": [
        "محمد رمضان",
        "ايمن",
        "حماده",
        "طارق",
        "مندوب مبيعات"
    ],
    "month": MONTHS,
    "expense_group": [
        "مصاريف الأستاذ",
        "مصاريف الخزينة",
        "سداد الافريقية"
    ],
    "expense_type": [
        "بنزين",
        "مصاريف",
        "سداد الافريقية",
        "وارد",
        "منصرف"
    ],
    "transaction_type": ["إيداع", "سحب"],
    "conditions": [
        "على المبيعات",
        "على الشيك",
        "مره واحده",
        "شهرى",
        "ربع سنوى",
        "نصف سنوى",
        "سنوى"
    ]
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
    }
}


def db():
    connection = sqlite3.connect(DB, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def read(sql, arguments=()):
    connection = db()
    try:
        return pd.read_sql_query(
            sql,
            connection,
            params=arguments
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
    return float(
        txt(value).replace(",", "") or 0
    )


def digest(value):
    return hashlib.sha256(
        str(value).encode()
    ).hexdigest()


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
                    logo_path TEXT
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
            """)

            for page, (table, fields) in CONFIG.items():
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

                columns = {
                    name: "REAL" if kind == "n" else "TEXT"
                    for name, label, kind in fields
                }

                columns["company_id"] = "INTEGER"
                columns.update(EXTRAS.get(table, {}))

                for name, sql_type in columns.items():
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

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                ("tarek",)
            ).fetchone()

            if existing_user is None:
                connection.execute(
                    """
                    INSERT INTO users(
                        username,
                        password_hash,
                        full_name,
                        role,
                        company_id,
                        permissions,
                        is_active
                    )
                    VALUES(?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        "tarek",
                        digest("159019"),
                        "طارق",
                        "super_admin",
                        1,
                        "ALL"
                    )
                )

    finally:
        connection.close()


def admin():
    return (
        st.session_state.user["role"]
        == "super_admin"
    )


def can(page, action):
    if admin():
        return True

    result = read(
        """
        SELECT allowed
        FROM page_permissions
        WHERE user_id = ?
          AND page = ?
          AND action = ?
        """,
        (
            int(st.session_state.user["id"]),
            page,
            action
        )
    )

    return (
        not result.empty
        and bool(result.iloc[0]["allowed"])
    )


def require(page, action):
    if not can(page, "view") or not can(page, action):
        raise ValueError(
            "ليس لديك صلاحية تنفيذ هذه العملية"
        )


def data(page):
    table = CONFIG[page][0]

    return read(
        f"""
        SELECT *
        FROM "{table}"
        WHERE company_id = 1
        ORDER BY id DESC
        """
    )


def audit(connection, action, details):
    connection.execute(
        """
        INSERT INTO audit_events(
            user_id, action, details
        )
        VALUES(?, ?, ?)
        """,
        (
            int(st.session_state.user["id"]),
            action,
            json.dumps(details, ensure_ascii=False)
        )
    )


def choices(name, label):
    found = read(
        """
        SELECT DISTINCT value
        FROM dropdown_options
        WHERE company_id = 1
          AND field IN (?, ?)
        ORDER BY id
        """,
        (name, label)
    )

    if not found.empty:
        return (
            found["value"]
            .dropna()
            .astype(str)
            .tolist()
        )

    return list(LISTS.get(name, []))


def picker(prefix, initial=""):
    clients = data("العملاء")

    mapping = {
        str(row.customer_code): str(row.customer_name)
        for row in clients.itertuples()
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
        st.session_state[name_key] = (
            st.session_state[code_key]
        )

    def sync(source, target):
        st.session_state[target] = (
            st.session_state[source]
        )

    left, right = st.columns(2)

    left.selectbox(
        "كود العميل",
        [""] + list(mapping),
        key=code_key,
        on_change=sync,
        args=(code_key, name_key)
    )

    right.selectbox(
        "اسم العميل",
        [""] + list(mapping),
        format_func=lambda value: (
            f"{mapping[value]} — {value}"
            if value else "اختر العميل"
        ),
        key=name_key,
        on_change=sync,
        args=(name_key, code_key)
    )

    code = st.session_state[code_key]
    return code, mapping.get(code, "")


def due_for_customer(customer, invoice_date):
    method = txt(customer["payment_method"])

    if method in (
        "على المبيع",
        "فاتورة + فاتورة"
    ):
        return method

    invoice_date = pd.Timestamp(invoice_date)

    if method == "كاش":
        return str(
            (
                invoice_date
                + pd.Timedelta(days=1)
            ).date()
        )

    raw_duration = customer["due_days"]

    try:
        duration = num(raw_duration)
    except (ValueError, TypeError):
        raise ValueError(
            "العميل "
            f"{customer['customer_code']} "
            f"— {customer['customer_name']}: "
            "مدة الاستحقاق يجب أن تكون رقماً، "
            f"لكن المسجل هو {txt(raw_duration)!r}"
        ) from None

    if not duration.is_integer() or duration < 0:
        raise ValueError(
            "مدة الاستحقاق يجب أن تكون "
            "عدداً صحيحاً غير سالب"
        )

    days = int(duration)
    due_type = txt(customer["due_type"])

    if "نهاية" in due_type:
        return str(
            (
                invoice_date.replace(day=1)
                + pd.DateOffset(months=1)
                + pd.Timedelta(days=days)
            ).date()
        )

    if due_type == "شهر":
        return str(
            (
                invoice_date
                + pd.DateOffset(months=days)
            ).date()
        )

    return str(
        (
            invoice_date
            + pd.Timedelta(days=days)
        ).date()
    )


def prepare(page, values, record_id=None):
    values = dict(values)

    for name, label, kind in CONFIG[page][1]:
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

            values[name] = str(
                pd.Timestamp(value).date()
            )

        else:
            values[name] = txt(value)

    unique_field = {
        "العملاء": "customer_code",
        "المبيعات": "invoice_no",
        "المرتجعات": "return_no",
        "الموردين": "supplier_code",
        "فواتير الموردين": "invoice_no"
    }.get(page)

    if unique_field:
        if not values[unique_field]:
            raise ValueError(
                "الكود أو رقم المستند مطلوب"
            )

        table = CONFIG[page][0]

        duplicate = read(
            f"""
            SELECT id
            FROM "{table}"
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
            raise ValueError(
                "الكود أو رقم المستند موجود بالفعل"
            )

    if (
        page == "العملاء"
        and not values["customer_name"]
    ):
        raise ValueError(
            "اسم العميل مطلوب"
        )

    if page in CLIENT_PAGES:
        clients = data("العملاء")

        code = values["customer_code"]
        name = values["customer_name"]

        if code:
            matches = clients[
                clients["customer_code"].astype(str)
                == code
            ]
        else:
            matches = clients[
                clients["customer_name"].astype(str)
                == name
            ]

        if len(matches) != 1:
            raise ValueError(
                "العميل غير موجود أو الاسم متكرر؛ "
                "استخدم كود العميل"
            )

        customer = matches.iloc[0]

        if (
            name
            and name != txt(customer["customer_name"])
        ):
            raise ValueError(
                "اسم العميل لا يطابق الكود"
            )

        values["customer_code"] = str(
            customer["customer_code"]
        )
        values["customer_name"] = str(
            customer["customer_name"]
        )

        if page == "المبيعات":
            values.update(
                due_date=due_for_customer(
                    customer,
                    values["invoice_date"]
                ),
                payment_method=txt(
                    customer["payment_method"]
                ),
                tax_amount=(
                    values["invoice_total"]
                    - values["before_tax"]
                ),
                discount_note=(
                    values["before_tax"] * 0.01
                )
            )

        if page in (
            "المرتجعات",
            "التحصيلات",
            "الخصومات"
        ):
            if page == "المرتجعات":
                invoice = txt(
                    values.get(
                        "original_invoice_no",
                        ""
                    )
                )
            else:
                invoice = txt(
                    values.get(
                        "invoice_no",
                        ""
                    )
                )

            # رقم الفاتورة اختياري للمرتجع.
            # عند إدخاله نتحقق أنه يخص العميل.
            if invoice:
                found_invoice = read(
                    """
                    SELECT id
                    FROM sales
                    WHERE company_id = 1
                      AND invoice_no = ?
                      AND customer_code = ?
                    """,
                    (
                        invoice,
                        values["customer_code"]
                    )
                )

                if found_invoice.empty:
                    if page == "المرتجعات":
                        raise ValueError(
                            "رقم الفاتورة الأصلية غير مسجل "
                            "لهذا العميل. إذا كان الرقم "
                            "رقم توريد أو مرجعاً خارجياً، "
                            "اكتبه في خانة رقم التوريد "
                            "أو المرجع واترك رقم الفاتورة "
                            "الأصلية فارغاً."
                        )

                    raise ValueError(
                        "الفاتورة غير مسجلة لهذا العميل"
                    )

            elif page == "التحصيلات":
                raise ValueError(
                    "رقم الفاتورة مطلوب للتحصيل"
                )

    if page == "المرتجعات":
        values.update(
            due_date=str(
                (
                    pd.Timestamp(
                        values["return_date"]
                    )
                    + pd.Timedelta(days=1)
                ).date()
            ),
            tax_amount=(
                values["return_total"]
                - values["before_tax"]
            )
        )

    if page == "الخصومات":
        if (
            values["discount_type"]
            == "نسبة مئوية"
        ):
            discount_value = (
                values["invoice_total"]
                * values["discount_percent"]
                / 100
            )
        else:
            discount_value = (
                values["fixed_amount"]
            )

        values.update(
            discount_value=discount_value,
            tax_amount=(
                values["invoice_total"]
                - values["before_tax"]
            )
        )

    if page in ("العروض", "خصومات العقد"):
        if values["end_date"] < values["start_date"]:
            raise ValueError(
                "تاريخ النهاية يسبق البداية"
            )

    return values


def save(
    page,
    values,
    record_id=None,
    importing=False
):
    action = (
        "import"
        if importing
        else "edit"
        if record_id
        else "add"
    )

    require(page, action)

    values = prepare(
        page,
        values,
        record_id
    )

    table = CONFIG[page][0]
    connection = db()

    try:
        with connection:
            if record_id:
                assignments = ", ".join(
                    f'"{name}" = ?'
                    for name in values
                )

                connection.execute(
                    f"""
                    UPDATE "{table}"
                    SET {assignments}
                    WHERE company_id = 1
                      AND id = ?
                    """,
                    list(values.values())
                    + [int(record_id)]
                )

            else:
                columns = ", ".join(
                    f'"{name}"'
                    for name in values
                )
                placeholders = ", ".join(
                    "?" for _ in values
                )

                connection.execute(
                    f"""
                    INSERT INTO "{table}"(
                        company_id,
                        {columns}
                    )
                    VALUES(
                        1,
                        {placeholders}
                    )
                    """,
                    list(values.values())
                )

            audit(
                connection,
                action,
                {
                    "page": page,
                    "id": record_id
                }
            )

    finally:
        connection.close()


def refresh():
    st.session_state["revision"] = (
        st.session_state.get("revision", 0) + 1
    )
    st.session_state.pop("editing", None)
    st.rerun()


def record_form(page, row=None):
    record_id = (
        int(row["id"])
        if row is not None
        else None
    )

    prefix = f"{page}_{record_id or 'new'}"
    values = {}

    if page in CLIENT_PAGES:
        code, name = picker(
            prefix,
            txt(row["customer_code"])
            if record_id else ""
        )

        values.update(
            customer_code=code,
            customer_name=name
        )

    if page == "المرتجعات":
        st.info(
            "رقم الفاتورة الأصلية اختياري. "
            "المرتجع غير المرتبط بفاتورة "
            "يخصم من حساب العميل العام. "
            "اكتب رقم التوريد في خانته المستقلة."
        )

    with st.form("form_" + prefix):
        columns = st.columns(3)

        for index, field in enumerate(
            CONFIG[page][1]
        ):
            name, label, kind = field

            if name in values:
                continue

            old_value = (
                row.get(name)
                if record_id
                else None
            )

            container = columns[index % 3]
            key = prefix + "_" + name

            if kind == "n":
                try:
                    initial = num(old_value)

                except (ValueError, TypeError):
                    initial = 0.0

                    container.warning(
                        f"قيمة قديمة غير رقمية في {label}: "
                        f"{txt(old_value)}. "
                        "راجعها قبل الحفظ."
                    )

                if (
                    name == "year"
                    and not txt(old_value)
                ):
                    initial = float(
                        date.today().year
                    )

                values[name] = (
                    container.number_input(
                        label,
                        value=initial,
                        key=key
                    )
                )

            elif kind == "d":
                try:
                    initial = (
                        pd.Timestamp(
                            old_value
                        ).date()
                        if txt(old_value)
                        else date.today()
                    )

                except (ValueError, TypeError):
                    initial = date.today()

                values[name] = str(
                    container.date_input(
                        label,
                        value=initial,
                        key=key
                    )
                )

            else:
                options = (
                    choices(name, label)
                    if page != "المسودة"
                    else []
                )

                if options:
                    old_text = txt(old_value)

                    if (
                        old_text
                        and old_text not in options
                    ):
                        options = (
                            [old_text] + options
                        )

                    selected_index = (
                        options.index(old_text)
                        if old_text in options
                        else 0
                    )

                    values[name] = (
                        container.selectbox(
                            label,
                            options,
                            index=selected_index,
                            key=key
                        )
                    )

                else:
                    values[name] = (
                        container.text_input(
                            label,
                            value=txt(old_value),
                            key=key
                        )
                    )

        submitted = st.form_submit_button(
            "حفظ التعديل"
            if record_id
            else "إضافة"
        )

    if submitted:
        try:
            save(
                page,
                values,
                record_id
            )

        except (
            ValueError,
            TypeError,
            sqlite3.Error
        ) as error:
            st.error(str(error))

        else:
            refresh()


def excel_bytes(frame):
    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="xlsxwriter"
    ) as writer:
        frame.to_excel(
            writer,
            index=False,
            sheet_name="Data"
        )

        worksheet = writer.sheets["Data"]
        worksheet.right_to_left()
        worksheet.freeze_panes(1, 0)

        worksheet.set_column(
            0,
            max(len(frame.columns) - 1, 0),
            24
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
    fields = CONFIG[page][1]

    headers = [
        label
        for name, label, kind in fields
    ]

    if can(page, "export"):
        download(
            pd.DataFrame(columns=headers),
            "template_" + CONFIG[page][0]
        )

    if not can(page, "import"):
        return

    if page == "المرتجعات":
        st.info(
            "استخدم قالب المرتجعات الجديد. "
            "يمكن ترك رقم الفاتورة الأصلية فارغاً. "
            "رقم التوريد يكتب في رقم التوريد أو المرجع."
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
            uploaded,
            dtype=str
        ).fillna("")

        incoming.columns = [
            str(column).strip()
            for column in incoming.columns
        ]

    except Exception as error:
        st.error(
            f"تعذرت قراءة الملف: {error}"
        )
        return

    if incoming.columns.duplicated().any():
        st.error(
            "يوجد عنوان عمود مكرر في الملف."
        )
        return

    # قبول قالب المرتجعات السابق الذي لا يحتوي
    # عمود رقم التوريد الجديد، وإضافته فارغاً.
    if (
        page == "المرتجعات"
        and "رقم التوريد أو المرجع"
        not in incoming.columns
    ):
        incoming[
            "رقم التوريد أو المرجع"
        ] = ""

    if set(incoming.columns) != set(headers):
        st.error(
            "الأعمدة لا تطابق القالب."
        )

        missing = (
            set(headers)
            - set(incoming.columns)
        )

        extra = (
            set(incoming.columns)
            - set(headers)
        )

        if missing:
            st.write(
                "أعمدة ناقصة:",
                sorted(missing)
            )

        if extra:
            st.write(
                "أعمدة إضافية:",
                sorted(extra)
            )

        return

    st.dataframe(
        incoming.head(20),
        use_container_width=True
    )

    if st.button(
        "استيراد فعلي",
        key="import_" + page
    ):
        count = 0
        errors = []

        for index, row in incoming.iterrows():
            if all(
                txt(value) == ""
                for value in row
            ):
                continue

            try:
                values = {
                    name: row[label]
                    for name, label, kind
                    in fields
                }

                save(
                    page,
                    values,
                    importing=True
                )

                count += 1

            except (
                ValueError,
                TypeError,
                sqlite3.Error
            ) as error:
                errors.append(
                    {
                        "صف Excel": index + 2,
                        "السبب": str(error)
                    }
                )

        st.success(
            f"تم حفظ {count} صف فعلياً"
        )

        if errors:
            errors_frame = pd.DataFrame(
                errors
            )

            st.warning(
                f"لم يتم حفظ {len(errors)} صف"
            )

            st.dataframe(
                errors_frame,
                use_container_width=True
            )

            download(
                errors_frame,
                "import_errors"
            )


def remaining(connection, invoice):
    # يحسب المرتجعات المرتبطة بالفاتورة فقط.
    # المرتجعات غير المرتبطة تخصم من حساب العميل العام.
    returned = connection.execute(
        """
        SELECT COALESCE(
            SUM(return_total), 0
        )
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

    paid = connection.execute(
        """
        SELECT COALESCE(
            SUM(amount), 0
        )
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
        - num(paid),
        0
    )


def bulk_action(
    page,
    record_ids,
    action,
    options=None
):
    require(page, action)

    options = options or {}
    table = CONFIG[page][0]
    connection = db()

    try:
        with connection:
            for record_id in record_ids:
                row = connection.execute(
                    f"""
                    SELECT *
                    FROM "{table}"
                    WHERE company_id = 1
                      AND id = ?
                    """,
                    (int(record_id),)
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "أحد السجلات لم يعد موجوداً"
                    )

                if action == "delete":
                    if page == "العملاء":
                        for child in [
                            "sales",
                            "returns",
                            "collections",
                            "discounts",
                            "magazines",
                            "offers",
                            "contract_discounts"
                        ]:
                            linked = (
                                connection.execute(
                                    f"""
                                    SELECT id
                                    FROM "{child}"
                                    WHERE company_id = 1
                                      AND customer_code = ?
                                    LIMIT 1
                                    """,
                                    (
                                        row[
                                            "customer_code"
                                        ],
                                    )
                                ).fetchone()
                            )

                            if linked:
                                raise ValueError(
                                    "العميل مرتبط بحركات؛ "
                                    "عالجها أولاً"
                                )

                    if page == "المبيعات":
                        for child, column in [
                            (
                                "returns",
                                "original_invoice_no"
                            ),
                            (
                                "collections",
                                "invoice_no"
                            ),
                            (
                                "discounts",
                                "invoice_no"
                            )
                        ]:
                            linked = (
                                connection.execute(
                                    f"""
                                    SELECT id
                                    FROM "{child}"
                                    WHERE company_id = 1
                                      AND "{column}" = ?
                                      AND customer_code = ?
                                    LIMIT 1
                                    """,
                                    (
                                        row["invoice_no"],
                                        row["customer_code"]
                                    )
                                ).fetchone()
                            )

                            if linked:
                                raise ValueError(
                                    "الفاتورة مرتبطة بحركات؛ "
                                    "عالجها أولاً"
                                )

                    connection.execute(
                        f"""
                        DELETE FROM "{table}"
                        WHERE company_id = 1
                          AND id = ?
                        """,
                        (int(record_id),)
                    )

                elif (
                    action == "receive"
                    and page == "المبيعات"
                ):
                    connection.execute(
                        """
                        UPDATE sales
                        SET receipt_status = ?
                        WHERE company_id = 1
                          AND id = ?
                        """,
                        (
                            options["status"],
                            int(record_id)
                        )
                    )

                elif (
                    action == "settle"
                    and page == "المبيعات"
                ):
                    require(
                        "التحصيلات",
                        "add"
                    )

                    # حماية من سداد الفواتير دون مراعاة
                    # مرتجعات العميل غير المخصصة.
                    unallocated = connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM returns
                        WHERE company_id = 1
                          AND customer_code = ?
                          AND TRIM(
                              COALESCE(
                                  original_invoice_no,
                                  ''
                              )
                          ) = ''
                          AND COALESCE(
                              return_total,
                              0
                          ) <> 0
                        """,
                        (
                            row["customer_code"],
                        )
                    ).fetchone()[0]

                    if unallocated:
                        raise ValueError(
                            "هذا العميل لديه مرتجعات "
                            "غير مرتبطة بفواتير. "
                            "راجع صافي كشف حسابه "
                            "وسجل التحصيل يدوياً "
                            "على الفواتير المناسبة، "
                            "بدلاً من السداد الجماعي "
                            "بكامل متبقي الفواتير."
                        )

                    amount = remaining(
                        connection,
                        row
                    )

                    payment_date = (
                        options["date"]
                    )

                    if amount > 0.005:
                        connection.execute(
                            """
                            INSERT INTO collections(
                                company_id,
                                collection_date,
                                customer_code,
                                customer_name,
                                invoice_no,
                                amount,
                                collector_name,
                                month,
                                year,
                                notes
                            )
                            VALUES(
                                1, ?, ?, ?, ?,
                                ?, ?, ?, ?, ?
                            )
                            """,
                            (
                                str(payment_date),
                                row["customer_code"],
                                row["customer_name"],
                                row["invoice_no"],
                                amount,
                                options["collector"],
                                MONTHS[
                                    payment_date.month - 1
                                ],
                                payment_date.year,
                                "سداد جماعي"
                            )
                        )

                else:
                    raise ValueError(
                        "الإجراء غير متاح"
                    )

            audit(
                connection,
                action,
                {
                    "page": page,
                    "ids": [
                        int(value)
                        for value in record_ids
                    ]
                }
            )

    finally:
        connection.close()


def grid(page):
    frame = data(page)
    table, fields = CONFIG[page]

    search = st.text_input(
        "بحث",
        key="search_" + page
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
        for name, label, kind in fields
    }

    labels.update(
        {
            "id": "م",
            "due_date": "تاريخ الاستحقاق",
            "payment_method": "طريقة الدفع",
            "tax_amount": "مبلغ الضريبة",
            "discount_note": "إشعار خصم 1%",
            "discount_value": "قيمة الخصم"
        }
    )

    shown = (
        frame.drop(
            columns=["company_id"],
            errors="ignore"
        )
        .rename(columns=labels)
    )

    if page == "المبيعات" and not frame.empty:
        connection = db()

        try:
            shown["المتبقي المحسوب"] = [
                remaining(connection, row)
                for _, row in frame.iterrows()
            ]
        finally:
            connection.close()

        st.caption(
            "متبقي الفاتورة يشمل التحصيلات "
            "والمرتجعات المرتبطة بها فقط. "
            "المرتجعات غير المرتبطة تظهر "
            "في صافي حساب العميل بالملخص "
            "وكشف الحساب."
        )

    if page == "المرتجعات" and not frame.empty:
        shown["نوع الربط"] = [
            (
                "مرتبط بفاتورة"
                if txt(value)
                else "خصم من حساب العميل"
            )
            for value in frame[
                "original_invoice_no"
            ]
        ]

    if can(page, "export"):
        download(
            shown,
            "data_" + table
        )

    if frame.empty:
        st.info(
            "لا توجد بيانات"
        )
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
            state["manual"] = (
                state["ids"][:]
            )
            state["ids"] = [
                int(value)
                for value in frame["id"]
            ]
            state["phase"] = 1

        elif state["phase"] == 1:
            state["ids"] = (
                state["manual"][:]
            )
            state["phase"] = 2

        else:
            state.update(
                ids=[],
                manual=[],
                phase=0
            )

        state["revision"] += 1

    model = shown.copy()

    model.insert(
        0,
        "تحديد",
        frame["id"]
        .astype(int)
        .isin(state["ids"])
        .to_numpy()
    )

    model["إجراء"] = ""

    row_options = [""]

    if can(page, "edit"):
        row_options.append(
            "تعديل"
        )

    if can(page, "delete"):
        row_options.append(
            "حذف"
        )

    grid_key = (
        f"grid_{page}_"
        f"{state['revision']}_"
        f"{st.session_state.get('revision', 0)}"
    )

    edited = st.data_editor(
        model,
        hide_index=True,
        use_container_width=True,
        disabled=[
            column
            for column in model.columns
            if column not in (
                "تحديد",
                "إجراء"
            )
        ],
        column_config={
            "تحديد": (
                st.column_config.CheckboxColumn(
                    "تحديد"
                )
            ),
            "إجراء": (
                st.column_config.SelectboxColumn(
                    "إجراء",
                    options=row_options
                )
            )
        },
        key=grid_key
    )

    state["ids"] = [
        int(value)
        for value in edited.loc[
            edited["تحديد"],
            "م"
        ]
    ]

    requested = edited[
        edited["إجراء"] != ""
    ]

    if len(requested) > 1:
        st.info(
            "اختر إجراء صف واحد "
            "أو استخدم الإجراءات الجماعية"
        )

    elif len(requested) == 1:
        item = requested.iloc[0]
        record_id = int(item["م"])

        if item["إجراء"] == "تعديل":
            st.session_state.editing = (
                page,
                record_id
            )

        elif st.button(
            f"تأكيد حذف السجل {record_id}",
            key="row_delete_" + page
        ):
            try:
                bulk_action(
                    page,
                    [record_id],
                    "delete"
                )

            except (
                ValueError,
                sqlite3.Error
            ) as error:
                st.error(str(error))

            else:
                state["revision"] += 1
                refresh()

    editing = st.session_state.get(
        "editing",
        (None, None)
    )

    if editing[0] == page:
        match = frame[
            frame["id"] == editing[1]
        ]

        if not match.empty:
            st.subheader(
                f"تعديل السجل {editing[1]}"
            )

            record_form(
                page,
                match.iloc[0]
            )

            if st.button(
                "إلغاء التعديل",
                key="cancel_" + page
            ):
                state["revision"] += 1
                refresh()

    selected_ids = state["ids"]

    if not selected_ids:
        return

    with st.expander(
        "إعدادات وإجراءات المحدد — "
        f"{len(selected_ids)} سجل",
        expanded=True
    ):
        operations = {}
        details = {}

        if can(page, "delete"):
            operations[
                "حذف المحدد"
            ] = "delete"

        if (
            page == "المبيعات"
            and can(page, "receive")
        ):
            operations[
                "تغيير حالة الاستلام"
            ] = "receive"

        if (
            page == "المبيعات"
            and can(page, "settle")
            and can("التحصيلات", "add")
        ):
            operations[
                "سداد المتبقي بالكامل"
            ] = "settle"

        if not operations:
            st.info(
                "لا توجد عمليات جماعية مصرح بها"
            )
            return

        title = st.selectbox(
            "الإجراء",
            list(operations),
            key="bulk_operation_" + page
        )

        action = operations[title]

        if action == "receive":
            details["status"] = (
                st.selectbox(
                    "حالة الاستلام الجديدة",
                    LISTS["receipt_status"]
                )
            )

        if action == "settle":
            details["date"] = (
                st.date_input(
                    "تاريخ السداد"
                )
            )

            details["collector"] = (
                st.text_input(
                    "المحصل",
                    value="طارق"
                )
            )

            st.caption(
                "يسجل تحصيلات فعلية "
                "للمتبقي من الفواتير. "
                "يمنع التنفيذ للعميل "
                "الذي لديه مرتجعات غير مرتبطة "
                "حتى تراجع تسويتها. "
                "لا يخصص خصومات العميل "
                "والمجلات تلقائياً."
            )

        confirmed = st.checkbox(
            f"أوافق على {title} "
            f"لعدد {len(selected_ids)} سجل",
            key="bulk_confirm_" + page
        )

        if st.button(
            "تنفيذ على المحدد",
            disabled=not confirmed,
            key="execute_" + page
        ):
            try:
                bulk_action(
                    page,
                    selected_ids,
                    action,
                    details
                )

            except (
                ValueError,
                sqlite3.Error
            ) as error:
                st.error(str(error))

            else:
                state.update(
                    ids=[],
                    manual=[],
                    phase=0,
                    revision=(
                        state["revision"] + 1
                    )
                )
                refresh()


def users_page():
    if not admin():
        st.error(
            "إدارة المستخدمين للحساب الأساسي فقط"
        )
        return

    users = read(
        """
        SELECT
            id,
            username,
            full_name,
            role,
            is_active
        FROM users
        ORDER BY id
        """
    )

    st.dataframe(
        users,
        use_container_width=True
    )

    with st.form("new_user"):
        username = st.text_input(
            "اسم المستخدم الجديد"
        )
        full_name = st.text_input(
            "الاسم الكامل"
        )
        password = st.text_input(
            "كلمة المرور",
            type="password"
        )
        submitted = st.form_submit_button(
            "إنشاء حساب بلا صلاحيات"
        )

    if submitted:
        if (
            not username.strip()
            or not password
        ):
            st.error(
                "اسم المستخدم وكلمة المرور مطلوبان"
            )

        else:
            existing = read(
                """
                SELECT id
                FROM users
                WHERE username = ?
                COLLATE NOCASE
                """,
                (username.strip(),)
            )

            if not existing.empty:
                st.error(
                    "اسم المستخدم موجود"
                )

            else:
                write(
                    """
                    INSERT INTO users(
                        username,
                        password_hash,
                        full_name,
                        role,
                        company_id,
                        permissions,
                        is_active
                    )
                    VALUES(
                        ?, ?, ?, ?,
                        1, ?, 1
                    )
                    """,
                    (
                        username.strip(),
                        digest(password),
                        full_name,
                        "user",
                        ""
                    )
                )
                refresh()

    user_id = st.selectbox(
        "الحساب لتعديل صلاحياته",
        users["id"].tolist(),
        format_func=lambda value: str(
            users.loc[
                users["id"] == value,
                "username"
            ].iloc[0]
        )
    )

    user = users[
        users["id"] == user_id
    ].iloc[0]

    if user["role"] == "super_admin":
        st.info(
            "الحساب الأساسي له جميع الصلاحيات "
            "ومحمي من الحذف والتعطيل"
        )

        with st.form("admin_password"):
            replacement = st.text_input(
                "كلمة مرور جديدة للحساب الأساسي",
                type="password"
            )
            update_password = (
                st.form_submit_button(
                    "تغيير كلمة المرور"
                )
            )

        if update_password:
            if replacement:
                write(
                    """
                    UPDATE users
                    SET password_hash = ?
                    WHERE id = ?
                    """,
                    (
                        digest(replacement),
                        int(user_id)
                    )
                )
                st.success(
                    "تم تغيير كلمة المرور"
                )
            else:
                st.error(
                    "أدخل كلمة المرور الجديدة"
                )

        return

    saved = read(
        """
        SELECT *
        FROM page_permissions
        WHERE user_id = ?
        """,
        (int(user_id),)
    )

    lookup = {
        (row.page, row.action):
        bool(row.allowed)
        for row in saved.itertuples()
    }

    matrix = pd.DataFrame(
        [
            {
                "الصفحة": page,
                **{
                    label: lookup.get(
                        (page, action),
                        False
                    )
                    for action, label
                    in ACTIONS.items()
                }
            }
            for page in PAGES
        ]
    )

    st.caption(
        "إلغاء عرض يمنع الدخول وكل العمليات. "
        "السداد والاستلام للمبيعات فقط."
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
        connection = db()

        try:
            with connection:
                for _, row in edited.iterrows():
                    for action, label in ACTIONS.items():
                        permitted = (
                            bool(row[label])
                            and bool(row["عرض"])
                        )

                        connection.execute(
                            """
                            INSERT OR REPLACE
                            INTO page_permissions(
                                user_id,
                                page,
                                action,
                                allowed
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
                    UPDATE users
                    SET is_active = ?
                    WHERE id = ?
                    """,
                    (
                        int(active),
                        int(user_id)
                    )
                )

                if replacement:
                    connection.execute(
                        """
                        UPDATE users
                        SET password_hash = ?
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
                    {
                        "user_id": int(user_id)
                    }
                )

        finally:
            connection.close()

        st.success(
            "تم حفظ الصلاحيات"
        )

    confirm_delete = st.checkbox(
        "تأكيد حذف هذا المستخدم",
        key=f"delete_user_confirm_{user_id}"
    )

    if st.button(
        "حذف المستخدم",
        disabled=not confirm_delete
    ):
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
                    """
                    DELETE FROM users
                    WHERE id = ?
                    """,
                    (int(user_id),)
                )

        finally:
            connection.close()

        refresh()


def reports(page):
    sources = [
        "العملاء",
        "المبيعات",
        "المرتجعات",
        "التحصيلات",
        "الخصومات",
        "المجلات"
    ]

    if not all(
        can(source, "view")
        for source in sources
    ):
        st.warning(
            "التقرير يحتاج صلاحية عرض جميع مصادره"
        )
        return

    clients = data("العملاء")

    if page == "كشف الحساب":
        code, name = picker("report")

        if not code:
            return

        left, right = st.columns(2)

        start = left.date_input(
            "من تاريخ",
            value=date(2024, 1, 1)
        )

        end = right.date_input(
            "إلى تاريخ",
            value=date.today()
        )

        if end < start:
            st.error(
                "الفترة غير صحيحة"
            )
            return

        customer = clients[
            clients["customer_code"].astype(str)
            == code
        ].iloc[0]

        balance = num(
            customer["opening_balance"]
        )

        movements = []

        movement_sources = [
            (
                "المبيعات",
                "invoice_date",
                "invoice_total",
                1,
                "invoice_no"
            ),
            (
                "المرتجعات",
                "return_date",
                "return_total",
                -1,
                "return_no"
            ),
            (
                "التحصيلات",
                "collection_date",
                "amount",
                -1,
                "invoice_no"
            ),
            (
                "الخصومات",
                "discount_date",
                "discount_value",
                -1,
                "invoice_no"
            )
        ]

        for (
            source,
            day_column,
            amount_column,
            sign,
            reference_column
        ) in movement_sources:
            frame = data(source)

            frame = frame[
                frame["customer_code"].astype(str)
                == code
            ]

            for _, row in frame.iterrows():
                parsed = pd.to_datetime(
                    row[day_column],
                    errors="coerce"
                )

                if pd.isna(parsed):
                    continue

                description = ""
                supply_reference = ""

                if source == "المرتجعات":
                    linked_invoice = txt(
                        row.get(
                            "original_invoice_no"
                        )
                    )

                    description = (
                        f"مرتجع مرتبط بالفاتورة {linked_invoice}"
                        if linked_invoice
                        else "مرتجع خصم من حساب العميل"
                    )

                    supply_reference = txt(
                        row.get(
                            "supply_reference"
                        )
                    )

                movements.append(
                    {
                        "date": parsed.date(),
                        "type": source,
                        "reference": txt(
                            row.get(
                                reference_column
                            )
                        ),
                        "supply_reference":
                        supply_reference,
                        "description":
                        description,
                        "value": (
                            sign * num(
                                row.get(
                                    amount_column
                                )
                            )
                        )
                    }
                )

        magazines = data("المجلات")

        magazines = magazines[
            magazines["customer_code"].astype(str)
            == code
        ]

        for _, row in magazines.iterrows():
            month = txt(row["month"])
            year = int(num(row["year"]))

            if month in MONTHS and year:
                movements.append(
                    {
                        "date": date(
                            year,
                            MONTHS.index(month) + 1,
                            1
                        ),
                        "type": "المجلات",
                        "reference": txt(
                            row["magazine_type"]
                        ),
                        "supply_reference": "",
                        "description": "خصم مجلة",
                        "value": -num(
                            row["discount_value"]
                        )
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
                "رقم التوريد أو المرجع": "",
                "البيان": "",
                "مدين": 0,
                "دائن": 0,
                "الرصيد": balance
            }
        ]

        movements.sort(
            key=lambda movement:
            movement["date"]
        )

        for movement in movements:
            movement_date = (
                movement["date"]
            )

            if not (
                start <= movement_date <= end
            ):
                continue

            amount = movement["value"]
            balance += amount

            output.append(
                {
                    "التاريخ": str(
                        movement_date
                    ),
                    "النوع": movement["type"],
                    "المستند": movement[
                        "reference"
                    ],
                    "رقم التوريد أو المرجع":
                    movement["supply_reference"],
                    "البيان":
                    movement["description"],
                    "مدين": max(amount, 0),
                    "دائن": max(-amount, 0),
                    "الرصيد": balance
                }
            )

        report = pd.DataFrame(
            output
        )

        st.subheader(
            f"{name} — {code}"
        )

        st.caption(
            "يشمل المرتجعات المرتبطة وغير المرتبطة "
            "بفواتير. خصومات المجلات تؤرخ "
            "بأول يوم من الشهر المسجل."
        )

    else:
        search = st.text_input(
            "اكتب الكل أو اسم العميل أو كوده"
        )

        if not search.strip():
            st.info(
                "مخفي"
            )
            return

        report = clients[
            [
                "customer_code",
                "customer_name",
                "opening_balance"
            ]
        ].copy()

        totals_sources = [
            (
                "المبيعات",
                "invoice_total",
                "المبيعات"
            ),
            (
                "المرتجعات",
                "return_total",
                "المرتجعات"
            ),
            (
                "التحصيلات",
                "amount",
                "التحصيلات"
            ),
            (
                "الخصومات",
                "discount_value",
                "الخصومات"
            ),
            (
                "المجلات",
                "discount_value",
                "المجلات"
            )
        ]

        for (
            source,
            amount_column,
            label
        ) in totals_sources:
            frame = data(source)

            frame[amount_column] = (
                pd.to_numeric(
                    frame[amount_column],
                    errors="coerce"
                ).fillna(0)
            )

            totals = frame.groupby(
                "customer_code"
            )[amount_column].sum()

            report[label] = (
                report["customer_code"]
                .map(totals)
                .fillna(0)
            )

        opening = pd.to_numeric(
            report["opening_balance"],
            errors="coerce"
        ).fillna(0)

        report["المستحق"] = (
            opening
            + report["المبيعات"]
            - report["المرتجعات"]
            - report["التحصيلات"]
            - report["الخصومات"]
            - report["المجلات"]
        )

        if search.strip() != "الكل":
            mask = report[
                [
                    "customer_code",
                    "customer_name"
                ]
            ].astype(str).apply(
                lambda column:
                column.str.contains(
                    search,
                    regex=False,
                    na=False
                )
            ).any(axis=1)

            report = report[mask]

        report = report.rename(
            columns={
                "customer_code": "كود العميل",
                "customer_name": "اسم العميل",
                "opening_balance": "رصيد أول المدة"
            }
        )

        st.caption(
            "إجمالي المرتجعات يشمل كل مرتجعات "
            "العميل، سواء لها رقم فاتورة أم لا."
        )

    st.dataframe(
        report,
        use_container_width=True
    )

    if can(page, "export"):
        download(
            report,
            "report_" + page
        )


def navigate(group):
    st.session_state.group = group
    st.session_state.pop("page", None)
    st.session_state.pop("editing", None)


def login_screen():
    st.title(
        "تسجيل الدخول"
    )

    with st.form("login"):
        username = st.text_input(
            "اسم المستخدم"
        )
        password = st.text_input(
            "كلمة المرور",
            type="password"
        )
        submitted = st.form_submit_button(
            "دخول"
        )

    if not submitted:
        return

    if (
        not username.strip()
        or not password
    ):
        st.error(
            "أدخل اسم المستخدم وكلمة المرور"
        )
        return

    found = read(
        """
        SELECT *
        FROM users
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
        st.session_state.group = (
            "الرئيسية"
        )
        st.rerun()

    else:
        st.error(
            "اسم المستخدم أو كلمة المرور "
            "غير صحيحة أو الحساب غير مفعّل"
        )


def company_settings(company):
    with st.form("settings"):
        company_name = st.text_input(
            "اسم الشركة",
            value=txt(company["name"])
        )

        system_name = st.text_input(
            "اسم النظام",
            value=txt(
                company["system_name"]
            )
        )

        submitted = st.form_submit_button(
            "حفظ"
        )

    if not submitted:
        return

    if not can(
        "إعدادات الشركة",
        "edit"
    ):
        st.error(
            "ليس لديك صلاحية التعديل"
        )
        return

    if not company_name.strip():
        st.error(
            "اسم الشركة مطلوب"
        )
        return

    write(
        """
        UPDATE companies
        SET name = ?,
            system_name = ?
        WHERE id = 1
        """,
        (
            company_name.strip(),
            system_name.strip()
        )
    )

    refresh()


def main():
    st.caption(
        "نسخة التشغيل: " + BUILD
    )

    try:
        initialize()

    except sqlite3.Error as error:
        st.error(
            "تعذر تجهيز قاعدة البيانات؛ "
            "راجع سجل التشغيل ولا تحذف البيانات"
        )
        st.write(
            "نوع الخطأ:",
            type(error).__name__
        )
        return

    st.session_state.setdefault(
        "user",
        None
    )

    if st.session_state.user is None:
        login_screen()
        return

    found = read(
        """
        SELECT *
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (
            int(
                st.session_state.user["id"]
            ),
        )
    )

    if found.empty:
        st.session_state.clear()
        st.rerun()

    st.session_state.user = (
        found.iloc[0].to_dict()
    )

    company = read(
        """
        SELECT *
        FROM companies
        WHERE id = 1
        """
    ).iloc[0]

    st.title(
        txt(company["system_name"])
        or "نظام الحسابات والمبيعات"
    )

    st.caption(
        f"{company['name']} | "
        f"{st.session_state.user['full_name']} | "
        f"{date.today()}"
    )

    if st.sidebar.button(
        "تسجيل الخروج"
    ):
        st.session_state.clear()
        st.rerun()

    group = st.session_state.get(
        "group",
        "الرئيسية"
    )

    if group == "الرئيسية":
        st.subheader(
            "الأقسام الرئيسية"
        )

        columns = st.columns(3)
        visible = 0

        for group_name, pages in GROUPS.items():
            if not any(
                can(page, "view")
                for page in pages
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
                "لا توجد صفحات مصرح بها؛ "
                "اطلب من طارق ضبط صلاحياتك"
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
        st.warning(
            "لا توجد صفحات مصرح بها"
        )
        return

    page = st.sidebar.radio(
        group,
        pages,
        key="page"
    )

    st.subheader(
        page
    )

    if page in CONFIG:
        operations = [
            "عرض"
        ]

        if can(page, "add"):
            operations.append(
                "إضافة"
            )

        if (
            can(page, "import")
            or can(page, "export")
        ):
            operations.append(
                "قالب واستيراد"
            )

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

    elif page == "إدارة المستخدمين":
        users_page()

    elif page in (
        "كشف الحساب",
        "الملخص"
    ):
        reports(page)

    elif page == "إعدادات الشركة":
        company_settings(company)


if __name__ == "__main__":
    main()

# END OF APP
