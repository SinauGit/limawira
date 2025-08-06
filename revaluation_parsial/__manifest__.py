{
    'name': 'Custom Stock Valuation Revaluation',
    'version': '1.0',
    'depends': ['stock_account','stock'],
    'data': [
        'security/ir.model.access.csv'
        # 'views/stock_valuation_layer_views.xml',
        # 'wizard/stock_valuation_layer_revaluation_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}