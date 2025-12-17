# -*- coding: utf-8 -*-

import json
import jwt
import pytz

from odoo import http, fields

from odoo.http import request, Response
from odoo.addons.web.controllers import main

class IsyCardAPI(http.Controller):

    def _get_response(self, status, data=None):
        if data is None:
            data = {}
        return Response(
            json.dumps(data),
            status=status,
            mimetype='application/json'
        )

    def _authenticate(self):
        encoded_jwt = request.httprequest.headers.get('Api-Key') or False
        #decode username and password dict
        try:
            credential_dict = jwt.decode(encoded_jwt, '3498CA36F63D31C8C5311BB657C8B', algorithms=['HS256'])
            username = credential_dict['username']
            password = credential_dict['password']
            database = request.env['ir.config_parameter'].sudo().get_param('database.db_name') or False
            if database == False:
                return self._get_response(401, {
                    "error": "Unauthorized. Please contact to system administrator to define default database."
                })

            result = main.Session.authenticate(self, database, username, password)
            if not result.get('uid'):
                return self._get_response(401, {
                    "error": "Unauthorized Api Token."
                })
        except Exception as e:
            return self._get_response(401, {
                "error": "Unauthorized Api Token."
            })

    def check_number(self, amount):
        try:
            # Try converting to float
            float(amount)
            return True
        except (ValueError, TypeError):
            # Not a number
            return False

    def convert_timezone(self, date):
        yangon = pytz.timezone('Asia/Yangon')
        utc_dt = fields.Datetime.from_string(date)
        return utc_dt.replace(tzinfo=pytz.utc).astimezone(yangon)

    def date_to_string(self, date):
        return fields.Datetime.to_string(self.convert_timezone(date))

    @http.route('/api/v1/card_balance', type='http', auth='none', methods=['GET'], csrf=False)
    def card_balance(self, **kw):
        # Check API key
        error = self._authenticate()
        if error:
            return error

        barcode = kw.get("barcode")

        # Validate input
        if not barcode:
            return self._get_response(400, {
                "error": "Invalid input."
            })

        # Check partner related to barcode
        partner = request.env['res.partner'].sudo().search([('card_barcode', '=', barcode)], limit=1)

        if not partner:
            return self._get_response(404, {
                "error": "Barcode not found."
            })

        return self._get_response(200, {
            "barcode": barcode,
            "balance": partner.card_balance
        })

    @http.route('/api/v1/recharge', type='http', auth='none', methods=['PUT'], csrf=False)
    def recharge_balance(self, **kw):
        # Check API key
        error = self._authenticate()
        if error:
            return error

        barcode = kw.get("barcode")
        amount = kw.get("amount")

        # Validate input
        if not barcode or not self.check_number(amount):
            return self._get_response(400, {
                "error": "Missing or invalid parameters."
            })

        # Check partner related to barcode
        partner = request.env['res.partner'].sudo().search([('card_barcode', '=', barcode)], limit=1)

        if not partner:
            return self._get_response(404, {
                "error": "Partner not found."
            })

        # Add the amount to the existing balance
        old_balance = partner.card_balance or 0
        new_balance = float(old_balance) + float(amount)
        partner.sudo().write({"card_balance": new_balance})

        # Add the recharge history
        request.env['isy.card.recharge.history'].sudo().create({
            'partner_id': partner.id,
            'amount': amount
        })

        return self._get_response(200, {
            "barcode": barcode,
            "old_balance": float(old_balance),
            "recharged_amount": float(amount),
            "new_balance": float(new_balance)
        })

    @http.route('/api/v1/recharge_history', type='http', auth='none', methods=['GET'], csrf=False)
    def recharge_history(self, **kw):
        # Check API key
        error = self._authenticate()
        if error:
            return error

        barcode = kw.get("barcode")

        # Validate input
        if not barcode:
            return Response(json.dumps({"error": "invalid_input"}), status=400, mimetype='application/json')

        # Check partner related to barcode
        partner = request.env['res.partner'].sudo().search([('card_barcode', '=', barcode)], limit=1)

        if not partner:
            return self._get_response(404, {
                "error": "Barcode not found."
            })

        # Get all recharge history
        history_list = []
        for history in request.env['isy.card.recharge.history'].sudo().search([('barcode', '=', barcode)]):
            history_list.append({
                'name': history.name,
                'student_number': history.student_number,
                'barcode': history.barcode,
                'amount': history.amount,
                'date': self.date_to_string(history.date)
            })
        
        return self._get_response(200, history_list)

    @http.route('/api/v1/invoice_list', type='http', auth='none', methods=['GET'], csrf=False)
    def invoice_list(self, **kw):
        # Check API key
        error = self._authenticate()
        if error:
            return error

        barcode = kw.get("barcode")

        # Validate input
        if not barcode:
            return Response(json.dumps({"error": "invalid_input"}), status=400, mimetype='application/json')

        # Check partner related to barcode
        partner = request.env['res.partner'].sudo().search([('card_barcode', '=', barcode)], limit=1)

        if not partner:
            return self._get_response(404, {
                "error": "Barcode not found."
            })

        # Get all invoices related to partner
        order_list = []
        for order in request.env['pos.order'].sudo().search([('partner_id', '=', partner.id),('state','not in',('draft','cancel'))]):
            order_list.append({
                'order_number': order.pos_reference,
                'student_number': partner.display_name,
                'barcode': partner.card_barcode,
                'amount': order.payment_ids[0].amount if order.payment_ids else 0.00,
                'date': self.date_to_string(order.date_order)
            })
        
        return self._get_response(200, order_list)

    @http.route('/api/v1/invoice_detail', type='http', auth='none', methods=['GET'], csrf=False)
    def invoice_detail(self, **kw):
        # Check API key
        error = self._authenticate()
        if error:
            return error

        order_number = kw.get("order_number")

        if not order_number:
            return self._get_response(404, {
                "error": "Order not found."
            })

        # Get all invoices related to partner
        order = request.env['pos.order'].sudo().search([('pos_reference', '=', order_number),('state','not in',('draft','cancel'))])
        if not order:
            return self._get_response(404, {
                "error": "Order not found."
            })

        return self._get_response(200, {
            "order_number": order.pos_reference,
            "student_number": order.partner_id.display_name,
            "barcode": order.partner_id.card_barcode,
            "amount": order.payment_ids[0].amount if order.payment_ids else 0.00,
            "date": self.date_to_string(order.date_order),
            "items": [
                {
                    "name": line.product_id.name,
                    "quantity": line.qty,
                    "price": line.price_unit,
                    "total": line.price_subtotal
                } for line in order.lines
            ]
        })
