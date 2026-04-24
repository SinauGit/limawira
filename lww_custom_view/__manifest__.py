                                 
{
    "name": "LWW Custom View",
    "version": "1.0.0",
    "author": "Rizky Abdi S.H",
    "website": "www.lui.co.id",
    "depends": ["account", "sale", "project","stock","sales_team","lww_sales", 'purchase', 'hr',        
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/purchase_menu_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
} 