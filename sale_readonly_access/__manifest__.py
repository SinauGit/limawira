{
    'name': 'Sale Read Only Access',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': ['sale_management', 'sale_project','project','sale'],
    'data': [
        'security/sale_readonly_security.xml',
        'security/ir.model.access.csv',
        # 'views/sale_menu_access.xml',
        'views/project_view_inherit.xml',
    ],
    'license': 'LGPL-3',
}