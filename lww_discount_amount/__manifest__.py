{
    'name': 'Discount on Total Amount',
    'version': '18.0.1.1.0',
    'depends': ['sale_management', 'account', 'purchase'],
    'data': [
        # 'views/res_config_settings_views.xml',
        # 'views/sale_order_views.xml',
        'views/account_move_views.xml',
        # 'views/account_move_templates.xml',
        # 'views/sale_order_templates.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
