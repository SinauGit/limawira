from odoo import models, fields
from datetime import datetime

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
        """
        Check if there's a line section with EXACT text 'Down Payment / Termin'
        """
        target_section_name = 'Down Payment / Termin'
        
        for line in self.invoice_line_ids:
            if line.display_type == 'line_section' and line.name:
                if line.name.strip() == target_section_name:
                    return True
        
        return False

    def get_down_payment_or_termin_count(self):
        """
        Get the exact count of lines containing down payment or termin keywords
        """
        count = 0
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                count += 1
        return count

    def has_exactly_one_down_payment_or_termin(self):
        """
        Check if invoice has exactly one line with down payment or termin keywords
        """
        return self.get_down_payment_or_termin_count() == 1

    def get_related_sale_order_lines(self):
        """
        Get related sale order lines based on invoice origin
        Returns only product lines (excludes sections and notes)
        """
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.search([('name', '=', self.invoice_origin)], limit=1)
        
        if sale_order:
            # Return only product lines, exclude sections and notes
            return sale_order.order_line.filtered(lambda l: not l.display_type and l.product_id)
        
        return []

    def get_downpayment_lines(self):
        """
        Get down payment lines from current invoice
        Returns lines that contain 'down payment' or 'termin' keywords
        """
        downpayment_lines = []
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                downpayment_lines.append(line)
        return downpayment_lines

    def get_downpayment_invoice_number(self):
        """
        Determine which down payment installment this invoice is
        Counts previous down payment invoices from same sales order
        
        Returns: Integer (1 for first, 2 for second, etc.)
        """
        self.ensure_one()
        if not self.invoice_origin:
            return 1
        
        # Search for all posted invoices from same sales order (invoice_origin)
        previous_invoices = self.env['account.move'].search([
            ('invoice_origin', '=', self.invoice_origin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'in', ['posted', 'draft']),
            ('id', '!=', self.id)  # Exclude current invoice
        ])
        
        # Count how many of these previous invoices are down payment invoices
        downpayment_count = 0
        for invoice in previous_invoices:
            if invoice.get_down_payment_or_termin_count() > 0:
                downpayment_count += 1
        
        # Current invoice is downpayment number: previous count + 1
        return downpayment_count + 1

    def should_show_downpayment_template(self):
        """
        Main method to determine if downpayment template should be shown
        
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
        if self.get_related_sale_order_lines():
            return True
        
        return False

    def get_downpayment_line_with_installment_number(self):
        """
        Get down payment line with installment number label
        
        Returns: Dictionary with line data and installment number
        Example:
        {
            'line': <account.move.line>,
            'installment_number': 1,
            'display_name': 'Down Payment / Termin 1'
        }
        
        Returns empty dict if no down payment line found
        """
        downpayment_lines = self.get_downpayment_lines()
        
        if not downpayment_lines:
            return {}
        
        # Get the first down payment line (should be only 1 based on validation)
        line = downpayment_lines[0]
        installment_num = self.get_downpayment_invoice_number()
        
        # Create display name
        if installment_num == 1:
            display_name = 'Down Payment / Termin'
        else:
            display_name = f'Down Payment / Termin {installment_num}'
        
        return {
            'line': line,
            'installment_number': installment_num,
            'display_name': display_name,
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal
        }

    def get_downpayment_debug_info(self):
        """
        DEBUG METHOD: Debug method to help troubleshoot down payment detection
        Returns dictionary with detailed information
        """
        debug_info = {
            'total_lines': len(self.invoice_line_ids),
            'downpayment_lines': [],
            'downpayment_sections': [],
            'line_count': 0,
            'section_count': 0,
            'installment_number': 0,
            'related_so_lines_count': 0
        }
        
        # Check regular lines
        for line in self.invoice_line_ids:
            if self._is_downpayment_line(line):
                debug_info['downpayment_lines'].append({
                    'line_name': line.name,
                    'product_name': line.product_id.name if line.product_id else None,
                    'line_id': line.id,
                    'display_type': line.display_type,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal
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
        debug_info['related_so_lines_count'] = len(self.get_related_sale_order_lines())
        debug_info['installment_number'] = self.get_downpayment_invoice_number()
        debug_info['downpayment_line_info'] = self.get_downpayment_line_with_installment_number()
        
        return debug_info