import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep
import json
import datetime
import os
import sys
import threading
import scrape
import multiprocessing

using_python3 = sys.version_info[0] >= 3
if not using_python3:
	print('You must use python 3. Run with python3 <filename>')
	sys.exit(1)

# only edit these if you're having problems
delay = .1  # time to wait for scrolling (comments)
pop_up_tweet_selector ='.permalink-container'
text_selector = '.tweet-text'
metadata_selector = '.metadata'
like_selector = '.js-actionFavorite .ProfileTweet-actionCount'
comment_selector = '.js-actionReply .ProfileTweet-actionCount'
retweet_selector = '.js-actionRetweet .ProfileTweet-actionCount'
MEMORY_PERCENT_THRESHOLD = 30

# Just to set default barrier parties and make sure it is global
memory_release_barrier = threading.Barrier(parties=1)
tweet_details_file_mutex = threading.Lock()

# comment is a reference to '.tweet'
def get_comment_details(comment):
	comment_dict = None
	try:
		commenter_username = comment.find_element_by_css_selector('.username').text
		comment_text = comment.find_element_by_css_selector('.tweet-text').text
		date_of_comment = comment.find_element_by_css_selector('._timestamp').text
		comment_like_num = comment.find_element_by_css_selector(like_selector).text
		comment_comment_num = comment.find_element_by_css_selector(comment_selector).text
		comment_retweet_num = comment.find_element_by_css_selector(retweet_selector).text
		comment_media = get_tweet_media(comment)
		# Handling empty comment stats
		if comment_like_num.strip() == "":
			comment_like_num = 0
		if comment_comment_num.strip() == "":
			comment_comment_num = 0
		if comment_retweet_num.strip() == "":
			comment_retweet_num = 0

		comment_dict = {
			"commenter_username": commenter_username,
			"comment_media":comment_media,
			"comment_text":comment_text,
			"date_of_comment":date_of_comment,
			"comment_like_num":comment_like_num,
			"comment_comment_num":comment_comment_num,
			"comment_retweet_num":comment_retweet_num
		}
		return comment_dict
	except:
		print('Exception in comments')
		return comment_dict

# tweet is selenium element reference to '.permalink-container' class
def get_comments(driver, tweet):
	reply_to_container = driver.find_element_by_css_selector('.replies-to')
	comments = reply_to_container.find_elements_by_css_selector('.tweet')
	old_comment_len = len(comments)
	new_comment_len = -1
	while(old_comment_len != new_comment_len):
		driver.execute_script('document.getElementById(\'permalink-overlay\').scrollTo(0, document.getElementById(\'permalink-overlay\').scrollHeight)')
		sleep(delay)
		comments = tweet.find_elements_by_css_selector('.tweet')
		old_comment_len = new_comment_len
		new_comment_len = len(comments)

	c = []
	# The first comment is the actual post not a comment so strip it out
	for comment in comments[1:]:
		comment_details = get_comment_details(comment)
		c.append(comment_details)
	return c

def get_tweet_media(tweet):
	media_dict = None
	try:
		adaptive_media_selector = '.AdaptiveMedia-container'
		adaptive_media = tweet.find_element_by_css_selector(adaptive_media_selector)
		imgs = adaptive_media.find_elements_by_css_selector('img')
		img_urls = [img.get_attribute("src") for img in imgs]
		media_dict = {
			'img_urls': img_urls
		}
		return media_dict
	except:
		return media_dict

def get_tweet_info(driver,tweet, id):
	text = tweet.find_element_by_css_selector(text_selector).text
	metadata = tweet.find_element_by_css_selector(metadata_selector).text
	like_num = tweet.find_element_by_css_selector(like_selector).text
	comment_num = tweet.find_element_by_css_selector(comment_selector).text
	comments = get_comments(driver, tweet)
	tweet_media = get_tweet_media(tweet)
	retweet_num = tweet.find_element_by_css_selector(retweet_selector).text
	tweet_dict = {
		"tweet_id": id,
		"tweet_text": text,
		"tweet_metadata": metadata,
		"tweet_media": tweet_media,
		"like_num": like_num,
		"comment_num": comment_num,
		"comments": comments,
		"retweet_num": retweet_num,
	}
	return tweet_dict

def form_tweet_detail_url(id, user):
	url = 'https://twitter.com/' + user + '/status/' + id
	return url

