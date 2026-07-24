{
    'name': 'Landed Cost Access for Purchase & Billing',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Allow Purchase User and Billing to create landed costs from vendor bills',
    'depends': ['stock_landed_costs', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
