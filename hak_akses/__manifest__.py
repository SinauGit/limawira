{
    'name': 'Hak Akses LWW',
    'version': '1.0',
    'author': 'Rizky Abdi S.H',
    'website': 'www.lui.co.id',
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
