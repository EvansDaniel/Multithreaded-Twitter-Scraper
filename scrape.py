from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep
import json
import datetime
import os
import psutil
import threading
from datetime import datetime, timedelta
import sys

using_python3 = sys.version_info[0] >= 3
if not using_python3:
	print('You must use python 3. Run with python3 scrape.py')
	sys.exit(1)

# time to wait on each page load before reading the page
delay = 1 

# edit these three variables
user = 'realdonaldtrump'
filename=input('What is the id filename?')
start = datetime(2015, 1, 1)  # year, month, day
end = datetime(2017, 12, 3)  # year, month, day

# don't mess with this stuff
id_selector = '.time a.tweet-timestamp'
tweet_selector = 'li.js-stream-item'
MEMORY_PERCENT_THRESHOLD = 85
tweet_id_prefix = '_tweets'
user = user.lower()

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

def save_file(ids, num_files):
	twitter_ids_filename = user + tweet_id_prefix + '_' + str(threading.get_ident()) + '_' + \
		str(num_files) + '_' + start.strftime("%m_%d_%y") + '_' + end.strftime("%m_%d_%y") + '.json'
	with open(twitter_ids_filename, 'w') as outfile:
		ids = list(set(ids))
		print(ids,'\n')
		tweet_ids = {
			"user":user,
			"ids":ids
		}
		json.dump(tweet_ids, outfile)

def create_tweet_id_file(start, end):
	num_files = 0
	ids = []
	driver = webdriver.Firefox()  
	days = (end - start).days + 1
	for day in range(days):
		d1 = format_day(increment_day(start, 0))
		d2 = format_day(increment_day(start, 1))
		search_url = form_url(d1, d2)
		print(search_url)
		driver.get(search_url)
		sleep(delay)

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

		if psutil.virtual_memory().percent >= MEMORY_PERCENT_THRESHOLD:
			save_file(ids, num_files)
			ids = []
			num_files += 1

		# Go to next day of tweets
		start = increment_day(start, 1)

	# Save remaining found ids
	save_file(ids, num_files)
	driver.close()

if __name__ == "__main__":
	days = (end-start).days + 1
	# divide by two to account for hyperthreading
	num_cores = psutil.cpu_count() // 2 
	if days >= num_cores:
	#	print(start, end_date)
		num_days_between = days//4
	#	print((num_days_between) * 4 + (days % 4), days)
		threads = []
		num_threads = num_cores-1
		for i in range(num_threads):
			end_for_thread = start + timedelta(days=num_days_between-1)
			t = threading.Thread(target=create_tweet_id_file, kwargs={'start':start, 'end':end_for_thread})
			print('start and end for thread', i,':', start.strftime("%m_%d_%y"), end_for_thread.strftime("%m_%d_%y"))
			threads.append(t)
			t.start()
			start = end_for_thread + timedelta(days=1)

		print('start and end for main thread', start.strftime("%m_%d_%y"), end.strftime("%m_%d_%y"))
		create_tweet_id_file(start, end)
		# Wait for threads
		for t in threads:
			t.join()
	else:
		create_tweet_id_file(start,end)

			
