# Twitter Scraper

This scraper will be used to analyze twitter users sentiment towards Donald Trump and Barack Obama's presidency. I want to find out who is liked more, what policies people supported, what twitter users think of Trump and Obama. Other topics of interest will peoples' sentiment towards the Trump-Russia investigation, how Trump used Twitter to erode Hillary Clinton's campaign. The analysis may also include sentiment towards Hillary Clinton and perhaps compare it to what people thought of Barack Obama when he was campaigning (both times) for president. It might also be interesting to analyze sentiment towards the rest of the Trump family as well.

The analysis may appear either in this repository or in the machine-learning repository.

Also, special thanks to <a href="https://github.com/bpb27">bpb27</a>. This scraper is an extension of the scraper found at <a href="https://github.com/bpb27/twitter_scraping">https://github.com/bpb27/twitter_scraping</a>. I have added parallelization to speed up gathering tweet details, comment scraping, tweet metadata scraping (such as number of likes and retweets), and, <strike>since the program uses a lot of virtual memory, I have added checks for memory availabilty</strike> it is only true that the program consumes a lot of memory when you use Firefox as the selenium web browser; I believe it has some memory leaks, so there are checks for that to eliminate the issue. Specifically, when memory is low, each thread will write its current tweet details to a unique JSON file and the browsers will be closed and reopened to eliminate high memory usage. The individual JSON files will be combined into a single JSON file once all tweets have been fetched.

Timings and speed up due to parallelization of tweet_details.py (y axis for timings is in seconds):

<strong>6x speed up using 8 cores!</strong>

![Twitter Scraping Timings and Speed Ups from Parallelization](http://hive.sewanee.edu/evansdb0/Twitter_Speedups.png)
