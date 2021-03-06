# -*- coding: utf8 -*-
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

import base64
import os
import time
import unittest

from django import http
from django.test.client import Client
from google.appengine.api import users as google_users
from django.test import TestCase as DjangoTestCase

from common.testutil import FormTestCaseHelper
import auth
from auth import forms as auth_forms
from auth import roles
from auth.models import User, KeyStorage
from auth.views import _reindex


# These are needed by the App Engine local user service stub.
# (google_appengine/google/appengine/api/user_service_stub.py)
os.environ['SERVER_NAME'] = 'localhost'
os.environ['SERVER_PORT'] = '1234'
# We need this in order to instantiate a google_users.User object.
os.environ['USER_EMAIL'] = 'test@test.com'


class AuthTestCase(DjangoTestCase):

    def setUp(self):
        # Remember the original versions of these functions.
        self._orig_get_current_user = google_users.get_current_user
        self._orig_is_current_user_admin = google_users.is_current_user_admin
        self._orig_time = time.time
        # Now replace them with mocks.
        self.g_user = None
        self.is_superuser = False
        self.now = 12345
        google_users.get_current_user = lambda: self.g_user
        google_users.is_current_user_admin = lambda: self.is_superuser
        time.time = lambda: self.now

    def tearDown(self):
        # Restore the google_users APIs we mocked out.
        google_users.get_current_user = self._orig_get_current_user
        google_users.is_current_user_admin = self._orig_is_current_user_admin
        time.time = self._orig_time

    def test_user_model_role_properties(self):
        user = User(email='test')
        self.assertFalse(user.is_volunteer_coordinator)
        self.assertFalse(user.is_music_director)
        user.roles.append(roles.VOLUNTEER_COORDINATOR)
        self.assertTrue(user.is_volunteer_coordinator)
        self.assertFalse(user.is_music_director)
        user.roles.append(roles.MUSIC_DIRECTOR)
        self.assertTrue(user.is_volunteer_coordinator)
        self.assertTrue(user.is_music_director)
        self.assertFalse(user.is_dj)
        user.roles.append(roles.DJ)
        self.assertTrue(user.is_dj)

    def test_user_password_checks(self):
        user = User(email='test_pw_checks@test.com')
        self.assertFalse(user.check_password('foo'))
        user.set_password('foo')
        self.assertTrue(user.check_password('foo'))
        self.assertFalse(user.check_password('bar'))

    def test_security_token_create_and_parse(self):
        # Set up a test user.
        email = 'token_test@test.com'
        user = User(email=email)
        token = auth._create_security_token(user)
        # A new token should work fine and not be stale.
        cred = auth._parse_security_token(token)
        self.assertEqual(email, cred.email)
        self.assertFalse(cred.security_token_is_stale)
        # Don't accept time-traveling tokens.
        self.now -= 60
        self.assertEqual(None, auth._parse_security_token(token))
        # This token is still valid, but is stale.
        self.now += 0.75 * auth._TOKEN_TIMEOUT_S
        cred = auth._parse_security_token(token)
        self.assertEqual(email, cred.email)
        self.assertTrue(cred.security_token_is_stale)
        # Now the token has expired.
        self.now += 0.75 * auth._TOKEN_TIMEOUT_S
        self.assertEqual(None, auth._parse_security_token(token))
        # Reject random garbage.
        for garbage in (None, '', 'garbage'):
            self.assertEqual(None, auth._parse_security_token(garbage))

    def test_password_reset_token_create_and_parse(self):
        email = 'password_reset_token@test.com'
        user = User(email=email)
        token = auth.get_password_reset_token(user)
        observed_email = auth.parse_password_reset_token(token)
        self.assertEqual(email, observed_email)

    def test_attach_credentials(self):
        # Set up a test user.
        email = 'attach_test@test.com'
        user = User(email=email)
        # Attach the user's credentials to a test response.
        response = http.HttpResponse('test')
        auth.attach_credentials(response, user)
        # Make sure the response now contains a cookie with the correct
        # security token.
        self.assertTrue(auth._CHIRP_SECURITY_TOKEN_COOKIE in response.cookies)
        token = response.cookies[auth._CHIRP_SECURITY_TOKEN_COOKIE].value
        cred = auth._parse_security_token(token)
        self.assertEqual(email, cred.email)

    def test_get_current_user(self):
        # Set up a test user.
        email = 'get_current_user_test@test.com'
        user = User(email=email)
        user.save()

        # Create some security tokens.
        expired_token = auth._create_security_token(user)
        self.now += 0.75 * auth._TOKEN_TIMEOUT_S
        stale_token = auth._create_security_token(user)
        self.now += 0.75 * auth._TOKEN_TIMEOUT_S
        good_token = auth._create_security_token(user)

        # Create a test HttpRequest, and test using it against our
        # various tokens.
        request = http.HttpRequest()
        request.COOKIES[auth._CHIRP_SECURITY_TOKEN_COOKIE] = expired_token
        self.assertEqual(None, auth.get_current_user(request))
        request.COOKIES[auth._CHIRP_SECURITY_TOKEN_COOKIE] = stale_token
        user = auth.get_current_user(request)
        self.assertEqual(email, user.email)
        self.assertTrue(user._credentials.security_token_is_stale)
        request.COOKIES[auth._CHIRP_SECURITY_TOKEN_COOKIE] = good_token
        user = auth.get_current_user(request)
        self.assertEqual(email, user.email)
        self.assertFalse(user._credentials.security_token_is_stale)

        # Test that a password reset token can be used to authenticate
        # when POSTed in a variable named CHIRP_Auth.
        request = http.HttpRequest()
        request.method = "POST"
        self.assertEqual(None, auth.get_current_user(request))
        request.POST["CHIRP_Auth"] = base64.urlsafe_b64encode(expired_token)
        self.assertEqual(None, auth.get_current_user(request))
        request.POST["CHIRP_Auth"] = "bogus!!!"
        self.assertEqual(None, auth.get_current_user(request))
        request.POST["CHIRP_Auth"] = base64.urlsafe_b64encode(good_token)
        user = auth.get_current_user(request)
        self.assertEqual(email, user.email)

        # Check that we will reject an inactive user.
        user.is_active = False
        user.save()
        self.assertRaises(auth.UserNotAllowedError,
                          auth.get_current_user, request)
        user.is_active = True
        user.save()

    # This also tests our monkey-patching of Django to make
    # client.login() and client.logout().
    def test_auth_middleware(self):
        client = Client()
        # When returning a user of None, we should get redirected to
        # a login page.
        response = client.get('/')
        self.assertEqual(302, response.status_code)
        # Logged out users should be able to get to the login page.
        response = client.get('/auth/hello')
        self.assertEqual(200, response.status_code)
        # Log in as a test user.
        assert client.login(email='test@test.com')
        # Logged in, active users should be able to reach '/'.
        response = client.get('/')
        self.assertEqual(200, response.status_code)
        # Hitting the logout URL should actually log us out.
        response = client.get('/auth/goodbye')
        self.assertEqual(302, response.status_code)  # Redirects us off-site
        # Since we are now logged out, '/' should try to redirect us to
        # log in.
        response = client.get('/')
        self.assertEqual(302, response.status_code)
        # Deactived users should get a 403
        client.login(email='test@test.com', is_active=False)
        response = client.get('/')
        self.assertEqual(403, response.status_code)
        # Logging out should take us back where we started.
        client.logout()
        response = client.get('/')
        self.assertEqual(302, response.status_code)
    
    def test_logout_redirect(self):
        client = Client()
        # Log in as a test user.
        client.login(email='test@test.com')
        # Logged in, active users should be able to reach '/'.
        response = client.get('/')
        self.assertEqual(200, response.status_code)
        
        response = client.get('/auth/goodbye')
        self.assertRedirects(response, 'http://testserver/auth/hello/')
        
        response = client.get('/auth/goodbye', {'redirect': '/somewhere/else'})
        self.assertRedirects(response, 'http://testserver/auth/hello/?redirect=/somewhere/else')

    def test_client_login_supports_roles(self):
        client = Client()
        # This should be rejected, since the /auth/ page requires
        # special credentials.
        client.login(email='test@test.com', is_active=True)
        response = client.get('/auth/')
        self.assertEqual(403, response.status_code)
        # This should work.
        client.login(email='test@test.com',
                     roles=[roles.VOLUNTEER_COORDINATOR])
        response = client.get('/auth/')
        self.assertEqual(200, response.status_code)

    def test_bootstrapping_via_google_accounts(self):
        client = Client()
        # Not signed in at all?  We should be redirected to a Google
        # login page.
        response = client.get('/auth/_bootstrap')
        self.assertEqual(302, response.status_code)
        # Already signed in?  You should see a 403.
        client.login(email='bootstrap_test_user@test.com')
        response = client.get('/auth/_bootstrap')
        self.assertEqual(403, response.status_code)
        self.assertEqual('Already logged in', response.content)
        client.logout()
        # Reject people who are not superusers.
        g_email = 'google_user@gmail.com'
        self.g_user = google_users.User(email=g_email)
        self.is_superuser = False
        response = client.get('/auth/_bootstrap')
        self.assertEqual(403, response.status_code)
        self.assertEqual('Not a chirpradio project admin', response.content)
        # Create a new User object for superusers.
        self.assertEqual(None, User.get_by_email(g_email))
        self.is_superuser = True
        response = client.get('/auth/_bootstrap')
        self.assertEqual(302, response.status_code)  # Redirect to login page.
        user = User.get_by_email(g_email)
        self.assertEqual(g_email, user.email)
        # If the user already exists for the superuser, 403.
        response = client.get('/auth/_bootstrap')
        self.assertEqual(403, response.status_code)
        self.assertEqual('User %s already exists' % g_email, response.content)

    def test_url_generation(self):
        # This is just a smoke test.
        auth.create_login_url("not actually a path")

    def test_key_storage(self):
        # Explicitly clear our cache.
        KeyStorage._cached = (None, None)
        # Call get method to retrieve our singleton KeyStorage.
        ks = KeyStorage.get()
        self.assertTrue(ks is not None)
        # We should cache this object, so another call will return the
        # same object.
        self.assertTrue(ks is KeyStorage.get())
        # Now advance mock time enough to expire our cache.
        self.now += 365 * 24 * 60 * 60  # 1 year should be enough time
        self.assertTrue(ks is not KeyStorage.get())


