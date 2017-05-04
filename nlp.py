import sys, os, re

print ' Loading spacy..',; sys.stdout.flush();
import spacy
nlp = spacy.load('en')
print '.'

def unistr(strg):
	if not isinstance(strg, unicode):
		return unicode(strg, "utf-8")
	return strg

def parse(text):
	#print ' Parsing ..',; sys.stdout.flush();
	doc = nlp(unistr(text))
	#print '.'
	def print_tree(node):
		def print_rec(node, depth):
			print ' {}|_[{}] ({} {})'.format( ''.join([' ']*((depth-1)*2)), node, node.dep_, node.pos_)
			for c in node.children:
				print_rec(c, depth+1)
		print ' [{}] ({} {})'.format(node, node.dep_, node.pos_)
		for c in node.children:
			print_rec(c, 1)
	roots = {}
	for el in doc:
		#print dir(el)
		#print el.pos, el.ent_id, el.i, el.idx, el.head.pos
		if el.i == el.head.i:
			roots[el] = el
	for root in roots:
		print_tree(root)
	if False:
		for np in doc.noun_chunks:
			print ' ', (np.text, np.root.text, np.root.dep_, np.root.head.text)

def main():
	if '-bourb' in sys.argv[1]:
		file_path = 'bourb_el_alg_1.txt'
		def find_matches(rex, text):
			#return re.finditer(rex, text, re.IGNORECASE)
			return re.finditer(rex, text)
		with open(os.path.expanduser(file_path),'r') as f:
			text = f.read()
		pats = ['Definition', 'def-sent']
		pat_rex = {}; pat_matches = {};
		for pat in pats:
			if pat == 'def-sent':
				pat_rex[pat] = r"\b(Definition)(\s*)(\d+)((?:\.\d+)+)*(.)([^.]*)"
			else:
				pat_rex[pat] = r"\b({})(\s*)(\d+)((?:\.\d+)+)*".format(pat)
			#\b(Definition)(\s*)(\d+)((?:\.\d+)+)*.([^.!?]*)+([.!?])
			#\b(Definition)(\s*)(\d+)((?:\.\d+)+)*(.)([^.]*)
			#\b(Definition)(\s*)(\d+)((?:\.\d+)+)*(.\s){1}([a-z\s]*)
			pat_matches[pat] = find_matches(pat_rex[pat], text)
		for mi, match in enumerate(pat_matches['def-sent']):
			def_sent = match.groups()[-1].replace('\n', ' ').strip()
			print '[{}.]'.format(def_sent)
			print ''; parse(def_sent); print '';
			#print match.group()
			if mi >= 20:
				break
		print [(x, sum(1 for _ in pat_matches[x])) for x in pat_rex.keys()]
	elif len(sys.argv) > 1:
		parse(unistr(sys.argv[1]))
	else:
		inp = None
		while inp is None or len(inp):
			if inp is not None:
				print ''; parse(inp); print '';
			inp = raw_input(" Sentence> ")

main()

