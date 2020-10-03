# This assignment has been completed by keeping the cookbook as a source of reference
# Importing all the required python modules for the project
import twitter
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine

from functools import partial
from sys import maxsize as maxint
import operator

import networkx as nx
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

#Giving the twitter developer account authentication keys to use the twitter APIs

CONSUMER_KEY = '****'
CONSUMER_SECRET = '****'
OAUTH_TOKEN = '****'
OAUTH_TOKEN_SECRET = '***'

auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)

twitter_api = twitter.Twitter(auth=auth)
print(twitter_api)


def twitter_http_request(twitter_api_func, max_errors=10, *args, **kw):
    # A function to handle all the HTTP Errors.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):

        if wait_period > 3600:
            print('Exceeded the number retries. Exiting.', file=sys.stderr)
            raise e

        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429:
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes.....", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60 * 15 + 5)
                print('.....Trying again.', file=sys.stderr)
                return 2
            else:
                raise e  # Caller to handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'.format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    wait_period = 2
    error_count = 0

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Number of errors are more. Discontinuing..", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Number of errors are more. Discontinuing..", file=sys.stderr)
                raise


def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    # Must have either screen_name or user_id
    assert (screen_name != None) != (user_id != None), "Must have screen_name or user_id, but not both"

    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters

    get_friends_ids = partial(twitter_http_request, twitter_api.friends.ids,
                              count=5000)
    get_followers_ids = partial(twitter_http_request, twitter_api.followers.ids,
                                count=5000)

    friends_ids, followers_ids = [], []

    for twitter_api_func, limit, ids, label in [
        [get_friends_ids, friends_limit, friends_ids, "friends"],
        [get_followers_ids, followers_limit, followers_ids, "followers"]
    ]:

        if limit == 0: continue

        cursor = -1
        while cursor != 0:

            # Use twitter_http_request via the partially bound callable...
            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else:  # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']

            print('Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name)),
                  file=sys.stderr)

            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances

            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]


def crawl_followers(twitter_api, screen_name):
    # Retrieving friends and followers of the specified screen name
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, screen_name, friends_limit=5000,
                                                           followers_limit=5000)

    # Retrieving reciprocal friends
    reciprocal_friends = list(set(friends_ids).intersection(followers_ids))[
                         0:15]  # 15 because retrieving info of very large number of reciprocal friends throws a http error.

    # Retrieving user info for the reciprocal friends
    reciprocalfriends_userinfo = twitter_http_request(twitter_api.users.lookup, user_id=reciprocal_friends)

    dict_reciprocalfriends = {}

    # Checking if the user info is not None and adding the screen name and followers count of the reciprocal friends to the dictionary
    if reciprocalfriends_userinfo is not None:
        for acc in reciprocalfriends_userinfo:
            dict_reciprocalfriends[acc['screen_name']] = acc['followers_count']

    # Sort and list the screen names in deescending order of followerscount
    sorted_reciprocalfriends = dict(sorted(dict_reciprocalfriends.items(), key=operator.itemgetter(1), reverse=True))
    return list(sorted_reciprocalfriends.keys())[0:5]


G = nx.Graph()
screen_name = "MadhavCb"
top5 = crawl_followers(twitter_api, screen_name)
users = top5
G.add_node(screen_name)
for user in top5:
    G.add_node(user)
    G.add_edge(screen_name, user)

# Giving range 20 to get 100 nodes
for i in range(20):
    user = users[i]
    #retrieving top 5 reciprocal friends for new friends list
    new_users = crawl_followers(twitter_api, user)
    #adding new users to the list
    users += new_users

    #plotting the graph for the nodes
    for new in new_users:
        G.add_node(new)
        G.add_edge(user, new)

print("Name of users nodes:", users)
print("Number of nodes:", len(users) + 1)

# Network graph
nx.draw(G, with_labels=True, font_weight='bold')

# Output txt file to write the program output

f = open("output.txt", "w")
f.write("Course: Social Media Mining and Data Mining\n")
f.write("Assingment - 2 \n")
f.write("Average distance of network " + str(nx.average_shortest_path_length(G)) + "\n")
f.write("Average diameter of network " + str(nx.diameter(G)) + "\n")
f.write("Network Size \n")
f.write("Number of nodes:" + str(len(users) + 1) + "\n")
f.write("Number of Edges:" + str(G.number_of_edges()))
f.close()

nx.draw(G)
plt.savefig("graph.png")