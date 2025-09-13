{
    'name': 'Project & Analytic Transfer Tool',
    'version': '18.0.1.0.0',
    'category': 'Project Management',
    'summary': 'Transfer projects and analytics across Sales Orders, Purchase Orders, Invoices, Expenses, and Stock Moves',
    'description': """
        Project & Analytic Transfer Tool
        ================================
        
        This module allows you to transfer projects and analytic accounts from one to another across multiple document types:
        
        Features:
        * Transfer Sales Orders (project_id + analytic_distribution)
        * Transfer Purchase Orders (project_id + analytic_distribution)  
        * Transfer Invoices/Bills/Journal Entries (project_id + analytic_distribution)
        * Transfer Expenses (analytic_distribution)
        * Transfer Stock Moves/Receipts/Deliveries (analytic_distribution)
        * Multi-company support (within same company only)
        * Hybrid approach: Safe unpost/repost for posted documents
        * Complete analytic distribution replacement
        * User-friendly wizard interface
        * Progress tracking and result logging
    """,
    'author': 'Custom Developer',
    'depends': [
        'base',
        'project',
        'analytic',
        'sale',
        'purchase', 
        'account',
        'hr_expense',
        'stock',
        'lww_stock_analytic',
        'stock_analytic',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/transfer_config_views.xml',
        'wizard/project_analytic_transfer_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}