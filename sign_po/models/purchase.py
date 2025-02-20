# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from datetime import timedelta

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    signed_by = fields.Char(
        string="Signed By",  required=True, copy=False)

    signed_on = fields.Datetime(
        string="Signed On", required=True, copy=False)

    signature = fields.Image(
        string="Signature",
        copy=False, required=True, attachment=True, max_width=1024, max_height=1024)

    signed_by2 = fields.Char(
        string="Signed By",  required=True, copy=False)

    signed_on2 = fields.Datetime(
        string="Signed On", required=True, copy=False)

    signature2 = fields.Image(
        string="Signature",
        copy=False, required=True, attachment=True, max_width=1024, max_height=1024)

