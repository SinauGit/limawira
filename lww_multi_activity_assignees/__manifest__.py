# -*- coding: utf-8 -*-
{
    'name': 'Mail Activity Multi Assign',
    'version': '18.0.1.0.0',
    'depends': ['base_setup','mail'],
    'data': [
        'views/mail_activity_schedule_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'mail_activity_multi_assign/static/src/js/activity_widget.js',
    #         'mail_activity_multi_assign/static/src/xml/activity_templates.xml',
    #     ],
    # },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}