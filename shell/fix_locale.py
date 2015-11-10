#!/usr/bin/env python
import sys
import re


def print_fixed_msgid_quoting(lines):
    inside_id = False
    inside_str = False

    lines = list(lines)

    for line_no, line in enumerate(lines):
        if not line.strip():
            inside_id = False
            inside_str = False

            print
            continue
        elif line.startswith('#'):
            inside_id = False
            inside_str = False

            print line.strip('\n')
            continue

        line = line.strip('\n')
        unquoted_line = line.replace('\\"', '')

        if unquoted_line.startswith('msgid'):
            for inner_line in lines[line_no:]:
                if inner_line.startswith('msgstr'):
                    break

                if re.search(r'%\(\w+\)s', inner_line):
                    print '#, python-format'
                    break

        if unquoted_line == 'msgid ""':
            inside_id = True
            inside_str = False

            print line
            continue
        elif unquoted_line == 'msgstr ""':
            inside_id = False
            inside_str = True

            print line
            continue
        elif line.startswith('msgid'):
            inside_id = True
            inside_str = False

            if not unquoted_line.endswith('"') or unquoted_line.count('"') == 1:
                line = line + '"'

            print line
            continue
        elif line.startswith('msgstr'):
            inside_id = False
            inside_str = True

            if not unquoted_line.endswith('"') or unquoted_line.count('"') == 1:
                line = line + '"'

            print line
            continue

        if not (inside_id or inside_str):
            raise Exception("Encountered unknown state while parsing: {}.".format(line))

        if not unquoted_line.startswith('"'):
            line = '"' + line

        if not unquoted_line.endswith('"'):
            line = line + '"'

        print line

if __name__ == '__main__':
    lines = sys.stdin
    print_fixed_msgid_quoting(lines)

