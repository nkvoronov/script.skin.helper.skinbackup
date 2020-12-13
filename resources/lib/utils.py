#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Various helper methods'''

import os, sys
import xbmc
import xbmcvfs
import xbmcgui
import urllib.parse
from traceback import format_exc
import unicodedata

ADDON_ID = "script.skin.helper.skinbackup"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
ADDON_DATA = u'special://profile/addon_data/%s/' % ADDON_ID


def log_msg(msg, loglevel=xbmc.LOGDEBUG):
    '''log to kodi logfile'''
    xbmc.log("Skin Helper Backup --> %s" % msg, level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log exception details'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGNOTICE)
    log_msg("ERROR in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)
    dialog = xbmcgui.Dialog()
    dialog.notification(
        "Skin Helper Backup",
        "Error while executing, please check your kodi logfile.",
        xbmcgui.NOTIFICATION_ERROR)
    del dialog


def kodi_json(jsonmethod, params=None):
    '''get info from the kodi json api'''
    import json
    kodi_json = {}
    kodi_json["jsonrpc"] = "2.0"
    kodi_json["method"] = jsonmethod
    if not params:
        params = {}
    kodi_json["params"] = params
    kodi_json["id"] = 1
    json_response = xbmc.executeJSONRPC(json.dumps(kodi_json))
    json_object = json.loads(json_response)
    result = None
    if 'result' in json_object:
        # look for correct returntype
        if isinstance(json_object['result'], dict):
            for key, value in json_object['result'].items():
                if not key == "limits":
                    result = value
                    break
        else:
            return json_object['result']
    return result


def recursive_delete_dir(fullpath):
    '''helper to recursively delete a directory'''
    success = True
    dirs, files = xbmcvfs.listdir(fullpath)
    for file in files:
        success = xbmcvfs.delete(os.path.join(fullpath, file))
    for directory in dirs:
        success = recursive_delete_dir(os.path.join(fullpath, directory))
    success = xbmcvfs.rmdir(fullpath)
    return success


def copy_file(source, destination, do_wait=False):
    '''copy a file on the filesystem, wait for the action to be completed'''
    if xbmcvfs.exists(destination):
        delete_file(destination)
    xbmcvfs.copy(source, destination)
    if do_wait:
        count = 20
        while count:
            xbmc.sleep(500)  # this first sleep is intentional
            if xbmcvfs.exists(destination):
                break
            count -= 1


def delete_file(filepath, do_wait=False):
    '''delete a file on the filesystem, wait for the action to be completed'''
    xbmcvfs.delete(filepath)
    if do_wait:
        count = 20
        while count:
            xbmc.sleep(500)  # this first sleep is intentional
            if not xbmcvfs.exists(filepath):
                break
            count -= 1


def get_clean_image(image):
    '''helper to strip all kodi tags/formatting of an image path/url'''
    if image and "image://" in image:
        image = image.replace("image://", "")
        image = urllib.parse.unquote(image)
        if image.endswith("/"):
            image = image[:-1]
    if "music@" in image:
        # filter out embedded covers
        image = ""
    return image


def normalize_string(text):
    '''normalize string, strip all special chars'''
    text = text.replace(":", "")
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = text.replace("<", "")
    text = text.replace(">", "")
    text = text.replace("*", "")
    text = text.replace("?", "")
    text = text.replace('|', "")
    text = text.replace('(', "")
    text = text.replace(')', "")
    text = text.replace("\"", "")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', text)
    return text


def add_tozip(src, zip_file, abs_src):
    '''helper method'''
    dirs, files = xbmcvfs.listdir(src)
    for filename in files:
        log_msg("zipping %s" % filename)
        filepath = xbmcvfs.translatePath(os.path.join(src, filename))
        absname = os.path.abspath(filepath)
        arcname = absname[len(abs_src) + 1:]
        try:
            # newer python can use unicode for the files in the zip
            zip_file.write(absname, arcname)
        except Exception:
            # older python version uses utf-8 for filenames in the zip
            zip_file.write(absname, arcname)
    for directory in dirs:
        add_tozip(os.path.join(src, directory), zip_file, abs_src)
    return zip_file


def zip_tofile(src, dst):
    '''method to create a zip file from all files/dirs in a path'''
    import zipfile
    zip_file = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(xbmcvfs.translatePath(src))
    zip_file = add_tozip(src, zip_file, abs_src)
    zip_file.close()


def unzip_fromfile(zip_path, dest_path):
    '''method to unzip a zipfile to a destination path'''
    import shutil
    import zipfile
    zip_path = xbmcvfs.translatePath(zip_path)
    dest_path = xbmcvfs.translatePath(dest_path)
    log_msg("START UNZIP of file %s  to path %s " % (zip_path, dest_path))
    zip_file = zipfile.ZipFile(zip_path, 'r')
    for fileinfo in zip_file.infolist():
        filename = fileinfo.filename
        log_msg("unzipping: " + filename)
        splitter = None
        if "\\" in filename:
            xbmcvfs.mkdirs(os.path.join(dest_path, filename.rsplit("\\", 1)[0]))
            splitter = "\\"
        elif "/" in filename:
            xbmcvfs.mkdirs(os.path.join(dest_path, filename.rsplit("/", 1)[0]))
            splitter = "/"
        filename = os.path.join(dest_path, filename)
        if not (splitter and filename.endswith(splitter)):
            try:
                # newer python uses unicode
                outputfile = open(filename, "wb")
            except Exception:
                # older python uses utf-8
                outputfile = open(filename, "wb")
            # use shutil to support non-ascii formatted files in the zip
            shutil.copyfileobj(zip_file.open(fileinfo.filename), outputfile)
            outputfile.close()
    zip_file.close()
    log_msg("UNZIP DONE of file %s  to path %s " % (zip_path, dest_path))


def get_skin_name():
    ''' get the skin name filtering out any beta prefixes and such.'''
    skin_name = xbmc.getSkinDir()
    skin_name = skin_name.replace("skin.", "")
    skin_name = skin_name.replace(".kryptonbeta", "")
    skin_name = skin_name.replace(".jarvisbeta", "")
    skin_name = skin_name.replace(".leiabeta", "")
    return skin_name
