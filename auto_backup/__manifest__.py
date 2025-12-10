                       
{
    'name': "mencadangkan",
    'author': "Van Ginneken di revisi dan migrasi dari odoo 17 ke 18 oleh Rizky Abdi",
    'category': 'Administration',
    'website': "www.lui.co.id",
    'version': '18.0.0.1',
    'installable': True,
    'license': 'LGPL-3',
    'module_type': 'official',

    'depends': ['base'],
    'external_dependencies': {'python': ['paramiko']},

                   
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/backup_view.xml',
        'data/backup_data.xml',
    ],
}
