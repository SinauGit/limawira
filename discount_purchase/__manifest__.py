{
    'name': 'Purchase Discount',
    "version": "18.0.1.0.0",
    'summary': 'Add discount feature in purchase',
    'description': """
        Add fixed amount discount feature in purchase orders
    """,
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'website': '',
    'category': 'Purchase',
    'license': 'LGPL-3',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/purchase_order_discount_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
