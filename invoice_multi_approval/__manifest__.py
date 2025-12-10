                       
                                                                             
 
                                    
 
                                                                                
                                                          
 
                                                        
                                                 
 
                                                                    
                                                                   
                                                                  
                                                                  
 
                                                                             
                                       
                                                
 
                                                                             
{
    'name': "Invoice Multi Level Approval",
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': """This module add the multiple approval option for invoice,
     bill, refund and credit notes with single or multiple approvals""",
    'description': """This module add the multiple approval option for invoice,
     bill,refund and credit notes.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['account'],
    'data': [
        'security/invoice_multi_approval_groups.xml',
        'security/ir.model.access.csv',
        'data/invoice_approval_data.xml',
        'views/invoice_approval_views.xml',
        'views/account_move_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
