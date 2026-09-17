{
    'name': 'LWW - Edit Customer/UoM After SO Confirm',
    'version': '18.0.2.0.0',
    'category': 'Sales',
    'summary': 'Tie Customer/UoM editability on confirmed Sales Orders to native Lock/Unlock, '
               'and extend Lock/Unlock access to the order\'s own Salesperson',
    'author': 'limawira',
    'depends': ['sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
