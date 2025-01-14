{
    'name': 'Stock Card',
    'version': '18.0.1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Add stock move and partner information to valuation layers',
    'description': """
        This module adds stock move and partner information to stock valuation layers view.
    """,
    'depends': ['stock_account'],
    'data': [
        'views/stock_valuation_layer_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 