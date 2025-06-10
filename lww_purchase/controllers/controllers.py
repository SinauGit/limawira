# -*- coding: utf-8 -*-
# from odoo import http


# class LwwPurchase(http.Controller):
#     @http.route('/lww_purchase/lww_purchase', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lww_purchase/lww_purchase/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('lww_purchase.listing', {
#             'root': '/lww_purchase/lww_purchase',
#             'objects': http.request.env['lww_purchase.lww_purchase'].search([]),
#         })

#     @http.route('/lww_purchase/lww_purchase/objects/<model("lww_purchase.lww_purchase"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lww_purchase.object', {
#             'object': obj
#         })

