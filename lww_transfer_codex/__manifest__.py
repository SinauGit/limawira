{
    'name': 'LWW Transfer Codex',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Focused tool to reassign Project and Analytic on Invoices/Bills and Stock Moves',
    'depends': [
        'base',
        'project',
        'analytic',
        'sale',
        'purchase',
        'account',
        'stock',
        'hr_expense',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/transfer_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}
