{
    'name': 'LWW Company Module Restriction',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Restrict visible modules/menus per company',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
