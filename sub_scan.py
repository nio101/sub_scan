#!python3
# -*- coding: utf-8 -*-

"""
Python3 script that will use the pythonopensubtitles module to retrieve/rename the proper fr/en subtitles.
+ rename the sub as movie.[fr|en].srt
+ save other alternatives if not sure of the result => fr.1, fr.2...

notes:
+ take into account the 40 HTTP requests per 10 seconds per IP address!


"""

import sys
from time import sleep
import configparser
import argparse
import rich
from rich.console import Console
from rich.markdown import Markdown
from rich.traceback import install
from rich.panel import Panel
from rich.theme import Theme
import os.path
from pythonopensubtitles.opensubtitles import OpenSubtitles
from pythonopensubtitles.utils import File
import os
import requests
import zipfile


# --- helpers ---

# --- main stuff ---
install()

custom_theme = Theme({
    "warning": "yellow",
    "important": "bold red",
})
console = Console(theme=custom_theme, highlight=False)

# --- args
parser = argparse.ArgumentParser(description='Capturing pods starting times on OpenShift.\r\n More info here: https://gitlab.tech.orange/iva-integration-performance/tools/openshift/openshift_podsizing_tools')
requiredNamed = parser.add_argument_group('required named arguments')
requiredNamed.add_argument('-u', '--user', help='Opensubtitles login', required=True)
requiredNamed.add_argument('-p', '--password', help='Opensubtitles password', required=True)
requiredNamed.add_argument('-f', '--file', help='media file to search subtitles for', required=True)
#parser.parse_args(['-h'])
args = parser.parse_args()

# --- title
print()
console.print(Panel.fit("sub_scan.py", box=rich.box.ASCII, style="bold magenta", border_style="bright_black"))

console.print(Markdown("> Checking file"))
file = sys.argv[-1]
console.print(file)  #sys.argv[1] is the file to upload
if not os.path.isfile(file):
	raise("error: could not find file.")
else:
	print('> ok.')
f = File(file)
(path, filename) = os.path.split(os.path.abspath(file))
filename_root = filename[:-4]

console.print(Markdown("> Checking OpenSubtitles API access"))
ost = OpenSubtitles() 
if ost.login(args.user, args.password) is None:
	raise("error: cannot login to OpenSubtitles API using the given username/password.")
else:
	print('> ok.')

# best solution: hash size
# if no result => search for title on IMDB (manually)
# then search by IMDB movie id

res = {}
title = ""
imdb_movie_id_found = None
year = ""
subfilename = {}
for lang in ['eng', 'fre']:
	res[lang] = []
	done = False
	console.print(Markdown("> Searching OpenSubtitles for {} subtitles...".format(lang)))
	# objectif: sortir 2 sous-titres en fr, puis 2 sous-titres en eng
	# 1) essai meilleur qualité: match movie hash+size
	data = ost.search_subtitles([{'sublanguageid': lang, 'moviehash': f.get_hash(), 'moviebytesize': f.size}])

	def analyze_answer(hash_search):
		global data, res, lang, done, imdb_movie_id_found, title
		#console.print("{} result(s) found.".format(len(data)))	
		for e in data:
			#console.print("# ",e['Score'], e['SubFileName'], e['IDMovieImdb'], e['MovieName'], e['SubAddDate'], e['SubEncoding'])
			#console.print(e['ZipDownloadLink'])
			if e['SubFormat']=='srt':
				#console.print("imdb movie id:", e['IDMovieImdb'])
				#console.print("imdb movie name:", e['MovieName'])
				if hash_search is True and imdb_movie_id_found is None:
					imdb_movie_id_found = e['IDMovieImdb']
					console.print("IMDB movie ID found:", imdb_movie_id_found)
					title = e['MovieName'] +' '+ e['MovieYear'] + " BluRay"
					console.print("title found:", title)
				if e['ZipDownloadLink'] not in res[lang]:
					console.print("> {:.0f}% - {}".format(e['Score'], e['SubFileName']))
					res[lang].append(e['ZipDownloadLink'])
					subfilename[e['ZipDownloadLink']] = e['SubFileName']
				if len(res[lang])>=2:
					done = True
					break
			else:
				console.print("x ignoring non SRT sub!")

	console.print("searching using hash/size...")
	if len(data) == 0:
		print("x no result found.")
	else:
		analyze_answer(True)

	if not done:
		console.print("searching using filename/tag...")
		# search by IMDB movie id!
		try:
			data = ost.search_subtitles([{'sublanguageid': lang, 'tag': filename_root}])
		except:
			print("** error looking for the filename/tag!?! **")
		if data is not None or len(data) == 0:
			print("x no result found.")
		else:
			analyze_answer(False)

	if not done:
		console.print("searching using title...")
		# if not found, let's ask the user for the movie title
		if title == "":
			title = input("Please enter the movie title: ")
		else:
			console.print("using title:", title)
		data = ost.search_subtitles([{'sublanguageid': lang, 'query': title}])
		if len(data) == 0:
			print("x no result for found.")
		else:
			analyze_answer(False)

	if not done and imdb_movie_id_found is not None:
		console.print("searching using IMDB movie id...")
		# search by IMDB movie id!
		data = ost.search_subtitles([{'sublanguageid': lang, 'imdbid': imdb_movie_id_found, 'tags': 'BluRay'}])
		if len(data) == 0:
			print("x no result for found.")
		else:
			analyze_answer(False)

	if len(res[lang])>=1:
		#print("preparing to download:", res[lang])
		names_dict = {}
		if len(res[lang]) >= 1:
			names_dict[res[lang][0]] = path+'\\'+filename_root+'.'+lang+'.srt'
		if len(res[lang]) >= 2:
			names_dict[res[lang][1]] = path+'\\'+filename_root+'.'+lang+'.'+lang+'2.srt'
		if len(res[lang]) >= 3:
			names_dict[res[lang][2]] = path+'\\'+filename_root+'.'+lang+'.'+lang+'3.srt'
		console.print(Markdown("> Downloading subtitles..."))
		#down = ost.download_subtitles(res[lang], override_filenames=names_dict, output_directory=path)
		for url in res[lang]:
			r = requests.get(url, allow_redirects=True)
			open('tmp.zip', 'wb').write(r.content)
			with zipfile.ZipFile('tmp.zip', 'r') as zip_ref:
				zip_ref.extract(subfilename[url], path=path)
    		# now rename the file to names_dict[url]
			try:
				os.remove(names_dict[url])
			except OSError:
				pass
			os.rename(path+'\\'+subfilename[url], names_dict[url])
			try:
				os.remove('tmp.zip')
			except OSError:
				pass
			print(">> {}.".format(names_dict[url]))

#data = ost.download_subtitles([id_subtitle_file], override_filenames={id_subtitle_file: 'output_filename.srt'}, output_directory='PATH/TO/DIR', extension='srt')

# we consumed ~10 http requests on the API?
# let's sleep 3s to prevent rate-limiting...
sleep(3)
