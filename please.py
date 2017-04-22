import sys, subprocess, os, math, os.path, traceback, time, shutil
import urllib, urllib2, urlparse
import re
import json
try:
	#import urllib2.urlparse
	import requests
	import lxml
	import lxml.html
	import lxml.cssselect
except ImportError:
	lxml = None
try:
	import unidecode
except ImportError:
	unidecode = None
try:
	import graphviz
except ImportError:
	graphviz = None

g_dbg = False

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

def print_and_choose(list, indent='', postindex = False, forceChoose = False):
	if (len(list) == 0): return []
	if (len(list) == 1 and forceChoose == False): return [0]
	for i in range(len(list)):
		vt_coli(gAltCols[i % len(gAltCols)])
		if postindex:
			print indent + '. {} ({})'.format(list[i], i+1)
		else:
			print indent + '{}. {}'.format(i+1, list[i])
	vt_col('default')
	print '>',
	input_str = raw_input()
	choices = []
	if ('-' in input_str):
		list = input_str.split('-')
		choices = range(int(list[0]), int(list[1])+1)
	elif (',' in input_str):
		choices = [int(x) for x in input_str.split(',')]
	else:
		if len(input_str):
			choices.append(int(input_str))
	choices = [i-1 for i in choices]
	return choices

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
def fileSize(num, suffix='b'):
	for unit in ['','K','M','G','T','P','E','Z']:
			if abs(num) < 1024.0:
					return "%3.1f %s%s" % (num, unit, suffix)
			num /= 1024.0
	return "%.1f %s%s" % (num, 'Y', suffix)
def long_substr(data):
	substr = ''
	if len(data) > 1 and len(data[0]) > 0:
		for i in range(len(data[0])):
			for j in range(len(data[0])-i+1):
				if j > len(substr) and is_substr(data[0][i:i+j], data):
					substr = data[0][i:i+j]
	return substr
def is_substr(find, data):
	if len(data) < 1 and len(find) < 1:
		return False
	for i in range(len(data)):
		if find not in data[i]:
			return False
	return True
def hash_str_12(s):
	return abs(hash(s)) % (10 ** 12)
def format_proc_out(err, indent=''):
	return [indent + x.strip() for x in err.split('\n') if (len(x.strip()))] if len(err) else []
def print_formatted_proc_err(elines):
	if len(elines):
		vt_col('red'); print elines; vt_col('default');
