# lww_custom_view/__manifest__.py
{
    "name": "LWW Custom View",
    "version": "1.0.0",
    "depends": ["account", "sale", "project","hr_expense"],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}