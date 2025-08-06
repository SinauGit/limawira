# -*- coding: utf-8 -*-
{
    'name': 'Purchase Bill Status',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Menampilkan status pembayaran bill pada purchase order',
    'depends': [
        'base',
        'purchase',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}