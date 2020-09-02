#coding=utf-8

from bs4 import BeautifulSoup
from time import sleep as wait
import re
import requests

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

##################################################
# Copied code
##################################################

class MLStripper(HTMLParser):
    """
    Strips html from strings

    From: http://stackoverflow.com/a/925630/3664835
    """

    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        """
        Saves data internally
        """

        self.fed.append(d)

    def get_data(self):
        """
        Returns all saved data
        """

        return ''.join(self.fed)


def strip_tags(html):
    """
    Strips html from a string

    From: http://stackoverflow.com/a/925630/3664835
    """

    s = MLStripper()
    s.feed(html)
    return ' '.join(s.get_data().split())

##################################################
# Helpers
##################################################


def generate_url(query, first, recent, country_code):
    """
    Generates a Bing search URL for the given query and parameters

    Best: http://www.bing.com/search?q=hello+world&first=9
    Recent: http://www.bing.com/search?q=hello+world&filters=ex1%3a%22ez1%22
    """

    query = '+'.join(query.split())
    url = 'http://www.bing.com/search?q=' + query + '&first=' + first
    if recent in ['h', 'd', 'w', 'm', 'y']: # A True/False would be enough. This is just to maintain consistancy with google.
        url = url + '&filters=ex1%3a%22ez1%22'
    if country_code is not None:
        url += '&cc=' + country_code
    return url


def generate_news_url(query, first, recent, country_code):
    """
    Generates a Bing news URL for the given query and parameters

    Best: http://www.bing.com/news/search?q=hello+world&first=11
    Recent: http://www.bing.com/news/search?q=hello+world&qft=sortbydate%3d%221%22
    """

    query = '+'.join(query.split())
    url = 'http://www.bing.com/news/search?q=' + query + '&first' + first
    if recent in ['h', 'd', 'w', 'm', 'y']: # A True/False would be enough. This is just to maintain consistancy with google.
        url = url + '&qft=sortbydate%3d%221%22'
    if country_code is not None:
        url += '&cc=' + country_code
    return url

def try_cast_int(s):
    """
    Concatenates and converts all digits in the given string into a
    single number
    """

    try:
        temp = re.findall('\d', str(s))
        temp = ''.join(temp)
        return int(temp)
    except:
        return s

##################################################
# Class
##################################################

class Bing:
    """
    Utility class for Bing
    """

    @staticmethod
    def search(query, num=10, start=0, sleep=True, recent=None, country_code=None):
        """
        Retrieves search results
        """

        results = []
        _start = start # Remembers the initial value of start for later use
        _url = None
        related_queries = []
        total_results = None

        while len(results) < num:
            if sleep: # Prevents loading too many pages too soon
                wait(1)
            url = generate_url(query, str(start), recent, country_code)
            if _url is None:
                _url = url # Remembers the first url that is generated
            soup = BeautifulSoup(requests.get(url).text, "html.parser")
            new_results = Bing.scrape_search_result(soup)
            results += new_results
            start += len(new_results)
            if total_results is None:
                raw_total_results = soup.find('span', attrs = {'class' : 'sb_count'})
                total_results = 0
                if raw_total_results is not None:
                    for i in raw_total_results.string:
                        try:
                            temp = int(i)
                            total_results = total_results * 10 + temp
                        except:
                            continue
            if len(new_results) == 0:
                break
            if related_queries == []:
                related_queries = Bing.scrape_related(soup)

        results = results[:num]

        temp = {'results' : results,
                'url' : _url,
                'expected_num' : num,
                'received_num' : start,
                'start' : _start,
                'search_engine' : 'bing',
                'related_queries' : related_queries,
                'total_results' : total_results,
                'country_code': country_code,
        }
        return temp

    @staticmethod
    def scrape_related(soup):
        """
        Retrieves all related items to search results
        """

        related_queries = []

        # Find related item lists
        raw_related = soup.find('ul', attrs = {'class' : 'b_vList'})

        # Retrieve the item titles
        raw_related = raw_related.find_all('a')

        # Strip away the tags
        for related in raw_related:
            related_queries.append(strip_tags(str(related)))

        return related_queries

    @staticmethod
    def scrape_search_result(soup):
        """
        Extracts info from the search results
        """

        # Get the results
        raw_results = soup.find_all('li', attrs = {'class' : 'b_algo'})
        results = []

        for result in raw_results:
            # Get the title
            link = result.find('a').get('href')

            raw_link_text = result.find('a')
            link_text = strip_tags(str(raw_link_text))

            additional_links = dict()

            # Extract other info
            raw_link_info = result.find('div', attrs = {'class' : 'b_caption'})
            description = raw_link_info.find('div', attrs = {'class' : 'b_snippet'})
            if description is None:
                # There are no related links
                link_info = strip_tags(str(raw_link_info.find('p')))
            else:
                # Extract related links
                link_info = strip_tags(str(description))
                for a_link in raw_link_info.find_all('a'):
                    additional_links[strip_tags(str(a_link))] = a_link.get('href')

            temp = { 'link' : link,
                     'link_text' : link_text,
                     'link_info' : link_info,
                     'additional_links' : additional_links,
            }
            results.append(temp)
        return results

    @staticmethod
    def search_news(query, num=10, start=0, sleep=True, recent=None, country_code=None):
        """
        Retrieves news results
        """

        results = []

        # Remembers the initial value of start for later use
        _start = start

        _url = None
        while len(results) < num:
            # Prevents loading too many pages too soon
            if sleep:
                wait(1)

            url = generate_news_url(query, str(start), recent, country_code)
            if _url is None:
                # Remembers the first url that is generated
                _url = url

            # Scrape results from Bing
            soup = BeautifulSoup(requests.get(url).text, "html.parser")
            new_results = Bing.scrape_news_result(soup)
            results += new_results
            start += len(new_results)

        results = results[:num]

        temp = {'results' : results,
                'url' : _url,
                'num' : num,
                'start' : _start,
                'search_engine' : 'bing',
                'country_code': country_code,
        }
        return temp

    @staticmethod
    def scrape_news_result(soup):
        """
        Extracts info from the news results
        """

        # Extract results
        raw_results = soup.find_all('div', attrs = {'class' : 'sn_r'})
        results = []

        for result in raw_results:
            # Get the title
            link = result.find('a').get('href')

            raw_link_text = result.find('a')
            link_text = strip_tags(str(raw_link_text))

            additional_links = dict() # For consistancy

            # Extract other info
            raw_link_info = result.find('span', attrs = {'class' : 'sn_snip'})
            link_info = strip_tags(str(raw_link_info))

            raw_source = result.find('cite', attrs = {'class' : 'sn_src'})
            source = strip_tags(str(raw_source))

            raw_time = result.find('span', attrs = {'class' : 'sn_tm'})
            time = strip_tags(str(raw_time))

            temp = { 'link' : link,
                     'link_text' : link_text,
                     'link_info' : link_info,
                     'additional_links' : additional_links,
                     'source' : source,
                     'time' : time,
            }
            results.append(temp)
        return results
