{
    'name': 'Department Expense Bill Management',
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
        # 'data/journal_data.xml',
        'data/ir_actions_data.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}