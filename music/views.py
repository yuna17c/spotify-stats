from django.shortcuts import render, redirect
from django.http import JsonResponse
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
from django.views.decorators.csrf import csrf_exempt

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Add this line to disable HTTPS requirement

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = 'http://127.0.0.1:8000/callback/'
authorization_base_url = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'
scope = 'user-library-read'

def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def logout(request):
    request.session.flush()
    return redirect('/login/')


def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={artist_name}&type=artist&limit=1"
    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]
    if len(json_result) == 0:
        return None
    return json_result[0]

def get_songs_by_artist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["tracks"]
    return json_result

def index(request):
    return render(request, 'index.html')

def home(request):
    if 'oauth_token' not in request.session:
        return redirect('spotify_login')
    return render(request, 'home.html')


@csrf_exempt
def search(request):
    data = json.loads(request.body)
    artist_name = data['artist_name']
    token = get_token()
    artist = search_for_artist(token, artist_name)
    if artist is None:
        return JsonResponse({"error": "No artist found"})
    artist_id = artist['id']
    songs = get_songs_by_artist(token, artist_id)
    songs_list = [{"name": song["name"]} for song in songs]
    return JsonResponse({"songs": songs_list})

def spotify_login(request):
    spotify = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorization_url, state = spotify.authorization_url(authorization_base_url)
    request.session['oauth_state'] = state
    return redirect(authorization_url)

def spotify_callback(request):
    spotify = OAuth2Session(client_id, redirect_uri=redirect_uri, state=request.session['oauth_state'])
    token = spotify.fetch_token(token_url, client_secret=client_secret, authorization_response=request.build_absolute_uri())
    request.session['oauth_token'] = token
    return redirect('home')

def user_stats(request):
    token = request.session.get('oauth_token')
    if not token:
        return redirect('/login/')

    headers = get_auth_header(token['access_token'])
    user_profile = get('https://api.spotify.com/v1/me', headers=headers).json()
    user_top_artists = get('https://api.spotify.com/v1/me/top/artists', headers=headers).json()
    user_top_tracks = get('https://api.spotify.com/v1/me/top/tracks', headers=headers).json()

    context = {
        'user_profile': user_profile,
        'top_artists': user_top_artists['items'],
        'top_tracks': user_top_tracks['items']
    }
    print(context)

    return render(request, 'stats.html', context)

def get_top_songs(request):
    token = request.session.get('oauth_token')
    if not token:
        return redirect('/login/')

    headers = get_auth_header(token['access_token'])
    user_top_tracks = get('https://api.spotify.com/v1/me/top/tracks', headers=headers).json()
    print(user_top_tracks)

    return JsonResponse({
        'top_tracks': user_top_tracks['items']
    })

