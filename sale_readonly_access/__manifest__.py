{
    'name': 'Custom Access',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': [
        'sale_project',
        'spreadsheet_sale_management',
    ],
    'data': [
        'security/custom_access_groups.xml',
        'security/custom_access_rules.xml',
    ],
    'installable': True,
    'application': False,
}
