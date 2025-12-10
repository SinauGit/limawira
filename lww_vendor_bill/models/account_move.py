                                                       
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.tools.misc import formatLang, format_date
                                           


class AccountMove(models.Model):
    _inherit = "account.move"

                                                                                 
    def action_post(self):
\
\
\
           
        to_autodate = self.filtered(lambda m: m.move_type == "in_invoice" and not m.invoice_date)
        if to_autodate:
            today = fields.Date.context_today(self)
            for move in to_autodate:
                move.invoice_date = today
        return super().action_post()

                                                                              
    def _post(self, soft=True):
\
\
\
\
           

                                                             
                                                                                              
                                                                                          

                                                                              
        self = self.with_context(skip_is_manually_modified=True)                 

        validation_msgs = set()

                                                        
        for invoice in self.filtered(lambda move: move.is_invoice(include_receipts=True)):
            if (
                invoice.quick_edit_mode
                and invoice.quick_edit_total_amount
                and invoice.currency_id.compare_amounts(invoice.quick_edit_total_amount, invoice.amount_total) != 0
            ):
                validation_msgs.add(_(
                    "The current total is %(current_total)s but the expected total is %(expected_total)s. In order to post the invoice/bill, "
                    "you can adjust its lines or the expected Total (tax inc.).",
                    current_total=formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    expected_total=formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                validation_msgs.add(_(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                ))
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                validation_msgs.add(_(
                    "You cannot validate an invoice with a negative total amount. "
                    "You should create a credit note instead. "
                    "Use the action menu to transform it into a credit note or refund."
                ))

            if not invoice.partner_id:
                if invoice.is_sale_document():
                    validation_msgs.add(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif invoice.is_purchase_document():
                    validation_msgs.add(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

                                          
                                                                
                                                                                                
            if not invoice.invoice_date:
                if invoice.is_sale_document(include_receipts=True):
                    invoice.invoice_date = fields.Date.context_today(self)
                elif invoice.is_purchase_document(include_receipts=True):
                                                                          
                                                                  
                    invoice.invoice_date = fields.Date.context_today(self)

                                                  
        for move in self:
            if move.state in ['posted', 'cancel']:
                validation_msgs.add(_('The entry %(name)s (id %(id)s) must be in draft.', name=move.name, id=move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                validation_msgs.add(_('You need to add a line before posting.'))
            if not soft and move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                validation_msgs.add(_("This move is configured to be auto-posted on %(date)s", date=date_msg))
            if not move.journal_id.active:
                validation_msgs.add(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))
            if move.display_inactive_currency_warning:
                validation_msgs.add(_(
                    "You cannot validate a document with an inactive currency: %s",
                    move.currency_id.name
                ))
            if move.line_ids.account_id.filtered(lambda account: account.deprecated) and not self._context.get('skip_account_deprecation_check'):
                validation_msgs.add(_("A line of this move is using a deprecated account, you cannot post it."))

                                     
            move.checked = move.journal_id.autocheck_on_post

                                      
                                                                            
                                                                                  
                             
                                                                 
                                  

                                       
        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            for move in future_moves:
                if move.auto_post == 'no':
                    move.auto_post = 'at_date'
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        for move in to_post:
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report, lock_dates=lock_dates)

                                        
        to_post.line_ids._create_analytic_lines()

                                                
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        for invoice in to_post:
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(lambda aml:
                aml.partner_id != invoice.commercial_partner_id
                and aml.display_type not in ('line_note', 'line_section')
            )
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

                                                                        
        draft_reverse_moves = to_post.filtered(lambda move: move.reversed_entry_id and move.reversed_entry_id.state == 'posted')

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        draft_reverse_moves.reversed_entry_id._reconcile_reversed_moves(draft_reverse_moves, self._context.get('move_reverse_cancel', False))
        to_post.line_ids._reconcile_marked()

        for invoice in to_post:
            partner_id = invoice.partner_id
            subscribers = [partner_id.id] if partner_id and partner_id not in invoice.sudo().message_partner_ids else None
            invoice.message_subscribe(subscribers)

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in to_post:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
            elif invoice.move_type == 'entry':
                sale_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'asset_receivable')
                for partner in sale_amls.mapped('partner_id'):
                    customer_count[partner] += 1
                purchase_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'liability_payable')
                for partner in purchase_amls.mapped('partner_id'):
                    supplier_count[partner] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

                                                            
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        return to_post
