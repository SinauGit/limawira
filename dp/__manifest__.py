{
    'name': 'Custom Down Payment Validation',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Prevent delivery without down payment for specific products',
    'author': 'Rizky',
    'depends': ['sale', 'stock', 'account'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}