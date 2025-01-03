{
    'name': 'Custom Down Payment Validation',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Prevent delivery without down payment for specific products',
    'author': 'Rizky',
    'depends': ['sale', 'stock', 'account'],
    'license': 'LGPL-3',
    'data': [
        'views/product_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}