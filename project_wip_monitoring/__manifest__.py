{
    'name': 'WIP Project Analytic Items',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Analytic Items view for WIP Project',
    'description': """
        Custom module to display Analytic Items filtered by account '1061 WIP Project'
        with grouping by Reference and Journal Item.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
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