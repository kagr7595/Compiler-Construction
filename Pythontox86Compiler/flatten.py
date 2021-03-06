#!/usr/bin/python

import compiler
import sys, getopt, os
from x86_ast import *
from compiler.ast import *
from liveness_analysis import *
from generate_rig import *
from color_graph import *
from generate_spill_code import *
from explicate_ast import *

# meaningfully named constants
TEMP_COUNT = 0
ATOMIC     = 0
BINDINGS   = 1

# return: the next variable name
def get_variable_name():
    global TEMP_COUNT
    variable_name = "temp$" + str(TEMP_COUNT)
    TEMP_COUNT = TEMP_COUNT + 1
    return variable_name

def flatten_ast(stmts):
	flattened_stmts = []
	for stmt in stmts:
		flattened = flatten_stmt(stmt)
		flattened_stmts = flattened_stmts + flattened
	return flattened_stmts

def flatten_stmt(s):
	if isinstance(s, Printnl):
		[atomic, bindings] = flatten_expr(s.nodes[0])
		return bindings + [Printnl([atomic], s.dest)]
	elif isinstance(s, CallFunc):
		return flatten_expr(s)[1]
	elif isinstance(s, Assign):
		atomic_n = s.nodes
		bindings_n = []
		if isinstance(s.nodes, Subscript):
			[atomic_n, bindings_n] = flatten_expr(s.nodes)
		[atomic_e, bindings_e] = flatten_expr(s.expr)
		return bindings_e + bindings_n + [Assign(atomic_n, atomic_e)]
	elif isinstance(s, Discard):
		[atomic, bindings] = flatten_expr(s.expr)
		return bindings + [Discard(atomic)]
	elif isinstance(s, Return):
		[atomic, bindings] = flatten_expr(s.value)
		return bindings + [Return(atomic)]
	elif isinstance(s, Let):
		[atomic, bindings] = flatten_expr(s)
		return bindings + [Discard(atomic)]
	elif isinstance(s, If):
		then = flatten_ast(s.tests[0][1])
		else_ = flatten_ast(s.else_)
		[atomic, bindings] = flatten_expr(s.tests[0][0])
		return bindings + [IfStmt(then, atomic, else_)]
	elif isinstance(s, While):
		s.body = Stmt(flatten_ast(s.body))
		s.test = flatten_expr(s.test)
		return [s]
	elif isinstance(s, Lambda):
		[atomic, bindings] = flatten_expr(s)
		return [atomic]
	#elif isinstance(s, FunctionCl):
	#	fvs_res = [flatten_expr(fvs) for fvs in s.fvs]
	#	params_res = [flatten_expr(params) for params in s.params]
	#	lambda_args = [f for (f, b) in fvs_res] + [p for (p, b) in params_res]
	#	flat_code = flatten_ast(s.code)
	#	return bindings_fvs + bindings_params + [Lambda(lambda_args, s.name, None, flat_code] 
	else:
		print
		print s
		raise Exception('unrecognized statement node %s' % s)


