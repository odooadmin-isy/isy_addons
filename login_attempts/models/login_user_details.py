# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, AccessDenied
from lxml import etree
import logging
from itertools import chain
from odoo.http import request
from odoo import models, fields, api, _
from datetime import datetime
from datetime import timedelta
_logger = logging.getLogger(__name__)
USER_PRIVATE_FIELDS = ['password']
concat = chain.from_iterable

class LoginLocation(models.Model):

    _name = 'login.location'
    _description = 'Location which is specifically allowed to this user'

    name = fields.Char(string='Name', required=True)
    ip_address = fields.Char(string='IP Address', required=True)

class LoginUpdate(models.Model):

    _name = 'login.detail'
    _description = 'User login attempts and details'
    _order = 'date_time desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date_time = fields.Datetime(string="Login Date", default=lambda self: fields.datetime.now())
    time = fields.Char(compute="_compute_time", string="Login Time")
    ip_address = fields.Char(string="IP Address")
    database = fields.Char(string='Database',  readonly=True)
    login_state = fields.Selection([('success', 'Success'),
                                    ('fail', 'Fail')],
                                   string='Attempt Status', readonly=True)
    location_id = fields.Many2one(comodel_name='login.location', string='Location', readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string='User', readonly=True)
    password = fields.Char(string='Password', help="""This field is visible when a user logs in with a different password than the one set on their profile.
                                                      This field is invisible when:
                                                         \t* A login trial is successful.
                                                         \t* A user uses the correct password but from a different location than the set one.
                                                         \t* A user uses the correct password but is blocked at the moment. """, readonly=True)
    password_value = fields.Char(related="password", help="This field is visible when a user logs in with a different password than the one set on their profile.")
    not_password = fields.Boolean('Show Password')
    show_log = fields.Boolean('Show Log', default=True)


    def name_get(self):
        res = []
        for rec in self:
            name = rec.user_id.name
            res.append((rec.id, name))
        return res

    def _compute_time(self):
        for rec in self:
            start_dt = datetime.strptime(str(rec.date_time), '%Y-%m-%d %H:%M:%S') + timedelta(hours=6.5)
            rec.time = datetime.strftime(start_dt, "%H:%M:%S")


    def show_password(self):
        self.write({'not_password': True})


    def hide_password(self):
        self.write({'not_password': False})

    def update_show_log(self):
        recs = self.search([])
        recs.write({'show_log': True})

    def read(self, fields=None, load='_classic_read'):
        if self._context.get('is_recursive', False):
            return super(LoginUpdate, self).read(fields, load)
        if not (self.env.user.id == self.env.ref('base.user_root').id) and 'password' in fields:
            for rec in self:
                if rec.with_context(is_recursive=True).show_log:

                    msg = self.env.user.name + "  \n  " + str(datetime.strptime(str(datetime.now())[:19], '%Y-%m-%d %H:%M:%S'))
                    message_values = {
                        'body': msg,
                        'message_type': 'notification',
                        'model': 'login.detail',
                        'res_id': rec.id,
                        'subtype_id':self.env.ref('mail.mt_note').id,
                        }
                    message = self.env['mail.message'].create(message_values)
                    rec.show_log = False
        return super(LoginUpdate, self).read(fields, load)

