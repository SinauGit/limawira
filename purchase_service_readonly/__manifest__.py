{
    'name': 'Purchase Service Readonly',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['purchase', 'account', 'sale_readonly_access', 'ship_via'],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
