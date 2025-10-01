{
    'name': 'Department Vendor Bill Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Manage vendor bills by department with user-level access control',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'hr',
    ],
    'data': [
        'security/security.xml',
        # 'security/ir.model.access.csv',
        'data/ir_actions_data.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}