import traceback, sys, os, os.path, requests, unidecode, subprocess
import pymysql

g_dbg = '-dbg' in sys.argv
g_verbose = '-verbose' in sys.argv
g_progress = '-progress' in sys.argv
g_outsilent = '-out_silent' in sys.argv

def sys_argv_has(keys):
	if (hasattr(sys, 'argv')):
		return any(x in sys.argv for x in keys)
	return False
def sys_argv_has_key(keys):
	if ( hasattr(sys, 'argv')):
		for key in keys:
			ki = sys.argv.index(key) if key in sys.argv else -1
			if (ki >= 0 and ki+1 < len(sys.argv)):
				return True
	return False
def sys_argv_get(keys, dflt):
	if ( hasattr(sys, 'argv')):
		for key in keys:
			ki = sys.argv.index(key) if key in sys.argv else -1
			if (ki >= 0 and ki+1 < len(sys.argv)):
				return sys.argv[ki+1]
	return dflt
gPrintCol = [ 'default', 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'bdefault', 'bblack', 'bred', 'bgreen', 'byellow', 'bblue', 'bmagenta', 'bcyan', 'bwhite'  ]
gPrintColCode = [ "\x1B[0m", "\x1B[30m", "\x1B[31m", "\x1B[32m", "\x1B[33m", "\x1B[34m", "\x1B[35m", "\x1B[36m", "\x1B[37m",
"\x1B[49m", "\x1B[40m", "\x1B[41m", "\x1B[42m", "\x1B[43m", "\x1B[44m", "\x1B[45m", "\x1B[46m", "\x1B[47m", ]
gAltCols = [ gPrintCol.index(x) for x in ['default', 'yellow'] ]
gLastColI = 0
def vt_coli(coli):
	global gLastColI; gLastColI = coli;
	coli = coli % len(gPrintCol)
	code = gPrintColCode[coli]
	sys.stdout.write(code)
	#sys.stdout.write('\x1B[{}D'.format(len(code)-3))
def vt_col(col):
	vt_coli(gPrintCol.index(col))
def vt_col_code(col):
	return gPrintColCode[gPrintCol.index(col)]


k_wikioff_db = 'enwiki-20170520'.replace('-', '_')
k_wikioff_db_usr = 'root'

def wikioff_get_cat_edges(cur, cat_title, get_parents=True, get_children=True):
	children = []
	parents = []
	cmd_children = "select P.page_title from page as P, categorylinks as CL where CL.cl_to='{}' and CL.cl_type='subcat' and P.page_id=CL.cl_from and P.page_namespace=14".format(cat_title.replace("'", "\\'"))
	cmd_parents = "select CL.cl_to from page as P, categorylinks as CL where P.page_title='{}' and P.page_namespace=14 and CL.cl_from=P.page_id and CL.cl_type='subcat'".format(cat_title.replace("'", "\\'"))
	if get_children:
		cur.execute(cmd_children)
		children.extend([x[0] for x in cur.fetchall()])
	if get_parents:
		cur.execute(cmd_parents)
		parents.extend([x[0] for x in cur.fetchall()])
	return (parents, children)

def wikioff_cat_graph_down(cur, cat_title, max_depth, verbose=False, progress=False):
	graph = {}
	recurse_subs = []
	def edges(node):
		if node in graph:
			return graph[node]
		graph[node] = {}
		if progress and not verbose:
			info_str = '{}. [{}]...'.format(len(graph), node)
			sys.stdout.write('\x1B[2K'); sys.stdout.write('\r'); sys.stdout.write(' {}'.format(info_str)); sys.stdout.flush();
		return edges(node)
	def recurse():
		while len(recurse_subs) > max_depth:
			return
		next_subs = []
		for sub in recurse_subs[-1]:
			sub_children = wikioff_get_cat_edges(cur, sub, False, True)[1]
			for sub_child in sub_children:
				edges(sub)[sub_child] = ''
			next_subs.extend(sub_children)
		if verbose:
			print '---{}---\n'.format(len(recurse_subs)),next_subs,'\n'
		recurse_subs.append(next_subs)
		recurse()
	recurse_subs.append([cat_title])
	recurse()
	if progress and not verbose:
		print ' (done)'
	return graph

def wikioff_graph_node_purity(cur, graph, cat_title):
	def list_diff(l1, l2):
		sl1 = set(l1); sl2 = set(l2); slu = sl1.union(sl2)
		return [x for x in slu if x in sl1 and x not in sl2 or x in sl2 and x not in sl1]
	def extract_parents(graph, node):
		parents = []
		for k,v in graph.items():
			if node in v:
				parents.append(k)
		return parents
	cat_parents, cat_children = wikioff_get_cat_edges(cur, cat_title, True, True)
	graph_children = graph[cat_title]
	graph_parents = extract_parents(graph, cat_title)
	diff_parents = list_diff(cat_parents, graph_parents)
	diff_children = list_diff(cat_children, graph_children)
	return (diff_parents, diff_children)

def wikioff_graph_node_is_pure(cur, graph, cat_title):
	diff_parents, diff_children = wikioff_graph_node_purity(cur, graph, cat_title)
	return len(diff_parents) + len(diff_children) == 0

def wikioff_graph_pure_nodes(cur, graph):
	ret = []
	for i,k in enumerate(sorted(graph.keys())):
			if wikioff_graph_node_is_pure(cur, graph, k):
				ret.append(k)
	return ret


