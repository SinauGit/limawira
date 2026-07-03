{
    'name': 'Purchase Down Payment',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'author': 'Cybrosys  - Revised by Rizky Abdi S.H',
    'depends': ['purchase', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_advance_payment_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
