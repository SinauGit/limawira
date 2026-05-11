# -*- coding: utf-8 -*-
import base64
import io
import json
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    raise ImportError("Please install openpyxl: pip install openpyxl")


class ProjectCostExportWizard(models.TransientModel):
    _name = 'project.cost.export.wizard'
    _description = 'Project Cost Export Wizard'

    # Excel styling constants
    COLOR_LABEL = 'B4C6E7'
    COLOR_HEADER = '8EA9DB'
    COLOR_TOTAL = 'D9E1F2'
    
    FONT_SIZE = 10
    
    COLUMN_WIDTHS = {
        'A': 25,
        'B': 22,
        'C': 18,
        'D': 28,
        'E': 18,
        'F': 18,
        'G': 18,
        'H': 60
    }
    
    MONTHS_ID = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
        7: 'Jul', 8: 'Agust', 9: 'Sep', 10: 'Okt', 11: 'Nop', 12: 'Des'
    }

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )
    file_data = fields.Binary(string='File', readonly=True)
    file_name = fields.Char(string='Filename', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    def _format_number(self, value):
        """Format number dengan format Indonesia (titik ribuan, koma desimal)"""
        if not value or value == 0:
            return '-'
        return "{:,.2f}".format(value).replace(',', 'X').replace('.', ',').replace('X', '.')

    def _format_date(self, date_value):
        """Format date ke format Indonesia"""
        if not date_value:
            return ''
        
        if isinstance(date_value, str):
            date_value = fields.Date.from_string(date_value)
        if hasattr(date_value, 'date'):
            date_value = date_value.date()
        
        day = date_value.day
        month = self.MONTHS_ID.get(date_value.month, '')
        year = str(date_value.year)[-2:]
        return f"{day:02d}-{month}-{year}"

    def _get_project_analytic_account_ids(self, project):
        """Get analytic account IDs dari project"""
        analytic_ids = []
        
        # Odoo 18: project menggunakan analytic_account_id atau account_id
        if hasattr(project, 'analytic_account_id') and project.analytic_account_id:
            analytic_ids.append(project.analytic_account_id.id)
        
        if hasattr(project, 'account_id') and project.account_id:
            if project.account_id.id not in analytic_ids:
                analytic_ids.append(project.account_id.id)
        
        # Coba dari analytic_account_ids (jika ada multiple)
        if hasattr(project, 'analytic_account_ids') and project.analytic_account_ids:
            for acc in project.analytic_account_ids:
                if acc.id not in analytic_ids:
                    analytic_ids.append(acc.id)
        
        return analytic_ids

    def _get_sale_order(self, project):
        """Get sale order terkait project"""
        sale_order = False
        
        # Coba dari field sale_order_id
        if hasattr(project, 'sale_order_id') and project.sale_order_id:
            sale_order = project.sale_order_id
        
        # Coba dari sale_line_id
        elif hasattr(project, 'sale_line_id') and project.sale_line_id:
            sale_order = project.sale_line_id.order_id
        
        # Coba cari dari sale.order yang memiliki project_id
        if not sale_order:
            sale_order = self.env['sale.order'].search([
                '|',
                ('project_id', '=', project.id),
                ('project_ids', 'in', [project.id])
            ], limit=1)
        
        # Coba dari analytic account
        if not sale_order:
            analytic_ids = self._get_project_analytic_account_ids(project)
            if analytic_ids:
                sale_order = self.env['sale.order'].search([
                    ('analytic_account_id', 'in', analytic_ids)
                ], limit=1)
        
        return sale_order

    def _get_pekerjaan(self, sale_order):
        """Get custom_description dari sale order line, gabung dengan ' - ' jika lebih dari 1"""
        if not sale_order or not sale_order.order_line:
            return ''
        
        descriptions = []
        for line in sale_order.order_line:
            if hasattr(line, 'display_type') and line.display_type in ('line_section', 'line_note'):
                continue
            if hasattr(line, 'custom_description') and line.custom_description:
                description = line.custom_description
                if description and description not in descriptions:
                    descriptions.append(description)
        
        return ' - '.join(descriptions) if descriptions else ''

    def _get_nilai_pekerjaan(self, sale_order):
        """Get total dari sale order"""
        if not sale_order:
            return 0.0
        return sale_order.amount_total or 0.0

    def _get_nama_sales(self, sale_order):
        """Get nama sales dari employee_id pada sale order"""
        if not sale_order:
            return ''
        
        # Coba dari employee_id langsung
        if hasattr(sale_order, 'employee_id') and sale_order.employee_id:
            return sale_order.employee_id.name or ''
        
        # Coba dari user_id.employee_id
        if sale_order.user_id:
            employee = self.env['hr.employee'].search([
                ('user_id', '=', sale_order.user_id.id)
            ], limit=1)
            if employee:
                return employee.name or ''
            return sale_order.user_id.name or ''
        
        return ''

    def _check_analytic_distribution(self, analytic_distribution, analytic_ids):
        """Check apakah analytic_distribution mengandung salah satu analytic_ids"""
        if not analytic_distribution or not analytic_ids:
            return False
        
        # analytic_distribution adalah JSON/dict dengan format {analytic_id: percentage}
        if isinstance(analytic_distribution, str):
            try:
                analytic_distribution = json.loads(analytic_distribution)
            except:
                return False
        
        if isinstance(analytic_distribution, dict):
            for key in analytic_distribution.keys():
                try:
                    if int(key) in analytic_ids:
                        return True
                except:
                    continue
        
        return False

    def _get_vendor_bills(self, project):
        """Get vendor bills terkait project berdasarkan line_ids dengan account 1061"""
        analytic_ids = self._get_project_analytic_account_ids(project)
        
        if not analytic_ids:
            return []
        
        bills_data = []
        
        vendor_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
        ], order='date asc, id asc')
        
        for bill in vendor_bills:
            for line in bill.line_ids:
                # Kondisi 1: Account code harus 1061
                if line.account_id.code == '1061':
                    # Kondisi 2: Hanya ambil yang debit (normal case)
                    if line.debit > 0:
                        # Kondisi 3: Analytic distribution harus match dengan project
                        if self._check_analytic_distribution(line.analytic_distribution, analytic_ids):
                            
                            note = ''
                            if hasattr(line, 'custom_description') and line.custom_description:
                                note = line.custom_description
                            elif line.name:
                                note = line.name

                            invoice_no = ''
                            if hasattr(bill, 'invoice_no') and bill.invoice_no:
                                invoice_no = bill.invoice_no
                            elif bill.ref:
                                invoice_no = bill.ref

                            bills_data.append({
                                'txno': bill.name or '',
                                'invoice_no': invoice_no,
                                'date': bill.date or '',
                                'subject': bill.partner_id.name if bill.partner_id else '',
                                'value': line.debit,
                                'debet': line.debit,
                                'credit': 0.0,
                                'note': note,
                            })
        
        return bills_data

    def _build_picking_note(self, picking):
        """Bangun note dari daftar barang di picking.
        
        Format per baris: {qty} {uom} {custom_description} - {po_number}
        Setiap barang dipisahkan dengan newline.
        """
        lines = []
        for move in picking.move_ids:
            # Qty — tampilkan tanpa desimal jika bilangan bulat
            qty = move.product_uom_qty
            qty_str = str(int(qty)) if qty == int(qty) else str(qty)

            # UOM
            uom_str = move.product_uom.name if move.product_uom else ''

            # Nama barang — utamakan description_picking, fallback ke product name
            product = move.product_id
            if move.description_picking:
                item_name = move.description_picking
            elif product:
                item_name = product.name or ''
            else:
                item_name = ''

            # Nomor PO — 3 jalur pencarian
            po_number = ''

            # Jalur 1: purchase_line_id langsung di move (receipt)
            if not po_number and hasattr(move, 'purchase_line_id') and move.purchase_line_id:
                po_order = move.purchase_line_id.order_id
                if po_order:
                    po_number = po_order.name or ''

            # Jalur 2: serial/lot number dari move_line_ids
            # → cari receipt asal lot → purchase_id picking
            if not po_number:
                lot_ids = move.move_line_ids.mapped('lot_id')
                for lot in lot_ids:
                    origin_lines = self.env['stock.move.line'].search([
                        ('lot_id', '=', lot.id),
                        ('state', '=', 'done'),
                        ('picking_id.purchase_id', '!=', False),
                    ], limit=1)
                    if origin_lines:
                        po_order = origin_lines.picking_id.purchase_id
                        po_number = po_order.name or ''
                        break

            # Jalur 3: parsing field origin picking
            if not po_number and picking.origin:
                import re
                match = re.search(r'P[O0]*(\d+)', picking.origin, re.IGNORECASE)
                if match:
                    po_number = match.group(0).upper()

            # Rakit baris
            if po_number:
                line = f"{qty_str} {uom_str} {item_name} - {po_number}"
            else:
                line = f"{qty_str} {uom_str} {item_name}"

            if line.strip():
                lines.append(line)

        return '\n'.join(lines)

    def _get_stock_pickings(self, project):
        """Get stock pickings terkait project via analytic_distribution"""
        analytic_ids = self._get_project_analytic_account_ids(project)
        
        if not analytic_ids:
            return []
        
        pickings_data = []
        
        # Optimasi: Cari picking dengan state done saja
        all_pickings = self.env['stock.picking'].search([
            ('state', '=', 'done'),
            ('picking_type_id.code', 'in', ['incoming', 'outgoing']),
        ], order='date_done asc, id asc')
        
        for picking in all_pickings:
            has_analytic = False
            
            # Check analytic_distribution di picking
            if hasattr(picking, 'analytic_distribution') and picking.analytic_distribution:
                has_analytic = self._check_analytic_distribution(picking.analytic_distribution, analytic_ids)
            
            # Check di stock.move
            if not has_analytic:
                for move in picking.move_ids:
                    if hasattr(move, 'analytic_distribution') and move.analytic_distribution:
                        if self._check_analytic_distribution(move.analytic_distribution, analytic_ids):
                            has_analytic = True
                            break
            
            # Check di stock.move.line
            if not has_analytic:
                for move in picking.move_ids:
                    for move_line in move.move_line_ids:
                        if hasattr(move_line, 'analytic_distribution') and move_line.analytic_distribution:
                            if self._check_analytic_distribution(move_line.analytic_distribution, analytic_ids):
                                has_analytic = True
                                break
                    if has_analytic:
                        break
            
            if has_analytic:
                picking_type = picking.picking_type_id.code if picking.picking_type_id else ''
                
                # Untuk outgoing (Delivery Order)
                if picking_type == 'outgoing':
                    # Check account code 1061 dari stock moves
                    has_account_1061 = False
                    value = 0.0
                    
                    for move in picking.move_ids:
                        if move.account_move_ids:
                            for account_move in move.account_move_ids:
                                for line in account_move.line_ids:
                                    if line.account_id.code == '1061':
                                        has_account_1061 = True
                                        value += abs(line.debit - line.credit)
                    
                    if not has_account_1061:
                        continue
                    
                    # Jika tidak ada value dari account move, hitung dari valuation layer
                    if value == 0.0:
                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('stock_move_id', 'in', picking.move_ids.ids)
                        ])
                        for layer in valuation_layers:
                            value += abs(layer.value)
                    
                    # Jika masih 0, hitung manual
                    if value == 0.0:
                        for move in picking.move_ids:
                            if hasattr(move, 'price_unit'):
                                value += abs(move.product_uom_qty * move.price_unit)
                    
                    note = self._build_picking_note(picking)

                    no_do = ''
                    if hasattr(picking, 'no_do') and picking.no_do:
                        no_do = picking.no_do

                    pickings_data.append({
                        'txno': picking.name or '',
                        'no_do': no_do,
                        'date': picking.date_done or picking.scheduled_date,
                        'subject': picking.partner_id.name if picking.partner_id else '',
                        'value': value,
                        'debet': value,
                        'credit': 0.0,
                        'note': note,
                    })

                # Untuk incoming (Receipt Return saja)
                elif picking_type == 'incoming':
                    # Check jika ini adalah return
                    if not picking.origin or 'Return' not in picking.origin:
                        continue
                    
                    # Check account code 1061 dari stock moves
                    has_account_1061 = False
                    value = 0.0
                    
                    for move in picking.move_ids:
                        if move.account_move_ids:
                            for account_move in move.account_move_ids:
                                for line in account_move.line_ids:
                                    if line.account_id.code == '1061':
                                        has_account_1061 = True
                                        value += abs(line.debit - line.credit)
                    
                    if not has_account_1061:
                        continue
                    
                    # Jika tidak ada value dari account move, hitung dari valuation layer
                    if value == 0.0:
                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('stock_move_id', 'in', picking.move_ids.ids)
                        ])
                        for layer in valuation_layers:
                            value += abs(layer.value)
                    
                    # Jika masih 0, hitung manual
                    if value == 0.0:
                        for move in picking.move_ids:
                            if hasattr(move, 'price_unit'):
                                value += abs(move.product_uom_qty * move.price_unit)
                    
                    note = self._build_picking_note(picking)

                    no_do = ''
                    if hasattr(picking, 'no_do') and picking.no_do:
                        no_do = picking.no_do

                    pickings_data.append({
                        'txno': picking.name or '',
                        'no_do': no_do,
                        'date': picking.date_done or picking.scheduled_date,
                        'subject': picking.partner_id.name if picking.partner_id else '',
                        'value': value,
                        'debet': 0.0,
                        'credit': value,
                        'note': note,
                    })
        
        return pickings_data

    def _create_excel_styles(self):
        """Create reusable Excel styles"""
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        styles = {
            'thin_border': thin_border,
            'label_fill': PatternFill(start_color=self.COLOR_LABEL, end_color=self.COLOR_LABEL, fill_type='solid'),
            'label_font': Font(bold=True, size=self.FONT_SIZE),
            'data_font': Font(size=self.FONT_SIZE),
            'header_fill': PatternFill(start_color=self.COLOR_HEADER, end_color=self.COLOR_HEADER, fill_type='solid'),
            'header_font': Font(bold=True, size=self.FONT_SIZE),
            'total_fill': PatternFill(start_color=self.COLOR_TOTAL, end_color=self.COLOR_TOTAL, fill_type='solid'),
            'total_font': Font(bold=True, size=self.FONT_SIZE),
            'center_align': Alignment(horizontal='center', vertical='center'),
            'right_align': Alignment(horizontal='right', vertical='center'),
            'left_align': Alignment(horizontal='left', vertical='center', wrap_text=True),
        }
        
        return styles

    def _set_column_widths(self, ws):
        """Set column widths for worksheet"""
        for col, width in self.COLUMN_WIDTHS.items():
            ws.column_dimensions[col].width = width

    def _render_header_section(self, ws, project, sale_order, styles):
        """Render header section dengan info project"""
        headers_data = [
            (_('NO PROYEK'), project.name or ''),
            (_('CUSTOMER'), project.partner_id.name if project.partner_id else ''),
            (_('PEKERJAAN'), self._get_pekerjaan(sale_order)),
            (_('NILAI PEKERJAAN'), self._get_nilai_pekerjaan(sale_order)),
            (_('NAMA SALES'), self._get_nama_sales(sale_order)),
        ]

        for row_idx, (label, value) in enumerate(headers_data, start=1):
            ws[f'A{row_idx}'] = label
            ws[f'A{row_idx}'].fill = styles['label_fill']
            ws[f'A{row_idx}'].font = styles['label_font']
            ws[f'A{row_idx}'].border = styles['thin_border']
            
            if label == _('NILAI PEKERJAAN'):
                ws[f'B{row_idx}'] = self._format_number(value) if value else '-'
                ws[f'B{row_idx}'].alignment = styles['right_align']
            else:
                ws[f'B{row_idx}'] = value
            ws[f'B{row_idx}'].border = styles['thin_border']
            ws[f'B{row_idx}'].font = styles['data_font']
            
            for col in ['C', 'D', 'E', 'F', 'G', 'H']:
                ws[f'{col}{row_idx}'].border = styles['thin_border']

    def _render_transaction_section(self, ws, current_row, trans_data, styles, extra_col_header='', extra_col_key=''):
        """Render transaction section (vendor bills atau stock pickings)

        Layout: A(TXNO), B(extra_col), C(DATE), D(SUBJECT), E(VALUE), F(DEBIT), G(CREDIT), H(NOTE)
        """
        trans_headers = [
            _('TXNO'), extra_col_header or '',
            _('DATE'), _('SUBJECT'),
            _('VALUE'), _('DEBIT'), _('CREDIT'), _('NOTE')
        ]
        trans_cols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        # Render headers
        for col, header in zip(trans_cols, trans_headers):
            cell = ws[f'{col}{current_row}']
            cell.value = header
            cell.fill = styles['header_fill']
            cell.font = styles['header_font']
            cell.border = styles['thin_border']
            cell.alignment = styles['center_align']

        current_row += 1

        total_debet = 0.0
        total_credit = 0.0

        # Data rows
        for item in trans_data:
            ws[f'A{current_row}'] = item['txno']
            ws[f'A{current_row}'].border = styles['thin_border']
            ws[f'A{current_row}'].font = styles['data_font']

            ws[f'B{current_row}'] = item.get(extra_col_key, '') if extra_col_key else ''
            ws[f'B{current_row}'].border = styles['thin_border']
            ws[f'B{current_row}'].font = styles['data_font']

            ws[f'C{current_row}'] = self._format_date(item['date'])
            ws[f'C{current_row}'].border = styles['thin_border']
            ws[f'C{current_row}'].font = styles['data_font']
            ws[f'C{current_row}'].alignment = styles['center_align']

            ws[f'D{current_row}'] = item['subject']
            ws[f'D{current_row}'].border = styles['thin_border']
            ws[f'D{current_row}'].font = styles['data_font']

            ws[f'E{current_row}'] = self._format_number(item['value'])
            ws[f'E{current_row}'].border = styles['thin_border']
            ws[f'E{current_row}'].font = styles['data_font']
            ws[f'E{current_row}'].alignment = styles['right_align']

            ws[f'F{current_row}'] = self._format_number(item['debet'])
            ws[f'F{current_row}'].border = styles['thin_border']
            ws[f'F{current_row}'].font = styles['data_font']
            ws[f'F{current_row}'].alignment = styles['right_align']

            ws[f'G{current_row}'] = self._format_number(item['credit'])
            ws[f'G{current_row}'].border = styles['thin_border']
            ws[f'G{current_row}'].font = styles['data_font']
            ws[f'G{current_row}'].alignment = styles['right_align']

            ws[f'H{current_row}'] = item['note']
            ws[f'H{current_row}'].border = styles['thin_border']
            ws[f'H{current_row}'].font = styles['data_font']
            ws[f'H{current_row}'].alignment = styles['left_align']

            total_debet += item['debet']
            total_credit += item['credit']
            current_row += 1

        return current_row, total_debet, total_credit

    def _render_totals_section(self, ws, current_row, total_debet, total_credit, styles):
        """Render totals section — layout A-H (8 kolom)"""
        # Empty row before totals
        current_row += 1

        # Totals row: A-E border, F=total debet, G=total credit, H=border
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws[f'{col}{current_row}'].border = styles['thin_border']

        ws[f'F{current_row}'] = self._format_number(total_debet)
        ws[f'F{current_row}'].fill = styles['total_fill']
        ws[f'F{current_row}'].font = styles['total_font']
        ws[f'F{current_row}'].border = styles['thin_border']
        ws[f'F{current_row}'].alignment = styles['right_align']

        ws[f'G{current_row}'] = self._format_number(total_credit)
        ws[f'G{current_row}'].fill = styles['total_fill']
        ws[f'G{current_row}'].font = styles['total_font']
        ws[f'G{current_row}'].border = styles['thin_border']
        ws[f'G{current_row}'].alignment = styles['right_align']

        ws[f'H{current_row}'].border = styles['thin_border']

        current_row += 2

        # Total cost row: A=label, B-F border, G=total cost, H=border
        ws[f'A{current_row}'] = _('TOTAL COST')
        ws[f'A{current_row}'].fill = styles['label_fill']
        ws[f'A{current_row}'].font = styles['label_font']
        ws[f'A{current_row}'].border = styles['thin_border']

        for col in ['B', 'C', 'D', 'E', 'F']:
            ws[f'{col}{current_row}'].border = styles['thin_border']

        total_cost = total_debet - total_credit
        ws[f'G{current_row}'] = self._format_number(total_cost)
        ws[f'G{current_row}'].fill = styles['total_fill']
        ws[f'G{current_row}'].font = styles['total_font']
        ws[f'G{current_row}'].border = styles['thin_border']
        ws[f'G{current_row}'].alignment = styles['right_align']

        ws[f'H{current_row}'].border = styles['thin_border']

    def action_export_excel(self):
        """Main export action dengan error handling"""
        self.ensure_one()
        
        # Validasi project
        if not self.project_id:
            raise UserError(_("Please select a project first."))
        
        project = self.project_id
        
        # Validasi analytic account
        analytic_ids = self._get_project_analytic_account_ids(project)
        if not analytic_ids:
            raise UserError(_(
                "Project '%s' does not have an Analytic Account.\n"
                "Unable to track project costs. Please configure the analytic account first."
            ) % project.name)
        
        try:
            # Get related data
            sale_order = self._get_sale_order(project)
            vendor_bills = self._get_vendor_bills(project)
            stock_pickings = self._get_stock_pickings(project)

            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = _("Project Cost Report")

            # Create styles
            styles = self._create_excel_styles()

            # Set column widths
            self._set_column_widths(ws)

            # Render header section
            self._render_header_section(ws, project, sale_order, styles)

            # Starting row for transactions
            current_row = 8

            # Render vendor bills section
            current_row, vendor_debet, vendor_credit = self._render_transaction_section(
                ws, current_row, vendor_bills, styles,
                extra_col_header=_('INVOICE MANUAL'),
                extra_col_key='invoice_no',
            )

            # Render stock pickings section
            current_row, stock_debet, stock_credit = self._render_transaction_section(
                ws, current_row, stock_pickings, styles,
                extra_col_header=_('DO MANUAL'),
                extra_col_key='no_do',
            )

            # Calculate total
            total_debet = vendor_debet + stock_debet
            total_credit = vendor_credit + stock_credit

            # Render totals section
            self._render_totals_section(ws, current_row, total_debet, total_credit, styles)

            # Save to buffer
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            # Encode to base64
            file_data = base64.b64encode(output.read())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"Project_Cost_{project.name}_{timestamp}.xlsx"

            self.write({
                'file_data': file_data,
                'file_name': file_name,
                'state': 'done'
            })

            return {
                'name': _('Export Excel'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.cost.export.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(_('Error during export: %s') % str(e))