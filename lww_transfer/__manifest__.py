{
    'name': 'Project Analytic Transfer',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Transfer project and analytic distribution across documents',
    'description': """
        Transfer project and analytic distribution across multiple documents:
        - Sales Orders
        - Purchase Orders
        - Invoices/Bills/Journal Entries
        - Expenses
        - Stock Moves
    """,
    'author': 'Your Company',
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