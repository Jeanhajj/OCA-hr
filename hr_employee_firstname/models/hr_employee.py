# -*- coding: utf-8 -*-
# ©  2010 - 2014 Savoir-faire Linux (<http://www.savoirfairelinux.com>)
# Copyright 2016-2019 Onestein (<https://www.onestein.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

UPDATE_PARTNER_FIELDS = ['firstname', 'lastname', 'user_id', 'address_home_id']


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_name(self, lastname, firstname):
        return self.env['res.partner']._get_computed_name(lastname, firstname)

    @api.onchange('firstname', 'lastname')
    def _onchange_firstname_lastname(self):
        if self.firstname or self.lastname:
            self.name = self._get_name(self.lastname, self.firstname)

    firstname = fields.Char()
    lastname = fields.Char()

    @api.model
    def create(self, vals):
        self._prepare_vals_on_create_firstname_lastname(vals)
        res = super(HrEmployee, self).create(vals)
        res._update_partner_firstname()
        return res

    @api.multi
    def write(self, vals):
        self._prepare_vals_on_write_firstname_lastname(vals)
        res = super(HrEmployee, self).write(vals)
        if set(vals).intersection(UPDATE_PARTNER_FIELDS):
            self._update_partner_firstname()
        return res

    def _prepare_vals_on_create_firstname_lastname(self, vals):
        if vals.get('firstname') or vals.get('lastname'):
            vals['name'] = self._get_name(vals['lastname'], vals['firstname'])
        elif vals.get('name'):
            vals['lastname'] = self.split_name(vals['name'])['lastname']
            vals['firstname'] = self.split_name(vals['name'])['firstname']
        else:
            raise UserError(_('No name set.'))

    def _prepare_vals_on_write_firstname_lastname(self, vals):
        if 'firstname' in vals or 'lastname' in vals:
            if 'lastname' in vals:
                lastname = vals.get('lastname')
            else:
                lastname = self.lastname
            if 'firstname' in vals:
                firstname = vals.get('firstname')
            else:
                firstname = self.firstname
            vals['name'] = self._get_name(lastname, firstname)
        elif vals.get('name'):
            vals['lastname'] = self.split_name(vals['name'])['lastname']
            vals['firstname'] = self.split_name(vals['name'])['firstname']

    @api.model
    def split_name(self, name):
        clean_name = " ".join(name.split(None)) if name else name
        return self.env['res.partner']._get_inverse_name(clean_name)

    @api.model
    def _get_names_order(self):
        return self.env['res.partner']._get_names_order()

    @api.multi
    def _inverse_name(self):
        """Try to revert the effect of :method:`._compute_name`."""
        order = self._get_names_order()
        for record in self:
            parts = self.env['res.partner']._get_inverse_name(record.name)
            if len(parts) > 2:
                keys = [item for item in parts.keys() if item not in [
                    'firstname', 'lastname']]
                additional_parts = ''
                if order == 'last_first':
                    field = 'lastname'
                else:
                    field = 'firstname'
                for key in keys:
                    additional_parts += ' ' + parts[key] if parts[key] else ''
                parts[field] += additional_parts
            record.lastname = parts['lastname']
            record.firstname = parts['firstname']

    @api.model
    def _install_employee_firstname(self):
        """Save names correctly in the database.

        Before installing the module, field ``name`` contains all full names.
        When installing it, this method parses those names and saves them
        correctly into the database. This can be called later too if needed.
        """
        # Find records with empty firstname and lastname
        records = self.search([("firstname", "=", False),
                               ("lastname", "=", False)])

        # Force calculations there
        records._inverse_name()
        _logger.info("%d employees updated installing module.", len(records))

    def _update_partner_firstname(self):
        for employee in self:
            partners = employee.mapped('user_id.partner_id')
            partners |= employee.mapped('address_home_id')
            partners.write({
                'firstname': employee.firstname,
                'lastname': employee.lastname,
            })

    @api.constrains("firstname", "lastname")
    def _check_name(self):
        """Ensure at least one name is set."""
        for record in self:
            if not (record.firstname or record.lastname or record.name):
                raise UserError(_('No name set.'))
