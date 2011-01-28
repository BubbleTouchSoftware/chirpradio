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

"""Constants and definitions related to roles.

We use these roles to define a very simple set of permissions.
"""

# A hard-wired list of all possible roles.  Each role is specified by
# a more-or-less human-readable string.
DJ = 'dj'
MUSIC_DIRECTOR = 'music_director'
REVIEWER = 'reviewer'
VOLUNTEER_COORDINATOR = 'volunteer_coordinator'
TRAFFIC_LOG_ADMIN = 'traffic_log_admin'

# A tuple containing all possible roles.
ALL_ROLES = (
    DJ,
    MUSIC_DIRECTOR,
    REVIEWER,
    VOLUNTEER_COORDINATOR,
    TRAFFIC_LOG_ADMIN,
)
