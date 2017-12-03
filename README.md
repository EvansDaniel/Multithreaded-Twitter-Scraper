# Twitter Scraper

This scraper will be used to analyze twitter users sentiment towards Donald Trump and Barack Obama's presidency. I want to find out who is liked more, what policies people supported, what twitter users think of Trump and Obama. Other topics of interest will peoples' sentiment towards the Trump-Russia investigation, how Trump used Twitter to erode Hillary Clinton's campaign. The analysis may also include sentiment towards Hillary Clinton and perhaps compare it to what people thought of Barack Obama when he was campaigning (both times) for president. It might also be interesting to analyze sentiment towards the rest of the Trump family as well.

The analysis may appear either in this repository or in the machine-learning repository.

Also, special thanks to <a href="https://github.com/bpb27">bpb27</a>. This scraper is an extension of the scraper found at <a href="https://github.com/bpb27/twitter_scraping">https://github.com/bpb27/twitter_scraping</a>. I have added parallelization to gathering tweet details, comment scraping, tweet statistic scraping (such as number of likes), and, since the program uses a lot of virtual memory, I have added checks for memory availabilty. Each thread will create a JSON file and exports the current tweet details when memory is low.

Timings and speed up due to parallelization of scraper (y axis for timings is in seconds):

![Twitter Scraping Timings and Speed Ups](http://hive.sewanee.edu/evansdb0/Twitter_Speedups.png)
