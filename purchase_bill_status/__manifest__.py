# -*- coding: utf-8 -*-
{
    'name': 'Purchase Bill Status',
    'version': '1.0',
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
}