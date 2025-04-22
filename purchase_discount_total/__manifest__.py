{
    'name': 'Purchase Discount Amount',
    'version': '18.0.1.0.0',
    'category': 'Purchase Management',
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'depends': ['purchase_stock', 'account',],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/res_config_settings_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        # 'wizard/purchase_order_discount_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
} 