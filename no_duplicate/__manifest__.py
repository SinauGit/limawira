{
    'name': 'No Duplicate Vendor, Product Categories Product',
    "version": "18.0.1.0.0",
    'author': 'Rizky Abdi S.H',
    'website': 'www.lui.co.id',
    'depends': ['account', 'purchase', 'product', 'hak_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