def save_tweet_details_to_file(tweets, filename):
	tweet_details_file_mutex.acquire()
	try:
		tweet_detail_file = scrape.open_file(filename, 'r+')
		try:
			file_tweets = json.load(tweet_detail_file)
			tweets.extend(file_tweets)
			all_tweets = tweets
		except:
			all_tweets = tweets

		# Seek to beginning and truncate the file
		tweet_detail_file.seek(0)
		tweet_detail_file.truncate()
		json.dump(all_tweets, tweet_detail_file)
	finally:
		if tweet_detail_file:
			tweet_detail_file.close()
		tweet_details_file_mutex.release()

def ensure_unique_tweets(filename):
	tweet_detail_file = scrape.open_file(filename, 'r+')
	try:
		file_tweets = json.load(tweet_detail_file)
	except:
		print(filename, 'does not contain valid JSON')
		sys.exit(1)
	tweet_ids = []
	unique_tweets = []
	for tweet in file_tweets:
		tweet_id = tweet['tweet_id']
		if not tweet_id in tweet_ids:
			unique_tweets.append(tweet)
		tweet_ids.append(tweet_id)

	tweet_detail_file.seek(0)
	tweet_detail_file.truncate()
	json.dump(unique_tweets, tweet_detail_file)

def get_tweet_details(ids, tweet_detail_file_name):
	if len(ids) == 0:
		return
	driver = webdriver.Firefox()  # options are Chrome() Firefox() Safari()
	tweets = []
	for id in ids:
		driver.get(form_tweet_detail_url(id, user))
		tweet = driver.find_element_by_css_selector(pop_up_tweet_selector)
		tweet_dict = get_tweet_info(driver,tweet, id)
		tweets.append(tweet_dict)
		# If memory available is less than threshold, save tweet data to a file to save memory
		print(scrape.memory()['percent'])
		if scrape.memory()['percent'] >= MEMORY_PERCENT_THRESHOLD:
			# Wait till all threads realize that they need to relinquish their excess memory
			#print('n waiting', memory_release_barrier.n_waiting)
			memory_release_barrier.wait()
			print('----------------- VIRTUAL MEMORY IS ALMOST FULL ---------------------')
			save_tweet_details_to_file(tweets, tweet_detail_file_name)
			tweets = []
			driver.close()
			driver = webdriver.Firefox()

	save_tweet_details_to_file(tweets, tweet_detail_file_name)
	driver.close()

if __name__ == "__main__":
	id_file_name = input('What is the name of the id file? ')
	tweet_detail_file_name = input('What is the tweet detail output file name? ')
	num_threads = input('How many threads to use? (Hit enter to use all cores) ')

	# Make sure we are not doing duplicate work by checking for duplicate twitter ids
	all_ids = []
	try:
		user_tweet_dict = json.load(open(id_file_name))
	except:
		print('File not found. Please enter an existing filename')
		sys.exit(1)
	user = user_tweet_dict['user']
	all_ids = list(set(user_tweet_dict['ids']))

	current_milli_time = lambda: int(round(time.time() * 1000))

	start = current_milli_time()
	# Use multiple threads if multiple id_files
	use_all_cores = num_threads == ''
	if use_all_cores:
		num_cores = multiprocessing.cpu_count() // 2
		num_threads = num_cores
	else:
		num_threads = int(num_threads)


	memory_release_barrier = threading.Barrier(parties=num_threads)
	#print('parties:', memory_release_barrier.parties)
	if len(all_ids) > num_threads:
		num_ids_each = len(all_ids) // num_threads
		start_index = 0
		end_index = start_index + num_ids_each
		threads = []
		# Minus 1 b/c we want to use the main thread as well
		num_threads -= 1
		for i in range(num_threads):
			#print('thread',i,start_index, end_index,len(all_ids[start_index:end_index]))
			t = threading.Thread(target=get_tweet_details, 
				kwargs={'ids':all_ids[start_index:end_index], 'tweet_detail_file_name':tweet_detail_file_name})
			threads.append(t)
			t.start()
			start_index = end_index
			end_index = start_index + num_ids_each

		#print('main thread',start_index,len(all_ids[start_index:]))
		# Set the main thread to work
		get_tweet_details(all_ids[start_index:], tweet_detail_file_name)

		# Wait for other threads to finish
		for t in threads:
			t.join()

		print((current_milli_time() - start) / 1000, 'seconds')
	else:
		get_tweet_details(all_ids, tweet_detail_file_name)

	# Make sure all tweet details are unique
	ensure_unique_tweets(tweet_detail_file_name)