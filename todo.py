#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Todo CLI

Usage:
  todo (add | a) [-i]
  todo (edit | e) <task_id>
  todo (done | d) <task_id>
  todo (print | p) [-v]
  todo -h | --help
  todo -V | --version

Subcommands:
  add                 Add task
  print               Print tasks

Options:
  -h, --help          Help information
  -V, --version       Show version
  -i                  Add task in interactive mode
  task_id             Id of task
"""
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
import re
import io
import errno
import random
import string
import datetime
import unicodedata
import yaml
from docopt import docopt

__version__ = '0.0.1'
date_fmt = '%Y-%m-%d %H:%M'
settings = None


class ParseError(Exception):
    pass


def mkdir_p(path):
    """Make parent directories as needed, like `mkdir -p`"""
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        # if dir exists, not error
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def generate_id(length=6, chars=None):
    if not chars:
        chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def add_task(use_interactive=False):
    task_id = generate_id()

    now = datetime.datetime.now().strftime(date_fmt)

    title = project = expire = ''
    priority = 1
    if use_interactive:
        title = raw_input('title: ').decode('utf-8')
        project = raw_input('project: ').decode('utf-8')
        priority = raw_input('priority (1,2,3): ') or 1
        expire = raw_input('expire [{0}]: '.format(date_fmt))

    meta = '\n'.join([
        '---',
        'title: {0}'.format(title),
        'project: {0}'.format(project),
        'priority: {0}'.format(priority),
        'create: {0}'.format(now),
        'expire: {0}'.format(expire),
        'id: {0}'.format(task_id),
        '---',
    ]) + '\n\n\n'

    todo_dir = os.path.join(settings['task_dir'], 'todo')
    if not os.path.exists(todo_dir):
        mkdir_p(todo_dir)

    task_file = os.path.join(todo_dir, '{0}.txt'.format(task_id))
    if os.path.exists(task_file):
        print('error: task file {0} exists'.format(task_file))
    else:
        with io.open(task_file, "wt", encoding="utf-8") as fd:
            fd.write(meta)
        print('create task: {0}'.format(task_file))
        if use_interactive and os.environ['EDITOR']:
            os.system('{0} {1}'.format(os.environ['EDITOR'], task_file))


def find_task_by_id(task_id):
    """Return absolute path of task file, or None if not exists"""
    filename = '{0}.txt'.format(task_id)
    task_file = None
    for task_list in ('todo', 'today'):
        task_dir = os.path.join(settings['task_dir'], task_list)
        for root, dirs, files in os.walk(task_dir):
            files = [f for f in files if not f.startswith(".")]
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            if filename in files:
                task_file = os.path.join(root, filename)
    return task_file


def edit_task(task_id):
    task_file = find_task_by_id(task_id)
    if not task_file:
        raise Exception('task(id: `{0}\') not exists'.format(task_id))
    if os.environ['EDITOR']:
        print('edit task: {0}'.format(task_file))
        os.system('{0} {1}'.format(os.environ['EDITOR'], task_file))
    else:
        print('environ $EDITOR not set, can\'t edit task')


def done_task(task_id):
    filename = '{0}.txt'.format(task_id)
    task_file = find_task_by_id(task_id)
    if not task_file:
        raise Exception('task(id: `{0}\') not exists'.format(task_id))
    done_dir = os.path.join(settings['task_dir'], 'done')
    if not os.path.exists(done_dir):
        mkdir_p(done_dir)
    new_task_file = os.path.join(done_dir, filename)
    os.rename(task_file, new_task_file)
    print('done task: {0}'.format(new_task_file))


def parse_task(filename):
    """Parse todo file"""
    regex = re.compile('(?sm)^---(?P<meta>.*?)^---(?P<description>.*)')
    task = {}

    with open(filename, 'r') as fd:
        match_obj = re.match(regex, fd.read())
        if match_obj:
            meta = yaml.load(match_obj.group('meta'))
            # pure digit in yaml is int
            for f in ('id', 'title', 'project'):
                if meta[f] is None:
                    meta[f] = u''
                if isinstance(meta[f], int):
                    meta[f] = unicode(meta[f])
                elif isinstance(meta[f], str):
                    meta[f] = meta[f].decode('utf-8')
            task.update(meta)
            task.update({'description': match_obj.group('description')})
        else:
            raise ParseError("can't parse {0}".format(filename))

    return task


def cmp_task(task_a, task_b):
    """Sorting logic: list (today > todo) > expire > priority"""
    if task_a['list'] != task_b['list']:
        if task_a['list'] == 'today':
            return 1
        else:
            return -1
    else:
        if task_a.get('expire') != task_b.get('expire'):
            task_a_expire = task_a.get('expire') or '2100-01-01 00:00'
            task_b_expire = task_b.get('expire') or '2100-01-01 00:00'
            delta = \
                datetime.datetime.strptime(task_a_expire, date_fmt) - \
                datetime.datetime.strptime(task_b_expire, date_fmt)
            return - int(delta.total_seconds())
        else:
            # note do not use > to compare
            return task_a['priority'] - task_b['priority']


class Palette(object):
    """color palette for tasks"""
    COLOR_CODES = {
        "reset": "\033[0m",
        "bggrey1": "\033[48;5;241m",
        "bggrey2": "\033[48;5;235m",
        "bggrey3": "\033[48;5;236m",
    }

    def _color(self, color, s):
        return Palette.COLOR_CODES[color] + s + Palette.COLOR_CODES["reset"]

    def color_header(self, s):
        return self._color('bggrey1', s)

    def color_odd(self, s):
        return self._color('bggrey2', s)
        pass

    def color_even(self, s):
        return self._color('bggrey3', s)
        pass


def wide_chars(s):
    """return the extra width for wide characters
    ref: http://stackoverflow.com/a/23320535/1276501"""
    return sum(unicodedata.east_asian_width(x) == 'W' for x in s)


