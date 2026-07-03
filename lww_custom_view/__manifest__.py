                                 
{
    "name": "LWW Custom View",
    "version": "1.0.0",
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    "depends": ["account", "sale", "project","stock","sales_team","lww_sales","project_wip_monitoring",        
    ],
    "data": [
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
        "views/project_costing_views.xml",
    ],
    "installable": True,
    "application": False,
}