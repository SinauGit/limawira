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

    def get_all_downpayment_invoices_for_so(self):
        """
        Get ALL down payment invoices from same Sales Order (sorted by date)
        
        Includes CURRENT invoice + all previous down payment invoices
        from same SO (invoice_origin)
        
        Returns: List of account.move records (sorted by invoice date)
        """
        self.ensure_one()
        if not self.invoice_origin:
            return []
        
        # Search for all invoices from same SO
        all_invoices = self.env['account.move'].search([
            ('invoice_origin', '=', self.invoice_origin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'in', ['posted', 'draft'])
        ], order='invoice_date asc, create_date asc')
        
        # Filter only down payment invoices
        downpayment_invoices = []
        for invoice in all_invoices:
            if invoice.get_down_payment_or_termin_count() > 0:
                downpayment_invoices.append(invoice)
        
        return downpayment_invoices

    def get_total_downpayment_count_for_so(self):
        """
        Get total count of down payment invoices for this Sales Order
        
        Returns: Integer (total number of DP invoices including current)
        """
        self.ensure_one()
        return len(self.get_all_downpayment_invoices_for_so())

    def get_downpayment_lines_with_installment_numbers(self):
        """
        Get ALL down payment lines from ALL down payment invoices for this SO
        with installment numbers
        
        LOGIC:
        - If total DP invoices = 1 → no numbering
        - If total DP invoices > 1 → show numbering (1, 2, 3, etc)
        
        Returns: List of dictionaries
        [
            {
                'line': <account.move.line>,
                'display_name': 'Down Payment / Termin' or 'Down Payment / Termin 1',
                'quantity': 1,
                'price_unit': 500,
                'price_subtotal': 500
            },
            ...
        ]
        """
        self.ensure_one()
        
        # Get all DP invoices for this SO
        dp_invoices = self.get_all_downpayment_invoices_for_so()
        total_dp_count = len(dp_invoices)
        
        if total_dp_count == 0:
            return []
        
        # Collect all DP lines with numbering
        dp_lines_with_numbers = []
        
        for index, invoice in enumerate(dp_invoices, start=1):
            dp_lines = invoice.get_downpayment_lines()
            
            for line in dp_lines:
                # Determine display name based on total count
                if total_dp_count == 1:
                    # Only 1 DP invoice → no numbering
                    display_name = 'Down Payment / Termin'
                else:
                    # Multiple DP invoices → show numbering
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

    def get_invoice_lines_for_report(self):
        """
        Get invoice lines excluding down payment lines with proper sorting
        Used in report template to avoid showing down payment lines in standard table
        
        Returns: List of account.move.line (excluding down payment lines)
        Sorted by: -sequence, date, move_name, -id (reversed)
        """
        # Filter out down payment lines
        filtered_lines = []
        for line in self.invoice_line_ids:
            if not self._is_downpayment_line(line):
                filtered_lines.append(line)
        
        # Sort using the same logic as Odoo standard
        # sorted(key=lambda l: (-l.sequence, l.date, l.move_name, -l.id), reverse=True)
        sorted_lines = sorted(
            filtered_lines,
            key=lambda l: (-l.sequence, l.date or '', l.move_name or '', -l.id),
            reverse=True
        )
        
        return sorted_lines

    def get_downpayment_debug_info(self):
        """
        DEBUG METHOD: Debug method to help troubleshoot down payment detection
        Returns dictionary with detailed information
        """
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
        
        # Check regular lines in current invoice
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
        
        # Get all DP invoices for SO
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
        
        # Get DP lines with numbers
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