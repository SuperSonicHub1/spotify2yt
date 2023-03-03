from spotipy import Spotify
from requests import Session
from flask import Flask, redirect, abort
from selectolax.parser import HTMLParser
from ytmusicapi import YTMusic
import json
from typing import Optional
from urllib.parse import urlparse
from os.path import split 

session = Session()

def get_spotify_token():
	res = session.get("https://open.spotify.com/")
	res.raise_for_status()
	tree = HTMLParser(res.text)
	session_data_node = tree.css_first("script#session")
	assert session_data_node
	return json.loads(session_data_node.text())['accessToken']

def spotify_content_type_to_yt_music_filter(content_type: str) -> Optional[str]:
	"""
	https://ytmusicapi.readthedocs.io/en/stable/reference.html#ytmusicapi.YTMusic.search
	https://community.spotify.com/t5/Desktop-Windows/URI-Codes/td-p/4479486
	"""

	if content_type == '/album':
		return 'albums'
	elif content_type == '/track':
		return 'songs'
	elif content_type == '/artist':
		return 'artists'
	else:
		return None

sp = Spotify(get_spotify_token(), requests_session=session)
ytmusic = YTMusic(requests_session=session)

def spotify2yt(url: str) -> str:
	path = urlparse(url).path
	content_type, spotify_id = split(path)
	assert content_type
	assert spotify_id

	yt_music_filter = spotify_content_type_to_yt_music_filter(content_type)
	
	if content_type == '/album':
		album = sp.album(url)
		assert album
		query = f"{album['name']} {album['artists'][0]['name']}"
	elif content_type == '/track':
		track = sp.track(url)
		assert track
		query = f"{track['name']} {track['artists'][0]['name']}"
	elif content_type == '/artist':
		artist = sp.artist(url)
		assert artist
		query =  artist['name']
	else:
		return url

	results = ytmusic.search(query, filter=yt_music_filter, limit=1, ignore_spelling=True)
	assert results

	result = results[0]
	result_type = result['resultType']

	if result_type == 'song':
		redirect = f"https://music.youtube.com/watch?v={result['videoId']}"
	elif result_type == 'album' or result_type == 'artist':
		redirect = f"https://music.youtube.com/browse/{result['browseId']}"

	return redirect

# print(spotify2yt("https://open.spotify.com/album/7oFLY1YL5bBI32UHsmQO6q?si=Uj4Hax1WStuur4nI5OY8_g"))
# print(spotify2yt("https://open.spotify.com/track/4nmjL1mUKOAfAbo9QG9tSE?si=a66197f934754b75"))
# print(spotify2yt("https://open.spotify.com/artist/1S2S00lgLYLGHWA44qGEUs"))

app = Flask(__name__)

@app.route("/")
def index():
	return "Use this site like: /spotify_url"

@app.route("/<path:url>")
def redirection(url: str):
	if not url:
		abort(400)
	return redirect(spotify2yt(url))

app.run(host='0.0.0.0', port=8080)
