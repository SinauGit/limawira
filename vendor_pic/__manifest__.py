{
    'name': 'Vendor Multiple PIC',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'depends': ['base', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/vendor_pic_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}