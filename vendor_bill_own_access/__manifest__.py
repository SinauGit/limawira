{
    'name': 'Vendor Bill Own Access',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Group akses vendor bill terbatas pada bill milik sendiri',
    'depends': ['account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
