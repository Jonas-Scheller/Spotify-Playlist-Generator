import spotipy
import configparser
from spotipy.oauth2 import SpotifyOAuth
from datetime import date
from random import sample
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans


class SpotifyPlaylistCreator:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.cfg')
        client_id = config.get('SPOTIFY', 'CLIENT_ID')
        client_secret = config.get('SPOTIFY', 'CLIENT_SECRET')
        redirect_uri = config.get('SPOTIFY', 'REDIRECT_URI')
        username = config.get('SPOTIFY', 'USERNAME')

        scope = "user-top-read user-read-recently-played playlist-modify-public user-library-read"
        auth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri,
                            username=username, scope=scope)

        self.sp = spotipy.Spotify(auth_manager=auth)
        self.user_id = self.sp.me()['id']

    def get_recent_artists(self, term):
        """
        Returns the user's top 25 artists for the given term
        :param term: valid values short_term, medium_term, long_term
        :return: list of spotify artist uris
        """
        results = self.sp.current_user_top_artists(time_range=term, limit=25)
        return [r['uri'] for r in results['items']]

    def get_top_tracks_of_artist(self, artist, top_tracks = 5):
        """
        Returns the top tracks for a given artist
        :param artist: spotify uri of artist
        :param top_tracks: number of top tracks to be returned
        :return: list of spotify song uri
        """
        response = self.sp.artist_top_tracks(artist)
        for track in response['tracks']:
            print(track['name'])

        return [track['uri'] for track in response['tracks'][:top_tracks]]

    def get_top_tracks(self, term, n_tracks=50):
        """
        Returns the user's top tracks for the given term
        :param term: valid values short_term, medium_term, long_term
        :param n_tracks: number of tracks to be returned
        :return: list of spotify track uris
        """
        tracks = self.sp.current_user_top_tracks(time_range=term, limit=n_tracks)['items']
        return [track['uri'] for track in tracks]

    def add_to_playlist(self, playlist_id, tracks):
        """
        Adds the given tracks to the playlist
        :param playlist_id: spotify playlist id
        :param tracks: list of spotify track uris
        """
        if len(tracks) >= 100:
            self.sp.user_playlist_add_tracks(self.user_id, playlist_id, tracks[:100])
            self.add_to_playlist(playlist_id, tracks[100:])
        else:
            self.sp.user_playlist_add_tracks(self.user_id, playlist_id, tracks)

    def create_playlist(self, playlist_name):
        """
        Creates a new playlist with the given name
        :param playlist_name: name of playlist to be created
        :return: created playlist id
        """
        resp = self.sp.user_playlist_create(self.user_id, playlist_name)
        return resp['id']

    def create_playlist_for_top_artists(self, term):
        """
        Creates a playlist only consisting of songs from the top artists that the user listened to in the given term
        :param term: valid values short_term, medium_term, long_term
        """
        artists = self.get_recent_artists(term)
        playlist_name = "Top Artists Track List " + str(date.today())
        playlist_id = self.create_playlist(playlist_name)
        for a in artists:
            tracks = self.get_top_tracks_of_artist(a)
            self.add_to_playlist(playlist_id, tracks)

    def create_playlist_for_top_songs(self, term):
        """
        Creates a playlist based on the user's most listened songs in the given term
        :param term: valid values short_term, medium_term, long_term
        """
        playlist_name = "Top Tracks " + str(date.today()) + " " + term

        playlist_id = self.create_playlist(playlist_name)
        top_tracks = self.get_top_tracks(term)
        self.add_to_playlist(playlist_id, top_tracks)

    def create_recommendation_playlist_for_term(self, term):
        """
        Creates a playlist with recommended songs based on the user's most listened songs in the given term
        :param term: valid values short_term, medium_term, long_term
        """
        playlist_name = "Recommendation for " + term + " " + str(date.today())
        playlist_id = self.create_playlist(playlist_name)
        tracks = self.get_top_tracks(term)

        for i in range(10):
            track_samples = sample(tracks, 5)
            rec = self.sp.recommendations(seed_tracks=track_samples)
            rec_tracks = [track['uri'] for track in rec['tracks']]

            self.add_to_playlist(playlist_id, rec_tracks)

    def get_saved_tracks(self):
        """
        Returns all tracks that the user has saved
        :return: list of spotify track uris
        """
        results = self.sp.current_user_saved_tracks()
        tracks_uris = [t['track']['uri'] for t in results['items']]
        added_dates = [t['added_at'] for t in results['items']]
        while results['next']:
            results = self.sp.next(results)
            tracks_uris += [t['track']['uri'] for t in results['items']]
            added_dates += [t['added_at'] for t in results['items']]

        return tracks_uris, added_dates

    def get_features_for_track(self, track_uris):
        """
        Returns the features for the given tracks
        :param track_uris: list of spotify track uris
        :return: normalized song features as numpy array
        """
        features_of_interest = ['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness',
                                'valence', 'tempo', 'mode']
        features = np.zeros((len(track_uris), len(features_of_interest)))

        for i in range(0, len(track_uris), 50):
            result = self.sp.audio_features(track_uris[i:i + 50])
            for j, f in enumerate(features_of_interest):
                features[i:i + 50, j] = np.array([track[f] for track in result])

        scaler = MinMaxScaler()
        scaler.fit(features)
        normalized_features = scaler.transform(features)
        return normalized_features

    def cluster_songs(self, nClusters=4):
        """
        Clusters the users saved tracks into playlists based on the attributes danceability, energy,
            loudness, speechiness, acousticness, instrumentalness, valence, tempo, mode as obtained
            by the spotify track analysis
        :param nClusters: number of playlists to be created
        """
        track_uris, added_dates = self.get_saved_tracks()
        features = self.get_features_for_track(track_uris)

        kmeans = KMeans(n_clusters=nClusters).fit(features)
        playlist_ids = [''] * nClusters

        for i in range(nClusters):
            playlist_ids[i] = self.create_playlist("Saved Tracks Cluster Playlist " + str(i))

        for c in range(nClusters):
            label_uris = [track_uris[j] for j in range(len(track_uris)) if kmeans.labels_[j] == c]
            self.add_to_playlist(playlist_ids[c], label_uris)

    def filter_tracks_for_time_period(self, tracks_uris, added_dates, year, month_start, month_end):
        """
        Filters given tracks based on the date it was added to the user's library, e.g.,
            find all tracks that were added in 2020 from January to March
        :param tracks_uris: list of spotify track uris
        :param added_dates: list of dates
        :param year: filter for year
        :param month_start: filter for month start
        :param month_end: filter for month end
        :return: list of spotify track uris
        """
        result_track_uris = []
        for index in range(len(added_dates)):
            track_year = int(added_dates[index][:4])
            track_month = int(added_dates[index][5:7])

            if track_year == year and month_start <= track_month <= month_end:
                result_track_uris.append(tracks_uris[index])

            if track_year < year:
                break

        return result_track_uris

    def create_play_list_by_half_year(self):
        """
        create a new playlist for every half a year based on the songs that were added in this period
        """
        playlist_name_dict = {0: 'First Half of ', 6: 'Second Half of '}
        tracks_uris, added_dates = self.get_saved_tracks()
        first_save_year = int(added_dates[-1][:4])
        first_save_month = int(added_dates[-1][5:7])
        last_save_year = int(added_dates[0][:4])
        last_save_month = int(added_dates[0][5:7])

        for year in range(first_save_year, last_save_year + 1, 1):
            for month in [0, 6]:
                if not (year == first_save_year and first_save_month > month) \
                        and not (year == last_save_year and month > last_save_month):
                    res_track_uris = self.filter_tracks_for_time_period(tracks_uris, added_dates, year, month,
                                                                        month + 5)
                    playlist_name = playlist_name_dict[month] + str(year)
                    playlist_id = self.create_playlist(playlist_name)
                    self.add_to_playlist(playlist_id, res_track_uris)


# gen = SpotifyPlaylistCreator()
# gen.cluster_songs()
# gen.get_saved_tracks()
# gen.create_play_list_by_half_year()
# gen.create_playlist_for_top_artists("short_term")
# for term in ['short_term', 'medium_term', 'long_term']:
#    gen.create_playlist_for_top_songs(term)
# gen.create_recommendation_playlist_for_term("short_term")

# gen.collect_statistics("short_term")
