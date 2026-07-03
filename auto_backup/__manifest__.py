                       
{
    'name': "mencadangkan",
    'author': "Van Ginneken di revisi dan migrasi dari odoo 17 ke 18 oleh Rizky Abdi",
    'author': 'Van Ginneken - Revised and Porting to odoo 18 by Rizky Abdi S.H',
    'website': 'https://lui.co.id',
    'company': 'Pt Lintang Utama Infotek',
    'version': '18.0.0.1',
    'installable': True,

    'depends': ['base'],
    'external_dependencies': {'python': ['paramiko']},

                   
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/backup_view.xml',
        'data/backup_data.xml',
    ],
}
