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
        months = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
            7: 'Jul', 8: 'Agust', 9: 'Sep', 10: 'Okt', 11: 'Nop', 12: 'Des'
        }
        if isinstance(date_value, str):
            date_value = fields.Date.from_string(date_value)
        if hasattr(date_value, 'date'):
            date_value = date_value.date()
        day = date_value.day
        month = months.get(date_value.month, '')
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
        """Get nama product dari sale order line, gabung dengan ' - ' jika lebih dari 1"""
        if not sale_order or not sale_order.order_line:
            return ''
        
        products = []
        for line in sale_order.order_line:
            if line.product_id:
                if hasattr(line, 'display_type') and line.display_type in ('line_section', 'line_note'):
                    continue
                product_name = line.product_id.name
                if product_name and product_name not in products:
                    products.append(product_name)
        
        return ' - '.join(products) if products else ''

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

    def _get_vendor_bill_payments(self, project):
        """Get vendor bill payments terkait project via analytic_distribution di Vendor Bill"""
        analytic_ids = self._get_project_analytic_account_ids(project)
        
        if not analytic_ids:
            return []
        
        payments_data = []
        processed_payment_ids = set()
        
        # Step 1: Cari Vendor Bills (account.move) yang memiliki analytic_distribution sesuai project
        vendor_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
        ], order='invoice_date asc, id asc')
        
        for bill in vendor_bills:
            has_analytic = False
            
            # Check analytic_distribution di invoice lines
            for line in bill.invoice_line_ids:
                if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                    if self._check_analytic_distribution(line.analytic_distribution, analytic_ids):
                        has_analytic = True
                        break
            
            # Jika tidak ada di invoice lines, cek di semua journal items
            if not has_analytic:
                for line in bill.line_ids:
                    if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                        if self._check_analytic_distribution(line.analytic_distribution, analytic_ids):
                            has_analytic = True
                            break
            
            if has_analytic:
                # Step 2: Cari Payment yang terkait dengan Vendor Bill ini
                # Cara 1: Via reconciled_bill_ids di payment
                related_payments = self.env['account.payment'].search([
                    ('state', '=', 'posted'),
                    ('reconciled_bill_ids', 'in', [bill.id]),
                ])
                
                # Cara 2: Jika tidak ketemu, cari via move line reconciliation
                if not related_payments:
                    for line in bill.line_ids.filtered(lambda l: l.account_id.account_type in ('liability_payable', 'asset_receivable')):
                        if line.matched_credit_ids:
                            for partial in line.matched_credit_ids:
                                if partial.credit_move_id.move_id.payment_id:
                                    related_payments |= partial.credit_move_id.move_id.payment_id
                        if line.matched_debit_ids:
                            for partial in line.matched_debit_ids:
                                if partial.debit_move_id.move_id.payment_id:
                                    related_payments |= partial.debit_move_id.move_id.payment_id
                
                # Tambahkan payment ke hasil
                for payment in related_payments:
                    if payment.id not in processed_payment_ids:
                        processed_payment_ids.add(payment.id)
                        
                        note = ''
                        if hasattr(payment, 'narration') and payment.narration:
                            note = html2plaintext(payment.narration) if '<' in str(payment.narration) else payment.narration
                        elif hasattr(payment, 'ref') and payment.ref:
                            note = payment.ref
                        
                        payments_data.append({
                            'txno': payment.name or '',
                            'date': payment.date,
                            'subject': payment.partner_id.name if payment.partner_id else '',
                            'value': payment.amount or 0.0,
                            'debet': payment.amount or 0.0,
                            'credit': 0.0,
                            'note': note,
                        })
        
        # Sort by date
        payments_data.sort(key=lambda x: x['date'] if x['date'] else fields.Date.today())
        
        return payments_data

    def _get_stock_pickings(self, project):
        """Get stock pickings terkait project via analytic_distribution"""
        analytic_ids = self._get_project_analytic_account_ids(project)
        
        if not analytic_ids:
            return []
        
        pickings_data = []
        
        # Cari semua picking dengan state done
        all_pickings = self.env['stock.picking'].search([
            ('state', '=', 'done'),
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
                # Get value dari stock.valuation.layer
                value = 0.0
                valuation_layers = self.env['stock.valuation.layer'].search([
                    ('stock_move_id', 'in', picking.move_ids.ids)
                ])
                for layer in valuation_layers:
                    value += abs(layer.value)
                
                # Jika tidak ada di valuation layer, hitung manual
                if value == 0.0:
                    for move in picking.move_ids:
                        if hasattr(move, 'price_unit'):
                            value += abs(move.product_uom_qty * move.price_unit)
                
                # Determine debet/credit based on picking type
                picking_type = picking.picking_type_id.code if picking.picking_type_id else ''
                debet = 0.0
                credit = 0.0
                
                if picking_type == 'incoming':  # Receipt
                    debet = value
                elif picking_type == 'outgoing':  # Delivery
                    credit = value
                else:
                    # Default: check location
                    if picking.location_dest_id.usage == 'customer':
                        credit = value
                    else:
                        debet = value
                
                note = ''
                if hasattr(picking, 'note') and picking.note:
                    note = html2plaintext(picking.note) if '<' in str(picking.note) else picking.note
                
                pickings_data.append({
                    'txno': picking.name or '',
                    'date': picking.date_done or picking.scheduled_date,
                    'subject': picking.partner_id.name if picking.partner_id else '',
                    'value': value,
                    'debet': debet,
                    'credit': credit,
                    'note': note,
                })
        
        return pickings_data

    def action_export_excel(self):
        self.ensure_one()
        project = self.project_id

        if not project:
            raise UserError(_("Pilih project terlebih dahulu."))

        # Get related data
        sale_order = self._get_sale_order(project)
        vendor_payments = self._get_vendor_bill_payments(project)
        stock_pickings = self._get_stock_pickings(project)

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Project Cost Report"

        # Define styles
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        label_fill = PatternFill(start_color='B4C6E7', end_color='B4C6E7', fill_type='solid')
        label_font = Font(bold=True, size=10)
        data_font = Font(size=10)
        
        header_fill = PatternFill(start_color='8EA9DB', end_color='8EA9DB', fill_type='solid')
        header_font = Font(bold=True, size=10)
        
        total_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
        total_font = Font(bold=True, size=10)

        center_align = Alignment(horizontal='center', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)

        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 28
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 60

        # ===== HEADER SECTION =====
        headers_data = [
            ('NO PROYEK', project.name or ''),
            ('CUSTOMER', project.partner_id.name if project.partner_id else ''),
            ('PEKERJAAN', self._get_pekerjaan(sale_order)),
            ('NILAI PEKERJAAN', self._get_nilai_pekerjaan(sale_order)),
            ('NAMA SALES', self._get_nama_sales(sale_order)),
        ]

        for row_idx, (label, value) in enumerate(headers_data, start=1):
            ws[f'A{row_idx}'] = label
            ws[f'A{row_idx}'].fill = label_fill
            ws[f'A{row_idx}'].font = label_font
            ws[f'A{row_idx}'].border = thin_border
            
            if label == 'NILAI PEKERJAAN':
                ws[f'B{row_idx}'] = self._format_number(value) if value else '-'
                ws[f'B{row_idx}'].alignment = right_align
            else:
                ws[f'B{row_idx}'] = value
            ws[f'B{row_idx}'].border = thin_border
            ws[f'B{row_idx}'].font = data_font
            
            for col in ['C', 'D', 'E', 'F', 'G']:
                ws[f'{col}{row_idx}'].border = thin_border

        # Empty rows
        current_row = 8

        # ===== SECTION 1: VENDOR BILL PAYMENTS =====
        trans_headers = ['TXNO', 'DATE', 'SUBJECT', 'VALUE', 'DEBET', 'CREDIT', 'NOTE']
        trans_cols = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        for col, header in zip(trans_cols, trans_headers):
            cell = ws[f'{col}{current_row}']
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = center_align
        
        current_row += 1

        total_debet = 0.0
        total_credit = 0.0

        # Data rows untuk vendor payments
        for payment in vendor_payments:
            ws[f'A{current_row}'] = payment['txno']
            ws[f'A{current_row}'].border = thin_border
            ws[f'A{current_row}'].font = data_font
            
            ws[f'B{current_row}'] = self._format_date(payment['date'])
            ws[f'B{current_row}'].border = thin_border
            ws[f'B{current_row}'].font = data_font
            ws[f'B{current_row}'].alignment = center_align
            
            ws[f'C{current_row}'] = payment['subject']
            ws[f'C{current_row}'].border = thin_border
            ws[f'C{current_row}'].font = data_font
            
            ws[f'D{current_row}'] = self._format_number(payment['value'])
            ws[f'D{current_row}'].border = thin_border
            ws[f'D{current_row}'].font = data_font
            ws[f'D{current_row}'].alignment = right_align
            
            ws[f'E{current_row}'] = self._format_number(payment['debet'])
            ws[f'E{current_row}'].border = thin_border
            ws[f'E{current_row}'].font = data_font
            ws[f'E{current_row}'].alignment = right_align
            
            ws[f'F{current_row}'] = self._format_number(payment['credit'])
            ws[f'F{current_row}'].border = thin_border
            ws[f'F{current_row}'].font = data_font
            ws[f'F{current_row}'].alignment = right_align
            
            ws[f'G{current_row}'] = payment['note']
            ws[f'G{current_row}'].border = thin_border
            ws[f'G{current_row}'].font = data_font
            ws[f'G{current_row}'].alignment = left_align
            
            total_debet += payment['debet']
            total_credit += payment['credit']
            current_row += 1

        # ===== SECTION 2: STOCK PICKINGS =====
        for col, header in zip(trans_cols, trans_headers):
            cell = ws[f'{col}{current_row}']
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = center_align
        
        current_row += 1

        # Data rows untuk stock pickings
        for picking in stock_pickings:
            ws[f'A{current_row}'] = picking['txno']
            ws[f'A{current_row}'].border = thin_border
            ws[f'A{current_row}'].font = data_font
            
            ws[f'B{current_row}'] = self._format_date(picking['date'])
            ws[f'B{current_row}'].border = thin_border
            ws[f'B{current_row}'].font = data_font
            ws[f'B{current_row}'].alignment = center_align
            
            ws[f'C{current_row}'] = picking['subject']
            ws[f'C{current_row}'].border = thin_border
            ws[f'C{current_row}'].font = data_font
            
            ws[f'D{current_row}'] = self._format_number(picking['value'])
            ws[f'D{current_row}'].border = thin_border
            ws[f'D{current_row}'].font = data_font
            ws[f'D{current_row}'].alignment = right_align
            
            ws[f'E{current_row}'] = self._format_number(picking['debet'])
            ws[f'E{current_row}'].border = thin_border
            ws[f'E{current_row}'].font = data_font
            ws[f'E{current_row}'].alignment = right_align
            
            ws[f'F{current_row}'] = self._format_number(picking['credit'])
            ws[f'F{current_row}'].border = thin_border
            ws[f'F{current_row}'].font = data_font
            ws[f'F{current_row}'].alignment = right_align
            
            ws[f'G{current_row}'] = picking['note']
            ws[f'G{current_row}'].border = thin_border
            ws[f'G{current_row}'].font = data_font
            ws[f'G{current_row}'].alignment = left_align
            
            total_debet += picking['debet']
            total_credit += picking['credit']
            current_row += 1

        # Empty row
        current_row += 1

        # ===== TOTALS ROW =====
        for col in trans_cols[:4]:
            ws[f'{col}{current_row}'].border = thin_border
        
        ws[f'E{current_row}'] = self._format_number(total_debet)
        ws[f'E{current_row}'].fill = total_fill
        ws[f'E{current_row}'].font = total_font
        ws[f'E{current_row}'].border = thin_border
        ws[f'E{current_row}'].alignment = right_align
        
        ws[f'F{current_row}'] = self._format_number(total_credit)
        ws[f'F{current_row}'].fill = total_fill
        ws[f'F{current_row}'].font = total_font
        ws[f'F{current_row}'].border = thin_border
        ws[f'F{current_row}'].alignment = right_align
        
        ws[f'G{current_row}'].border = thin_border

        current_row += 2

        # ===== TOTAL COST ROW =====
        ws[f'A{current_row}'] = 'TOTAL COST'
        ws[f'A{current_row}'].fill = label_fill
        ws[f'A{current_row}'].font = label_font
        ws[f'A{current_row}'].border = thin_border
        
        for col in ['B', 'C', 'D', 'E']:
            ws[f'{col}{current_row}'].border = thin_border
        
        total_cost = total_debet - total_credit
        ws[f'F{current_row}'] = self._format_number(total_cost)
        ws[f'F{current_row}'].fill = total_fill
        ws[f'F{current_row}'].font = total_font
        ws[f'F{current_row}'].border = thin_border
        ws[f'F{current_row}'].alignment = right_align
        
        ws[f'G{current_row}'].border = thin_border

        # Save to buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # Encode to base64
        file_data = base64.b64encode(output.read())
        file_name = f"Project_Cost_{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        self.write({
            'file_data': file_data,
            'file_name': file_name,
            'state': 'done'
        })

        return {
            'name': 'Export Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'project.cost.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
