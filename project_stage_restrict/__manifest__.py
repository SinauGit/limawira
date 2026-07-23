{
    'name': 'Project Stage Restrict',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Project User access without permission to change project stage',
    'depends': ['project'],
    'data': [
        'security/security_groups.xml',
        'views/project_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
