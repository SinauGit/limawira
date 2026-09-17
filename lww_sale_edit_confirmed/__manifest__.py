{
    'name': 'LWW - Edit Customer/UoM After SO Confirm',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Allow authorized users to edit Customer and UoM on confirmed Sales Orders',
    'author': 'limawira',
    'depends': ['sale'],
    'data': [
        'security/lww_sale_edit_confirmed_security.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
