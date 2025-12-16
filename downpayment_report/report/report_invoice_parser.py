from odoo import models, fields
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_downpayment_keywords(self):
          
        return ['down payment', 'termin']

    def _is_downpayment_line(self, line):

           
        keywords = self._get_downpayment_keywords()
        
        if line.name:
            line_name_lower = line.name.lower()
            for keyword in keywords:
                if keyword in line_name_lower:
                    return True
        
        if line.product_id and line.product_id.name:
            product_name_lower = line.product_id.name.lower()
            for keyword in keywords:
                if keyword in product_name_lower:
                    return True
        
        if hasattr(line, 'description') and line.description:
            description_lower = line.description.lower()
            for keyword in keywords:
                if keyword in description_lower:
                    return True
        
        return False

    def has_downpayment_line_section(self):
           
        target_section_name = 'Down Payment / Termin'
        
        for line in self.invoice_line_ids:
            if line.display_type == 'line_section' and line.name:
                if line.name.strip() == target_section_name:
                    return True
        
        return False

    def get_down_payment_or_termin_count(self):
           
        count = 0
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                count += 1
        return count

    def has_exactly_one_down_payment_or_termin(self):
           
        return self.get_down_payment_or_termin_count() == 1

    def get_related_sale_order_lines(self):



           
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        
        if sale_order:
                                                                   
            return sale_order.order_line.filtered(lambda l: not l.display_type and l.product_id)
        
        return []

    def get_downpayment_lines(self):



           
        downpayment_lines = []
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                downpayment_lines.append(line)
        return downpayment_lines

    def get_all_downpayment_invoices_for_so(self):







           
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
                                              
        all_invoices = self.env['account.move'].search([
            ('invoice_origin', '=', self.invoice_origin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'in', ['posted', 'draft'])
        ], order='invoice_date asc, create_date asc')
        
                                           
        downpayment_invoices = []
        for invoice in all_invoices:
            if invoice.get_down_payment_or_termin_count() > 0:
                downpayment_invoices.append(invoice)
        
        return downpayment_invoices

    def get_total_downpayment_count_for_so(self):




           
        self.ensure_one()
        return len(self.get_all_downpayment_invoices_for_so())

    def get_downpayment_lines_with_installment_numbers(self):



















           
        self.ensure_one()
        
                                         
        dp_invoices = self.get_all_downpayment_invoices_for_so()
        total_dp_count = len(dp_invoices)
        
        if total_dp_count == 0:
            return []
        
                                             
        dp_lines_with_numbers = []
        
        for index, invoice in enumerate(dp_invoices, start=1):
            dp_lines = invoice.get_downpayment_lines()
            
            for line in dp_lines:
                                                             
                if total_dp_count == 1:
                                                      
                    display_name = 'Down Payment / Termin'
                else:
                                                           
                    display_name = f'Down Payment / Termin {index}'
                
                dp_lines_with_numbers.append({
                    'line': line,
                    'display_name': display_name,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal
                })
        
        return dp_lines_with_numbers

    def should_show_downpayment_template(self):









           
                                                                 
        has_one_downpayment_line = self.has_exactly_one_down_payment_or_termin()
        
                                                                               
        has_forbidden_section = self.has_downpayment_line_section()
        
                                                                          
        if not has_one_downpayment_line or has_forbidden_section:
            return False
        
                                                              
        if self.get_related_sale_order_lines():
            return True
        
        return False

    def get_invoice_lines_for_report(self):








           
                                                                   
        if not self.should_show_downpayment_template():
                                                                            
            return self.invoice_line_ids.sorted(
                key=lambda l: (-l.sequence, l.date or '', l.move_name or '', -l.id),
                reverse=True
            )
        
                                                                      
        filtered_lines = []
        for line in self.invoice_line_ids:
            if not self._is_downpayment_line(line):
                filtered_lines.append(line)
        
                                                    
        sorted_lines = sorted(
            filtered_lines,
            key=lambda l: (-l.sequence, l.date or '', l.move_name or '', -l.id),
            reverse=True
        )
        
        return sorted_lines

    def get_downpayment_debug_info(self):



           
        debug_info = {
            'total_lines': len(self.invoice_line_ids),
            'downpayment_lines_current_invoice': [],
            'downpayment_sections': [],
            'line_count': 0,
            'section_count': 0,
            'total_dp_invoices_for_so': 0,
            'related_so_lines_count': 0,
            'all_dp_invoices': [],
            'downpayment_lines_with_numbers': []
        }
        
                                                
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                debug_info['downpayment_lines_current_invoice'].append({
                    'line_name': line.name,
                    'product_name': line.product_id.name if line.product_id else None,
                    'line_id': line.id,
                    'display_type': line.display_type,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal
                })
                debug_info['line_count'] += 1
        
                             
        target_section_name = 'Down Payment / Termin'
        for line in self.invoice_line_ids:
            if line.display_type == 'line_section' and line.name:
                if line.name.strip() == target_section_name:
                    debug_info['downpayment_sections'].append({
                        'section_name': line.name,
                        'line_id': line.id,
                        'exact_match': True
                    })
                    debug_info['section_count'] += 1
        
                                    
        all_dp_invoices = self.get_all_downpayment_invoices_for_so()
        debug_info['total_dp_invoices_for_so'] = len(all_dp_invoices)
        debug_info['all_dp_invoices'] = [
            {
                'invoice_id': inv.id,
                'invoice_name': inv.name,
                'invoice_date': str(inv.invoice_date),
                'dp_line_count': inv.get_down_payment_or_termin_count()
            }
            for inv in all_dp_invoices
        ]
        
                                   
        dp_with_numbers = self.get_downpayment_lines_with_installment_numbers()
        debug_info['downpayment_lines_with_numbers'] = [
            {
                'display_name': item['display_name'],
                'quantity': item['quantity'],
                'price_unit': item['price_unit'],
                'price_subtotal': item['price_subtotal']
            }
            for item in dp_with_numbers
        ]
        
        debug_info['has_exactly_one_line'] = self.has_exactly_one_down_payment_or_termin()
        debug_info['has_line_section'] = self.has_downpayment_line_section()
        debug_info['should_show_template'] = self.should_show_downpayment_template()
        debug_info['related_so_lines_count'] = len(self.get_related_sale_order_lines())
        
        return debug_info