{
    'name': 'Down Payment Validation',
    'version': '18.0.1.0.0',
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