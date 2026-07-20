{
    'name': 'Project Invoice Readonly Access',
    'version': '18.0.1.0.0',
    'category': 'Kustom',
    'depends': ['sale_readonly_access', 'sale_project', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/embedded_actions.xml',
        'views/project_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
