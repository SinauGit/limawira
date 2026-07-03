# -*- coding: utf-8 -*-
{
    'name': 'Project Cost Report Export',
    'version': '18.0.1.0.0',
    'author': 'Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'depends': [
        'project',
        'sale_project',
        'sale',
        'hr',
        'account',
        'stock',
        'stock_account',
        'lww_delivery',
        'lww_accounting',

    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/project_cost_export_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
