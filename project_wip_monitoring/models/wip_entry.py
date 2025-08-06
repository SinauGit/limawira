from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_wip_hanging = fields.Boolean(
        string='WIP Hanging',
        compute='_compute_is_wip_hanging', 
        store=True,
        help="Indicates if this line is a hanging WIP entry"
    )

    @api.depends('account_id', 'account_id.account_type', 'account_id.code', 'debit', 'credit', 'balance')
    def _compute_is_wip_hanging(self):
        """Compute if the line is a hanging WIP entry"""
        for line in self:
            is_wip = False
            if line.account_id:
                # Check if account is current asset and contains 'wip' in code
                is_wip = (
                    line.account_id.account_type == 'asset_current' and
                    line.account_id.code and
                    'wip' in line.account_id.code.lower()
                )
            line.is_wip_hanging = is_wip and line.debit > 0 and line.balance > 0

    def action_transfer_to_cogs(self):
        """Transfer WIP entries to COGS account"""
        if not self:
            raise UserError(_("No records selected for transfer."))
        
        # Validate that all selected records are WIP hanging
        non_wip_lines = self.filtered(lambda l: not l.is_wip_hanging)
        if non_wip_lines:
            raise UserError(_("Some selected entries are not hanging WIP entries."))
        
        # Search for COGS account - improved search
        cogs_account = self.env['account.account'].search([
            '|',
            ('name', 'ilike', 'WIP Prospect Awan'),
            ('code', 'ilike', 'cogs'),
        ], limit=1)
        
        if not cogs_account:
            raise UserError(_("COGS account not found. Please create a COGS account first."))

        # Group lines by company to create separate moves per company
        lines_by_company = {}
        for line in self:
            company_id = line.company_id.id
            if company_id not in lines_by_company:
                lines_by_company[company_id] = self.env['account.move.line']
            lines_by_company[company_id] |= line

        created_moves = self.env['account.move']
        
        for company_id, company_lines in lines_by_company.items():
            move_vals = {
                'move_type': 'entry',
                'date': fields.Date.today(),
                'ref': _('Transfer WIP to COGS'),
                'company_id': company_id,
                'line_ids': []
            }
            
            for line in company_lines:
                if line.balance <= 0:
                    continue
                    
                # Debit COGS account
                move_vals['line_ids'].append((0, 0, {
                    'account_id': cogs_account.id,
                    'name': _('Transfer from %s', line.account_id.name),
                    'debit': line.balance,
                    'credit': 0,
                    'analytic_distribution': line.analytic_distribution,
                    'partner_id': line.partner_id.id if line.partner_id else False,
                }))
                
                # Credit WIP account
                move_vals['line_ids'].append((0, 0, {
                    'account_id': line.account_id.id,
                    'name': _('Transfer WIP to COGS - %s', 
                             line.analytic_distribution and 
                             list(line.analytic_distribution.keys())[0] if line.analytic_distribution else 'N/A'),
                    'debit': 0,
                    'credit': line.balance,
                    'analytic_distribution': line.analytic_distribution,
                    'partner_id': line.partner_id.id if line.partner_id else False,
                }))
            
            if move_vals['line_ids']:
                try:
                    move = self.env['account.move'].create(move_vals)
                    move.action_post()  # Auto post the journal entry
                    created_moves |= move
                    _logger.info(f"Created and posted WIP transfer move: {move.name}")
                except Exception as e:
                    _logger.error(f"Error creating WIP transfer move: {str(e)}")
                    raise UserError(_("Error creating journal entry: %s", str(e)))
        
        if created_moves:
            # Return action to show created moves
            return {
                'type': 'ir.actions.act_window',
                'name': _('Created Journal Entries'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_moves.ids)],
                'context': {'create': False},
            }
        else:
            raise UserError(_("No valid WIP entries found to transfer."))