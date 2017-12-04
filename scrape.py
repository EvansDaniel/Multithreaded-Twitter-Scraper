from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep
import json
import datetime
import os
import threading
from datetime import datetime, timedelta
import sys
import multiprocessing

using_python3 = sys.version_info[0] >= 3
if not using_python3:
	print('You must use python 3. Run with python3 scrape.py')
	sys.exit(1)

# time to wait on each page load before reading the page
delay = .1

# edit these three variables
user = 'ivankatrump'
start = datetime(2015, 1, 1)  # year, month, day
end = datetime(2017, 12, 4)  # year, month, day

# don't mess with this stuff
id_selector = '.time a.tweet-timestamp'
tweet_selector = 'li.js-stream-item'
MEMORY_PERCENT_THRESHOLD = 85
user = user.lower()

# Set default barrier parties (1 thread)
memory_release_barrier = threading.Barrier(parties=1)
id_file_mutex = threading.Lock()

def format_day(date):
    day = '0' + str(date.day) if len(str(date.day)) == 1 else str(date.day)
    month = '0' + str(date.month) if len(str(date.month)) == 1 else str(date.month)
    year = str(date.year)
    return '-'.join([year, month, day])

def form_url(since, until):
    p1 = 'https://twitter.com/search?f=tweets&vertical=default&q=from%3A'
    p2 =  user + '%20since%3A' + since + '%20until%3A' + until + 'include%3Aretweets&src=typd'
    return p1 + p2

def increment_day(date, i):
    return date + timedelta(days=i)

def open_file(filename, *args, **kwargs):
	# Create file if not exists
    open(filename, 'a').close()
    # Encapsulate the low-level file descriptor in a python file object
    return open(filename, *args, **kwargs)

def save_to_file(ids, filename):
	# Open for reading and writing
	id_file_mutex.acquire()
	#print('aquiring mutex')
	try:
		id_json_file = open_file(filename, 'r+')
		ids = list(set(ids))
		try:
			file_ids = json.load(id_json_file)
			file_ids = file_ids['ids']
			file_ids.extend(ids)
			all_ids = list(set(file_ids))
		except:
			all_ids = ids
		#print(len(all_ids),len(ids),'\n')
		tweet_ids = {
			"user":user,
			"ids":all_ids
		}
		# Seek to beginning and truncate the file
		id_json_file.seek(0)
		id_json_file.truncate()
		json.dump(tweet_ids, id_json_file)
	finally:
		if id_json_file:
			id_json_file.close()
	#	print('releasing mutex')
		id_file_mutex.release()

# Courtesy of https://stackoverflow.com/questions/17718449/determine-free-ram-in-python#answer-17718729
# Can't use psutil for this since python3-dev/python-dev is not installed on Linux lab computers
def memory():
    """
    Get node total memory and memory usage
    """
    with open('/proc/meminfo', 'r') as mem:
        ret = {}
        tmp = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) == 'MemTotal:':
                ret['total'] = int(sline[1])
            elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                tmp += int(sline[1])
        ret['free'] = tmp
        ret['used'] = int(ret['total']) - int(ret['free'])
        ret['percent'] = int(ret['used']) / int(ret['total']) * 100
    return ret

def create_tweet_id_file(start, end, id_filename):
	ids = []
	driver = webdriver.Chrome()  
	days = (end - start).days + 1
	for day in range(days):
		d1 = format_day(increment_day(start, 0))
		d2 = format_day(increment_day(start, 1))
		search_url = form_url(d1, d2)
		print(search_url)
		driver.get(search_url)

		try:
			found_tweets = driver.find_elements_by_css_selector(tweet_selector)
			increment = 10

			while len(found_tweets) >= increment:
				print('scrolling down to load more tweets')
				driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
				sleep(delay)
				found_tweets = driver.find_elements_by_css_selector(tweet_selector)
				increment += 10

			print('{} tweets found, {} total'.format(len(found_tweets), len(ids)))

			for tweet in found_tweets:
				try:
					id = tweet.find_element_by_css_selector(id_selector).get_attribute('href').split('/')[-1]
					ids.append(id)
				except StaleElementReferenceException as e:
					print('lost element reference', tweet)

		except NoSuchElementException:
			print('no tweets on this day')

		if memory()['percent'] >= MEMORY_PERCENT_THRESHOLD:
			# Wait for all threds to realize that we are beyond the memory threshold
			# This is so that they will all relinquish their 'driver' and 'ids' memory,
			# not just the first thread to realize we are beyond the threshold
			memory_release_barrier.wait()
			save_to_file(ids, id_filename)
			ids = []
			driver.close()
			driver.Chrome()

		# Go to next day of tweets
		start = increment_day(start, 1)

	# Save remaining found ids
	save_to_file(ids, id_filename)
	driver.close()

if __name__ == "__main__":
	id_filename=input('File to store ids in? ')
	days = (end-start).days + 1
	# divide by two to account for hyperthreading
	num_cores = multiprocessing.cpu_count() // 2 
	memory_release_barrier = threading.Barrier(parties=num_cores)
	if days >= num_cores:
	#	print(start, end_date)
		num_days_between = days//4
	#	print((num_days_between) * 4 + (days % 4), days)
		threads = []
		num_threads = num_cores-1
		for i in range(num_threads):
			end_for_thread = start + timedelta(days=num_days_between-1)
			t = threading.Thread(target=create_tweet_id_file, kwargs={'start':start, 'end':end_for_thread, 'id_filename':id_filename})
			#print('start and end for thread', i,':', start.strftime("%m_%d_%y"), end_for_thread.strftime("%m_%d_%y"))
			threads.append(t)
			t.start()
			start = end_for_thread + timedelta(days=1)

		#print('start and end for main thread', start.strftime("%m_%d_%y"), end.strftime("%m_%d_%y"))
		create_tweet_id_file(start, end, id_filename)
		# Wait for threads
		for t in threads:
			t.join()
	else:
		create_tweet_id_file(start,end, id_filename)

			
