{
    'name': 'Custom Delivery Slip',
    "version": "18.0.1.0.0",
    'summary': 'Custom Delivery Slip with Signature Section',
    'description': """
        Customize delivery slip report by adding signature section
        for Customer, Sender, and Warehouse Keeper
    """,
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'website': '',
    'category': 'Inventory/Delivery',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'views/custom_delivery_slip.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
