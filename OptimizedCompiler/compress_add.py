import compiler
from compiler.ast import *


def get_internals(node):
	if not isinstance(node, Add):
		return [node]
	return get_internals(node.left) + get_internals(node.right)

def compress_constants(internals):
	constants = [node for node in internals if isinstance(node, Const)]
	unaries = [node for node in internals if isinstance(node, UnarySub) and isinstance(node.expr, Const)]
	const_unaries = constants + unaries
	if not const_unaries:
		return None
	sum = 0
	for constant in const_unaries:
		if isinstance(constant, Const):
			sum += constant.value
		else:
			sum -= constant.expr.value
	return [Const(sum)]

def make_new_node(internal):
	return reduce(lambda a, b: Add((a, b)), internal)
		

def compress(node):
	internals = get_internals(node)
	const = compress_constants(internals)
	if const is None:
		return node
	non_const = [node for node in internals if not isinstance(node, Const)]
	non_const1 = [node for node in non_const if not (isinstance(node, UnarySub) and isinstance(node.expr, Const))]
	return  make_new_node(non_const1 + const)

def compress_add_helper(n):
    if isinstance(n, Module):
        return compress_add_helper(n.node)
    elif isinstance(n, Stmt):
        stmt = []
        for node in n.nodes:
            e = compress_add_helper(node)
            if isinstance(e, list):
                stmt = stmt + e
            else:
                stmt.append(e)
        return Stmt(stmt)
    elif isinstance(n, Printnl):
        n.nodes = [compress_add_helper(n.nodes[0])]
        return n
    elif isinstance(n, Assign):
        nodes = compress_add_helper(n.nodes[0])
        expr = compress_add_helper(n.expr)
        return Assign(n.nodes, expr)
    elif isinstance(n, AssName):
        return n
    elif isinstance(n, Discard):
        result = compress_add_helper(n.expr)
        return Discard(result)
    elif isinstance(n, Const):
        return n
    elif isinstance(n, Name):
        return n
    elif isinstance(n, Add):
        return compress(n)
    elif isinstance(n, UnarySub):
		n.expr = compress_add_helper(n.expr)
		return n
    elif isinstance(n, Function):
		return n
    elif isinstance(n, Lambda):
	return n
    elif isinstance(n, Return):
		value = compress_add_helper(n.value)
		return Return(value)
    elif isinstance(n, CallFunc):
		return n
    elif isinstance(n, Compare):  #new
        e1 = compress_add_helper(n.expr)
        e2 = compress_add_helper(n.ops[0][1])
        return Compare(e1, [n.ops[0][0], e1])
    elif isinstance(n, And):      #new
        n.nodes[0] = compress_add_helper(n.nodes[0])
        n.nodes[1] = compress_add_helper(n.nodes[1])
        return n
    elif isinstance(n, Or):       #new
        n.nodes[0] = compress_add_helper(n.nodes[0])
        n.nodes[1] = compress_add_helper(n.nodes[1])
        return n
    elif isinstance(n, Not):      #new
        n.expr = compress_add_helper(n.expr)
        return n
    elif isinstance(n, List):     #new
        e = []
        for n in n.nodes:
            e.append(compress_add_helper(n))
        return List(e)
    elif isinstance(n, Dict):     #new
        exp_items = []
        for n in n.items:
            key = compress_add_helper(n[0])
            val = compress_add_helper(n[1])
            exp_items.append((key, val))
        return Dict(exp_items)
    elif isinstance(n, Subscript):     #new
		n.expr =  compress_add_helper(n.expr)
		n.subs[0] = compress_add_helper(n.subs[0])
		return n
    elif isinstance(n, If):
		n.tests[0] = (compress_add_helper(n.tests[0][0]), compress_add_helper(n.tests[0][1]))
		n.else_ = compress_add_helper(n.else_)
		return n
    elif isinstance(n, While):
		n.test = compress_add_helper(n.test)
		n.body = compress_add_helper(n.body)
		return n
    elif isinstance(n, IfExp):
        n.test = compress_add_helper(n.test)
        n.then = compress_add_helper(n.then)
        n.else_= compress_add_helper(n.else_)
        return n
    else:
        print "Error"
        print n
        raise Exception('Error in compress_add_helper: unrecognized AST node')


def compress_add(ast):
	return compress_add_helper(ast)


#ast = compiler.parse('m = 1 + 2 + -3; print m; m = 9+10+10')
#print compress_add(ast)
