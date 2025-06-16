{
    "name": "Enhanced Downpayment Invoice Report",
    "version": "2.0",
    "summary": "Advanced downpayment invoice report showing both invoice and complete order details",
    "description": """
        Enhanced Downpayment Invoice Report
        ===================================
        
        Features:
        ---------
        * Automatically detects downpayment invoices
        * Shows two sections in downpayment invoices:
          1. Invoice Items (Down Payment) - What's being invoiced
          2. Complete Order Details - Full order breakdown
        * Displays balance calculations
        * Uses standard invoice template for non-downpayment invoices
        * Flexible downpayment product detection
        
        Usage:
        ------
        * Click 'Print PDF' button on any invoice
        * System automatically chooses appropriate template
        * Downpayment invoices show comprehensive details
    """,
    "category": "Accounting",
    "author": "Enhanced by AI Assistant",
    "depends": ["sale", "account"],
    "data": [
        "views/account_move_views.xml",
        "report/downpayment_invoice_report.xml",
    ],
    "assets": {
        "web.report_assets_pdf": [
            "custom_downpayment_invoice/static/src/css/report_styles.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}