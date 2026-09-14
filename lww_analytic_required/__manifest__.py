{
    'name': 'LWW Analytic Distribution Required',
    'version': '18.0.1.0.0',
    'summary': 'Mewajibkan pengisian Analytic Distribution pada akun tertentu di Vendor Bill dan Journal Entry',
    'category': 'Accounting',
    'author': 'limawira',
    'depends': ['account'],
    'data': [
        'views/account_account_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