class UserTestCase(unittest.TestCase):
    
    def setUp(self):
        for u in User.all().fetch(1000):
            u.delete()

    def test_dj_name(self):
        user = User(email='someone@somewhere',
                    first_name='Steve',
                    last_name='Dolfin')
        user.save()
        self.assertEquals(user.effective_dj_name, 'Steve Dolfin')
        user.dj_name = 'DJ Night Moves'
        user.save()
        self.assertEquals(user.effective_dj_name, 'DJ Night Moves')

    def test_non_ascii_dj_name(self):
        unicode_text = 'フォクすけといっしょ'.decode('utf8')
        user = User(email='someone@somewhere',
                    first_name=unicode_text,
                    last_name=unicode_text)
        user.save()
        self.assertEquals(user.effective_dj_name,
                          u'%s %s' % (unicode_text, unicode_text))
        user.dj_name = unicode_text
        user.save()
        self.assertEquals(user.effective_dj_name, unicode_text)


class FormsTestCase(unittest.TestCase):
    
    def setUp(self):
        for u in User.all().fetch(1000):
            u.delete()
    
    def test_unknown_user_by_email(self):
        form = auth_forms.LoginForm({
            'redirect': '/', 
            'email': 'not-known@host.com', 
            'password': 'wrong'
        })
        self.assertFalse(form.is_valid())

    def test_login_form(self):
        # Set up a test user.
        email = 'test_login_form@test.com'
        user = User(email=email)
        user.set_password('password')
        user.save()
        # Missing required data
        form = auth_forms.LoginForm({'redirect': '/'})
        self.assertFalse(form.is_valid())
        form = auth_forms.LoginForm({'redirect': '/', 'email': email})
        self.assertFalse(form.is_valid())
        # Form should fail to validate if password is incorrect.
        form = auth_forms.LoginForm({'redirect': '/',
                                     'email': email,
                                     'password': 'incorrect password'})
        self.assertFalse(form.is_valid())
        # This should succeed.
        form = auth_forms.LoginForm({'redirect': '/',
                                     'email': email,
                                     'password': 'password'})
        self.assertTrue(form.is_valid())
        # The form should reject inactive users.
        user.is_active = False
        user.save()
        form = auth_forms.LoginForm({'redirect': '/',
                                     'email': email,
                                     'password': 'password'})
        self.assertFalse(form.is_valid())
        # The form should reject unknown users.
        form = auth_forms.LoginForm({'redirect': '/',
                                     'email': 'no_such_user@test.com',
                                     'password': 'password'})
        self.assertFalse(form.is_valid())

    def test_login_with_case_insensitive_email(self):
        # Set up a test user.
        email = 'test_login_form_email@test.com'
        user = User(email=email)
        user.set_password('password')
        user.save()
        
        # This should succeed.
        form = auth_forms.LoginForm({'redirect': '/',
                                     'email': 'TEST_LOGIN_FORM_EMAIL@TEST.COM',
                                     'password': 'password'})
        self.assertTrue(form.is_valid())
        
    def test_change_password_form(self):
        # Set up a test user
        user = User(email='test_change_password_form@test.com')
        user.set_password('password')
        
        # The form should fail to validate if the current password is wrong.
        form = auth_forms.ChangePasswordForm({
                'current_password': 'incorrect password',
                'new_password': 'foo',
                'confirm_new_password': 'foo',
                })
        form.set_user(user)
        self.assertFalse(form.is_valid())

        # The form should fail to validate if the two versions of the
        # new password do not agree.
        form = auth_forms.ChangePasswordForm({
                'current_password': 'password',
                'new_password': 'foo',
                'confirm_new_password': 'bar',
                })
        form.set_user(user)
        self.assertFalse(form.is_valid())

        # This should work.
        form = auth_forms.ChangePasswordForm({
                'current_password': 'password',
                'new_password': 'foo',
                'confirm_new_password': 'foo',
                })
        form.set_user(user)
        self.assertTrue(form.is_valid())

    def test_forgot_password_form(self):
        # Set up a test user
        user = User(email='test_forgot_password_form@test.com')
        user.set_password('password')
        user.save()
        # The form will validate if given a known email address.
        form = auth_forms.ForgotPasswordForm({'email': user.email})
        self.assertTrue(form.is_valid())
        # Check that the user gets attached to the form's user
        # property.
        self.assertEqual(user.email, form.user.email)
        # The form will not validate for an unknown email address.
        form = auth_forms.ForgotPasswordForm({'email': 'nosuchuser@test.com'})
        self.assertFalse(form.is_valid())
        self.assertEqual(None, form.user)

    def test_forgot_password_form_case_insensitive_email(self):
        # Set up a test user
        user = User(email='test_forgot_password_form_email@test.com')
        user.set_password('password')
        user.save()
        
        form = auth_forms.ForgotPasswordForm({'email': 'TEST_FORGOT_PASSWORD_FORM_EMAIL@TEST.COM'})
        self.assertTrue(form.is_valid())

    def test_reset_password_form(self):
        # The form should validate only if both passwords are identical.
        form = auth_forms.ResetPasswordForm({
                'token': 'token',
                'new_password': 'foo',
                'confirm_new_password': 'bar'})
        self.assertFalse(form.is_valid())
        form = auth_forms.ResetPasswordForm({
                'token': 'token',
                'new_password': 'foo',
                'confirm_new_password': 'foo'})
        self.assertTrue(form.is_valid())

