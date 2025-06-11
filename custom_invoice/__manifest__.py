{
    'name': 'Custom Invoice',
    'version': '18.0.1.0.0',
    'depends': ['account'],
    'data': [
        'reports/invoice_report.xml',
        'reports/invoice_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}