def flatten_expr(n):
    def make_assign(lhs, rhs):
        return Assign([AssName(lhs, 'OP_ASSIGN')], rhs)

    def atomic_bindings(flat_expr, bindings):
        var = get_variable_name()
        return [Name(var), bindings + [make_assign(var, flat_expr)]]

    # Handle expressions in P1
    # return [atomic, bindings]
    if isinstance(n, Assign):
        res = flatten_expr(n.expr)
        if isinstance(n.nodes[0], AssName):
            return res[BINDINGS] + [Assign(n.nodes, res[ATOMIC])]
        else:
			flat_nodes = flatten_expr(n.nodes[0])
			return res[BINDINGS] + [Assign(flat_nodes, res[ATOMIC])]
    elif isinstance(n, AssName):
        return [n, []]
    elif isinstance(n, Const):
		return [n, []]
    elif isinstance(n, Name):
		return [n, []]
    elif isinstance(n, Lambda):
		#(atomic_args, bindings_args) = flatten_expr(n.argnames)
		code = flatten_ast(n.code)
		return (Lambda(n.argnames, n.defaults, n.flags, code), [])
		#return make_assign(n.defaults, (Lambda(n.argnames, n.defaults, n.flags, code), []))
    elif isinstance(n, Add):
        (atomic_l, bindings_l) = flatten_expr(n.left)
        (atomic_r, bindings_r) = flatten_expr(n.right)
        return atomic_bindings(Add((atomic_l, atomic_r)), bindings_l + bindings_r)
    elif isinstance(n, UnarySub):
        (atomic, bindings) = flatten_expr(n.expr)
        return atomic_bindings(UnarySub(atomic), bindings)
    elif isinstance(n, CallFunc):
		flat_args = []
		bindings = []
		if n.args:
			for a in n.args:
				flat_a = flatten_expr(a)
				flat_args.append(flat_a[ATOMIC])
				bindings = bindings + flat_a[BINDINGS]
		(atomic_n, atomic_binding) = flatten_expr(n.node)
		#if isinstance(n.node, Lambda):
		#	atomic_n = Name(n.node.defaults)
		bindings += atomic_binding
		#return atomic_bindings(CallFunc(Name(n.node.name), flat_args, None, None), bindings)
		return atomic_bindings(CallFunc(atomic_n, flat_args, None, None), bindings)
    elif isinstance(n, IndirectCallFunc):
		# flatten n.node: should be a CallFunc
		(f, bindings_f) = flatten_expr(n.func_ptr)
		print "free_vars"
		if n.free_vars:
			(fv, bindings_fv) = flatten_expr(n.free_vars)
		else:
			fv = None
			bindings_fv = []
		# flatten the args
		arg_pairs = [flatten_expr(a) for a in n.args if a]
		args = [a for (a, b) in arg_pairs]
		bindings_a = reduce(lambda a, b: a + b, [b for (a, b) in arg_pairs], [])
		return atomic_bindings(IndirectCallFunc(f, fv, args), bindings_f + bindings_fv + bindings_a)
    elif isinstance(n, CreateClosure):
		(a, bindings) = flatten_expr(n.argnames)
		#arg_pairs = [flatten_expr(a) for a in n.argnames if a]
		#args = [a for (a, b) in arg_pairs]
		#bindings = reduce(lambda a, b: a + b, [b for (a, b) in arg_pairs], [])
		n.argnames = a
		return atomic_bindings(n, bindings)
    elif isinstance(n, IfExp):
		(flat_test, test_a) = flatten_expr(n.test)
		(flat_then, then_a) = flatten_expr(n.then)
		(flat_else, else_a)= flatten_expr(n.else_)
		temp = get_variable_name()

		bindings = test_a + [IfStmt(then_a + [make_assign(temp, flat_then)], \
						flat_test, \
						else_a + [make_assign(temp, flat_else)])]
		return [Name(temp), bindings]
    elif isinstance(n, Compare):
		(atomic_l, bindings_l) = flatten_expr(n.expr)
		(atomic_r, bindings_r) = flatten_expr(n.ops[0][1])
		return atomic_bindings(Compare(atomic_l, [n.ops[0][0], atomic_r]), bindings_l + bindings_r)
    elif isinstance(n, Subscript):
		(atomic_expr, bindings_expr) = flatten_expr(n.expr)
		if n.flags == "OP_ASSIGN":
			if isinstance(n.subs, list):
				(atomic_subs, bindings_subs) = flatten_expr(n.subs[0])
			else:
				(atomic_subs, bindings_subs) = flatten_expr(n.subs)
		else:
			if isinstance(n.subs, list):
				(atomic_subs, bindings_subs) = flatten_expr(n.subs[0])
			else:
				(atomic_subs, bindings_subs) = flatten_expr(n.subs)
		#var = get_variable_name()
		return atomic_bindings(Subscript(atomic_expr, n.flags, atomic_subs), bindings_expr + bindings_subs)
		#return Assign([AssName(var, 'OP_ASSIGN')], Subscript(atomic_expr, n.flags, atomic_subs), bindings_expr + bindings_subs)
		#return atomic_bindings(CallFunc(Name('get_subscript'), [atomic_subs, atomic_expr], None, None), bindings_expr + bindings_subs)
		#var = get_variable_name()
		#bindings = flat_expr[BINDINGS] + flat_subs[BINDINGS] + [Assign([AssName(var, 'OP_ASSIGN')], \
		#return Subscript(flat_expr[ATOMIC], n.flags, [flat_subs[ATOMIC]])
		#return [Name(var), bindings]
    elif isinstance(n, GetTag):
		(atomic, bindings) = flatten_expr(n.arg)
		return atomic_bindings(GetTag(n.typ, atomic), bindings)
    elif isinstance(n, InjectFrom):
		(atomic, bindings) = flatten_expr(n.arg)
		return atomic_bindings(InjectFrom(n.typ, atomic), bindings)
    elif isinstance(n, ProjectTo):
		(atomic, bindings) = flatten_expr(n.arg)
		return atomic_bindings(ProjectTo(n.typ, atomic), bindings)
    elif isinstance(n, Let):
		(atomic_rhs, bindings_rhs) = flatten_expr(n.rhs)
		rhs_assign = make_assign(n.var.name, atomic_rhs)
		(atomic_body, bindings_body) = flatten_expr(n.body)
		body_assign = get_variable_name()
		#return atomic_bindings(make_assign(body_assign, atomic_body), bindings_rhs + bindings_body)
		return [Name(body_assign), bindings_rhs + [rhs_assign] + bindings_body + [Assign([AssName(body_assign, 'OP_ASSIGN')], atomic_body)]]
    elif isinstance(n, List):
		bindings = []
		flat_exprs = []
		for expr in n.nodes:
			(flat_expr, bindings_flat) = flatten_expr(expr)
			bindings = bindings + bindings_flat
			flat_exprs.append(flat_expr)
		return atomic_bindings(List(flat_exprs), bindings)
    elif isinstance(n, Dict):
		bindings = []
		flat_items = []
		for item in n.items:
			(flat_key, bindings_key) = flatten_expr(item[0])
			(flat_val, bindings_val) = flatten_expr(item[1][0])
			bindings = bindings + bindings_key + bindings_val
			flat_items.append((flat_key, flat_val))
		return atomic_bindings(Dict(flat_items), bindings)
    else:
		print
		print n
		print
		raise Exception('Error in flatten_expr: unrecognized AST node')

