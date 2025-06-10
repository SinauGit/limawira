{
    'name': 'ship via dan employee di po',
    "version": "18.0.1.0.0",
    'description': """
        
    """,
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/ship_to_views.xml',
        'views/employee_views.xml',
        'views/customer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
