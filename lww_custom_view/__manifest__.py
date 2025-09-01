# lww_custom_view/__manifest__.py
{
    "name": "LWW Custom View",
    "version": "1.0.0",
    "depends": ["account", "sale", "project"],  # project is needed for project.project
    "data": [
        "views/account_move_views.xml",
    ],
    "application": False,
    "installable": True,
    "license": "OEEL-1",
}
