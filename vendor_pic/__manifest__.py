{
    'name': 'Vendor Multiple Persons In Charge',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Add multiple Persons in Charge (PICs) functionality for vendors',
    'description': """
        This module adds the ability to assign multiple Persons in Charge (PICs) to vendors,
        including contact details, position information, and assigned departments.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
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