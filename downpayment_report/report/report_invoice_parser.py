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
        
        # Search in description (if exists)
        if hasattr(line, 'description') and line.description:
            description_lower = line.description.lower()
            for keyword in keywords:
                if keyword in description_lower:
                    return True
        
        return False

    def has_downpayment_line_section(self):
        """
        NEW METHOD: Check if there's a line section with EXACT text 'Down Payment / Termin'
        
        This method specifically looks for lines with display_type = 'line_section'
        and checks if the section name is exactly 'Down Payment / Termin'
        
        Returns:
            bool: True if there's at least one line section with exact text 'Down Payment / Termin'
        """
        target_section_name = 'Down Payment / Termin'
        
        for line in self.invoice_line_ids:
            # Check if this is a line section with exact match
            if line.display_type == 'line_section' and line.name:
                if line.name.strip() == target_section_name:
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
        UPDATED METHOD: Main method to determine if downpayment template should be shown
        
        Conditions (must meet ALL):
        1. Has exactly 1 line containing 'Down Payment' OR 'termin' keywords, AND
        2. Does NOT have line section with exact text 'Down Payment / Termin', AND
        3. Must have related sale order lines
        
        Returns True only if ALL conditions are met
        """
        # Check condition 1: exactly one down payment/termin line
        has_one_downpayment_line = self.has_exactly_one_down_payment_or_termin()
        
        # Check condition 2: must NOT have line section 'Down Payment / Termin'
        has_forbidden_section = self.has_downpayment_line_section()
        
        # Must have exactly one down payment line AND no forbidden section
        if not has_one_downpayment_line or has_forbidden_section:
            return False
        
        # Additional check: must have related sale order lines
        if hasattr(self, 'get_related_sale_order_lines'):
            return bool(self.get_related_sale_order_lines())
        
        # If no sale order method, just return based on down payment checks
        return True

    def get_downpayment_debug_info(self):
        """
        UPDATED DEBUG METHOD: Debug method to help troubleshoot down payment detection
        Returns dictionary with detailed information including line section info
        """
        debug_info = {
            'total_lines': len(self.invoice_line_ids),
            'downpayment_lines': [],
            'downpayment_sections': [],
            'line_count': 0,
            'section_count': 0
        }
        
        # Check regular lines
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                debug_info['downpayment_lines'].append({
                    'line_name': line.name,
                    'product_name': line.product_id.name if line.product_id else None,
                    'line_id': line.id,
                    'display_type': line.display_type
                })
                debug_info['line_count'] += 1
        
        # Check line sections
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
        
        debug_info['has_exactly_one_line'] = self.has_exactly_one_down_payment_or_termin()
        debug_info['has_line_section'] = self.has_downpayment_line_section()
        debug_info['should_show_template'] = self.should_show_downpayment_template()
        debug_info['has_related_so_lines'] = bool(self.get_related_sale_order_lines())
        
        return debug_info