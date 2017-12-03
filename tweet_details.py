from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep
import json
import datetime
import os
import psutil
import sys
import threading

# only edit these if you're having problems
delay = .25  # time to wait on each page load before reading the page
pop_up_tweet_selector ='.permalink-container'
text_selector = '.tweet-text'
metadata_selector = '.metadata'
like_selector = '.js-actionFavorite .ProfileTweet-actionCount'
comment_selector = '.js-actionReply .ProfileTweet-actionCount'
retweet_selector = '.js-actionRetweet .ProfileTweet-actionCount'

# comment is a reference to '.tweet'
def get_comment_details(comment):
	commenter_username = comment.find_element_by_css_selector('.stream-item-header').find_element_by_css_selector('.username').text
	comment_text = comment.find_element_by_css_selector('.tweet-text').text
	time_from_original_post = comment.find_element_by_css_selector('._timestamp').text
	comment_like_num = comment.find_element_by_css_selector(like_selector).text
	comment_comment_num = comment.find_element_by_css_selector(comment_selector).text
	comment_retweet_num = comment.find_element_by_css_selector(retweet_selector).text

	# Handling empty comment stats
	if comment_like_num.strip() == "":
		comment_like_num = 0
	if comment_comment_num.strip() == "":
		comment_comment_num = 0
	if comment_retweet_num.strip() == "":
		comment_retweet_num = 0

	comment_dict = {
		"commenter_username": commenter_username,
		"comment_text":comment_text,
		"time_from_original_post":time_from_original_post,
		"comment_like_num":comment_like_num,
		"comment_comment_num":comment_comment_num,
		"comment_retweet_num":comment_retweet_num
	}
	return comment_dict

# tweet is selenium element reference to '.permalink-container' class
def get_comments(driver, tweet):
	reply_to_container = driver.find_element_by_css_selector('.replies-to')
	comments = reply_to_container.find_elements_by_css_selector('.tweet')
	old_comment_len = len(comments)
	new_comment_len = -1
	while(old_comment_len != new_comment_len):
		print('scrolling down to load more comments')
		driver.execute_script('document.getElementById(\'permalink-overlay\').scrollTo(0, document.getElementById(\'permalink-overlay\').scrollHeight)')
		sleep(delay)
		comments = tweet.find_elements_by_css_selector('.tweet')
		old_comment_len = new_comment_len
		new_comment_len = len(comments)
		print('old comments:', old_comment_len, 'current:', new_comment_len)

	c = []
	# The first comment is the actual post not a comment so strip it out
	for comment in comments[1:]:
		comment_details = get_comment_details(comment)
		c.append(comment_details)
	return c

def get_tweet_info(driver,tweet, id):
	text = tweet.find_element_by_css_selector(text_selector).text
	metadata = tweet.find_element_by_css_selector(metadata_selector).text
	like_num = tweet.find_element_by_css_selector(like_selector).text
	comment_num = tweet.find_element_by_css_selector(comment_selector).text
	comments = get_comments(driver, tweet)
	retweet_num = tweet.find_element_by_css_selector(retweet_selector).text
	tweet_dict = {
		"tweet_id": id,
		"tweet_text": text,
		"tweet_metadata": metadata,
		"like_num": like_num,
		"comment_num": comment_num,
		"comments": comments,
		"retweet_num": retweet_num,
	}
	return tweet_dict

def form_tweet_detail_url(id, user):
	url = 'https://twitter.com/' + user + '/status/' + id
	return url

def get_id_files(prefix):
	files = os.listdir('.')
	id_files = []
	for file in files:
		if os.path.isfile(file) and file.startswith('prefix'):
			id_files.append(file)
	return id_files

def create_tweet_detail_files(id_file=None):
	if not id_file:
		return
	driver = webdriver.Firefox()  # options are Chrome() Firefox() Safari()
	user_tweet_dict = json.load(open(id_file))
	user = user_tweet_dict['user']
	ids = user_tweet_dict['ids']
	tweets = []
	for id in ids:
		driver.get(form_tweet_detail_url(id, user))
		sleep(delay)
		tweet = driver.find_element_by_css_selector(pop_up_tweet_selector)
		tweet_dict = get_tweet_info(driver,tweet, id)
		tweets.append(tweet_dict)
		print(len(tweets))
		# If memory available is less than threshold, save tweet data to a file to save memory
		if psutil.virtual_memory().available <= MEMORY_THRESHOLD:
			print('-----------------VIRTUAL MEMORY IS ALMOST EMPTY---------------------')
			tweets_filename = tweets_filename_prefix + str(num_files) + '_' + str(os.getpid()) + '.json'
			with open(tweets_filename, 'w') as outfile:
				json.dump(tweets, outfile)
			num_files += 1
			tweets = []


MEMORY_THRESHOLD = 2000 * 1024 * 1024 # 2GB
twitter_user = input('What is the username of the twitter user? ')
id_files = get_id_files(twitter_user)
if len(id_files) == 0:
	print('No id files for that username:', twitter_user)
	print('Run python3 scrape.py with that twitter user as input')
	sys.exit(1)
# Use multiple threads if multiple id_files
threads = []
if len(id_files) > 1:
	for id_file in id_files[1:]:
		t=threading.Thread(target=create_tweet_detail_files, kwargs={'id_file':id_file})
		threads.append(t)
		t.start()

# Set the main thread to work
create_tweet_detail_files(id_files[0])

# Wait for other threads to finish
for t in threads:
	t.join()
