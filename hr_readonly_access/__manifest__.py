{
    'name': 'HR Readonly Access',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['hr', 'hr_org_chart', 'sale_readonly_access'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
