{
    'name': "Invoice Multi Level Approval",
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'author': 'Cybrosys direvisi dan disesuaikan ulang oleh Rizky Abdi',
    'depends': ['account'],
    'data': [
        'security/invoice_multi_approval_groups.xml',
        'security/ir.model.access.csv',
        'data/invoice_approval_data.xml',
        'views/invoice_approval_views.xml',
        'views/account_move_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
