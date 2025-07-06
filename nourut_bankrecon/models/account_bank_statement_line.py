from odoo import models, fields, api

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    
    narration = fields.Char(
        string='Notes',
        help='Additional notes for bank statement line'
    )