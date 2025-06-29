from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_downpayment_keywords(self):
        """
        Define keywords for down payment detection
        Returns list of keywords to search for
        """
        return ['down payment', 'termin']

    def _is_downpayment_line(self, line):
        """
        Check if a line contains down payment or termin keywords
        Searches in line name, product name, and description
        """
        keywords = self._get_downpayment_keywords()
        
        # Search in line name
        if line.name:
            line_name_lower = line.name.lower()
            for keyword in keywords:
                if keyword in line_name_lower:
                    return True
        
        # Search in product name
        if line.product_id and line.product_id.name:
            product_name_lower = line.product_id.name.lower()
            for keyword in keywords:
                if keyword in product_name_lower:
                    return True
        
        # Search in line description (if exists)
        if hasattr(line, 'description') and line.description:
            description_lower = line.description.lower()
            for keyword in keywords:
                if keyword in description_lower:
                    return True
        
        return False

    def get_down_payment_or_termin_count(self):
        """
        Get the exact count of lines containing down payment or termin keywords
        Counts any line that contains either 'down payment' OR 'termin'
        """
        count = 0
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                count += 1
        return count

    def has_exactly_one_down_payment_or_termin(self):
        """
        Check if invoice has exactly one line with down payment or termin keywords
        Returns True only if there's exactly 1 such line
        
        Requirements:
        - If 1 line with 'Down Payment' OR 'termin' → True
        - If more than 1 line with 'Down Payment' OR 'termin' → False  
        - If 0 lines with keywords → False
        """
        return self.get_down_payment_or_termin_count() == 1
    
    def get_related_sale_order_lines(self):
        """
        Get related sale order lines based on invoice origin
        """
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        return sale_order.order_line if sale_order else []

    def should_show_downpayment_template(self):
        """
        Main method to determine if downpayment template should be shown
        
        Conditions:
        1. Must have exactly 1 line containing 'Down Payment' OR 'termin'
        2. Must have related sale order lines (if this method exists)
        
        Returns True only if both conditions are met
        """
        # First check: exactly one down payment/termin line
        if not self.has_exactly_one_down_payment_or_termin():
            return False
        
        # Second check: has related sale order lines (if method exists)
        if hasattr(self, 'get_related_sale_order_lines'):
            return bool(self.get_related_sale_order_lines())
        
        # If no sale order method, just return based on down payment check
        return True

    def get_downpayment_debug_info(self):
        """
        Debug method to help troubleshoot down payment detection
        Returns dictionary with detailed information
        """
        debug_info = {
            'total_lines': len(self.invoice_line_ids),
            'downpayment_lines': [],
            'count': 0
        }
        
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                debug_info['downpayment_lines'].append({
                    'line_name': line.name,
                    'product_name': line.product_id.name if line.product_id else None,
                    'line_id': line.id
                })
                debug_info['count'] += 1
        
        debug_info['should_show_template'] = self.should_show_downpayment_template()
        return debug_info