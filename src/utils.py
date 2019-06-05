#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# start-here is an application that helps you to tweak Ubuntu,
# after install a new version of Ubuntu. First stepts with Ubuntu.
#
# Copyright © 2019  Lorenzo Carbonell (aka atareao)
# <lorenzo.carbonell.cerezo at gmail dotcom>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import requests
import gi
try:
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('GLib', '2.0')
except Exception as e:
    print(e)
    exit(1)
from gi.repository import GdkPixbuf
from gi.repository import GLib
import base64
import os
import re
import subprocess
import io
try:
    from . import comun
except Exception as e:
    import sys
    PACKAGE_PARENT = '..'
    SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(),
                                 os.path.expanduser(__file__))))
    sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))
    import comun


def variant_to_value(variant):
    '''Returns the value of a GLib.Variant
    '''
    # pylint: disable=unidiomatic-typecheck
    if type(variant) != GLib.Variant:
        return variant
    type_string = variant.get_type_string()
    if type_string == 's':
        return variant.get_string()
    elif type_string == 'i':
        return variant.get_int32()
    elif type_string == 'b':
        return variant.get_boolean()
    elif type_string == 'as':
        # In the latest pygobject3 3.3.4 or later, g_variant_dup_strv
        # returns the allocated strv but in the previous release,
        # it returned the tuple of (strv, length)
        if type(GLib.Variant.new_strv([]).dup_strv()) == tuple:
            return variant.dup_strv()[0]
        else:
            return variant.dup_strv()
    else:
        print('error: unknown variant type: %s' %type_string)
    return variant


def select_value_in_combo(combo, value):
    model = combo.get_model()
    for i, item in enumerate(model):
        if value == item[1]:
            combo.set_active(i)
            return
    combo.set_active(0)


def get_selected_value_in_combo(combo):
    model = combo.get_model()
    return model.get_value(combo.get_active_iter(), 1)


def download_file(url, local_filename):
    # NOTE the stream=True parameter
    try:
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(e)
    return False


def read_remote_file(url):
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(e)
    return None


def select_value_in_combo(combo, value):
    model = combo.get_model()
    for i, item in enumerate(model):
        if value == item[1]:
            combo.set_active(i)
            return
    combo.set_active(0)


def get_selected_value_in_combo(combo):
    model = combo.get_model()
    return model.get_value(combo.get_active_iter(), 1)


def get_pixbuf_from_base64string(base64string):
    if base64string is None:
        return NOIMAGE
    raw_data = base64.b64decode(base64string.encode())
    try:
        pixbuf_loader = GdkPixbuf.PixbufLoader.new_with_mime_type("image/jpeg")
        pixbuf_loader.write(raw_data)
        pixbuf_loader.close()
        pixbuf = pixbuf_loader.get_pixbuf()
        return pixbuf
    except Exception as e:
        print(e)
    try:
        pixbuf_loader = GdkPixbuf.PixbufLoader.new_with_mime_type("image/png")
        pixbuf_loader.write(raw_data)
        pixbuf_loader.close()
        pixbuf = pixbuf_loader.get_pixbuf()
        return pixbuf
    except Exception as e:
        print(e)
    return NOIMAGE


def from_remote_image_to_base64(image_url):
    base64string = None
    try:
        r = requests.get(image_url, timeout=5, verify=False)
        if r.status_code == 200:
            writer_file = io.BytesIO()
            for chunk in r.iter_content(1024):
                writer_file.write(chunk)
            old_image = Image.open(writer_file)
            old_image.thumbnail((128, 128), Image.ANTIALIAS)
            new_image = io.BytesIO()
            old_image.save(new_image, "png")
            base64string = base64.b64encode(new_image.getvalue())
    except Exception as e:
        print(e)
    if base64string is not None:
        return base64string.decode()
    return None


def get_thumbnail_filename_for_audio(audio):
    thumbnail_filename = os.path.join(comun.THUMBNAILS_DIR,
                                      '{0}.png'.format(audio['hash']))
    if not os.path.exists(thumbnail_filename):
        pixbuf = get_pixbuf_from_base64string(audio['thumbnail_base64'])
        pixbuf.savev(thumbnail_filename, 'png', [], [])
    return thumbnail_filename


def create_thumbnail_for_audio(hash, thumbnail_base64):
    thumbnail_filename = os.path.join(comun.THUMBNAILS_DIR,
                                      '{0}.png'.format(hash))
    if not os.path.exists(thumbnail_filename):
        if thumbnail_base64 is not None:
            pixbuf = get_pixbuf_from_base64string(thumbnail_base64)
        else:
            pixbuf = NOIMAGE
        pixbuf = pixbuf.scale_simple(256, 256, GdkPixbuf.InterpType.BILINEAR)
        pixbuf.savev(thumbnail_filename, 'png', [], [])


def is_running(process):
    # From http://www.bloggerpolis.com/2011/05/\
    # how-to-check-if-a-process-is-running-using-python/
    # and http://richarddingwall.name/2009/06/18/\
    # windows-equivalents-of-ps-and-kill-commands/
    try:  # Linux/Unix
        s = subprocess.Popen(["ps", "axw"], stdout=subprocess.PIPE)
    except Exception as e:  # Windows
        print(e)
        s = subprocess.Popen(["tasklist", "/v"], stdout=subprocess.PIPE)
    for x in s.stdout:
        if re.search(process, x.decode()):
            return True
    return False


def get_desktop_environment():
    desktop_session = os.environ.get("DESKTOP_SESSION")
    # easier to match if we doesn't have  to deal with caracter cases
    if desktop_session is not None:
        desktop_session = desktop_session.lower()
        if desktop_session in ["gnome", "unity", "cinnamon", "mate",
                               "budgie-desktop", "xfce4", "lxde", "fluxbox",
                               "blackbox", "openbox", "icewm", "jwm",
                               "afterstep", "trinity", "kde"]:
            return desktop_session
        # ## Special cases ##
        # Canonical sets $DESKTOP_SESSION to Lubuntu rather than
        # LXDE if using LXDE.
        # There is no guarantee that they will not do the same with
        # the other desktop environments.
        elif "xfce" in desktop_session or\
                desktop_session.startswith("xubuntu"):
            return "xfce4"
        elif desktop_session.startswith("ubuntu"):
            return "unity"
        elif desktop_session.startswith("lubuntu"):
            return "lxde"
        elif desktop_session.startswith("kubuntu"):
            return "kde"
        elif desktop_session.startswith("razor"):  # e.g. razorkwin
            return "razor-qt"
        elif desktop_session.startswith("wmaker"):  # eg. wmaker-common
            return "windowmaker"
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        return "kde"
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        if "deprecated" not in os.environ.get(
                'GNOME_DESKTOP_SESSION_ID'):
            return "gnome2"
    # From http://ubuntuforums.org/showthread.php?t=652320
    elif is_running("xfce-mcs-manage"):
        return "xfce4"
    elif is_running("ksmserver"):
        return "kde"
    return "unknown"


if __name__ == '__main__':
    print(get_desktop_environment())