def textSearchPdfDjvu(path, phrase):
	fname_, fext = os.path.splitext(path); fext = fext.lower();
	if (fext.lower() == '.pdf'):
		args = ['pdftotext', '\"{}\"'.format(path), '-', '|', 'grep', '\"{}\"'.format(phrase)]
	elif (fext.lower() == '.djvu'):
		args = ['djvutxt', '\"{}\"'.format(path), '|', 'grep', '\"{}\"'.format(phrase)]
	else:
		return ([],[])
	#print ' '.join(args)
	proc = subprocess.Popen(' '.join(args), stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	elines = format_proc_out(err, ' '); lines = format_proc_out(out)
	return (elines, lines)
def content_to_pdf(content, pdf):
	pop_in = ['node', fpjoinhere(['npm', 'arg_to_pdf.js']), '"{}"'.format(content), pdf]
	#print ' '.join(pop_in)
	pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = pop.communicate()
	if err and len(err):
		print err
		return False
	return True
def url_to_pdf(url, pdf, delay = None):
	if False:
		pop_in = ['wkhtmltopdf', '-q', '' if delay is None else '--javascript-delay {}'.format(int(delay*1000)), '"{}"'.format(url), pdf]
	else:
		pop_in = ['node', fpjoinhere(['npm', 'url_to_pdf.js']), '"{}"'.format(url), pdf]
	#print ' '.join(pop_in)
	pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = pop.communicate()
	if err and len(err):
		print err
		return False
	return True
def url_download(url, fp):
	try:
		response = urllib2.urlopen(url)
		file = open(fp, 'w')
		file.write(response.read())
		file.close()
		return True
	except:
		print ' Error'
	return False
def process_scrape(arg, stay_in = None):
	if lxml == None:
			print "You need to install 'lxml' and 'requests' first."
			return
	mktemp()
	temps = []
	#try to get main page as pdf
	src_pdf_fp = fpjoinhere(['temp', 'scrape_source.pdf'])
	print ' Converting {} -> {} ...'.format(arg, src_pdf_fp)
	if url_to_pdf(arg, src_pdf_fp):
		temps.append(src_pdf_fp)
	else:
		print '  Failed to convert source page'
	urllib.URLopener.version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0'
	print ' Reading \n  {} ...'.format(arg), ;sys.stdout.flush();
	page = requests.get(arg)
	dom =  lxml.html.fromstring(page.text)
	selAnchor = lxml.cssselect.CSSSelector('a')
	foundElements = selAnchor(dom)
	#print [e.get('href') for e in foundElements if e.get('href') and e.get('href').endswith('.pdf')]
	foundPdf = [e.get('href') for e in foundElements if e.get('href') and e.get('href').endswith('.pdf')]
	#print foundPdf
	print ' [{} files]'.format(len(foundPdf)); sys.stdout.flush();
	print ' Downloading {} files...'.format(len(foundPdf))
	for pdf in foundPdf:
		fn = urllib2.urlparse.urlsplit(pdf).path.split('/')[-1]
		fp = fpjoinhere(['temp', fn])
		furl = urlparse.urljoin(arg, pdf).replace('\\', '/')
		print '  {} -> {} ...'.format(furl,  fp),; sys.stdout.flush();
		if (os.path.isfile(fp)):
			print ' (cached)',
		else:
			urllib.urlretrieve(furl, fp)
		temps.append(fp)
		print '[{}]'.format(fileSize(os.path.getsize(fp)))
	return temps
def quote_list(items):
	return [x if (x.startswith("''") or x.startswith('"')) else '"{}"'.format(x) for x in items]
def join_files(files):
	fname_substr = long_substr(files)
	if len(fname_substr) and (os.path.isdir(fname_substr) == False):
		out_name = '{}.pdf'.format(fname_substr.strip())
	else:
		out_dir = fname_substr if os.path.isdir(fname_substr) else fptemp()
		out_name = fpjoin([out_dir, randfilename(out_dir, 'join_', 'pdf')])
	pop_in = [fpjoinhere(['concat_pdf']), '--output', out_name] + quote_list(files)
	pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = pop.communicate()
	return out_name
def move_tabs_to_new_window():
	scpt = """
	tell application "Safari"
	set l to tabs of window 1 where index >= (get index of current tab of window 1)
	make new document
	repeat with t in (reverse of l)
		move t to beginning of tabs of window 1
	end repeat
	delete tab -1 of window 1
	end tell
	"""
	args = []
	p = subprocess.Popen(['osascript', '-'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out,err = p.communicate(scpt)
	#print (p.returncode, stdout, stderr)
def get_list_tabs_field(field, right_of_curr = False):
	scpt_templ = """
	set all_urls to ""
	tell application "Safari"
		set l to tabs of window 1 {}
		repeat with t in l
			set url_str to (_FIELD_ of t) as string
			set all_urls to all_urls & url_str & "\n"
		end repeat
	end tell
	return all_urls
	""".format('where index >= (get index of current tab of window 1)' if right_of_curr else '')
	scpt = scpt_templ.replace('_FIELD_', field)
	args = []
	p = subprocess.Popen(['osascript', '-'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	out,err = p.communicate(scpt)
	urls = [x for x in out.split('\n') if len(x)]
	return urls
def get_list_tabs(fields = ['URL'], right_of_curr = False):
	ret = []
	for f in fields:
		ret.append(get_list_tabs_field(f, right_of_curr))
	return ret[0] if len(fields) ==  1 else ret
def tex_escape(text):
	"""
		:param text: a plain text message
		:return: the message escaped to appear correctly in LaTeX
	"""
	conv = {
		'&': r'\&',
		'%': r'\%',
		'$': r'\$',
		'#': r'\#',
		'_': r'\_',
		'{': r'\{',
		'}': r'\}',
		'~': r'\textasciitilde{}',
		'^': r'\^{}',
		'\\': r'\textbackslash{}',
		'<': r'\textless',
		'>': r'\textgreater',
	}
	regex = re.compile('|'.join(re.escape(unicode(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
	out = regex.sub(lambda match: conv[match.group()], text)
	return out
def ask_yes(question):
	var = raw_input('{} '.format(question))
	return var in ['y', 'yes']
def list_tabs(cmd_text, right_of_curr = False):
	if 'href' in cmd_text or 'md' in cmd_text:
		urls_titles = get_list_tabs(['URL', 'name'], right_of_curr)
		urls_titles = zip(urls_titles[0], urls_titles[1])
		if 'href' in cmd_text:
			print '\n', '\n'.join(['\\href{{ {} }}{{ {} }}'.format(tex_escape(x[0]), tex_escape(x[1])) for x in urls_titles]), '\n'
		else:
			print '\n', '\n'.join(['[{}]( {} )'.format(tex_escape(x[0]), tex_escape(x[1])) for x in urls_titles]), '\n'
	else:
		use_tex = 'tex' in cmd_text
		urls = get_list_tabs(['URL'], right_of_curr)
		print '\n', '\n'.join(['\\url{{ {} }}'.format(tex_escape(x)) if use_tex else x for x in urls]), '\n'
def join_tabs(right_of_curr = False, interactive = False, TOC_only = False):
	def url_to_pdf_2(url, pdf):
		return url_to_pdf(url, pdf, 2)
	def rem_proto(url):
		return url[url.index('://')+len('://'):] if '://' in url else url
	def cached_get_url(url, ext):
		hsh = str(hash_str_12(url))
		temp_fp = fpjoin([fptemp(), hsh+ext])
		cache_fp = fpjoin([fptemp(), hsh+ext+'.cache.txt'])
		is_cached = False
		if os.path.isfile(temp_fp):
			curl = ''
			if os.path.isfile(cache_fp):
				with open(cache_fp,'r') as f:
					curl = f.read()
			if curl == url:
				return (True, temp_fp, cache_fp)
			else:
				#new_fp = fpjoin([fptemp(), randfilename(fptemp(), 'join_tab_', ext[1:])])
				return (False, temp_fp, cache_fp)
		return (False, temp_fp, cache_fp)
	def cache_register(url, cache_fp):
		with open(cache_fp,'w') as f:
			f.write(url)
	def cached_process(show_orig, orig_url, url, ext, get_lambda, temps, descr, col):
		if show_orig:
			vt_col('red'); print ' {}'.format(orig_url),;
		if descr and len(descr):
			vt_col(col); print ' [{}]'.format(descr),;
		cached, temp_fp, cache_fp = cached_get_url(url, ext)
		vt_col('white'); print ' -> [{}]'.format(temp_fp),;
		if cached:
			vt_col('magenta'); print ' (cache)';
		else:
			print '';
		vt_col('default')
		if cached:
			temps.append(temp_fp)
		else:
			if get_lambda(url, temp_fp):
				temps.append(temp_fp)
				cache_register(url, cache_fp)
	urls = get_list_tabs(['URL'], right_of_curr)
	mktemp()
	temps = []
	print ''
	title_content = '<html><body> <center><b>{}</b></center> <ol> {} </ol></body></html>'.format(time.ctime(), ''.join('<li>{}</li>'.format(x) for x in urls))
	cached_process(True, 'T.O.C', title_content, '.pdf', lambda x,y: content_to_pdf(x, y), temps, None, None)
	if TOC_only:
		return
	urli = 0
	for url in urls:
		print ' {}.'.format(urli+1),; urli = urli+1;
		try:
			detected = False
			if not detected:
				if '.stackexchange.com' in url:
					url2 = rem_proto(url)
					dot_splt = url2.split('.')
					stack_topic = dot_splt[0]
					sl_splt = url2.split('/')
					if 'questions' in sl_splt:
						quest_ind = sl_splt.index('questions')
						if quest_ind >= 0 and quest_ind+1 < len(sl_splt):
							stack_number = sl_splt[quest_ind+1]
							detected = True
							pdf_url = 'http://www.stackprinter.com/export?question={}&service={}.stackexchange'.format(stack_number, stack_topic)
							cached_process(False, url, pdf_url, '.pdf', lambda x,y: url_to_pdf_2(x, y), temps, 'stack-exch:{}:{}'.format(stack_topic, stack_number), 'green')
				if 'mathoverflow.net' in url:
					url2 = rem_proto(url)
					sl_splt = url2.split('/')
					if 'questions' in sl_splt:
						quest_ind = sl_splt.index('questions')
						if quest_ind >= 0 and quest_ind+1 < len(sl_splt):
							stack_number = sl_splt[quest_ind+1]
							detected = True
							pdf_url = 'http://www.stackprinter.com/export?question={}&service=mathoverflow'.format(stack_number)
							cached_process(False, url, pdf_url, '.pdf', lambda x,y: url_to_pdf_2(x,y), temps, 'math-over:{}'.format(stack_number), 'yellow')
				if url.endswith('.pdf'):
					detected = True
					pdf = url.split('/')[-1]; pdf_url = url;
					cached_process(False, url, pdf_url, '.pdf', lambda x,y: url_download(x, y), temps, 'pdf', 'blue')
			if not detected:
				cached_process(True, url, url, '.pdf', lambda x,y: url_to_pdf_2(x,y), temps, 'webpage', 'cyan')
		except KeyboardInterrupt:
			vt_col('default')
			return
		except:
			traceback.print_exc()
	vt_col('default')
	print ''
	#print temps
	if interactive and not ask_yes('Should I join these files?'):
		return
	print join_files(temps)
def ec2_extract_profiles():
	cfg = ''
	cfg_fp = os.path.expanduser('~/.aws/config')
	if os.path.isfile(cfg_fp):
		with open(cfg_fp,'r') as f:
			cfg = f.read()
	lines = [x.strip() for x in cfg.split('\n')]
	prof_lines = [x for x in lines if x.startswith('[profile ') and x.endswith(']')]
	profiles = {}
	for x in prof_lines:
		prof = x[len('[profile '):-1]; profiles[prof] = '';
	profiles['default'] = ''
	return profiles.keys()
def ec2_inst_json(profile = 'default', inst_id = None, silent=False):
	args = ['aws', 'ec2', 'describe-instances', '--profile', profile]
	do_print = False
	if inst_id is not None:
		args.extend(['--instance-ids', inst_id])
	else:
		sys.stdout.write('querying aws ({})..'.format(profile)); sys.stdout.flush(); do_print = True;
	proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	(out, err) = proc.communicate()
	if do_print:
		print '.'
	print_formatted_proc_err(format_proc_out(err))
	return json.loads(out)
def ec2_info_from_json(data):
	infos = []
	for res in data['Reservations']:
		for inst in res['Instances']:
			info = {}
			for x in ['InstanceId', 'KeyName', 'PublicDnsName', 'LaunchTime']:
				info[x] = inst.get(x)
			if 'State' in inst:
				info['State'] = inst['State'].get('Name', '')
			for tag in inst['Tags']:
				if any([x in tag['Key'] for x in ['Name']]):
					info['Tag_' + tag['Key']] = tag['Value']
			infos.append(info)
	return infos
def extract_all_ec2s():
	profiles = ec2_extract_profiles()
	profs_datas = [ec2_inst_json(x) for x in profiles]
	profs_ec2s = [ec2_info_from_json(x) for x in profs_datas]
	all_ec2s = []
	for i in range(len(profiles)):
		profile = profiles[i]; prof_ec2s = profs_ec2s[i];
		for ec2 in prof_ec2s:
			ec2['Profile'] = profile
			all_ec2s.append(ec2)
	return all_ec2s
def to_clipboard(clip_str):
	os.system('echo %s | tr -d "\n" | pbcopy' % clip_str)
def ec2_start_stop_instances(ec2s, start):
	for ec2 in ec2s:
		if (start and ec2['State'] in ['running', 'pending']) or (not start and ec2['State'] in ['stopping']):
			continue
		args = ['aws', 'ec2', 'start-instances' if start else 'stop-instances', '--profile', ec2['Profile'], '--instance-ids', ec2['InstanceId']]
		proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		(out, err) = proc.communicate()
		print_formatted_proc_err(format_proc_out(err))
		#print out
	if len(ec2s) > 0:
		print (' Starting.' if start else ' Stopping.'),
	ec2_states = ['pending']*len(ec2s)
	while len([x for x in ec2_states if x == 'pending']) > 0:
		for ec2_i in range(len(ec2s)):
			if ec2_states[ec2_i] == 'pending':
				data = ec2_info_from_json(ec2_inst_json(ec2['Profile'], ec2s[ec2_i]['InstanceId']))[0]
				if data['State'] in ['running', 'terminated', 'stopped']:
					ec2_states[ec2_i] = data['State']
			ec2s[ec2_i]['PublicDnsName'] = data['PublicDnsName']
		sys.stdout.write('.'); sys.stdout.flush();
		time.sleep(1)
	print ''
	for ec2_i in range(len(ec2s)):
		dns_str = ec2s[0].get('PublicDnsName', '')
		print '  ' + '[{}] -> {}'.format(ec2s[ec2_i]['Tag_Name'], dns_str),
		if ec2_i == 0 and len(dns_str):
			to_clipboard(dns_str)
			print ' -> clipboard'
		else:
			print ''
def file_size(file_path):
		bytes = os.stat(file_path).st_size if os.path.isfile(file_path) else 0
		for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
				if bytes < 1024.0:
					return "%3.1f %s" % (bytes, x)
				bytes /= 1024.0
def google_wget_dload(url, file_out):
		args_1 = ['wget', '--save-cookies cookies.txt', '--keep-session-cookies', '--no-check-certificate', url, '-O-']
		proc = subprocess.Popen(' '.join(args_1), stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell = True)
		(out_1, err) = proc.communicate()
		#print out_1, err
		args_2 = ['sed', '-rn', "'s/.*confirm=([0-9A-Za-z_]+).*/Code: \\1\\n/p'"]
		proc = subprocess.Popen(' '.join(args_2), stdin = subprocess.PIPE, stdout = subprocess.PIPE, shell=True)
		(out_2, err) = proc.communicate(input=out_1)
		#print out_2
		conf_code = out_2.split(':')[1].strip()
		args_3 = ['wget', '--load-cookies cookies.txt', '-O', "'{}'".format(file_out), "'{}&confirm={}'".format(url, conf_code)]
		#print ' '.join(args_3)
		subprocess.Popen(' '.join(args_3), shell=True)
		proc.communicate()
def str_to_ascii(strg):
	if unidecode:
		strg = unicode(strg, 'utf-8')
		strg = unidecode.unidecode(strg)
	return strg
def pdftotext(file_path, file_out = None, to_ascii = False):
	args = ['pdftotext', '"{}"'.format(os.path.expanduser(file_path)), '-']
	proc = subprocess.Popen(' '.join(args), stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell = True)
	(out, err) = proc.communicate()
	if g_dbg and len(err):
		print args
		vt_col('red'); print err; vt_col('default')
	if len(out.strip()) == 0:
		return False
	if to_ascii:
		out = str_to_ascii(out)
	if file_out is None:
		print out
	else:
		with open(os.path.expanduser(file_out),'w') as fo:
			fo.write(out)
	return True
def ocr(file_path, file_out = None, to_ascii = False):
	mktemp()
	fname = os.path.splitext(os.path.basename(file_path))[0]
	fpat = '{}/{}_scan_%d.tif'.format(fptemp(), fname.replace(' ', '_'))
	args_1 = ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=tiffg4', '-sOutputFile="{}"'.format(fpat), '"{}"'.format(os.path.expanduser(file_path))]
	proc = subprocess.Popen(' '.join(args_1), stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell = True)
	(out_1, err) = proc.communicate()
	has_errs = False
	if g_dbg and len(err):
		print ' '.join(args_1)
		vt_col('red'); print err; vt_col('default');
		has_errs = True
	pi = 1
	while os.path.isfile(fpat.replace('%d', str(pi))):
		pi = pi+1
	pc = pi-1; pi = 1;
	while os.path.isfile(fpat.replace('%d', str(pi))):
		args_2 = ['tesseract', fpat.replace('%d', str(pi)), 'stdout']
		proc = subprocess.Popen(' '.join(args_2), stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell = True)
		(out_2, err) = proc.communicate()
		if g_dbg and len(err):
			print args_2
			vt_col('red'); print err; vt_col('default');
			has_errs = True
		if to_ascii:
			out_2 = str_to_ascii(out_2)
		if file_out is None:
			print out_2
		else:
			print '{} page {} of {} ...'.format('\r' if pi > 1 else '', pi, pc),
			sys.stdout.flush()
			with open(os.path.expanduser(file_out),'w' if pi==1 else 'a') as fo:
				fo.write(out_2)
		pi = pi+1
	return has_errs == False
def process(text_):
	patts = []
	def new_patt(name, ext = None):
		patts.append([name, ext, '{} [{}]'.format(name, ext) if ext else name ]); return name;
	text = text_.strip()
	patt1 = new_patt('find files with ')
	patt2 = new_patt('find files named ')
	patt3 = new_patt('find duplicates')
	patt4 = new_patt('join files named ', 'interactive')
	patt5 = new_patt('show ')
	patt6 = new_patt('count files')
	patt7 = new_patt('scrape and join ')
	patt8 = new_patt('scrape ', 'staying in ')
	patt9 = new_patt('move tabs')
	patt10 = new_patt('list all tabs', 'tex | href | md')
	patt11 = new_patt('list tabs', 'tex | href | md')
	patt12 = new_patt('join tabs', 'interactive')
	patt12_1 = new_patt('toc tabs')
	patt13 = new_patt('clean temp')
	patt14 = new_patt('git status')
	patt15 = new_patt('push git', 'message ')
	patt16 = new_patt('aws list')
	patt17 = new_patt('aws start ')
	patt18 = new_patt('aws stop')
	patt19 = new_patt('aws ssh to')
	patt20 = new_patt('aws start and ssh to ')
	patt21 = new_patt('wget from google ', 'as ')
	patt22 = new_patt('ocr ', 'to | ascii')
	patt23 = new_patt('text ', 'to | ascii')
	if text.startswith(patt1):
		arg = text[len(patt1):]
		pop_in = ['grep', '-ril', '"{}"'.format(arg), '.']
		pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
		out, err = pop.communicate()
		print out
	elif text.startswith(patt2):
		arg = text[len(patt2):]
		head,tail = os.path.split(arg); head = '.' if len(head) == 0 else head;
		pop_in = ['find', head, '-maxdepth', '1', '-iname', '"*{}*"'.format(tail)]
		pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
		out, err = pop.communicate()
		print out
	elif text.startswith(patt3):
		pop_in = ['fdupes', '.']
		pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
		out, err = pop.communicate()
		print out
	elif text.startswith(patt4):
		arg = text[len(patt4):]
		interactive = False
		if arg.strip().endswith('interactive'):
			interactive = True
			arg = arg[:-1-len('interactive')].strip()
		head,tail = os.path.split(arg); head = '.' if len(head) == 0 else head;
		pop_in = ['find', head, '-maxdepth', '1', '-iname', '"*{}*"'.format(tail)]
		pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
		out, err = pop.communicate()
		files = [x for x in sorted(out.split('\n')) if len(x)]
		if len(files):
			if interactive:
				print 'Found:'
				print '\n'.join([' '+ x for x in files])
				if not ask_yes('Should I join these files?'):
					return
			print join_files(files)
		else:
			print 'No files could be matched to [{}]'.format(tail)
	elif text.startswith(patt5):
		arg = text[len(patt5):]
		if arg.endswith('.txt'):
			pop_in = ['cat', arg]
			pop = subprocess.Popen(' '.join(pop_in), shell = True)
			pop.wait()
			print ''
		else:
			pop_in = ['open', '-a', 'Preview.app', arg]
			subprocess.Popen(' '.join(pop_in), shell = True)
	elif text.startswith(patt6):
		pop_in = ['find', '.', '-type', 'f', '-maxdepth', '1']
		pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
		out, err = pop.communicate()
		print len([x for x in out.split('\n') if x.strip() != ''])
	elif text.startswith(patt7):
		arg = text[len(patt7):]
		temps = process_scrape(arg)
		print ' Joining ...'
		print '  {}'.format(join_files(temps))
	elif text.startswith(patt8):
		args = text[len(patt8):].split(' ')
		process_scrape(args[0], args[3:] if len(args)>= 4 else None)
	elif text.startswith(patt9):
		move_tabs_to_new_window()
	elif text.startswith(patt10):
		list_tabs(text, False)
	elif text.startswith(patt11):
		list_tabs(text, True)
	elif text.startswith(patt12):
			join_tabs(True, 'interactive' in text)
	elif text.startswith(patt12_1):
			join_tabs(True, False, True)
	elif text.startswith(patt13):
		shutil.rmtree(fptemp())
	elif text.startswith(patt14):
		pop_in = ['git', 'status']
		pop = subprocess.Popen(' '.join(pop_in), shell = True)
		pop.communicate()
	elif text.startswith(patt15):
		arg = text[len(patt15):].strip()
		print arg
		pop_in = ['git', 'add', '*']; pop = subprocess.Popen(' '.join(pop_in), shell = True); pop.communicate();
		pop_in = ['git', 'commit', '-m', '"{}"'.format('trivial' if len(arg)==0 else arg)]; pop = subprocess.Popen(' '.join(pop_in), shell = True); pop.communicate();
		pop_in = ['git', 'push', 'origin', 'master']; pop = subprocess.Popen(' '.join(pop_in), shell = True); pop.communicate();
	elif any( text.startswith(x) for x in [patt16] ):
		def format_ec2_pair(x):
			pair_str = '[{}: {}]'.format(x[0], x[1])
			if x[0] == 'State':
				colis = {'running':gPrintCol.index('green'), 'stopped':gPrintCol.index('red'), 'pending':gPrintCol.index('yellow'), 'stopping':gPrintCol.index('magenta'), 'terminated':gPrintCol.index('cyan') }
				coli = colis.get(x[1], gPrintCol.index('cyan'))
				pair_str = gPrintColCode[coli] + pair_str + gPrintColCode[0]
			return pair_str
		ec2s = extract_all_ec2s()
		for ec2 in ec2s:
			print ' ' + ' '.join([format_ec2_pair(x) for x in ec2.items()])
	elif text.startswith(patt17) or text.startswith(patt20):
		arg = text[len(patt20):] if text.startswith(patt20) else text[len(patt17):]
		ec2s = extract_all_ec2s()
		cands_i = []
		for i in range(len(ec2s)):
			if arg.lower() in ec2s[i]['Tag_Name'].lower():
				cands_i.append(i)
		if len(cands_i) > 0:
			if len(cands_i) > 1:
				start_i = print_and_choose([' {} ({})'.format(ec2s[x]['Tag_Name'], ec2s[x]['InstanceId'])  for x in cands_i], ' ')
			else:
				start_i = cands_i
			ec2_start_stop_instances([ec2s[x] for x in start_i], True)
			if text.startswith(patt20):
				process(text.replace('start and ssh', 'ssh'))
	elif text.startswith(patt18):
		arg = text[len(patt18)+1:] if len(text) > len(patt18) else ''
		ec2s = extract_all_ec2s()
		cands_i = []
		for i in range(len(ec2s)):
			if ec2s[i]['State'] in ['running', 'stopping', 'pending'] and arg.lower() in ec2s[i]['Tag_Name'].lower():
				cands_i.append(i)
		if len(cands_i) > 0:
			if arg == '':
				start_i = cands_i
			else:
				if len(cands_i) > 1:
					start_i = print_and_choose([' {} ({})'.format(ec2s[x]['Tag_Name'], ec2s[x]['InstanceId'])  for x in cands_i], ' ')
				else:
					start_i = cands_i
			ec2_start_stop_instances([ec2s[x] for x in start_i], False)
	elif text.startswith(patt19):
		arg = text[len(patt19)+1:] if len(text) > len(patt18) else ''
		ec2s = extract_all_ec2s()
		cands_i = []
		for i in range(len(ec2s)):
			if ec2s[i]['State'] == 'running' and arg.lower() in ec2s[i]['Tag_Name'].lower():
				cands_i.append(i)
		if len(cands_i) > 0:
			if len(cands_i) > 1:
				ssh_i = print_and_choose([' {} ({})'.format(ec2s[x]['Tag_Name'], ec2s[x]['InstanceId'])  for x in cands_i], ' ')
			else:
				ssh_i = cands_i
			for i in ssh_i:
				args = ['ssh', '-i', os.path.expanduser('~/Dropbox/Temp/test_1.400.pem.txt'), 'ubuntu@{}'.format(ec2s[i]['PublicDnsName'])]
				clip_str = ' '.join(args)
				print '[{}]'.format(clip_str),
				if len(ssh_i) == 1:
					print ' -> clipboard'.format(clip_str)
					to_clipboard(clip_str)
					#subprocess.Popen(' '.join(args), shell=True)
				else:
					print ''
	elif text.startswith(patt21):
		args = text[len(patt21):].split(' ')
		file_id = args[0]; file_out = ' '.join(args[2:]);
		google_wget_dload(file_id, file_out)
		print '[{}] : {}'.format(file_out, file_size(file_out))
	elif text.startswith(patt22):
		to_ascii = False
		if text.endswith('ascii'):
			to_ascii = True; text = text[:-len(' ascii')];
		args = text[len(patt22):].split(' to ')
		file_path, out_file = (args[0], args[1] if len(args) > 1 else None)
		ocr(file_path, out_file, to_ascii)
	elif text.startswith(patt23):
		to_ascii = False
		if text.endswith(' ascii'):
			to_ascii = True; text = text[:-len(' ascii')];
		args = text[len(patt23):].split(' to ')
		file_path, out_file = (args[0], args[1] if len(args) > 1 else None)
		if pdftotext(file_path, out_file, to_ascii) == False:
			ocr(file_path, out_file, to_ascii)
	elif text.startswith('analyze '):
		def find_matches(rex, text):
			return re.finditer(rex, text, re.IGNORECASE)
		args = text[len('analyze '):].split(' ')
		file_path = args[0]
		max_n = 50 if len(args) == 1 else int(args[1])
		text = None
		with open(os.path.expanduser(file_path),'r') as f:
			text = f.read()
		pats = ['Definition', 'Theorem', 'Lemma', 'Example', 'Exercise']
		pat_rex = {}; pat_matches = {};
		for pat in pats:
			pat_rex[pat] = r"\b({})(\s*)(\d+)((?:\.\d+)+)*".format(pat)
			pat_matches[pat] = find_matches(pat_rex[pat], text)
		if g_dbg:
			print [(pat, sum(1 for _ in pat_matches[pat])) for pat in pats]
		pat_info = {}
		for pat in pats:
			pat_info[pat] = {}
			matches = find_matches(pat_rex[pat], text)
			for match in matches:
				match_str = match.group(0)
				match_str = match_str.replace('\n', ' ')
				match_str = match_str.replace('\\x0', ' ')
				for ri in range(10):
					match_str = match_str.replace('  ', ' ')
				if match_str in pat_info[pat]:
					pat_info[pat][match_str]['starts'].append(match.start())
					pat_info[pat][match_str]['count'] = pat_info[pat][match_str]['count'] + 1
				else:
					pat_info[pat][match_str] = { 'count':1, 'starts':[match.start()] }
		match_dist_table = {}
		for pat in pats:
			for match_str, match_info in pat_info[pat].items():
				match_dist_table[match_str] = {}
				for pat2 in pats:
					for match_str2, match_info2 in pat_info[pat2].items():
						if match_str2 > match_str:
							dists = []
							for si in match_info['starts']:
								for sj in match_info2['starts']:
									dists.append(abs(si-sj))
							match_dist_table[match_str][match_str2] = min(dists)
		match_dist_flat = []
		for match_str, match_dists in match_dist_table.items():
			for match_str2, match_dist in match_dists.items():
				match_dist_flat.append((match_str, match_str2, match_dist))
		match_dist_flat = sorted(match_dist_flat, key = lambda x: x[2])
		if g_dbg:
			print [(pat, len(pat_info[pat])) for (i, pat) in enumerate(pats)]
		dist_rels = []
		for mdist in match_dist_flat:
			if mdist[2] / 8 < max_n:
				if all([ (not mdist[x].lower().startswith('Exercise'.lower())) for x in [0,1]]):
					if all([ (not mdist[x].lower().startswith('Example'.lower())) for x in [0,1]]):
						dist_rels.append(mdist)
			else:
				break
		if False:
			print match_dist_flat[:3]
		if g_dbg:
			print dist_rels
		if graphviz:
			def make_node_name(strg):
				return strg.replace(' ', '_').replace('.', '_').lower()
			graph = graphviz.Digraph(comment='Analysis of "[{}]"'.format(file_path))
			for rel in dist_rels:
				graph.node(make_node_name(rel[0]), rel[0])
				graph.node(make_node_name(rel[1]), rel[1])
				graph.edge(make_node_name(rel[0]), make_node_name(rel[1]))
			#print graph.source
			dot_fpath = file_path+'.dot'
			with open(os.path.expanduser(dot_fpath),'w') as fo:
				fo.write(graph.source)
			pdf_fpath = dot_fpath+'.pdf'
			pop_in = ['dot', '-Tpdf', '"-o{}"'.format(pdf_fpath), '"{}"'.format(dot_fpath)]
			pop = subprocess.Popen(' '.join(pop_in), shell = True, stdout=subprocess.PIPE)
			out, err = pop.communicate()
			if g_dbg and len(err):
				vt_col('red'); print err; vt_col('default')

	else:
		print "Apologies, I could not understand what you said."
		print "I understand:"
		print '\n'.join([' ' + x[2] for x in patts])

if '-dbg' in sys.argv:
	g_dbg = True
	sys.argv.pop(sys.argv.index('-dbg'))
process(' '.join(sys.argv[1:]))