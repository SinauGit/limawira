{
    "name": "Invoice Downpayment Report",
    "version": "1.0",
    "depends": ["account", "sale"],
    "author": "ChatGPT",
    "category": "Accounting",
    "summary": "Custom invoice report showing order lines if downpayment is involved",
    "data": [
        "reports/report_invoice_templates.xml",
        "reports/report_action.xml"
    ],
    "installable": True,
    "application": False,
}
