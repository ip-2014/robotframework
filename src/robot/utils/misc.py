#  Copyright 2008-2009 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import os
import sys
import tempfile
import urllib
import posixpath

from robot.errors import FrameworkError
from robottypes import is_str, is_list, unic, is_integer
from normalizing import normpath


def get_doc(obj):
    try:
        doc = obj.__doc__
    except AttributeError:
        doc = ''
    if not doc:
        return ''
    return '\n'.join([ line.strip() for line in doc.strip().splitlines() ])


def printable_name(string, code_style=False):
    """Generates and returns printable name from the given string.

    Examples:
    'simple'           -> 'Simple'
    'name with spaces' -> 'Name With Spaces'
    'more   spaces'    -> 'More Spaces'
    'Cases AND spaces' -> 'Cases AND Spaces'
    ''                 -> ''
    
    If 'code_style' is True:
    
    'mixedCAPSCamel'   -> 'Mixed CAPS Camel'
    'camelCaseName'    -> 'Camel Case Name'
    'under_score_name' -> 'Under Score Name'
    'under_and space'  -> 'Under And Space'
    'miXed_CAPS_nAMe'  -> 'MiXed CAPS NAMe'
    ''                 -> ''
    """
    if code_style:
        string = string.replace('_', ' ')
    parts = string.split()
    if len(parts) == 0:
        return ''
    elif len(parts) == 1 and code_style:
        parts = _splitCamelCaseString(parts[0])
    parts = [ part[0].upper() + part[1:] for part in parts if part != '' ]
    return ' '.join(parts)


def _splitCamelCaseString(string):
    parts = []
    current_part = []          
    string = ' ' + string + ' '  # extra spaces make going through string easier
    for i in range(1, len(string)-1):
        # on 1st/last round prev/next is ' ' and char is 1st/last real char
        prev, char, next = string[i-1:i+2]  
        if _isWordBoundary(prev, char, next):
            parts.append(''.join(current_part))
            current_part = [ char ]
        else:
            current_part.append(char)
    parts.append(''.join(current_part))   # append last part
    return parts


def _isWordBoundary(prev, char, next):
    if char.isupper():
        return (prev.islower() or next.islower()) and prev.isalnum()
    if char.isdigit():
        return prev.isalpha()
    return prev.isdigit()


def cygpath(path, options='-wa'):
    """Converts given path using Cygwin command 'cygpath'.
    
    Default options convert unixy path to an absolute Windows path.
    
    Returns path unmodified if not in Cygwin.
    """
    if 'cygwin' not in sys.platform:
        return path
    output = os.popen('cygpath %s "%s"' % (options, path))
    winpath = output.read().splitlines()[0]
    output.close()
    return winpath
 

def get_temp_dir(extrapath=None):
    tempdir = os.path.normpath(tempfile.gettempdir())
    if not os.path.isdir(tempdir):
        raise EnvironmentError("Temp directory '%s' does not exist" % tempdir)
    if extrapath is not None:
        tempdir = os.path.join(tempdir, extrapath)
        # make sure there's no file with the same name as tempdir
        if os.path.isfile(tempdir):
            i = 1
            while os.path.isfile('%s%d' % (tempdir, i)):
                i += 1
            tempdir = '%s%d' % (tempdir, i)
        if not os.path.exists(tempdir):
            os.mkdir(tempdir)
    return tempdir


def plural_or_not(list_or_int):
    if is_integer(list_or_int):
        return list_or_int != 1 and "s" or ""
    else:
        return len(list_or_int) != 1 and "s" or ""
    

def seq2str(sequence, quote="'", sep=', ', lastsep=' and ', quote_all=False):
    """Returns sequence in format 'item 1', 'item 2' and 'item 3' """
    def elem(string):
        if not is_str and not quote_all: 
            return unic(string)
        return quote + unic(string) + quote

    if not is_list(sequence):
        return elem(sequence)
    elif len(sequence) == 0:
        return ''
    elif len(sequence) == 1:
        return elem(sequence[0])
    ret = []
    for i in range(len(sequence)):
        if i + 2 == len(sequence):
            ret.append(elem(sequence[i]) + lastsep + elem(sequence[i+1]))
            break
        ret.append(elem(sequence[i]))
    return sep.join(ret)


