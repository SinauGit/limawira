{
    'name': 'Custom Down Payment Validation',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Prevent delivery without down payment for specific customers',
    'author': 'Rizky',
    'depends': ['sale', 'stock', 'account'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/partner_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}