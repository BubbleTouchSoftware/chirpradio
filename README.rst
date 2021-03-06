CHIRP Radio is a non-profit organization that runs a community radio station in Chicago
focused on new music and the arts.

Get started by reading the `development guide`_.

.. _`development guide`: http://chirpradio.readthedocs.org/en/latest/index.html

This is the code for CHIRP's internal web applications.  The apps run
on Google App Engine, under the 'chirpradio' project.  The source code is
hosted on Google Code, also under the 'chirpradio' project.

This code is covered by the Apache License, version 2.0 and is
copyrighted by the Chicago Indepedent Radio Project.  For the details of
the Apache License, see:
http://www.apache.org/licenses/LICENSE-2.0.html

For the chirpradio developer dashboard, go to:
http://appengine.google.com/dashboard?&app_id=chirpradio-hrd

For the end-user landing page, go to:
http://chirpradio.appspot.com/

For the Google Code project:
http://code.google.com/p/chirpradio

Helpful external documentation:

* App Engine Python API
  http://code.google.com/appengine/docs/python/

* Django 1.0:
  http://www.djangobook.com/en/2.0/
  Be sure you are looking at the right version of the book!  We are using
  version 1.0 of Django, which is covered by (confusing enough) version 2.0
  of the Django book.

* Mercurial
  http://hgbook.red-bean.com/


OVERVIEW OF THE TREE
====================

There are part of the common infrastructure.::

  docs/
    Documentation.
  djzango.zip
    Django 1.0.2-final, zipped up.  We never want to change this.
  appengine_django/
    From google-app-engine-django, AppEngine helper & glue code.
  common/
    Code & data shared by all apps.
  django-extras/
    A tree that is merged into the django namespace.  We put our own
    glue code here.  This should be kept small and simple.
  __init__.py
  main.py
  manage.py
    Launchers for Django.
  settings.py
    Global configuration for Django.
  urls.py
    Main URL file.
  auth/
    Our own custom authentication & account management system.
  media/common/css/
    Stylesheets common to multiple apps.
  media/common/img/
    Images common to multiple apps.
  media/common/js/
    JavaScripts common to multiple apps, organized by sub directory.
  media/common/js/chirp/
    CHIRP-related JavaScripts that are common to multiple applications.
  media/common/js/[package_name]
    Common external JavaScript packages (like JQuery) would go here.
    Note that since jQuery plugins are generally external to jQuery itself
    they should live in their own subdirectory.

These are places where all applications store data.::

  media/[application name]/{js, css, img}/
  templates/[application name]/

These are applications that are running in production.::

  (None so far)

These are applications that are under development.::

  landing_page/
    Where you end up when you go to "/".  Currently a test page.


THIRD-PARTY CODE
================

* google-app-engine-django

Some of the files in this directory and all of files under the
appengine_django/ subdirectory are based on rev 81 of the
google-app-engine-django Subversion repository.

* Django

All files in django.zip are taken from Django 1.0.2-final.  It was
constructed by running the following commands::

  zip -r django.zip django/__init__.py django/bin django/core \
                    django/db django/dispatch django/forms \
                    django/http django/middleware django/shortcuts \
                    django/template django/templatetags \
                    django/test django/utils django/views

  zip -r django.zip django/conf -x 'django/conf/locale/*'

These commands were taken from
http://code.google.com/appengine/articles/django10_zipimport.html

Some of the CSS files media/common/css are based on files that
were copied from django/contrib/admin/media/css.

* jQuery

The code under media/ext_js/jquery-* is part of the jQuery library
(http://www.jquery.com) and is covered by the MIT license.
