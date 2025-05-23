{
    'name': 'No Duplicate Vendor, Product Categories Product',
    "version": "18.0.1.0.0",
    'summary': 'Prevent duplicate vendor, product names payment terms dan Product Categories',
    'description': """
        This module prevents duplicate vendor, product names (case insensitive) and can create payment terms
    """,
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'website': '',
    'category': 'Purchase',
    'license': 'LGPL-3',
    'depends': ['account', 'purchase', 'product', 'hak_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
