# Licensed under a 3-clause BSD style license - see LICENSE.rst

# This sub-module is destined for common non-package specific utility
# functions that will ultimately be merged into `astropy.utils`

# As far as possible, utils contains classes of generic use, such as
# PosInt for positive integer input. See e.g. 'hcam' for more instrument
# dependent components.

from __future__ import print_function, unicode_literals, absolute_import, division
import six
if not six.PY3:
    import tkFont as font
else:
    from tkinter import font


def get_root(w):
    """
    Simple method to access root for a widget
    """
    next_level = w
    while next_level.master:
        next_level = next_level.master
    return next_level


def addStyle(w):
    """
    Styles the GUI: global fonts and colours.

    Parameters
    ----------
    w : tkinter.tk
        widget element to style
    """
    # access global container in root widget
    root = get_root(w)
    g = root.globals

    # Default font
    fam_name_list = [fam for fam in font.families() if 'times' in fam.lower()]
    if len(fam_name_list):
        font_dict = {'family': fam_name_list[0],
                     'weight': 'bold',
                     'size': 10}
        g.DEFAULT_FONT = font.Font(w, **font_dict)
    else:
        print('falling back to defaults')
        g.DEFAULT_FONT = font.nametofont("TkDefaultFont")
        g.DEFAULT_FONT.configure(size=10, weight='bold')
    w.option_add('*Font', g.DEFAULT_FONT)

    # Menu font
    if len(fam_name_list):
        font_dict = {'family': fam_name_list[0],
                     'weight': 'normal',
                     'size': 10}
        g.MENU_FONT = font.Font(w, **font_dict)
    else:
        g.MENU_FONT = font.nametofont("TkMenuFont")
        g.MENU_FONT.configure(size=10)
    w.option_add('*Menu.Font', g.MENU_FONT)

    # Entry font
    if len(fam_name_list):
        font_dict = {'family': fam_name_list[0],
                     'weight': 'normal',
                     'size': 10}
        g.ENTRY_FONT = font.Font(w, **font_dict)
    else:
        g.ENTRY_FONT = font.nametofont("TkTextFont")
        g.ENTRY_FONT.configure(size=10)
    w.option_add('*Entry.Font', g.ENTRY_FONT)

    # position and size
    # root.geometry("320x240+325+200")

    # Default colours. Note there is a difference between
    # specifying 'background' with a capital B or lowercase b
    w.option_add('*background', g.COL['main'])
    w.option_add('*HighlightBackground', g.COL['main'])
    w.config(background=g.COL['main'])
