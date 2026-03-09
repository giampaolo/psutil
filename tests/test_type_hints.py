#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import functools
import types

import pytest

import psutil

from . import PsutilTestCase
from . import check_fun_type_hints
from . import check_ntuple_type_hints
from . import is_namedtuple
from . import process_namespace
from . import system_namespace

# ===================================================================
# --- named tuples type hints
# ===================================================================


class TestTypeHintsNtuples(PsutilTestCase):
    """Check that namedtuple field values match the type annotations
    defined in psutil/_ntuples.py.
    """

    def check_result(self, ret):
        if is_namedtuple(ret):
            check_ntuple_type_hints(ret)
        elif isinstance(ret, list):
            for item in ret:
                if is_namedtuple(item):
                    check_ntuple_type_hints(item)

    def test_system_ntuple_types(self):
        for fun, name in system_namespace.iter(system_namespace.getters):
            try:
                ret = fun()
            except psutil.Error:
                continue
            with self.subTest(name=name, fun=str(fun)):
                if isinstance(ret, dict):
                    for v in ret.values():
                        if isinstance(v, list):
                            for item in v:
                                self.check_result(item)
                        else:
                            self.check_result(v)
                else:
                    self.check_result(ret)

    def test_process_ntuple_types(self):
        p = psutil.Process()
        ns = process_namespace(p)
        for fun, name in ns.iter(ns.getters):
            with self.subTest(name=name, fun=str(fun)):
                try:
                    ret = fun()
                except psutil.Error:
                    continue
                self.check_result(ret)


# ===================================================================
# --- returned type hints
# ===================================================================


class TestTypeHintsReturned(PsutilTestCase):
    """Check that annotated return types in psutil/__init__.py match
    the actual values returned at runtime.
    """

    def check(self, fun, name):
        try:
            ret = fun()
        except psutil.Error:
            return
        check_fun_type_hints(fun, ret)

    def test_system_return_types(self):
        for fun, name in system_namespace.iter(system_namespace.getters):
            with self.subTest(name=name, fun=str(fun)):
                self.check(fun, name)

    def test_process_return_types(self):
        p = psutil.Process()
        ns = process_namespace(p)
        for fun, name in ns.iter(ns.getters):
            with self.subTest(name=name, fun=str(fun)):
                self.check(fun, name)


# =====================================================================
# --- Tests for check_fun_type_hints() test utility fun
# =====================================================================


class TestCheckFunTypeHints(PsutilTestCase):

    @pytest.mark.skipif(
        not hasattr(types, "UnionType"), reason="Python 3.10+ only"
    )
    def test_no_annotation(self):
        def foo():
            return 1

        with pytest.raises(ValueError, match="no type hints defined"):
            check_fun_type_hints(foo, 1)

    def test_float(self):
        def foo() -> float:
            return 1.0

        check_fun_type_hints(foo, 1.0)
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    def test_bool(self):
        def foo() -> bool:
            return True

        check_fun_type_hints(foo, True)
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    @pytest.mark.skipif(
        not hasattr(types, "UnionType"), reason="Python 3.10+ only"
    )
    def test_list(self):
        def foo() -> list[int]:
            return [1]

        check_fun_type_hints(foo, foo())
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    @pytest.mark.skipif(
        not hasattr(types, "UnionType"), reason="Python 3.10+ only"
    )
    def test_dict(self):
        def foo() -> dict[str, int]:
            return {'a': 1}

        check_fun_type_hints(foo, foo())
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    def test_namedtuple(self):
        from psutil._ntuples import addr

        def foo() -> addr:
            return addr('127.0.0.1', 80)

        check_fun_type_hints(foo, addr('127.0.0.1', 80))
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    @pytest.mark.skipif(
        not hasattr(types, "UnionType"), reason="Python 3.10+ only"
    )
    def test_union_with_none(self):
        def foo() -> int | None:
            return 1

        check_fun_type_hints(foo, 1)
        check_fun_type_hints(foo, None)
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    @pytest.mark.skipif(
        not hasattr(types, "UnionType"), reason="Python 3.10+ only"
    )
    def test_union_or_dict_or_none(self):
        def foo() -> int | dict[str, int] | None:
            return 1

        check_fun_type_hints(foo, 1)
        check_fun_type_hints(foo, {'a': 1})
        check_fun_type_hints(foo, None)
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    def test_generator(self):
        from typing import Generator

        def foo() -> Generator[int, None, None]:
            yield 1

        check_fun_type_hints(foo, foo())
        with pytest.raises(AssertionError):
            check_fun_type_hints(foo, "str")

    def test_partial(self):
        def foo(x) -> int:
            return x

        fun = functools.partial(foo, 1)
        check_fun_type_hints(fun, 1)
        with pytest.raises(AssertionError):
            check_fun_type_hints(fun, "str")

    def test_bound_method(self):
        class MyClass:
            def foo(self) -> int:
                return 1

        obj = MyClass()
        check_fun_type_hints(obj.foo, 1)
        with pytest.raises(AssertionError):
            check_fun_type_hints(obj.foo, "str")
