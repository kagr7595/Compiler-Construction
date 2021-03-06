#!/usr/bin/python

import compiler
import sys, getopt, os
from x86_ast import *
from compiler.ast import *
from explicate_ast import *


RESERVE = set(['%esp', '%ebp', '%eax'])

# input: list of x86 AST nodes
# return: a list of sets indicating
#         that variables are alive at
#         a given instruction
def liveness_analysis(n, l_after):
    live_variables = [l_after]
    instructions = []
    n.reverse()
    for node in n:
        if isinstance(node, Pushl):
            read = set()
            if isinstance(node.node, Name) and node.node.name not in RESERVE:
				if "func$" not in node.node.name:
					read.add(node.node.name)
            live_variables.append(live_variables[-1] | read)
            instructions.append(node)
        elif isinstance(node, Popl):
            write = set()
            if isinstance(node.node, Name) and node.node.name not in RESERVE:
                write.add(node.node.name)
            live_variables.append(live_variables[-1])# - write) # | set([node.node.name]))
            instructions.append(node)
        elif isinstance(node, PrintX86):
            read = set()
            if isinstance(node.node, Name) and node.node.name not in RESERVE:
                read.add(node.node.name)
            live_variables.append(live_variables[-1] | read)
            instructions.append(node)
        elif isinstance(node, Movl):
            read = set()
            if isinstance(node.left, Name) \
               and node.left.name not in RESERVE \
               and node.left.name[:12] != "unspillable$":
                read.add(node.left.name)
            #create write set
            write = set()
            if isinstance(node.right, Name) \
               and node.right.name not in RESERVE \
               and node.right.name[:12] != "unspillable$":
				write.add(node.right.name)
            l_before = (live_variables[-1] - write) | read
            live_variables.append(l_before)
            instructions.append(node)
        elif isinstance(node, Addl):
            read = set()
            write = set()
            if isinstance(node.left, Name) \
               and node.left.name not in RESERVE \
               and node.left.name[:12] != "unspillable$":
                read.add(node.left.name)
            #create write set
            if isinstance(node.right, Name) \
               and node.right.name not in RESERVE \
               and node.right.name[:12] != "unspillable$":
                write.add(node.right.name)
            l_before = (live_variables[-1] - write) | read
            live_variables.append(l_before)
            instructions.append(node)
        elif isinstance(node, Call):
            read = set()
            if isinstance(node.node, Name) and "$" in node.node.name:
                read.add(node.node.name)
            instructions.append(node)
            live_variables.append(live_variables[-1] | read)
        #elif isinstance(node, PrintX86):
        #    instructions.append(node)
        #    live_variables.append(live_variables[-1])
        elif isinstance(node, Negl):
            if isinstance(node.node, Name) and node.node.name not in RESERVE:
                live_variables.append(live_variables[-1] | set([node.node.name]))
            else:
                live_variables.append(live_variables[-1])
            instructions.append(node)
        elif isinstance(node, NOOP):
            live_variables.append(live_variables[-1])
            instructions.append(node)
        elif isinstance(node, IfStmt):
            then_live = liveness_analysis(node.then, live_variables[-1])
            else_live = liveness_analysis(node.else_, live_variables[-1])
            live = set([])
            for l in zip(*then_live)[1]:
                for e in l:
                     live.add(e)
            for l in zip(*else_live)[1]:
                for e in l:
                     live.add(e)
            #live.append(node.test.name)
            live.add(node.test.name) #live_variables[-1] | set(live)
            live_variables.append(live)
            instructions.append(node)
	elif isinstance(node, While):
		l4 = live_variables[-1]
		l2 = set([])
		cond = set([node.test[0].name])
		while True:
			old_l2 = l2
			l1 = l4 | l2 | cond
			l0 = l1
			l3 = l1
			l2 = set([])
			l2_live = liveness_analysis(node.body, l3)
			for l in zip(*l2_live)[1]:
				for e in l:
					l2.add(e)
			if ((l0 == l1 == l3) and (old_l2 == l2)):
				live_variables.append(l0)
				break
		instructions.append(node)
		test_res = liveness_analysis(node.test[1], live_variables[-1])
		instructions += [i for (i, l) in test_res]
		live_variables += [l for (i, l) in test_res]
        elif isinstance(node, x86Compare):
            read = set()
            if isinstance(node.expr, Name) \
               and node.expr.name not in RESERVE \
               and node.expr.name[:12] != "unspillable$":
                read.add(node.expr.name)
            #create write set
            if isinstance(node.ops[0][1], Name) \
               and node.ops[0][1].name not in RESERVE \
               and node.ops[0][1].name[:12] != "unspillable$":
				read.add(node.ops[0][1].name)
            l_before = live_variables[-1] | read
            live_variables.append(l_before)
            instructions.append(node)
        else:
            print
            print node
            raise Exception('Error in liveness analysis: unrecognized x86 AST node')
    result = zip(instructions, live_variables)
    result.reverse()
    print
    #for p in result:
    #    print p
    n.reverse()
    return result
