{
    'name': 'WIP Project Analytic Items',
    'version': '18.0.1.0.0',
    'depends': ['account', 'analytic', 'analytic_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'views/analytic_line_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}