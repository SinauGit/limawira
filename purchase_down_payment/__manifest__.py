                       
                                                                               
 
                                    
 
                                                                               
                                                 
 
                                                       
                                                
 
                                                                   
                                                                  
                                                                 
                                                                 
 
                                                                            
                                      
                                                                              
{
    'name': 'Purchase Down Payment',
    'version': '18.0.1.0.0',
    'summary': """Down payment with purchase order""",
    'description': 'This module provides easy feature to register down payment'
                   'against the purchase order. User will be able to register '
                   'downpayment in percentage and amount that would deduct from'
                   'vendor bill.',
    'category': 'Purchase',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['purchase', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_advance_payment_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
