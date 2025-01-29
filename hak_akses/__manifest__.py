{
    'name': 'Hak Akses LWW',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Kustomisasi hak akses untuk LWW',
    'description': """
        Modul ini menambahkan grup akses baru 'Admin LWW' dengan pembatasan akses tertentu
    """,
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
