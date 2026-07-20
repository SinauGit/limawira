{
    'name': 'Purchase BS Access',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'depends': ['purchase', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
