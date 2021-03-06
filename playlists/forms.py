###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

"""Forms for DJ playlists."""

import auth
from django.utils.translation import ugettext_lazy as _
from django.template import loader
from django import forms
from djdb.models import Artist, Album, Track
from google.appengine.api import memcache
from playlists.models import Playlist, PlaylistTrack, chirp_playlist_key
from common.autoretry import AutoRetry

class PlaylistTrackForm(forms.Form):
    """
    Manage a track in a DJ playlist
    """
    artist = forms.CharField(label=_("Artist"),
                required=True,
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the artist name.'})
    artist_key = forms.Field(label=_("Artist Key"),
                required=False,
                widget=forms.HiddenInput())
    album = forms.CharField(label=_("Album"),
                required=True,
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the album.'})
    album_key = forms.Field(label=_("Album Key"),
                required=False,
                widget=forms.HiddenInput())
    label = forms.CharField(label=_("Label"),
                required=True,
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the label.'})
    song = forms.CharField(label=_("Song Title"),
                required=True,
                widget=forms.TextInput(attrs={'class':'text'}),
                error_messages={'required':'Please enter the song title.'})
    song_key = forms.Field(label=_("Song Key"),
                required=False,
                widget=forms.HiddenInput())
    is_heavy_rotation = forms.BooleanField(label=_("Heavy rotation"), required=False)
    is_light_rotation = forms.BooleanField(label=_("Light rotation"), required=False)
    is_local_current = forms.BooleanField(label=_("Local current"), required=False)
    is_local_classic = forms.BooleanField(label=_("Local classic"), required=False)
    song_notes = forms.CharField(label=_("Song Notes"),
                required=False,
                widget=forms.Textarea(attrs={'class':'text'}))

    def __init__(self, data=None, current_user=None, playlist=None):
        self.current_user = current_user
        self.playlist = playlist or chirp_playlist_key()
        super(PlaylistTrackForm, self).__init__(data=data)

    def save(self):
        if not self.current_user:
            raise ValueError("Cannot save() without a current_user")

        playlist_track = PlaylistTrack(
                            playlist=self.playlist,
                            selector=self.current_user)

        if self.cleaned_data['artist_key']:
            playlist_track.artist = Artist.get(self.cleaned_data['artist_key'])
        else:
            playlist_track.freeform_artist_name = self.cleaned_data['artist']
        if self.cleaned_data['song_key']:
            playlist_track.track = Track.get(self.cleaned_data['song_key'])
        else:
            playlist_track.freeform_track_title = self.cleaned_data['song']
        if self.cleaned_data['album_key']:
            playlist_track.album = Album.get(self.cleaned_data['album_key'])
        elif self.cleaned_data['album']:
            playlist_track.freeform_album_title = self.cleaned_data['album']
        if self.cleaned_data['label']:
            playlist_track.freeform_label = self.cleaned_data['label']
        if self.cleaned_data['song_notes']:
            playlist_track.notes = self.cleaned_data['song_notes']
        if self.cleaned_data['is_heavy_rotation']:
            playlist_track.categories.append('heavy_rotation')
        if self.cleaned_data['is_light_rotation']:
            playlist_track.categories.append('light_rotation')
        if self.cleaned_data['is_local_current']:
            playlist_track.categories.append('local_current')
        if self.cleaned_data['is_local_classic']:
            playlist_track.categories.append('local_classic')
        AutoRetry(playlist_track).save()

        trk = playlist_track
        memcache.set('playlist.last_track', {
            'artist_name': trk.artist_name,
            'track_title': trk.track_title,
            'album_title_display': trk.album_title_display,
            'label_display': trk.label_display,
            'notes': trk.notes,
            'key': str(trk.key()),
            'categories': list(trk.categories),
            'selector_key': str(trk.selector.key()),
            'established_display': trk.established.timetuple()[0:7]
        }, 30)

        return playlist_track



class PlaylistReportForm(forms.Form):
    from_date = forms.DateField(required=True)
    to_date = forms.DateField(required=True)
