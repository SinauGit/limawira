{
    'name': 'Sale Read Only Access',
    'version': '18.0.1.0.1',
    'category': 'Sales',
    'summary': 'Read Only group for Sales Orders and related Invoices',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/sale_readonly_security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
