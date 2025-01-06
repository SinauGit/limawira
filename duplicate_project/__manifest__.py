{
    'name': 'Project Name Validation',
    "version": "17.0.1.0.0",
    'summary': 'Prevent duplicate project names ',
    'description': """
        This module prevents duplicate project names
    """,
    'author': 'Rizky Abdi Syahputra Hasibuan',
    'website': '',
    'category': 'Project',
    'license': 'LGPL-3',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
