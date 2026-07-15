# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
import base64
import requests
import json
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Partner(models.Model):
	_inherit = 'res.partner'

	dcid = fields.Integer(string="DCID")
	first_name = fields.Char(string="First Name")
	last_name = fields.Char(string="Last Name")
	middle_name = fields.Char(string="middle_name")
	family_id = fields.Char(string="Family ID")
	guardian_code = fields.Char(string="Guardian Code")
	guardian_1_email = fields.Char(string="Guardian 1 Email")
	guardian_1_name = fields.Char(string="Guardian 1 Name")
	guardian_1_relationship = fields.Char(string="Guardian 1 Relationship")
	guardian_1_mobile = fields.Char(string="Guardian 1 Mobile ")
	guardian_1_employer = fields.Char(string="Guardian 1 Employer ")
	guardian_2_employer = fields.Char(string="Guardian 2 Employer")
	guardian_2_email = fields.Char(string="Guardian 2 Email")
	guardian_2_name = fields.Char(string="Guardian 2 Name")
	guardian_2_relationship = fields.Char(string="Guardian 2 Relationship")
	guardian_2_mobile = fields.Char(string="Guardian 2 Mobile")
	dob = fields.Char(string="Date of Birth")
	gender = fields.Char(string="Gender")
	ethnicity = fields.Char(string="Ethnicity")
	grade_level = fields.Char(string="Grade Level")
	next_year_grade_level = fields.Char(string="Next Year Grade Level")
	addressline1 = fields.Char(string="Address")
	student_number = fields.Char(string="Student Number")
	payment_option = fields.Char(string="Payment Option")
	billing_address_line1 = fields.Char(string="Billing Address")
	billing1_township = fields.Char(string="Billing Township")
	home_phone = fields.Char(string="Home Phone")
	enroll_status = fields.Selection([
		('0','Active'),
		('1','Inactive'),
		('2','Transferred Out'),
		('-1','Pre-registered (Inactive)'),
		('1', 'inactive'),
		('3', 'Graduated'),
		('4', 'Imported as historical')
		],string="Enroll Status", default='0')

	def get_student_name(self, value):
		name = first_name = last_name = middle_name = " "
		if(value.get('legal_first_name')):
			if(value.get('legal_middle_name')):
				name = value.get('legal_first_name') + " " + value.get('legal_middle_name') + " " + value.get('legal_last_name')
				first_name = value.get('legal_first_name')
				last_name = value.get('legal_last_name')
				middle_name = value.get('legal_middle_name')
			else:
				name = value.get('legal_first_name')+" "+value.get('legal_last_name')
				first_name = value.get('legal_first_name')
				last_name = value.get('legal_last_name')
		else:
			if(value.get(middle_name)):
				name = value.get('first_name') + " " + value.get('middle_name')+" "+value.get('last_name')
				first_name = value.get('first_name')
				last_name = value.get('last_name')
				middle_name = value.get('middle_name')
			else:
				name = value.get('first_name')+" "+value.get('last_name')
				first_name = value.get('first_name')
				last_name = value.get('last_name')

		return name, first_name, last_name, middle_name

	def get_guardian_name(self, value):
		name = ""
		if(value.get('guardian_firstname', '')):
			name = value.get('guardian_firstname')+" "+value.get('guardian_lastname', '')
		if name == " ":
			print("Name is empty: ", value)
		return name

	def get_header(self):
		myurl = 'https://powerschool.isyedu.org/oauth/access_token/'
		ps_code = '07d8b31f-5904-4932-80cb-08b4e495920d'
		ps_secret = 'e6f48f28-b04f-490f-9412-5b20f19f0684'
		mydata = ps_code + ":" + ps_secret
		data_bytes = mydata.encode("utf-8")
		mysecret = base64.b64encode(data_bytes)
		headers = { "Authorization" : "Basic " + mysecret.decode("utf-8") }
		params = { "grant_type": "client_credentials"}
		response =  requests.post(myurl, headers = headers, data = params)
		data = response.json()
		access_token = data['access_token']

		return {'Authorization': 'Bearer ' + access_token,'Content-Type': 'application/json'}

	@api.model
	def sync_parent_data(self):
		try:
			header = self.get_header()
			myresponse = requests.post("https://powerschool.isyedu.org/ws/schema/query/api.school.pull_odoo_guardian?pagesize=0", headers=header)
			mydata = myresponse.json()
			mydata = mydata and mydata['record'] or []
			for value in mydata:
				name = self.get_guardian_name(value)
				partner = self.search([('guardian_code', '=', int(value.get('guardian_code')))], limit=1)
				if partner and int(partner.guardian_code) == int(value.get('guardian_code')):
					partner.sudo().write({
						'guardian_code': value.get('guardian_code'),
						'name': name
					})
				else:
					parent_tag = self.env['res.partner.category'].search([('name', '=', 'Parent')], limit=1)
					self.sudo().create({
						'name': name,
						'guardian_code': value.get('guardian_code'),
						'category_id': [(4, parent_tag.id)],
						'customer_rank': 1
					})

		except requests.HTTPError as e:
			_logger.debug("Data request failed with code: %r, msg: %r, content: %r",
						  e.response.status_code, e.response.reason, e.response.content)
			raise

		return True

	@api.model
	def sync_data(self):
		try:
			hed = self.get_header()
			myresponse = requests.post("https://powerschool.isyedu.org/ws/schema/query/api.school.pull_odoo_student?pagesize=0", headers=hed)
			mydata = myresponse.json()
			mydata = mydata and mydata['record'] or []
			for value in mydata:				
				name, first_name, last_name, middle_name = self.get_student_name(value)
				partner = self.search([('dcid', '=', int(value.get('dcid')))], limit=1)
				if partner and partner.dcid == int(value.get('dcid')):
					partner.sudo().write({
						'dcid': value.get('dcid'),
						'name': name,
						'first_name': first_name,
						'middle_name': middle_name,
						'last_name': last_name,
						'family_id': value.get('family_id'),
						'email':value.get('student_web_id'),
						'guardian_1_email': value.get('guardian_1_email'),
						'guardian_1_name': value.get('guardian_1_name'),
						'guardian_1_relationship': value.get('guardian_1_relationship'),
						'guardian_1_mobile': value.get('guardian_1_mobile'),
						'guardian_1_employer': value.get('guardian_1_employer'),
						'guardian_2_email': value.get('guardian_2_email') or value.get('guardian_1_email'),
						'guardian_2_name': value.get('guardian_2_name'),
						'guardian_2_relationship': value.get('guardian_2_relationship'),
						'guardian_2_employer': value.get('guardian_2_employer'),
						'guardian_2_mobile': value.get('guardian_2_mobile'),
						'dob': value.get('dob'),
						'gender': value.get('gender'),
						'ethnicity': value.get('ethnicity'),
						'grade_level': value.get('grade_level'),
						'addressline1': value.get('addressline1'),
						'student_number': value.get('student_number'),
						'payment_option': value.get('payment_option'),
						'home_phone' : value.get('home_phone'),
						'billing1_township': value.get('billing1_township'),
						'billing_address_line1': value.get('billing1_address_line1'),
						'enroll_status': value.get('enroll_status','0')
					})
				else:
					stud_val = {
						'name': name,
						'dcid': value.get('dcid'),
						'first_name': first_name,
						'middle_name': middle_name,
						'last_name': last_name,
						'family_id': value.get('family_id'),
						'email':value.get('student_web_id'),
						'guardian_1_email': value.get('guardian_1_email'),
						'guardian_1_name': value.get('guardian_1_name'),
						'guardian_1_relationship': value.get('guardian_1_relationship'),
						'guardian_1_mobile': value.get('guardian_1_mobile'),
						'guardian_1_employer': value.get('guardian_1_employer'),
						'guardian_2_email': value.get('guardian_2_email') or value.get('guardian_1_email'),
						'guardian_2_name': value.get('guardian_2_name'),
						'guardian_2_relationship': value.get('guardian_2_relationship'),
						'guardian_2_employer': value.get('guardian_2_employer'),
						'guardian_2_mobile': value.get('guardian_2_mobile'),
						'dob': value.get('dob'),
						'gender': value.get('gender'),
						'ethnicity': value.get('ethnicity'),
						'grade_level': value.get('grade_level'),
						'addressline1': value.get('addressline1'),
						'student_number': value.get('student_number'),
						'payment_option': value.get('payment_option'),
						'home_phone' : value.get('home_phone'),
						'billing1_township': value.get('billing1_township'),
						'billing_address_line1': value.get('billing1_address_line1'),
						'customer_rank': 1,
						'enroll_status': value.get('enroll_status','0')
					}
					self.sudo().create(stud_val)

		except requests.HTTPError as e:
			_logger.debug("Data request failed with code: %r, msg: %r, content: %r",
						  e.response.status_code, e.response.reason, e.response.content)
			raise

		return True

	def sync_request(self):
		#API_ENDPOINT = 'http://192.168.10.200/student.php'
		for partner in self:
			if partner.dcid:
				try:
					myurl = 'https://powerschool.isyedu.org/oauth/access_token/'
					ps_code = '07d8b31f-5904-4932-80cb-08b4e495920d'
					ps_secret = 'e6f48f28-b04f-490f-9412-5b20f19f0684'
					mydata = ps_code + ":" + ps_secret
					data_bytes = mydata.encode("utf-8")
					mysecret = base64.b64encode(data_bytes)
					postFields = {'grant_type':'client_credentials'}
					credentials = ('07d8b31f-5904-4932-80cb-08b4e495920d', 'e6f48f28-b04f-490f-9412-5b20f19f0684')
					headers = {
						"Authorization" : "Basic " + mysecret.decode("utf-8")
					}
					params = {
						"grant_type": "client_credentials"
					}
					response =  requests.post(myurl, headers = headers, data = params)
					data = response.json()
					access_token = data['access_token']
					hed = {'Authorization': 'Bearer ' + access_token,
						'Content-Type':'application/json'}
					myparams = {"dcid": partner.dcid }
					#myresponse = requests.post("https://powerschool.isyedu.org/ws/schema/query/api.school.pull_odoo_student?pagesize=0", headers=hed)
					myresponse = requests.post("https://powerschool.isyedu.org/ws/schema/query/api.school.pull_single_odoo_student",
						data = json.dumps(myparams), headers=hed)
					mydata = myresponse.json()
					#mydata = mydata and mydata['record'] or []
					#data = request.json()
					if mydata and mydata['record']:
						values = mydata['record'][0]
						_logger.debug(values)
						name = first_name = last_name = middle_name = " "
						if(values.get('legal_first_name')):
							if(values.get('legal_middle_name')):
								# name = values.get('legal_last_name') + "; " + values.get('legal_first_name') + " " + values.get('legal_middle_name')
								name = values.get('legal_first_name') + " " + values.get('legal_middle_name') +" "+ values.get('legal_last_name')
								first_name = values.get('legal_first_name')
								last_name = values.get('legal_last_name')
								middle_name = values.get('legal_middle_name')
						#print str(i) + 
							else:
								# name = values.get('legal_last_name') + "; " + values.get('legal_first_name')
								name = values.get('legal_first_name') + " "+values.get('legal_last_name') 
								first_name = values.get('legal_first_name')
								last_name = values.get('legal_last_name')
						else:
							if(values.get(middle_name)):
								# name = values.get('last_name') + "; " + values.get('first_name') + " " + values.get('middle_name')
								name = values.get('first_name') + " " + values.get('middle_name')+ " " + values.get('last_name')
								first_name = values.get('first_name')
								last_name = values.get('last_name')
								middle_name = values.get('middle_name')
							else:
								# name = values.get('last_name') + "; " + values.get('first_name')
								name = values.get('first_name')+" "+values.get('last_name')
								first_name = values.get('first_name')
								last_name = values.get('last_name')
						partner.sudo().write({
							'dcid': values.get('dcid'),
							'name': name,
							'first_name': first_name,
							'last_name': last_name,
							'middle_name': middle_name,
							'family_id': values.get('family_id'),
							'email':values.get('student_web_id'),
							'guardian_1_email': values.get('guardian_1_email'),
							'guardian_1_name': values.get('guardian_1_name'),
							'guardian_1_relationship': values.get('guardian_1_relationship'),
							'guardian_1_mobile': values.get('guardian_1_mobile'),
							'guardian_1_employer': values.get('guardian_1_employer'),
							#'guardian_2_email': values.get('guardian_2_email'),
							'guardian_2_email': values.get('guardian_2_email') or values.get('guardian_1_email'),
							'guardian_2_name': values.get('guardian_2_name'),
							'guardian_2_relationship': values.get('guardian_2_relationship'),
							'guardian_2_employer': values.get('guardian_2_employer'),
							'guardian_2_mobile': values.get('guardian_2_mobile'),
							'dob': values.get('dob'),
							'gender': values.get('gender'),
							'ethnicity': values.get('ethnicity'),
							'grade_level': values.get('grade_level'),
							'addressline1': values.get('addressline1'),
							'student_number': values.get('student_number'),
							'payment_option': values.get('payment_option'),
							'home_phone' : values.get('home_phone'),
							'billing1_township': values.get('billing1_township'),
							'billing_address_line1': values.get('billing1_address_line1'),
							'enroll_status': values.get('enroll_status','0')
						})

				except requests.HTTPError as e:
					_logger.debug("Data request failed with code: %r, msg: %r, content: %r",
								  e.response.status_code, e.response.reason, e.response.content)
					raise

		return True