def pretty_print_task_list(tasks, verbose):
    title_max_width = max([len('title')] +
                          [len(t['title']) + wide_chars(t['title'])
                           for t in tasks])
    project_max_width = max([len('project')] +
                            [len(t['project']) + wide_chars(t['project'])
                             for t in tasks])

    # key: field , value: [specifier, width]
    fmt_spec = [
        ['', '^', 3],  # is_today
        ['id', '<', 7],
        ['title', '<', title_max_width + 1],
        ['priority', '<', 9],
        ['project', '<', project_max_width + 1],
    ]
    if verbose:
        fmt_spec.extend([
            ['create', '<', 17],
            ['expire', '<', 17],
        ])

    # print header
    fmt_str = ''
    for i, (v_f, v_s, v_w) in enumerate(fmt_spec):
        fmt_str += '{%s:%s%s}' % (i, v_s, v_w)
    headers = [x[0] for x in fmt_spec]

    palette = Palette()
    print(palette.color_header(fmt_str.format(*headers)))

    for t_i, task in enumerate(tasks):
        fmt_str = ''
        for f_i, (v_f, v_s, v_w) in enumerate(fmt_spec):
            if v_f == 'title':
                fmt_str += '{%s:%s%s}' % (f_i, v_s,
                                          v_w - wide_chars(task[v_f]))
            else:
                fmt_str += '{%s:%s%s}' % (f_i, v_s, v_w)

        today_flag = '*' if task['list'] == 'today' else ''
        values = [today_flag] + list(task[h] for h in headers[1:])

        if t_i % 2:
            print(palette.color_odd(fmt_str.format(*values)))
        else:
            print(palette.color_even(fmt_str.format(*values)))


def print_task(verbose=False):
    tasks = []
    for task_list in ('todo', 'today'):
        task_dir = os.path.join(settings['task_dir'], task_list)
        for root, dirs, files in os.walk(task_dir):
            files = [f for f in files if not f.startswith(".")]
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for task_file in files:
                try:
                    task = parse_task(os.path.join(root, task_file))
                    task.update({'list': task_list})
                    tasks.append(task)
                except ParseError as e:
                    print('error: {0}'.format(unicode(e)))

    tasks = sorted(tasks, cmp_task, reverse=True)
    pretty_print_task_list(tasks, verbose)


def unicode_docopt(args):
    for k in args:
        if isinstance(args[k], basestring) and \
           not isinstance(args[k], unicode):
            args[k] = args[k].decode('utf-8')


def main(args=None):
    global settings

    if not args:
        args = docopt(__doc__, version='Todo-CLI {0}'.format(__version__))
    unicode_docopt(args)

    # load default settings
    settings_fn = os.path.expanduser('~/.todo-cli')
    if not os.path.exists(settings_fn):
        print('error: settings file {0} not exists'.format(settings_fn))
        sys.exit(1)
    with open(settings_fn, 'r') as fd:
        settings = yaml.load(fd.read())

    if args['add'] or args['a']:
        add_task(use_interactive=args['-i'])
    elif args['edit'] or args['e']:
        edit_task(task_id=args['<task_id>'])
    elif args['done'] or args['d']:
        done_task(task_id=args['<task_id>'])
    elif args['print'] or args['p']:
        print_task(verbose=args['-v'])


if __name__ == '__main__':
    main()
