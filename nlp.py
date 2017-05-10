import sys, os, re
import requests

if '-no_spacy' not in sys.argv:
	print ' Loading spacy..',; sys.stdout.flush();
	import spacy
	nlp = spacy.load('en')
	print '.'

def fpjoin(aa):
	ret = os.path.join(aa[0], aa[1])
	for a in aa[2:]:
		ret = os.path.join(ret,a)
	return ret
def fphere():
	return os.path.dirname(os.path.realpath(__file__))
def fpjoinhere(aa):
	return fpjoin([fphere()]+aa)
def fptemp():
	return fpjoin([fphere(), 'temp'])
def cwdtemp():
	os.chdir(fptemp())
def mktemp():
	if os.path.isdir(fptemp()) == False:
		os.mkdir(fptemp())
def randfilename(dir, pre, ext):
	i = 1
	while True:
		fname = "{}{}.{}".format(pre, i, ext)
		if (os.path.isfile(os.path.join(dir, fname)) == False):
			return fname
		i=i+1

def unistr(strg):
	if not isinstance(strg, unicode):
		return unicode(strg, "utf-8")
	return strg

def find_word_type(word):
	def clean_word(strng):
		ret = ''.join(ch for ch in strng.strip() if ch.isalnum() or ch in ['-']).lower()
		return '' if any(x.isdigit() for x in ret) else ret
	def is_valid_path(path):
		return os.path.exists(path) or os.access(os.path.dirname(path), os.W_OK)
	word = clean_word(word)
	dict_temp = os.path.join(fptemp(), 'dict')
	mktemp()
	if os.path.isdir(dict_temp) == False:
		os.mkdir(dict_temp)
	word_cache_path = os.path.join(dict_temp, 'cache_{}.txt'.format(word))
	is_cacheable = is_valid_path(word_cache_path)
	has_cache = os.path.exists(word_cache_path)
	if is_cacheable and (has_cache == False):
		site = 'en.wiktionary.org'
		site = 'en.wikipedia.org'
		url = 'https://{}/w/api.php?action=query&titles={}&prop=extracts&format=json'.format(site, word)
		print ' querying [{}]'.format(word),; sys.stdout.flush();
		resp = requests.post(url)
		print '.',
		with open(word_cache_path, 'w') as fo:
			fo.write(resp.text)
	if os.path.exists(word_cache_path):
		resp_text = ''
		with open(word_cache_path, 'r') as fi:
			resp_text = fi.read().lower()
		word_type = ''
		if any(x in resp_text for x in ['mathematics', 'mathematical']):
			word_type = 'math'
		elif 'The requested page title contains invalid characters'.lower() in resp_text:
			word_type = ''
		elif '"missing":""' in resp_text:
			word_type = ''
		else:
			word_type = 'nonmath'
	return word_type

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
		if True:
			all_words = {}
			for word in text.split():
				word = word.strip()
				if len(word):
					all_words[word] = all_words.get(word, 0) + 1
			def_all_words = {}
			for mi, match in enumerate(pat_matches['def-sent']):
				def_sent = match.groups()[-1].replace('\n', ' ').strip()
				for word in def_sent.split(' '):
					word = word.strip()
					if len(word):
						def_all_words[word] = def_all_words.get(word, 0) + 1
						#if word == '(resp':
						#	print '[{}.]'.format(def_sent)
			#print all_words['(resp'], def_all_words['(resp']; sys.exit(0);
			if True:
				#def_all_words = dict([kv for kv in def_all_words.items() if kv[0] in all_words and all_words[kv[0]] > 100 ])
				def_all_words = dict([kv for kv in sorted(def_all_words.items(), key = lambda x: x[0]) if kv[0] in all_words and all_words[kv[0]] > 20 and find_word_type(kv[0]) != 'math' ]); print '';
			def_all_words_lst = sorted(def_all_words.items(), key = lambda x: -x[1])
			#print len(def_all_words_lst), def_all_words_lst[:20]
			#def_words_in_all_words = [(kv[0], max(all_words.get(kv[0], -1), kv[1]) ) for kv in def_all_words.items()]
			def_words_in_all_words = dict([(kv[0], all_words[kv[0]]) for kv in def_all_words.items() if kv[0] in all_words])
			words_not_in_def = [x for x in all_words.keys() if x not in def_all_words]
			#print len(all_words), len(words_not_in_def), len(def_all_words); sys.exit(0);
			#print sorted(def_all_words.items(), key=lambda x: x[0])[:20]
			#print sorted(def_words_in_all_words)[:20]
			total_in_def = sum(def_all_words.values())
			total_in_all = sum(def_words_in_all_words.values())
			print total_in_def, total_in_all
			if True:
				buckets_def = {}
				for kv in def_all_words.items():
					buckets_def[kv[1]] = buckets_def.get(kv[1], []) + [kv[0]]
				buckets_all = {}
				for kv in def_words_in_all_words.items():
					buckets_all[kv[1]] =  buckets_all.get(kv[1], []) + [kv[0]]
				buck_sort_def = sorted(buckets_def.items(), key = lambda x: x[0])
				buck_sort_all = sorted(buckets_all.items(), key = lambda x: x[0])
				movers = []
				for k in def_all_words.keys():
					def find_buck_index(bucks, k):
						for i,buck in enumerate(bucks):
							if k in buck[1]:
								return i
						return -1
					movers.append( (k, find_buck_index(buck_sort_def, k)-find_buck_index(buck_sort_all, k) ) )
				mover_dict = dict(movers)
				print mover_dict['called']
				movers = sorted(movers, key = lambda x: -(x[1]))
				print movers[:50]
				if False:
					count_sort_in_def = sorted(def_all_words.keys(), key= lambda x: def_all_words[x])
					count_sort_in_all = sorted(def_words_in_all_words, key= lambda x: def_words_in_all_words[x])
					print [(x, def_all_words[x]) for x in count_sort_in_def[:20]]
					print [(x, def_words_in_all_words[x]) for x in count_sort_in_all[:20]]
					print def_all_words['qf'], def_words_in_all_words['qf'];
					movers = sorted([(x, count_sort_in_def.index(x)-count_sort_in_all.index(x) ) for x in def_all_words], key=lambda x: -x[1])
					print movers[:20]
			if True:
				ratios_in_def = dict([(kv[0], float(kv[1])/total_in_def) for kv in def_all_words.items()])
				ratios_in_all = dict([(kv[0], float(kv[1])/total_in_all) for kv in def_words_in_all_words.items()])
				ratio_diff_map = [ (x, ratios_in_def[x]/ratios_in_all[x]) for x in def_all_words.keys() if (x in ratios_in_def and x in ratios_in_all) ]
				ratio_diff_map = sorted(ratio_diff_map, key = lambda x: -x[1])
				print ''
				print [ (x, def_all_words[x[0]], all_words.get(x[0], -1)) for x in ratio_diff_map[:100]]
				print ''
		if False:
			for mi, match in enumerate(pat_matches['def-sent']):
				def_sent = match.groups()[-1].replace('\n', ' ').strip()
				print '[{}.]'.format(def_sent)
				print ''; parse(def_sent); print '';
				#print match.group()
				if mi >= 20:
					break
		if True:
			for pat in pats:
				pat_matches[pat] = find_matches(pat_rex[pat], text)
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

