{
    'name': 'Department Expense Bill Management',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.rule.xml',
        'security/ir.model.access.csv',
                                  
        'data/ir_actions_data.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}