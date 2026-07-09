{
    'name': 'ship via dan employee di po',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/ship_to_views.xml',
        # 'views/employee_views.xml',
        'views/customer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
