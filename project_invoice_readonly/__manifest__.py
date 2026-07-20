{
    'name': 'Project Invoice Readonly Access',
    'version': '18.0.1.1.0',
    'category': 'Kustom',
    'depends': ['sale_readonly_access', 'sale_project', 'project_stock', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/embedded_actions.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
