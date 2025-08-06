{
    'name': 'Hak Akses LWW',
    'version': '1.0',
    'depends': ['stock', 'stock_landed_costs', 'account', 'uom'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