class LoginUserDetail(models.Model):

    _inherit = 'res.users'

    location_ids = fields.Many2many('login.location', string='Allowed Locations', help="If Empty Then All Locations Allowed")
    login_locked = fields.Selection([('blocked', 'Blocked'), ('active', 'Active')], default='active', string="Login Status", track_visibility='onchange')
    login_locked_time = fields.Datetime(string="Locked Time")
    login_count = fields.Integer('Login Count', default=0)
    locked_message = fields.Text('Locked Message', compute='change_message')

    def change_message(self):
        if self.login_locked == 'blocked':
            self.locked_message = 'User blocked at ' + str(self.login_locked_time)[:19]
        else:
            self.locked_message = ''

    def unlock_user_login(self):
        self.ensure_one()
        if self.login_locked == 'blocked':
            self.write({'login_locked': 'active', 'login_locked_time': None, 'login_count': 0})
        return True

    @classmethod
    def authenticate(self, db, login, password, user_agent_env):
        uid = super(LoginUserDetail, self).authenticate(db, login, password, user_agent_env)
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        user_log_obj = request.env['login.detail']
        users_obj = request.env['res.users']
        is_allowed = False
        if uid:
            vals = {
                'date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': uid,
                'database': db,
                }
            user = users_obj.sudo().browse(uid)
            location_ids = user.location_ids

            if not location_ids:
                if user.login_locked == 'active':

                    is_allowed = True
                    location_idss = request.env['login.location'].sudo().search([])
                    location_id = False
                    for loc in location_idss:
                        if ip_address == loc.ip_address:
                            location_id = loc.id
                    vals.update({'login_state': 'success', 'location_id': location_id, 'ip_address': ip_address})

            for loc in location_ids:
                if ip_address == loc.ip_address:
                    if user.login_locked == 'active':
                        is_allowed = True
                        vals.update({'login_state': 'success', 'location_id': loc.id, 'ip_address': loc.ip_address})

            if not is_allowed:
                location_idss = request.env['login.location'].sudo().search([])
                location_id = False
                for loc in location_idss:
                    if ip_address == loc.ip_address:
                        location_id = loc.id
                vals.update({'login_state': 'fail', 'location_id': location_id, 'ip_address': ip_address})
                user_log_obj.sudo().create(vals)
                return 0
            else:

                user_log_obj.sudo().create(vals)
                # user.sudo().login_count = 0
                with user.pool.cursor() as cr:
                    user.with_env(user.env(cr=cr)).sudo().login_count  = 0
                return uid

    def _check_credentials(self, password, env):
        """ Validates the current user's password.

        Override this method to plug additional authentication methods.

        Overrides should:

        * call `super` to delegate to parents for credentials-checking
        * catch AccessDenied and perform their own checking
        * (re)raise AccessDenied if the credentials are still invalid
          according to their own validation method

        When trying to check for credentials validity, call _check_credentials
        instead.
        """
        """ Override this method to plug additional authentication methods"""
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        user_log_obj = request.env['login.detail']
        users_obj = request.env['res.users']

        db = self._cr.dbname
        login = self.env.user

        assert password
        self.env.cr.execute(
            "SELECT COALESCE(password, '') FROM res_users WHERE id=%s",
            [self.env.user.id]
        )
        [hashed] = self.env.cr.fetchone()
        valid, replacement = self._crypt_context()\
            .verify_and_update(password, hashed)
        if replacement is not None:
            self._set_encrypted_password(self.env.user.id, replacement)

        if not valid:

            location_ids = request.env['login.location'].sudo().search([])
            location_id = False
            for loc in location_ids:
                if ip_address == loc.ip_address:
                    location_id = loc.id
            vals = {
                    'user_id': login.id,
                    'database': db,
                    'location_id': location_id,
                    'login_state': 'fail',
                    'date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ip_address': ip_address
                    }

            if login.login_locked == 'blocked' or (login.location_ids.ids and ip_address not in login.location_ids.mapped('ip_address')):
                vals['password'] = False
            else:
                vals['password'] = password

            user_log_obj.sudo().create(vals)
            with self.pool.cursor() as cr:
                if self.env.user.has_group('base.group_user'):
                    self.with_env(self.env(cr=cr)).sudo().login_count = self.login_count + 1
            if self.login_count > 3:
                user = self.env.user
                if user:
                    sql = "UPDATE res_users SET login_locked = 'blocked' , login_locked_time='" + str(datetime.now()) + "' WHERE id=" + str(self.id) + ""
                    with self.pool.cursor() as cr:
                        cr.execute(sql)
                    user.sudo().create_mail_message(body='User ' + str(user.name) + ': has been Locked')
                    _logger.info('User  **' + str(user.name) + '** is Locked due to ' + str(self.login_count) + ' incorrect attempts')
            raise AccessDenied()


