{
    'name': 'Department Expense Bill Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Manage expense bills by department with user-level access control',
    'description': """
        Department Expense Bill Management
        ===================================
        
        This module adds expense bill management with department-based access control.
        
        Features:
        - Custom expense bill type using is_expense_bill field
        - Automatic journal assignment (EXP code)
        - Three-level access control:
          * User: Can only see their own expense bills
          * Manager: Can see all expense bills from their department
          * Admin: Can see all expense bills from all departments
        - Automatic department assignment based on creator
    """,
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'hr',
    ],
    'data': [
        'security/security.xml',
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