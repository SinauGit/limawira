{
    'name': 'Department Vendor Bill Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Manage vendor bills by department with user-level access control',
    'description': """
        Department Vendor Bill Management
        =================================
        
        This module provides:
        * User-level access control for vendor bills
        * Department-level access for managers
        * Auto-assignment of department based on user's department
        * Integration with existing Odoo vendor bill management
        
        Users can only view their own vendor bills, managers can view all bills from their department.
    """,
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