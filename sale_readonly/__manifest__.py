{
    'name': 'Sale Read Only Access',
    'version': '18.0.1.0.1',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['sale_management', 'account','spreadsheet_sale_management'],
    'data': [
        'security/sale_readonly_security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
