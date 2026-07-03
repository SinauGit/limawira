{
    "name": "Stock Analytic",
    "summary": "Adds analytic distribution in stock move",
    "version": "18.0.1.1.0",
    "author": "Julius Network - Revised by Rizky Abdi S.H",
    "category": "Warehouse Management",
    "license": "AGPL-3",
    "depends": ["stock_account", "analytic"],
    "data": [
        "views/account_analytic_plan_views.xml",
        "views/stock_move_views.xml",
                                        
        "views/stock_move_line_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
}
