import compiler
from compiler.ast import *


def get_internals(node):
	if not (isinstance(node, And) or isinstance(node, Or) or isinstance(node, Not)):
		return [node]
	if isinstance(node, Not):
		return get_internals(node.expr)
	else:
		return get_internals(node.nodes[0]) + get_internals(node.nodes[1])

def compress_boolean_operations(internals, logic):
	nodes = [node for node in internals if (isinstance(node, Const) or \
        (isinstance(node, Name) and (node.name == 'True' or node.name == 'False')))]

	if not nodes:
		return None
	
	#if isinstance(logic, And):
	#	logic_out = 1  
	#elif isinstance(logic, Or):
	#	logic_out = 0 

	#for node in nodes:
	if isinstance(logic, And):
			if isinstance(nodes[0], Const):
                                if nodes[0].value == 0:
                                        return nodes[0]
                                else:
                                        return nodes[1]
                        elif isinstance(nodes[0], Name):
                                if nodes[0].name == False:
                                        return nodes[0]
                                else:
                                        return nodes[1]	
                     	
			#	logic_out = logic_out and node.value
			#elif isinstance(node, Name):
			#	logic_out = logic_out and node.name
	elif isinstance(logic, Or):
			if isinstance(nodes[0], Const):
                                if nodes[0].value != 0:
                                        return nodes[0]
                                else:
                                        return nodes[1]	
                        elif isinstance(nodes[0], Name):
                                if nodes[0].name != False:
                                        return nodes[0]
                                else:
                                        return nodes[1]	
                        #if isinstance(node, Const):
			#	logic_out = logic_out or node.value
			#elif isinstance(node, Name) and (node.name == 'True' or node.name == 'False'):
			#	logic_out = logic_out or node.name
                                
		        if isinstance(logic, Not):
			        if isinstance(node, Const):	
				        logic_out = not node.value
			        elif isinstance(node, Name) and (node.name == 'True' or node.name == 'False'):
				        logic_out = True if node.name == 'False' else False
	return [logic_out]

def make_new_node(internal, node):
	return reduce(lambda a, b: And([a, b]), internal) if isinstance(node, And) else reduce(lambda a, b: Or([a, b]), internal)
		

def compress(node):
	internals = get_internals(node)
	op = compress_boolean_operations(internals, node)

	if op is None:
		return node
 
	non_bool_op = [n for n in internals if not (isinstance(n, Const) or \
        (isinstance(n, Name) and (n.name == 'True' or n.name == 'False')))]

        print non_bool_op

	if isinstance(op, Name):
		if str(op[0].name) == 'False' and isinstance(node, And):
			return Name(str(op[0].name))
		elif str(op[0].name) == 'True' and isinstance(node, Or):
			return Name(str(op[0].name))	
		op[0].name = str(op[0].name)

	elif isinstance(op, Const):
		if op.value == 0 and isinstance(node, And):
			return op
		elif op.value == 1 and isinstance(node, Or):
			return op

	if isinstance(node, Not):
		return op

	return  make_new_node([op] + non_bool_op, node)

def compress_boolean_helper(n):
    if isinstance(n, Module):
        return compress_boolean_helper(n.node)
    elif isinstance(n, Stmt):
        stmt = []
        for node in n.nodes:
            e = compress_boolean_helper(node)
            if isinstance(e, list):
                stmt = stmt + e
            else:
                stmt.append(e)
        return Stmt(stmt)
    elif isinstance(n, Printnl):
        n.nodes = [compress_boolean_helper(n.nodes[0])]
        return n
    elif isinstance(n, Assign):
        nodes = compress_boolean_helper(n.nodes[0])
        expr = compress_boolean_helper(n.expr)
        return Assign(n.nodes, expr)
    elif isinstance(n, AssName):
        return n
    elif isinstance(n, Discard):
        result = compress_boolean_helper(n.expr)
        return Discard(result)
    elif isinstance(n, Const):
        return n
    elif isinstance(n, Name):
        return n
    elif isinstance(n, Add):
	n.left = compress_boolean_helper(n.left)
        n.right = compress_boolean_helper(n.right)
        return compress(n)
    elif isinstance(n, UnarySub):
		n.expr = compress_boolean_helper(n.expr)
		return n
    elif isinstance(n, Function):
		return n
    elif isinstance(n, Lambda):
	return n
    elif isinstance(n, Return):
		value = compress_boolean_helper(n.value)
		return Return(value)
    elif isinstance(n, CallFunc):
		return n
    elif isinstance(n, Compare):  #new
        e1 = compress_boolean_helper(n.expr)
        e2 = compress_boolean_helper(n.ops[0][1])
        return Compare(e1, [n.ops[0][0], e1])
    elif isinstance(n, And):      #new
        return compress(n)
    elif isinstance(n, Or):       #new
        return compress(n)
    elif isinstance(n, Not):      #new
        return compress(n)
    elif isinstance(n, List):     #new
        e = []
        for n in n.nodes:
            e.append(compress_boolean_helper(n))
        return List(e)
    elif isinstance(n, Dict):     #new
        exp_items = []
        for n in n.items:
            key = compress_boolean_helper(n[0])
            val = compress_boolean_helper(n[1])
            exp_items.append((key, val))
        return Dict(exp_items)
    elif isinstance(n, Subscript):     #new
		n.expr =  compress_boolean_helper(n.expr)
		n.subs[0] = compress_boolean_helper(n.subs[0])
		return n
    elif isinstance(n, If):
		n.tests[0] = (compress_boolean_helper(n.tests[0][0]), compress_boolean_helper(n.tests[0][1]))
		n.else_ = compress_boolean_helper(n.else_)
		return n
    elif isinstance(n, While):
		n.test = compress_boolean_helper(n.test)
		n.body = compress_boolean_helper(n.body)
		return n
    elif isinstance(n, IfExp):
        n.test = compress_boolean_helper(n.test)
        n.then = compress_boolean_helper(n.then)
        n.else_= compress_boolean_helper(n.else_)
        return n
    else:
        print "Error"
        print n
        raise Exception('Error in compress_boolean_helper: unrecognized AST node')


def compress_booleans(ast):
	return compress_boolean_helper(ast)


ast = compiler.parse('(0 or 42) and (True or False)')
print compress_booleans(ast)
