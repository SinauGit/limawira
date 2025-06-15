{
    'name': 'Custom Invoice',
    'version': '18.0.1.0.0',
    'depends': ['base','web', 'account'],
    'data': [
        'reports/invoice_report.xml',
        'reports/invoice_template.xml',
    ],
    # 'assets': {
    #     'web.assets_common': [
    #         'static/src/css/invoice_style.css',
    #     ],
    # },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