class UserViewsTestCase(FormTestCaseHelper, DjangoTestCase):
    
    def setUp(self):
        for u in User.all():
            u.delete()
        assert self.client.login(email="test@test.com", roles=[roles.VOLUNTEER_COORDINATOR])

    def test_email_is_case_insensitive_on_creation(self):
        resp = self.client.post('/auth/add_user/', {
            'email': 'FancyPants@glitterCLUB.com',
            'first_name': 'Steve',
            'last_name': 'Dolfin',
            'dj_name': 'DJ Steve',
            'is_dj': 'checked'
        })
        self.assertNoFormErrors(resp)
        
        u = User.all().filter('last_name =', 'Dolfin').fetch(1)[0]
        self.assertEqual(u.email, 'fancypants@glitterclub.com')
        self.assertEqual(u.dj_name, 'DJ Steve')
        self.assertEqual(u.roles, ['dj'])
        self.assertEqual(u.password, None) # password prompt was emailed to user

    def test_create_user_with_initial_password(self):
        resp = self.client.post('/auth/add_user/', {
            'email': 'bob@bob.com',
            'first_name': 'Bob',
            'last_name': 'Jones',
            'dj_name': 'Dr. Jones',
            'password': "my-initial-password",
            'is_dj': 'checked'
        })
        self.assertNoFormErrors(resp)
        
        user = User.all().filter('email =', 'bob@bob.com').fetch(1)[0]
        # password was set:
        self.assertEqual(user.check_password('my-initial-password'), True)
        
    def test_user_edit_form(self):
        steve = User(
            email='steve@dolfin.com',
            first_name='Steve',
            last_name='Dolfin',
            dj_name='DJ Steve',
            roles=['dj'],
            is_active=True,
            password='123456' # pretend this is encrypted
        )
        steve.save()
        
        resp = self.client.post('/auth/edit_user/', {
            'original_email': 'steve@dolfin.com', # this is the key
            'email': 'steve@dolfin.com',
            'first_name': 'Steven',
            'last_name': 'Dolfin III',
            'dj_name': 'Steve Holt!',
            'is_active': 'checked',
            # change roles:
            'is_volunteer_coordinator': 'checked'
        })
        self.assertNoFormErrors(resp)
        
        user = User.all().filter('email =', 'steve@dolfin.com').fetch(1)[0]
        self.assertEqual(user.first_name, 'Steven')
        self.assertEqual(user.last_name, 'Dolfin III')
        self.assertEqual(user.dj_name, 'Steve Holt!')
        self.assertEqual(user.roles, ['volunteer_coordinator'])
        self.assertEqual(user.password, '123456') # should be untouched
        
    def test_user_edit_form_change_password(self):
        steve = User(
            email='steve@dolfin.com',
            first_name='Steve',
            last_name='Dolfin',
            dj_name='DJ Steve',
            roles=['dj'],
            is_active=True,
            password='123456'
        )
        steve.save()
        
        resp = self.client.post('/auth/edit_user/', {
            'original_email': 'steve@dolfin.com', # this is the key
            'email': 'steve@dolfin.com',
            'first_name': 'Steve',
            'last_name': 'Dolfin',
            'dj_name': 'DJ Seteve',
            'is_active': 'checked',
            'is_dj': 'checked',
            # new password
            'password': '1234567'
        })
        self.assertNoFormErrors(resp)

        user = User.all().filter('email =', 'steve@dolfin.com').fetch(1)[0]
        # password was changed:
        self.assertEqual(user.check_password('1234567'), True)
        

class AutocompleteViewsTestCase(DjangoTestCase):

    def setUp(self):
#        assert self.client.login(email="test@test.com")
        self.activeUser = User(
            email='foo@bar.com',
            first_name='Active',
            last_name='User',
            is_active=True,
            password='123456'
        )
        _reindex(self.activeUser)
        self.activeUser.save()
        self.inactiveUser = User(
            email='blah@blah.com',
            first_name='Inactive',
            last_name='User',
            is_active=False,
            password='123456'
        )
        _reindex(self.inactiveUser)
        self.inactiveUser.save()

    def test_active_user(self):
        response = self.client.get("/auth/search.txt", {'q': 'Active'})
        self.assertEqual(response.content,
            "%s|%s\n" % (self.activeUser, self.activeUser.key()))

    def test_inactive_user(self):
        response = self.client.get("/auth/search.txt", {'q': 'Inactive'})
        self.assertEqual(response.content, "")

