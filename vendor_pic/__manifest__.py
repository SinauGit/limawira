{
    'name': 'Vendor Multiple Persons In Charge',
    'version': '18.0.1.0.0',
    'author': "Rizky Abdi S.H",
    'website': "www.lui.co.id",
    'depends': ['base', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/vendor_pic_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}