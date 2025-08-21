from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
import io, base64
import xlsxwriter

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        """Override web_read_group to filter out groups with zero total amount"""
        
        context = self.env.context
        if context.get('filter_zero_amount_projects') and groupby and 'account_id' in groupby[0]:
            # Get the grouped data first
            result = super().web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)
            
            # Filter out groups where amount sum is 0
            if isinstance(result, dict) and 'groups' in result:
                filtered_groups = [
                    group for group in result['groups'] 
                    if group.get('amount', 0) != 0
                ]
                result['groups'] = filtered_groups
                result['length'] = len(filtered_groups)
            elif isinstance(result, list):
                # If result is a list of groups directly
                result = [
                    group for group in result 
                    if group.get('amount', 0) != 0
                ]
            
            return result
        
        return super().web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter out individual records from zero-total projects when grouped"""
        
        context = self.env.context
        if context.get('filter_zero_amount_projects') and context.get('group_by') == ['account_id']:
            if domain is None:
                domain = []
            
            # First, get all project totals
            all_records = self.search_read(
                [d for d in domain if d[0] != 'account_id'], 
                ['account_id', 'amount'], 
                0, None, None
            )
            
            # Calculate project totals
            project_totals = {}
            for record in all_records:
                account_id = record['account_id'][0] if record['account_id'] else False
                if account_id:
                    if account_id not in project_totals:
                        project_totals[account_id] = 0
                    project_totals[account_id] += record['amount']
            
            # Get projects with non-zero totals
            non_zero_projects = [
                project_id for project_id, total in project_totals.items() 
                if total != 0
            ]
            
            # Add filter for non-zero projects
            if non_zero_projects:
                domain = [d for d in domain if d[0] != 'account_id']  # Remove existing account_id filters
                domain.append(('account_id', 'in', non_zero_projects))
            else:
                # No projects with non-zero amounts, return empty
                domain.append(('id', 'in', []))
        
        return super().search_read(domain, fields, offset, limit, order)

    @api.model
    def _wip_export_domain(self):
        """Gabungkan domain aktif di UI + jaga filter akun WIP 1061 seperti di action"""
        active_domain = self.env.context.get('active_domain') or []
        base_domain = [('general_account_id.code', '=', '1061')]
        return expression.AND([active_domain, base_domain]) if active_domain else base_domain

    def action_export_wip_by_project_xlsx(self):
        """Export XLSX: Project (account_id) & Total Amount (sum)."""
        from odoo.osv import expression
        import io, base64, xlsxwriter
        _ = self.env._

        # domain: jika user select baris → pakai ids; kalau tidak → pakai active_domain + filter WIP (kode 1061)
        active_domain = self.env.context.get('active_domain') or []
        base_domain = [('general_account_id.code', '=', '1061')]
        domain = [('id', 'in', self.ids)] if self.ids else (expression.AND([active_domain, base_domain]) if active_domain else base_domain)

        # agregasi per project
        groups = self.env['account.analytic.line'].read_group(
            domain, ['amount:sum'], ['account_id'], lazy=False
        )

        # build xlsx in-memory
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('WIP by Project')
        fmt_hdr = wb.add_format({'bold': True})
        fmt_money = wb.add_format({'num_format': '#,##0.00'})

        ws.write(0, 0, 'Project', fmt_hdr)
        ws.write(0, 1, 'Total Amount', fmt_hdr)

        row, grand = 1, 0.0
        for g in groups:
            proj = g['account_id'][1] if g.get('account_id') else '(Tanpa Project)'
            amt = g.get('amount', 0.0)
            ws.write(row, 0, proj)
            ws.write_number(row, 1, amt, fmt_money)
            grand += amt
            row += 1

        ws.write(row, 0, 'Grand Total', fmt_hdr)
        ws.write_number(row, 1, grand, fmt_money)
        ws.set_column(0, 0, 45)
        ws.set_column(1, 1, 18)
        wb.close()

        data_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        # ← FIX: res_id harus INT (bukan list). Gunakan id pertama atau 0.
        res_id_int = self.ids[0] if self.ids else 0

        att = self.env['ir.attachment'].create({
            'name': 'wip_by_project.xlsx',
            'type': 'binary',
            'datas': data_b64,
            'res_model': 'account.analytic.line',
            'res_id': res_id_int,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{att.id}?download=true',
            'target': 'self',
        }