def wikioff_print_graph_purity(cur, graph, verbose=False):
	col_pure = 'green'; col_impure = 'yellow';
	for i,k in enumerate(sorted(graph.keys())):
		if verbose:
			status = wikioff_graph_node_purity(cur, graph, k)
			is_pure = len(status[0])+len(status[1]) == 0
		else:
			status = 'yes' if wikioff_graph_node_is_pure(cur, graph, k) else 'no'
			is_pure = status == 'yes'
		print ' {}. {}[{}]{} : {}'.format(i, vt_col_code(col_pure if is_pure else col_impure), k, vt_col_code('default'), status)

def wikioff_graph_to(graph, file_path, cat_title='', accepted_nodes = None):
	import graphviz
	accepted_nodes = set(accepted_nodes) if accepted_nodes is not None else None
	def accept(node):
		return accepted_nodes is None or k in accepted_nodes
	def make_node_name(strg):
		return strg.replace(' ', '_').replace('.', '_').lower()
	gviz = graphviz.Digraph(comment='Analysis of "[{}]"'.format(cat_title))
	for k in graph.keys():
		if accept(k):
			gviz.node(make_node_name(k))
	for k,v in graph.items():
		if accept(k):
			for vv in v:
				if accept(vv):
					gviz.edge(make_node_name(k), make_node_name(vv))
	#print gviz.source
	dot_fpath = file_path+'.dot'
	with open(os.path.expanduser(dot_fpath),'w') as fo:
		fo.write(gviz.source)
	if g_outsilent == False:
		print ' > out: [{}]'.format(dot_fpath)
	pdf_fpath = dot_fpath+'.pdf'
	pop_in = ['dot', '-Tpdf', '"-o{}"'.format(pdf_fpath), '"{}"'.format(dot_fpath)]
	pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
	out, err = pop.communicate()
	if g_outsilent == False:
		print ' > out: [{}]'.format(pdf_fpath)
	if g_dbg and len(err):
		vt_col('red'); print err; vt_col('default')

def test1():
	try:
		conn = pymysql.connect(db=k_wikioff_db, user=k_wikioff_db_usr)
		cur = conn.cursor(pymysql.cursors.SSCursor)
		cur2 = conn.cursor(pymysql.cursors.SSCursor)
		depth_subs = []
		def get_cat_direct_subs(cat_title):
			cmd_1 = "select P.page_title from page as P, categorylinks as CL where CL.cl_to='{}' and CL.cl_type='subcat' and P.page_id=CL.cl_from and P.page_namespace=14".format(cat_title.replace("'", "\\'"))
			cur.execute(cmd_1)
			my_subs = []
			for row in cur.fetchall():
				sub_title = row[0]
				accepted = True
				if len(depth_subs) == 2:
					print 'Checking: ', sub_title
					cmd_2 = "select CL.cl_to from page as P, categorylinks as CL where P.page_title='{}' and P.page_namespace=14 and CL.cl_from=P.page_id and CL.cl_type='subcat'".format(sub_title.replace("'", "\\'"))
					cur2.execute(cmd_2)
					had_rows = False
					for row in cur2.fetchall():
						print row
						had_rows = True
					if had_rows:
						sys.exit(1)
				my_subs.append(sub_title)
			return my_subs
		def bf_get_cat_subs(max_depth):
			while len(depth_subs) > max_depth:
				return
			single_direct_subs = []
			for sub in depth_subs[-1]:
				single_direct_subs.extend(get_cat_direct_subs(sub))
			print '---{}---\n'.format(len(depth_subs)),single_direct_subs
			depth_subs.append(single_direct_subs)
			bf_get_cat_subs(max_depth)
		depth_subs.append(['Fields_of_mathematics'])
		bf_get_cat_subs(sys.argv[sys.argv.index('-depth')+1] if '-depth' in sys.argv else 2)
		#print depth_subs
	except:
		traceback.print_exc()
	finally:
		if cur2:
			cur2.close()
		if cur:
			cur.close()
		if conn:
			conn.close()

def wikioff_run_with_conn(lbda):
	try:
		conn = pymysql.connect(db=k_wikioff_db, user=k_wikioff_db_usr)
		cur = conn.cursor(pymysql.cursors.SSCursor)
		return lbda(cur)
	except:
		traceback.print_exc()
	finally:
		if cur:
			cur.close()
		if conn:
			conn.close()

def test2():
	cat_title = sys_argv_get(['-cat'], 'Fields_of_mathematics')
	graph = wikioff_run_with_conn(lambda cur: wikioff_cat_graph_down(cur, cat_title, int(sys_argv_get(['-depth'], 2)), verbose=False, progress=g_progress))
	if sys_argv_has(['-purity']):
		wikioff_run_with_conn(lambda cur: wikioff_print_graph_purity(cur, graph, verbose=g_verbose))
	else:
		print ' total nodes: {}'.format(len(graph))
	if sys_argv_has(['-write']):
		if sys_argv_has(['-full']):
			wikioff_graph_to(graph, 'full_'+cat_title, cat_title)
		pure_nodes = wikioff_run_with_conn(lambda cur: wikioff_graph_pure_nodes(cur, graph))
		wikioff_graph_to(graph, cat_title, cat_title, pure_nodes)

#test1()
#print wikioff_run_with_conn(lambda cur: wikioff_get_cat_edges(cur, 'Fields_of_mathematics'))
#print wikioff_run_with_conn(lambda cur: wikioff_cat_graph_down(cur, 'Fields_of_mathematics', 2, verbose=g_verbose)), '\n'
test2()
