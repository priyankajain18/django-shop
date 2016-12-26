# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models
from django.test import TestCase
from shop import deferred

import six


def create_regular_class(name, fields={}):
    class Meta:
        app_label = 'foo'

    return type(str(name), (models.Model,), dict(Meta=Meta, __module__=__name__, **fields))


def create_deferred_base_class(name, fields={}):
    class Meta:
        app_label = 'foo'
        abstract = True

    return type(
        str(name),
        (six.with_metaclass(deferred.ForeignKeyBuilder, models.Model),),
        dict(Meta=Meta, __module__=__name__, **fields),
    )


def create_deferred_class(name, base, fields={}):
    class Meta:
        app_label = 'bar'

    return type(str(name), (base,), dict(Meta=Meta, __module__=__name__, **fields))


RegularUser = create_regular_class('RegularUser')
DeferredBaseUser = create_deferred_base_class('DeferredBaseUser')
DeferredUser = create_deferred_class('DeferredUser', DeferredBaseUser)


RegularCustomer = create_regular_class('RegularCustomer', {
    'user': models.OneToOneField(RegularUser, on_delete=models.PROTECT),
    'advertised_by': models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL),
})
DeferredBaseCustomer = create_deferred_base_class('DeferredBaseCustomer', {
    'user': deferred.OneToOneField(DeferredBaseUser, on_delete=models.PROTECT),
    'advertised_by': deferred.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL),
})
DeferredCustomer = create_deferred_class('DeferredCustomer', DeferredBaseCustomer)


RegularProduct = create_regular_class('RegularProduct')
DeferredBaseProduct = create_deferred_base_class('DeferredBaseProduct')
DeferredProduct = create_deferred_class('DeferredProduct', DeferredBaseProduct)


RegularOrder = create_regular_class('RegularOrder', {
    'customer': models.ForeignKey(RegularCustomer, on_delete=models.PROTECT),
    'items_simple': models.ManyToManyField(RegularProduct),
    'items_through': models.ManyToManyField('RegularProduct', through='RegularOrderItem'),
})
DeferredBaseOrder = create_deferred_base_class('DeferredBaseOrder', {
    'customer': deferred.ForeignKey(DeferredBaseCustomer, on_delete=models.PROTECT),
    'items_simple': deferred.ManyToManyField(DeferredBaseProduct),
    'items_through': deferred.ManyToManyField('DeferredBaseProduct', through='DeferredBaseOrderItem'),
})
DeferredOrder = create_deferred_class('DeferredOrder', DeferredBaseOrder)


RegularOrderItem = create_regular_class('RegularOrderItem', {
    'order': models.ForeignKey(RegularOrder, on_delete=models.CASCADE),
    'product': models.ForeignKey(RegularProduct, on_delete=models.PROTECT),
})
DeferredBaseOrderItem = create_deferred_base_class('DeferredBaseOrderItem', {
    'order': deferred.ForeignKey(DeferredBaseOrder, on_delete=models.CASCADE),
    'product': deferred.ForeignKey(DeferredBaseProduct, on_delete=models.PROTECT),
})
DeferredOrderItem = create_deferred_class('DeferredOrderItem', DeferredBaseOrderItem)


class DeferredTestCase(TestCase):

    def _test_foreign_key(self, order_class, customer_class):
        customer_field = order_class._meta.get_field('customer')

        self.assertTrue(customer_field.is_relation)
        self.assertTrue(customer_field.many_to_one)
        self.assertIs(customer_field.related_model, customer_class)

    def test_foreign_key_regular(self):
        self._test_foreign_key(RegularOrder, RegularCustomer)

    def test_foreign_key_deferred(self):
        self._test_foreign_key(DeferredOrder, DeferredCustomer)

    def _test_one_to_one_field(self, customer_class, user_class):
        user_field = customer_class._meta.get_field('user')

        self.assertTrue(user_field.is_relation)
        self.assertTrue(user_field.one_to_one)
        self.assertIs(user_field.related_model, user_class)

    def test_one_to_one_field_regular(self):
        self._test_one_to_one_field(RegularCustomer, RegularUser)

    def test_one_to_one_field_deferred(self):
        self._test_one_to_one_field(DeferredCustomer, DeferredUser)

    def _test_many_to_may_field_simple(self, order_class, product_class):
        items_field = order_class._meta.get_field('items_simple')

        self.assertTrue(items_field.is_relation)
        self.assertTrue(items_field.many_to_many)
        self.assertIs(items_field.related_model, product_class)

        m2m_field_name = items_field.m2m_field_name()
        m2m_field = items_field.rel.through._meta.get_field(m2m_field_name)
        m2m_reverse_field_name = items_field.m2m_reverse_field_name()
        m2m_reverse_field = items_field.rel.through._meta.get_field(m2m_reverse_field_name)

        self.assertIs(m2m_field.related_model, order_class)
        self.assertIs(m2m_reverse_field.related_model, product_class)

    def test_many_to_many_field_simple_regular(self):
        self._test_many_to_may_field_simple(RegularOrder, RegularProduct)

    def test_many_to_many_field_simple_deferred(self):
        self._test_many_to_may_field_simple(DeferredOrder, DeferredProduct)

    def _test_many_to_may_field_through(self, order_class, product_class, order_item_class):
        items_field = order_class._meta.get_field('items_through')

        self.assertTrue(items_field.is_relation)
        self.assertTrue(items_field.many_to_many)
        self.assertIs(items_field.related_model, product_class)
        self.assertIs(items_field.rel.through, order_item_class)

        m2m_field_name = items_field.m2m_field_name()
        m2m_field = items_field.rel.through._meta.get_field(m2m_field_name)
        m2m_reverse_field_name = items_field.m2m_reverse_field_name()
        m2m_reverse_field = items_field.rel.through._meta.get_field(m2m_reverse_field_name)

        self.assertIs(m2m_field.related_model, order_class)
        self.assertIs(m2m_reverse_field.related_model, product_class)

    def test_many_to_many_field_through_regular(self):
        self._test_many_to_may_field_through(RegularOrder, RegularProduct, RegularOrderItem)

    def test_many_to_many_field_through_deferred(self):
        self._test_many_to_may_field_through(DeferredOrder, DeferredProduct, DeferredOrderItem)

    def _test_foreign_key_self(self, customer_class):
        advertised_by_field = customer_class._meta.get_field('advertised_by')

        self.assertTrue(advertised_by_field.is_relation)
        self.assertTrue(advertised_by_field.many_to_one)
        self.assertIs(advertised_by_field.related_model, customer_class)

    def test_foreign_key_self_regular(self):
        self._test_foreign_key_self(RegularCustomer)

    def test_foreign_key_self_deferred(self):
        self._test_foreign_key_self(DeferredCustomer)