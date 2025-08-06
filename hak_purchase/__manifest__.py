{
    'name': 'Hak Akses Purchase LWW',
    'version': '1.0',
    'depends': ['stock','stock_landed_costs', 'uom', 'purchase', 'sales_team', 'account'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
