                                     
                                                                   

{
    "name": "Purchase Request",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "category": "Purchase Management",
    "depends": ["purchase_stock"],
    "data": [
        "security/purchase_request.xml",
        "security/ir.model.access.csv",
        "data/purchase_request_sequence.xml",
        "data/purchase_request_data.xml",
        "reports/report_purchase_request.xml",
        "wizard/purchase_request_line_make_purchase_order_view.xml",
        "views/purchase_request_view.xml",
        "views/purchase_request_line_view.xml",
        "views/purchase_request_report.xml",
        "views/product_template.xml",
        "views/purchase_order_view.xml",
        "views/stock_move_views.xml",
    ],
    "demo": ["demo/purchase_request_demo.xml"],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
