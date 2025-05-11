from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # One-to-many relationship with vendor PICs
    pic_ids = fields.One2many(
        'vendor.pic',
        'partner_id',
        string='Persons in Charge',
        help="List of persons in charge for this vendor"
    )
    
    pic_count = fields.Integer(
        string='PIC Count', 
        compute='_compute_pic_count',
        store=True,
        help="Number of PICs assigned to this vendor"
    )
    
    primary_pic_id = fields.Many2one(
        'vendor.pic',
        string='Primary PIC',
        compute='_compute_primary_pic',
        store=True,
        help="The primary person in charge for this vendor"
    )
    
    primary_pic_name = fields.Char(
        related='primary_pic_id.name',
        string='Primary PIC Name',
        store=True,
        readonly=True
    )
    
    primary_pic_phone = fields.Char(
        related='primary_pic_id.phone',
        string='Primary PIC Phone',
        store=True,
        readonly=True
    )
    
    primary_pic_email = fields.Char(
        related='primary_pic_id.email',
        string='Primary PIC Email',
        store=True,
        readonly=True
    )
    
    @api.depends('pic_ids')
    def _compute_pic_count(self):
        for partner in self:
            partner.pic_count = len(partner.pic_ids)
    
    @api.depends('pic_ids', 'pic_ids.is_primary')
    def _compute_primary_pic(self):
        for partner in self:
            primary_pics = partner.pic_ids.filtered(lambda p: p.is_primary)
            partner.primary_pic_id = primary_pics[0] if primary_pics else False
    
    def action_view_pics(self):
        self.ensure_one()
        return {
            'name': 'Persons in Charge',
            'view_mode': 'tree,form',
            'res_model': 'vendor.pic',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'type': 'ir.actions.act_window',
        }