# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class HrLeaveType(models.Model):
	_inherit = 'hr.leave.type'

	accumulated_leave = fields.Boolean(string='Accumulated leave', default =False)
	unpaid_accumulated_leave = fields.Boolean(string='Unpaid Accumulated Leave', default= False)

	@api.constrains('accumulated_leave', 'unpaid_accumulated_leave')
	def _check_duplicated_accumulated_leave(self):
		if self.accumulated_leave and self.unpaid_accumulated_leave:
			raise ValidationError(_("Accumulated and Unpaid Accumulated cannot enable at the same leave type."))

class HrSubLeaveType(models.Model):
	_name = 'hr.sub.leave.type'
	_description = 'Sub Leave Type'
	_inherit = ['mail.thread']

	name = fields.Char(string='Name')
	display_name = fields.Char(string='Display Name', compute='_compute_display_name')
	hr_leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type')
	max_days = fields.Float(string='Max Days')
	active = fields.Boolean(string='Active', default=True)
	is_personal_leave = fields.Boolean(string="Is Personal Leave", default=False)

	def get_fiscal_date(self):
		fd = self.env.user.company_id.fiscalyear_last_day
		fm = self.env.user.company_id.fiscalyear_last_month
		now = datetime.now()
		e_fiscal_date = datetime.strptime(
		"%s-%s-%s" % (now.year, fm, fd),
		DEFAULT_SERVER_DATE_FORMAT
		)
		if now >= e_fiscal_date:
			e_fiscal_date = datetime.strptime(
				"%s-%s-%s" % (now.year + 1, fm, fd),
				DEFAULT_SERVER_DATE_FORMAT
			) + timedelta(days=1)
		s_fiscal_date = datetime.strptime(
			"%s-%s-%s" % (e_fiscal_date.year - 1, fm, fd),
			DEFAULT_SERVER_DATE_FORMAT
		) + timedelta(days=1)

		return str(s_fiscal_date)

	def _get_allocated_leaves(self):
		employee_id = self.env.user.employee_id
		s_fiscal_date = self.get_fiscal_date()
		allocated_leaves = self.env['hr.leave.allocation'].search([
			('employee_id', '=', employee_id.id),
			('holiday_status_id', '=', self.hr_leave_type_id.id),
			('state', '=', 'validate'),
		])
		return sum(allocation.number_of_days_display for allocation in allocated_leaves)

	def get_remaining_leaves(self):
		self.ensure_one()
		if not self.is_personal_leave:
			max_days = self._get_allocated_leaves()
		else:
			max_days = float_round(self.max_days, precision_digits=2) or 0.0
		taken_sub_leave_days = self._taken_leave()
		taken_sub_leave_days = sum(leave.number_of_days for leave in taken_sub_leave_days)
		if self.max_days != self.hr_leave_type_id.max_leaves:
			if self.hr_leave_type_id.max_leaves < self.max_days:
				max_days = float_round(self.hr_leave_type_id.max_leaves, precision_digits=2) or 0.0
				remaining = float_round(self.hr_leave_type_id.max_leaves - taken_sub_leave_days, precision_digits=2) or 0.0
			else:
				remaining = float_round(self.max_days - taken_sub_leave_days, precision_digits=2) or 0.0
		else:
			remaining = float_round(self.hr_leave_type_id.virtual_remaining_leaves, precision_digits=2) or 0.0
		return (max(max_days, 0.0), max(remaining, 0.0))

	def _taken_leave(self):
		employee_id = self.env.user.employee_id
		s_fiscal_date = self.get_fiscal_date()
		if self.is_personal_leave:
			return self.env['hr.leave'].search([
				('employee_id', '=', employee_id.id),
				('holiday_status_id', '=', self.hr_leave_type_id.id),
				('state', 'in', ['validate', 'validate1', 'confirm']),
				('sub_leave_type_id', '=', self.id),
				('date_from','>',s_fiscal_date)
			])

		return self.env['hr.leave'].search([
                ('employee_id', '=', employee_id.id),
                ('holiday_status_id', '=', self.hr_leave_type_id.id),
                ('state', 'in', ['validate', 'validate1', 'confirm']),
				('date_from','>',s_fiscal_date)
            ])

	def requested_display_name(self):
		return self._context.get('sub_leave_type_display_name', True) and self._context.get('employee_id')

	@api.depends('hr_leave_type_id.requires_allocation', 'hr_leave_type_id.virtual_remaining_leaves', 'hr_leave_type_id.max_leaves', 'hr_leave_type_id.request_unit')
	@api.depends_context('sub_leave_type_display_name', 'holiday_status_display_name', 'employee_id', 'from_manager_leave_form')
	def _compute_display_name(self):
		if not self.hr_leave_type_id.requested_display_name():
			return super()._compute_display_name()

		for record in self:
			name = record.name
			leave_type = record.hr_leave_type_id
			if (
				leave_type.requires_allocation == "yes"
				and not self._context.get('from_manager_leave_form')
			):
				values = record.get_remaining_leaves()
				suffix = _(' hours') if leave_type.request_unit == 'hour' else _(' days')
				name = f"{name} ({_('%g remaining out of %g') % (values[1], values[0])}{suffix})"
			record.display_name = name
