import requests
from bs4 import BeautifulSoup
import json
import credentials
import re
import urllib.parse

# Header for POST request
headers = {
    "Authorization": "Bearer " + credentials.token,
    "Content-Type": "application/json"
}

def get_track_info(url):
    """
    This function returns a nested list containing the artist names and song titles from the setlist.
    """
    # Get content from url
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

    # Parse through html
    soup = BeautifulSoup(r.content, "html.parser")

    # From looking at the HTML, all songs are under a div with classname of "tlToogleData"
    extracted = soup.find_all(class_="tlToogleData")

    tracklist = []
    for data in extracted:
        # Song name and artist is located in <meta itemprop="name" content="[Artist - Song]"> with in the div
        track = data.find_all(itemprop="name")
        # Track is empty if (itemprop="name") not found, i.e. in the case of ID - ID
        if track:
            # Add [Artist, Song] to tracklist
            info = track[0].get("content").split(" - ")
            # ID - ID is used to denote unidentified artist or song
            if not (info[0] == "ID" or info[1] == "ID"):
                tracklist.append(info)

    return tracklist

def create_spotify_playlist(playlist_name="new_playlist"):
    """
    This function creates an empty playlist in Spotify. Returns the ID of the newly created playlist.
    """
    # Creates a dict that will be turned into JSON for POST request
    data = {
        "name": playlist_name
    }

    body_data = json.dumps(data)

    # POST request to create Spotify playlist
    r = requests.post("https://api.spotify.com/v1/users/{user_id}/playlists".format(user_id=credentials.user_id),
                      data=body_data, headers=headers)

    # Extracting playlist id from response JSON
    response = r.json()

    return response["uri"].split(":")[2]


def get_track_ids(tracklist):
    """
    This function searches for the tracks in the tracklist on Spotify. Returns a list of the URIs and a list of missing
    songs.
    """
    tracks_uris = []
    missing_tracks = []

    for track in tracklist:
        artist, song = track

        # If there is an ampersand, take first artist
        first_artist = artist.split(" & ")[0]
        artist = first_artist


        # Replace spaces with encoded spaces
        artist = urllib.parse.quote(artist)
        song = urllib.parse.quote(song)

        # Remove non alpha numeric characters and spaces
        artist = re.sub(r'[^A-Za-z0-9 %]+', '', artist)
        song = re.sub(r'[^A-Za-z0-9 %]+', '', song)

        # GET request to search song on Spotify
        r = requests.get(
            "https://api.spotify.com/v1/search?q=track:{track}%20artist:{artist}&type=track&limit=7".format(track=song,
                                                                                                    artist=artist),
            headers=headers)

        # Decode JSON returned by the GET request
        data = r.json()

        if "error" in data:
            print("Error: Related to get request. ({artist}, {song})".format(artist=track[0], song=track[1]))
            break
        else:
            # If search yield results
            if data["tracks"]["items"]:
                # Iterate through results
                found = False
                for result in data["tracks"]["items"]:
                    # If the result artist matches artist name, add
                    if result["artists"][0]["name"].lower() == first_artist.lower():
                        tracks_uris.append(result["uri"])
                        print ("ADDED: " + track[0] + " - " + track[1] + "\n")
                        found = True
                        break
                if not found:
                    print("NOT FOUND: " + track[0] + " - " + track[1] + "\n")
            # Search yielded no results
            else:
                missing_tracks.append([track[0], track[1]])
                print("NOT FOUND: " + track[0] + " - " + track[1] + "\n")

    return (tracks_uris, missing_tracks)

def fill_playlist(tracks_uris, playlist_id):
    """
    This function fills the empty playlist with the track URIs.
    """
    uris = ",".join(tracks_uris)
    r = requests.post("https://api.spotify.com/v1/playlists/{playlist_id}/tracks?uris={uri_list}".format(playlist_id=playlist_id,
                                                                                                         uri_list=uris),
                      headers=headers)

if __name__ == "__main__":
    # Get tracklist
    url = "https://www.1001tracklists.com/tracklist/2pykl2bk/amelie-lens-beatport-live-exhale-together-belgium-2021-02-28.html"
    tracklist = get_track_info(url)

    # # Create an empty Spotify playlist
    playlist_id = create_spotify_playlist("Amelie Lens @ Beatport Live EXHALE Together, Belgium")

    # Get track URIs
    search = get_track_ids(tracklist)[0]

    # # Fill playlist
    fill_playlist(search, playlist_id)
