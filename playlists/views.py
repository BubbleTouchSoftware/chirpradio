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

"""Views for DJ Playlists."""

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import loader, Context, RequestContext
from auth.decorators import require_role
import auth
from auth import roles
from playlists.forms import PlaylistTrackForm
from playlists.models import Playlist, PlaylistTrack, ChirpBroadcast
from djdb import search
from datetime import datetime, timedelta

common_context = {
    'title': 'CHIRPradio.org DJ Playlist Tracker'
}

@require_role(roles.DJ)
def landing_page(request):
    if request.method == 'POST':
        form = PlaylistTrackForm(data=request.POST)
    else:
        form = PlaylistTrackForm()
    broadcast = ChirpBroadcast()
    pl = PlaylistTrack.all().filter('playlist =', broadcast)
    pl = pl.filter('established >=', datetime.now() - timedelta(hours=3))
    pl = pl.order('-established')
    
    ctx_vars = { 
        'form': form,
        'playlist_events': [e for e in pl]
    }
    ctx_vars.update(common_context)
    
    ctx = RequestContext(request, ctx_vars)
    template = loader.get_template('playlists/landing_page.html')
    return HttpResponse(template.render(ctx))
    
@require_role(roles.DJ)
def add_track(request):
    if request.method == 'POST':
        form = PlaylistTrackForm(
                    data=request.POST, 
                    current_user=auth.get_current_user(request))
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('playlists_landing_page'))
    else:
        form = PlaylistTrackForm()
    ctx_vars = { 
        'form': form
    }
    ctx_vars.update(common_context)
    ctx = RequestContext(request, ctx_vars)
    template = loader.get_template('playlists/landing_page.html')
    return HttpResponse(template.render(ctx))
    