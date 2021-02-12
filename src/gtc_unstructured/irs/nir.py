# -*- coding: utf-8 -*-
#
# Eve Toolchain - GT4Py Project - GridTools Framework
#
# Copyright (c) 2020, CSCS - Swiss National Supercomputing Center, ETH Zurich
# All rights reserved.
#
# This file is part of the GT4Py project and the GridTools framework.
# GT4Py is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or any later
# version. See the LICENSE.txt file at the top-level directory of this
# distribution for a copy of the license or check <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List, Optional, Tuple, Union

from devtools import debug  # noqa: F401
from pydantic import root_validator, validator

from eve import Node, Str, SymbolTableTrait
from eve.type_definitions import SymbolName, SymbolRef
from gtc_unstructured.irs import common
from gtc import common as stable_gtc_common


class Expr(Node):
    location_type: common.LocationType
    pass


class Stmt(Node):
    location_type: common.LocationType
    pass


class Literal(Expr):
    value: Union[Str, common.BuiltInLiteral]
    vtype: common.DataType


class LocalVar(Node):
    name: Str
    vtype: common.DataType
    location_type: common.LocationType


class BlockStmt(Stmt):
    declarations: List[LocalVar]
    statements: List[Stmt]

    @root_validator(pre=True)
    def check_location_type(cls, values):
        all_locations = [s.location_type for s in values["statements"]] + [
            d.location_type for d in values["declarations"]
        ]

        if len(all_locations) == 0:
            return values  # nothing to validate

        if any(location != all_locations[0] for location in all_locations):
            raise ValueError(
                "Location type mismatch: not all statements and declarations have the same location type"
            )

        if "location_type" not in values:
            values["location_type"] = all_locations[0]
        elif all_locations[0] != values["location_type"]:
            raise ValueError("Location type mismatch")
        return values


class NeighborLoop(Stmt):
    name: SymbolName  # interpret as loop var
    connectivity: SymbolRef
    body: BlockStmt

    # @root_validator(pre=True)
    # def check_location_type(cls, values):
    #     if values["neighbors"].elements[-1] != values["body"].location_type:
    #         raise ValueError("Location type mismatch")
    #     return values


class Access(Expr):
    name: Str


class FieldAccess(Access):
    primary: SymbolRef  # TODO to a PrimaryLocation or a LocationComprehension
    secondary: Optional[SymbolRef]  # TODO unused? # to a LocationRef
    # TODO vertical

    # @property
    # def extent(self):
    #     return len(self.primary.elements) > 1


class VarAccess(Access):
    pass


class AssignStmt(common.AssignStmt[Access, Expr], Stmt):
    pass


class BinaryOp(common.BinaryOp[Expr], Expr):
    pass


class VerticalDimension(Node):
    pass


class HorizontalDimension(Node):
    primary: common.LocationType
    # secondary_connectivity: SymbolRef


class Dimensions(Node):
    horizontal: Optional[HorizontalDimension]
    vertical: Optional[VerticalDimension]
    # other: TODO


class UField(Node):
    name: SymbolName
    vtype: common.DataType
    dimensions: Dimensions


class SparseField(Node):
    name: SymbolName
    vtype: common.DataType
    dimensions: Dimensions
    connectivity: SymbolRef


class TemporaryField(UField):
    pass


class IterationSpace(Node):
    name: SymbolName
    location_type: common.LocationType


class HorizontalLoop(Node, SymbolTableTrait):
    stmt: BlockStmt
    iteration_space: IterationSpace  # maybe inline iterationspace?

    @root_validator(pre=True)
    def check_location_type(cls, values):
        # Don't infer here! The location type of the loop should always come from the frontend!
        if values["stmt"].location_type != values["iteration_space"].location_type:
            raise ValueError("Location type mismatch")
        return values


class VerticalLoop(Node):
    # each statement inside a `with location_type` is interpreted as a full horizontal loop (see parallel model of SIR)
    horizontal_loops: List[HorizontalLoop]
    loop_order: common.LoopOrder


class Stencil(Node):
    vertical_loops: List[VerticalLoop]


class Connectivity(Node):
    name: SymbolName
    primary: common.LocationType
    secondary: common.LocationType
    max_neighbors: int
    has_skip_values: bool


class Computation(Node, SymbolTableTrait):
    name: Str
    connectivities: List[Connectivity]
    params: List[Union[SparseField, UField]]
    stencils: List[Stencil]
    declarations: List[TemporaryField]

    _validate_symbol_refs = stable_gtc_common.validate_symbol_refs()