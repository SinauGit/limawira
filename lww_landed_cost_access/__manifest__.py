{
    'name': 'Landed Cost Access for Purchase & Billing',
    'version': '18.0.1.1.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['stock_landed_costs', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
