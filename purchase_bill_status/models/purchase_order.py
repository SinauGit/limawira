# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    payment_status = fields.Selection([
        ('no_bill', 'No Bill'),
        ('not_paid', 'Not Paid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Status Pembayaran', compute='_compute_payment_status', store=True, default='no_bill')
    
    bill_count = fields.Integer(string='Jumlah Bill', compute='_compute_bill_count', store=True)
    bill_total = fields.Monetary(string='Total Bill', compute='_compute_bill_amounts', store=True)
    bill_paid = fields.Monetary(string='Jumlah Terbayar', compute='_compute_bill_amounts', store=True)
    bill_unpaid = fields.Monetary(string='Sisa Pembayaran', compute='_compute_bill_amounts', store=True)
    
    @api.depends('invoice_ids', 'invoice_ids.payment_state')
    def _compute_bill_count(self):
        for order in self:
            order.bill_count = len(order.invoice_ids.filtered(lambda inv: inv.move_type == 'in_invoice'))
    
    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_bill_amounts(self):
        for order in self:
            bills = order.invoice_ids.filtered(lambda inv: inv.move_type == 'in_invoice')
            order.bill_total = sum(bills.mapped('amount_total'))
            order.bill_unpaid = sum(bills.mapped('amount_residual'))
            order.bill_paid = order.bill_total - order.bill_unpaid
    
    @api.depends('bill_count', 'bill_total', 'bill_paid', 'invoice_ids.payment_state')
    def _compute_payment_status(self):
        for order in self:
            if not order.invoice_ids or order.bill_count == 0:
                order.payment_status = 'no_bill'
            elif order.bill_unpaid <= 0:
                order.payment_status = 'paid'
            elif order.bill_paid > 0 and order.bill_unpaid > 0:
                order.payment_status = 'partially_paid'
            else:
                order.payment_status = 'not_paid'
    
    def action_view_invoice(self, invoices=False):
        """Override untuk mengelompokkan bill berdasarkan status pembayaran"""
        result = super(PurchaseOrder, self).action_view_invoice(invoices)
        return result