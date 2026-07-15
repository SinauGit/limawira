{
    'name': 'Sale Custom Access',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Read-only Sales Order access group, exposed via Project embedded action',
    'depends': ['sale_project', 'crm', 'spreadsheet_sale_management'],
    'data': [
        'security/sale_custom_access_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/embedded_actions_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
