from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_id = fields.Many2one('sale.order', string='Sale Order', 
                             related='invoice_line_ids.sale_line_ids.order_id', 
                             store=True, readonly=True)

    def has_downpayment_product(self):
        """Check if invoice contains downpayment product"""
        self.ensure_one()
        # More flexible downpayment detection
        downpayment_keywords = ['down payment', 'downpayment', 'dp', 'uang muka']
        
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.name:
                product_name = line.product_id.name.lower()
                if any(keyword in product_name for keyword in downpayment_keywords):
                    return True
        return False

    def get_combined_invoice_lines(self):
        """Get combined lines from invoice and related sale order for downpayment invoices"""
        self.ensure_one()
        combined_lines = []
        
        if not self.sale_id:
            return self.invoice_line_ids
        
        # Get all invoice lines (downpayment items)
        invoice_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        
        # Get all sale order lines (complete order details)
        sale_lines = self.sale_id.order_line.filtered(lambda l: l.display_type == 'product')
        
        # Create combined data structure
        # First add section: "INVOICE ITEMS (DOWN PAYMENT)"
        combined_lines.append({
            'type': 'section',
            'name': 'INVOICE ITEMS (DOWN PAYMENT)',
            'lines': invoice_lines
        })
        
        # Then add section: "COMPLETE ORDER DETAILS"  
        combined_lines.append({
            'type': 'section', 
            'name': 'COMPLETE ORDER DETAILS',
            'lines': sale_lines
        })
        
        return combined_lines

    def print_invoice_pdf(self):
        """Print appropriate invoice report based on content"""
        self.ensure_one()
        if self.has_downpayment_product():
            report_action = self.env.ref('custom_downpayment_invoice.downpayment_invoice_report')
        else:
            report_action = self.env.ref('account.account_invoices_without_payment')
        return report_action.report_action(self)

    @api.model
    def _get_downpayment_display_data(self, invoice_obj):
        """Helper method to prepare display data for downpayment template"""
        data = {
            'invoice_lines': [],
            'sale_lines': [],
            'show_both_sections': False
        }
        
        if not invoice_obj.sale_id:
            data['invoice_lines'] = invoice_obj.invoice_line_ids
            return data
            
        # Prepare invoice lines section
        invoice_lines = invoice_obj.invoice_line_ids.filtered(lambda l: l.display_type in ['product', 'line_section', 'line_note'])
        data['invoice_lines'] = invoice_lines
        
        # Prepare sale order lines section  
        sale_lines = invoice_obj.sale_id.order_line.filtered(lambda l: l.display_type in ['product', 'line_section', 'line_note'])
        data['sale_lines'] = sale_lines
        
        # Show both sections if we have sale order
        data['show_both_sections'] = bool(invoice_obj.sale_id and sale_lines)
        
        return data