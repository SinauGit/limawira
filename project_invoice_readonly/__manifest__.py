{
    'name': 'Project Invoice Readonly Access',
    'version': '18.0.1.3.0',
    'category': 'Kustom',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['sale_readonly_access', 'sale_project', 'project_stock', 'project_purchase', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/embedded_actions.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
