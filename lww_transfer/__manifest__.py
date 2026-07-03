{
    'name': 'Project Transfer',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': [
        'project',
        'sale_management',
        'purchase',
        'account',
        'hr_expense',
        'stock',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/project_analytic_transfer_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}