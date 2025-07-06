# -*- coding: utf-8 -*-
{
    'name': "data",
    'author': "Yenthe Van Ginneken di revisi dan migrasi dari odoo 17 ke 18 oleh Rizky Ganteng",
    'category': 'Administration',
    'version': '18.0.0.1',
    'installable': True,
    'license': 'LGPL-3',
    'module_type': 'official',

    'depends': ['base'],
    'external_dependencies': {'python': ['paramiko']},

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/backup_view.xml',
        'data/backup_data.xml',
    ],
}
