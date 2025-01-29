{
    'name': 'Hak Akses Purchase LWW',
    'version': '1.0',
    'category': 'Purchase   ',
    'summary': 'Kustomisasi hak akses untuk LWW',
    'description': """
        Modul ini menambahkan grup akses baru 'Purchase Admin LWW' dengan pembatasan akses tertentu
    """,
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
