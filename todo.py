#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Todo CLI

Usage:
  todo (add | a) [-i]
  todo -h | --help
  todo -V | --version

Subcommands:
  add                 Add task

Options:
  -h, --help          Help information
  -V, --version       Show version
  -i                  Add task in interactive mode
"""
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
import io
import errno
import random
import string
import datetime
import yaml
from docopt import docopt

__version__ = '0.0.1'
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


def add_task(interactive=False):
    task_id = generate_id()

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    title = project = expire = ''
    priority = 1
    if interactive:
        title = raw_input('title: ').decode('utf-8')
        project = raw_input('project: ').decode('utf-8')
        priority = raw_input('priority (1,2,3): ')
        expire = raw_input('expire [%Y-%m-%d %H:%M]: ')

    meta = '\n'.join([
        '---',
        'title: {0}'.format(title),
        'project: {0}'.format(project),
        'priority: {0}'.format(priority),
        'create: {0}'.format(now),
        'expire: {0}'.format(expire),
        'id: {0}'.format(task_id),
        '---',
    ]) + '\n\n'

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
        add_task(args['-i'])


if __name__ == '__main__':
    main()
