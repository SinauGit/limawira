{
    "name": "Custom Invoice Down Payment Report",
    "version": "1.0",
    "depends": ["account", "sale"],
    "category": "Accounting",
    "summary": "Customize invoice report to include sale order lines if Down Payment exists",
    "data": [
        # "report/report_invoice_downpayment.xml",
        "views/report_action.xml"
    ],
    "installable": True,
    "application": False,
}
