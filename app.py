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

        st.dataframe(
            report, use_container_width=True
        )

        if can(page, "export"):
            download(report, "report_" + page)

        return

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

    with st.expander("الفلاتر", expanded=True):
        filter_columns = st.columns(3)

        movement_options = ["الكل"] + sorted(
            report["النوع"].dropna().astype(str).unique()
        )

        document_options = ["الكل"] + sorted(
            report["المستند"].dropna().astype(str).unique()
        )

        notes_options = ["الكل"] + sorted(
            report["ملاحظات"].dropna().astype(str).unique()
        )

        movement_filter = filter_columns[0].selectbox(
            "نوع الحركة",
            movement_options,
            key="statement_movement_" + page
        )

        document_filter = filter_columns[1].selectbox(
            "رقم المستند",
            document_options,
            key="statement_document_" + page
        )

        notes_filter = filter_columns[2].selectbox(
            "البيان أو الملاحظات",
            notes_options,
            key="statement_notes_" + page
        )

        minimum = filter_columns[0].number_input(
            "أقل مبلغ حركة",
            min_value=0.0,
            value=0.0,
            key="statement_min_" + page
        )

        maximum = filter_columns[1].number_input(
            "أكبر مبلغ حركة",
            min_value=0.0,
            value=0.0,
            key="statement_max_" + page
        )

        search = st.text_input(
            "بحث في كل الحقول",
            key="statement_search_" + page
        )

    if movement_filter != "الكل":
        report = report[
            report["النوع"].astype(str) == movement_filter
        ]

    if document_filter != "الكل":
        report = report[
            report["المستند"].astype(str) == document_filter
        ]

    if notes_filter != "الكل":
        report = report[
            report["ملاحظات"].astype(str) == notes_filter
        ]

    if minimum > 0:
        report = report[
            (report["زيادة المستحق"] >= minimum)
            | (report["تخفيض المستحق"] >= minimum)
        ]

    if maximum > 0:
        report = report[
            (
                (report["زيادة المستحق"] <= maximum)
                | (report["زيادة المستحق"] == 0)
            )
            & (
                (report["تخفيض المستحق"] <= maximum)
                | (report["تخفيض المستحق"] == 0)
            )
        ]

    if search.strip():
        mask = report.astype(str).apply(
            lambda column: column.str.contains(
                search.strip(),
                regex=False,
                case=False,
                na=False
            )
        ).any(axis=1)
        report = report[mask]

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