def seq2str2(sequence):
    """Returns sequence in format [ item 1 | item 2 | ... ] """
    if not sequence:
        return '[ ]'
    return '[ %s ]' % ' | '.join([unic(item) for item in sequence])


def printable_name_from_path(path):
    """Create suite name from given path that points to file or directory.
    
    Examples:
        '/tmp/tests.py'         -> 'Tests'
        '/var/data/my_tests/    -> 'My Tests'
        'c:\path\my_tests.html' -> 'My Tests'
        'd:\MY TESTS.HTML'      -> 'MY TESTS'
        'e:\myTestCases.html    -> 'My Test Cases'
    """
    # Get name of the file/dir without leading path and possible extension
    name = os.path.splitext(os.path.basename(os.path.normpath(path)))[0]
    name = _remove_prefix(name)
    return printable_name(name, code_style=True)

def _remove_prefix(name):
    return name.split('__', 1)[-1]

def get_directory(path):
    """Returns the directory part of the given path.
    
    If path already is a directory returns it as is, otherwise returns the
    directory containing the file
    """
    if path.lower().startswith('http://'):
        return posixpath.dirname(path)
    path = normpath(path)
    if os.path.isdir(path):
        return path
    return os.path.dirname(path)
    

def get_link_path(target, base):
    """Returns a relative path to a target from a base. If base is an existing
    file, then its parent directory is considered. Otherwise, base is assumed
    to be a directory.

    Rationale: os.path.relpath is not available before Python 2.6
    """

    target = os.path.normcase(os.path.abspath(os.path.normpath(target)))
    base = os.path.normcase(os.path.abspath(os.path.normpath(base)))
    if os.path.isfile(base):
        base = os.path.dirname(base)
    if base == target:
        return urllib.pathname2url(os.path.basename(target))
    base_drive, base_path = os.path.splitdrive(base)
    # if in Windows and base and link on different drives
    if os.path.splitdrive(target)[0] != base_drive:
        return 'file:' + urllib.pathname2url(target)
    common_len = len(_common_path(base, target))
    if base_path == os.sep:
        return urllib.pathname2url(target[common_len:])
    if common_len == len(base_drive) + len(os.sep):
        common_len -= len(os.sep)
    dirs_up = os.sep.join([os.pardir] * base[common_len:].count(os.sep))
    return urllib.pathname2url(os.path.join(dirs_up, target[common_len + len(os.sep):]))


def _common_path(p1, p2):
    """Returns the longest path common to p1 and p2.

    Rationale: as os.path.commonprefix is character based, it doesn't consider
    path separators as such, so it may return invalid paths:
    commonprefix(('/foo/bar/', '/foo/baz.txt')) -> '/foo/ba' (instead of /foo)
    """
    while p1 and p2:
        if p1 == p2:
            return p1
        if len(p1) > len(p2):
            p1 = os.path.dirname(p1)
        else:
            p2 = os.path.dirname(p2)
    return ""

def calc_percents(passed, failed):
    total = passed + failed
    if total == 0:
        return 0.0, 0.0
    pass_percent = 100.0 * passed / total
    fail_percent = 100.0 * failed / total
    if 0 < pass_percent < 0.1:
        return 0.1, 99.9
    if 0 < fail_percent < 0.1:
        return 99.9, 0.1
    pass_percent = round(pass_percent, 1)
    fail_percent = round(fail_percent, 1)
    return pass_percent, fail_percent
    

def percents_to_widths(num1, num2):
    if num1 + num2 == 0:
        return 0.00, 0.00
    # Make small percentages better visible 
    if 0 < num1 < 1:
        num1, num2= 1.0, 99.0
    elif 0 < num2 < 1:
        num1, num2= 99.0, 1.0
    # Handle situation where both are rounded up
    while num1 + num2 > 100:
        num1, num2 = _subtract_from_larger(num1, num2, 0.1)
    # Make sure both pass and fail bar fit into 100% also in IE
    num1, num2 = _subtract_from_larger(num1, num2, 0.01)
    return num1, num2

def _subtract_from_larger(num1, num2, subtr):
    if num1 > num2:
        num1 -= subtr
    else:
        num2 -= subtr
    return num1, num2


def get_not_none(*args):
    for arg in args:
        if arg is not None:
            return arg
    raise FrameworkError('No non-None item found')
