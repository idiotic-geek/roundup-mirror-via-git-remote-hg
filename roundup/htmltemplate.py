#
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# IN NO EVENT SHALL BIZAR SOFTWARE PTY LTD BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# BIZAR SOFTWARE PTY LTD SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS"
# BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
# 
# $Id: htmltemplate.py,v 1.40 2001-11-03 01:56:51 richard Exp $

import os, re, StringIO, urllib, cgi, errno

import hyperdb, date, password

# This imports the StructureText functionality for the do_stext function
# get it from http://dev.zope.org/Members/jim/StructuredTextWiki/NGReleases
try:
    from StructuredText.StructuredText import HTML as StructuredText
except ImportError:
    StructuredText = None

class TemplateFunctions:
    def __init__(self):
        self.form = None
        self.nodeid = None
        self.filterspec = None
        self.globals = {}
        for key in TemplateFunctions.__dict__.keys():
            if key[:3] == 'do_':
                self.globals[key[3:]] = getattr(self, key)

    def do_plain(self, property, escape=0):
        ''' display a String property directly;

            display a Date property in a specified time zone with an option to
            omit the time from the date stamp;

            for a Link or Multilink property, display the key strings of the
            linked nodes (or the ids if the linked class has no key property)
        '''
        if not self.nodeid and self.form is None:
            return '[Field: not called from item]'
        propclass = self.properties[property]
        if self.nodeid:
            value = self.cl.get(self.nodeid, property)
        else:
            # TODO: pull the value from the form
            if isinstance(propclass, hyperdb.Multilink): value = []
            else: value = ''
        if isinstance(propclass, hyperdb.String):
            if value is None: value = ''
            else: value = str(value)
        elif isinstance(propclass, hyperdb.Password):
            if value is None: value = ''
            else: value = '*encrypted*'
        elif isinstance(propclass, hyperdb.Date):
            value = str(value)
        elif isinstance(propclass, hyperdb.Interval):
            value = str(value)
        elif isinstance(propclass, hyperdb.Link):
            linkcl = self.db.classes[propclass.classname]
            k = linkcl.labelprop()
            if value: value = str(linkcl.get(value, k))
            else: value = '[unselected]'
        elif isinstance(propclass, hyperdb.Multilink):
            linkcl = self.db.classes[propclass.classname]
            k = linkcl.labelprop()
            value = ', '.join([linkcl.get(i, k) for i in value])
        else:
            s = 'Plain: bad propclass "%s"'%propclass
        if escape:
            value = cgi.escape(value)
        return value

    def do_stext(self, property, escape=0):
        '''Render as structured text using the StructuredText module
           (see above for details)
        '''
        s = self.do_plain(property, escape=escape)
        if not StructuredText:
            return s
        return StructuredText(s,level=1,header=0)

    def do_field(self, property, size=None, height=None, showid=0):
        ''' display a property like the plain displayer, but in a text field
            to be edited
        '''
        if not self.nodeid and self.form is None and self.filterspec is None:
            return '[Field: not called from item]'
        propclass = self.properties[property]
        if self.nodeid:
            value = self.cl.get(self.nodeid, property, None)
            # TODO: remove this from the code ... it's only here for
            # handling schema changes, and they should be handled outside
            # of this code...
            if isinstance(propclass, hyperdb.Multilink) and value is None:
                value = []
        elif self.filterspec is not None:
            if isinstance(propclass, hyperdb.Multilink):
                value = self.filterspec.get(property, [])
            else:
                value = self.filterspec.get(property, '')
        else:
            # TODO: pull the value from the form
            if isinstance(propclass, hyperdb.Multilink): value = []
            else: value = ''
        if (isinstance(propclass, hyperdb.String) or
                isinstance(propclass, hyperdb.Date) or
                isinstance(propclass, hyperdb.Interval)):
            size = size or 30
            if value is None:
                value = ''
            else:
                value = cgi.escape(value)
                value = '&quot;'.join(value.split('"'))
            s = '<input name="%s" value="%s" size="%s">'%(property, value, size)
        elif isinstance(propclass, hyperdb.Password):
            size = size or 30
            s = '<input type="password" name="%s" size="%s">'%(property, size)
        elif isinstance(propclass, hyperdb.Link):
            linkcl = self.db.classes[propclass.classname]
            l = ['<select name="%s">'%property]
            k = linkcl.labelprop()
            if value is None:
                s = 'selected '
            else:
                s = ''
            l.append('<option %svalue="-1">- no selection -</option>'%s)
            for optionid in linkcl.list():
                option = linkcl.get(optionid, k)
                s = ''
                if optionid == value:
                    s = 'selected '
                if showid:
                    lab = '%s%s: %s'%(propclass.classname, optionid, option)
                else:
                    lab = option
                if size is not None and len(lab) > size:
                    lab = lab[:size-3] + '...'
                l.append('<option %svalue="%s">%s</option>'%(s, optionid, lab))
            l.append('</select>')
            s = '\n'.join(l)
        elif isinstance(propclass, hyperdb.Multilink):
            linkcl = self.db.classes[propclass.classname]
            list = linkcl.list()
            height = height or min(len(list), 7)
            l = ['<select multiple name="%s" size="%s">'%(property, height)]
            k = linkcl.labelprop()
            for optionid in list:
                option = linkcl.get(optionid, k)
                s = ''
                if optionid in value:
                    s = 'selected '
                if showid:
                    lab = '%s%s: %s'%(propclass.classname, optionid, option)
                else:
                    lab = option
                if size is not None and len(lab) > size:
                    lab = lab[:size-3] + '...'
                l.append('<option %svalue="%s">%s</option>'%(s, optionid, lab))
            l.append('</select>')
            s = '\n'.join(l)
        else:
            s = 'Plain: bad propclass "%s"'%propclass
        return s

    def do_menu(self, property, size=None, height=None, showid=0):
        ''' for a Link property, display a menu of the available choices
        '''
        propclass = self.properties[property]
        if self.nodeid:
            value = self.cl.get(self.nodeid, property)
        else:
            # TODO: pull the value from the form
            if isinstance(propclass, hyperdb.Multilink): value = []
            else: value = None
        if isinstance(propclass, hyperdb.Link):
            linkcl = self.db.classes[propclass.classname]
            l = ['<select name="%s">'%property]
            k = linkcl.labelprop()
            s = ''
            if value is None:
                s = 'selected '
            l.append('<option %svalue="-1">- no selection -</option>'%s)
            for optionid in linkcl.list():
                option = linkcl.get(optionid, k)
                s = ''
                if optionid == value:
                    s = 'selected '
                l.append('<option %svalue="%s">%s</option>'%(s, optionid, option))
            l.append('</select>')
            return '\n'.join(l)
        if isinstance(propclass, hyperdb.Multilink):
            linkcl = self.db.classes[propclass.classname]
            list = linkcl.list()
            height = height or min(len(list), 7)
            l = ['<select multiple name="%s" size="%s">'%(property, height)]
            k = linkcl.labelprop()
            for optionid in list:
                option = linkcl.get(optionid, k)
                s = ''
                if optionid in value:
                    s = 'selected '
                if showid:
                    lab = '%s%s: %s'%(propclass.classname, optionid, option)
                else:
                    lab = option
                if size is not None and len(lab) > size:
                    lab = lab[:size-3] + '...'
                l.append('<option %svalue="%s">%s</option>'%(s, optionid, option))
            l.append('</select>')
            return '\n'.join(l)
        return '[Menu: not a link]'

    #XXX deviates from spec
    def do_link(self, property=None, is_download=0):
        '''For a Link or Multilink property, display the names of the linked
           nodes, hyperlinked to the item views on those nodes.
           For other properties, link to this node with the property as the
           text.

           If is_download is true, append the property value to the generated
           URL so that the link may be used as a download link and the
           downloaded file name is correct.
        '''
        if not self.nodeid and self.form is None:
            return '[Link: not called from item]'
        propclass = self.properties[property]
        if self.nodeid:
            value = self.cl.get(self.nodeid, property)
        else:
            if isinstance(propclass, hyperdb.Multilink): value = []
            elif isinstance(propclass, hyperdb.Link): value = None
            else: value = ''
        if isinstance(propclass, hyperdb.Link):
            linkname = propclass.classname
            if value is None: return '[no %s]'%property.capitalize()
            linkcl = self.db.classes[linkname]
            k = linkcl.labelprop()
            linkvalue = linkcl.get(value, k)
            if is_download:
                return '<a href="%s%s/%s">%s</a>'%(linkname, value,
                    linkvalue, linkvalue)
            else:
                return '<a href="%s%s">%s</a>'%(linkname, value, linkvalue)
        if isinstance(propclass, hyperdb.Multilink):
            linkname = propclass.classname
            linkcl = self.db.classes[linkname]
            k = linkcl.labelprop()
            if not value : return '[no %s]'%property.capitalize()
            l = []
            for value in value:
                linkvalue = linkcl.get(value, k)
                if is_download:
                    l.append('<a href="%s%s/%s">%s</a>'%(linkname, value,
                        linkvalue, linkvalue))
                else:
                    l.append('<a href="%s%s">%s</a>'%(linkname, value,
                        linkvalue))
            return ', '.join(l)
        if isinstance(propclass, hyperdb.String):
            if value == '': value = '[no %s]'%property.capitalize()
        if is_download:
            return '<a href="%s%s/%s">%s</a>'%(self.classname, self.nodeid,
                value, value)
        else:
            return '<a href="%s%s">%s</a>'%(self.classname, self.nodeid, value)

    def do_count(self, property, **args):
        ''' for a Multilink property, display a count of the number of links in
            the list
        '''
        if not self.nodeid:
            return '[Count: not called from item]'
        propclass = self.properties[property]
        value = self.cl.get(self.nodeid, property)
        if isinstance(propclass, hyperdb.Multilink):
            return str(len(value))
        return '[Count: not a Multilink]'

    # XXX pretty is definitely new ;)
    def do_reldate(self, property, pretty=0):
        ''' display a Date property in terms of an interval relative to the
            current date (e.g. "+ 3w", "- 2d").

            with the 'pretty' flag, make it pretty
        '''
        if not self.nodeid and self.form is None:
            return '[Reldate: not called from item]'
        propclass = self.properties[property]
        if isinstance(not propclass, hyperdb.Date):
            return '[Reldate: not a Date]'
        if self.nodeid:
            value = self.cl.get(self.nodeid, property)
        else:
            value = date.Date('.')
        interval = value - date.Date('.')
        if pretty:
            if not self.nodeid:
                return 'now'
            pretty = interval.pretty()
            if pretty is None:
                pretty = value.pretty()
            return pretty
        return str(interval)

    def do_download(self, property, **args):
        ''' show a Link("file") or Multilink("file") property using links that
            allow you to download files
        '''
        if not self.nodeid:
            return '[Download: not called from item]'
        propclass = self.properties[property]
        value = self.cl.get(self.nodeid, property)
        if isinstance(propclass, hyperdb.Link):
            linkcl = self.db.classes[propclass.classname]
            linkvalue = linkcl.get(value, k)
            return '<a href="%s%s">%s</a>'%(linkcl, value, linkvalue)
        if isinstance(propclass, hyperdb.Multilink):
            linkcl = self.db.classes[propclass.classname]
            l = []
            for value in value:
                linkvalue = linkcl.get(value, k)
                l.append('<a href="%s%s">%s</a>'%(linkcl, value, linkvalue))
            return ', '.join(l)
        return '[Download: not a link]'


    def do_checklist(self, property, **args):
        ''' for a Link or Multilink property, display checkboxes for the
            available choices to permit filtering
        '''
        propclass = self.properties[property]
        if (not isinstance(propclass, hyperdb.Link) and not
                isinstance(propclass, hyperdb.Multilink)):
            return '[Checklist: not a link]'

        # get our current checkbox state
        if self.nodeid:
            # get the info from the node - make sure it's a list
            if isinstance(propclass, hyperdb.Link):
                value = [self.cl.get(self.nodeid, property)]
            else:
                value = self.cl.get(self.nodeid, property)
        elif self.filterspec is not None:
            # get the state from the filter specification (always a list)
            value = self.filterspec.get(property, [])
        else:
            # it's a new node, so there's no state
            value = []

        # so we can map to the linked node's "lable" property
        linkcl = self.db.classes[propclass.classname]
        l = []
        k = linkcl.labelprop()
        for optionid in linkcl.list():
            option = linkcl.get(optionid, k)
            if optionid in value or option in value:
                checked = 'checked'
            else:
                checked = ''
            l.append('%s:<input type="checkbox" %s name="%s" value="%s">'%(
                option, checked, property, option))

        # for Links, allow the "unselected" option too
        if isinstance(propclass, hyperdb.Link):
            if value is None or '-1' in value:
                checked = 'checked'
            else:
                checked = ''
            l.append('[unselected]:<input type="checkbox" %s name="%s" '
                'value="-1">'%(checked, property))
        return '\n'.join(l)

    def do_note(self, rows=5, cols=80):
        ''' display a "note" field, which is a text area for entering a note to
            go along with a change. 
        '''
        # TODO: pull the value from the form
        return '<textarea name="__note" wrap="hard" rows=%s cols=%s>'\
            '</textarea>'%(rows, cols)

    # XXX new function
    def do_list(self, property, reverse=0):
        ''' list the items specified by property using the standard index for
            the class
        '''
        propcl = self.properties[property]
        if not isinstance(propcl, hyperdb.Multilink):
            return '[List: not a Multilink]'
        value = self.cl.get(self.nodeid, property)
        if reverse:
            value.reverse()

        # render the sub-index into a string
        fp = StringIO.StringIO()
        try:
            write_save = self.client.write
            self.client.write = fp.write
            index = IndexTemplate(self.client, self.templates, propcl.classname)
            index.render(nodeids=value, show_display_form=0)
        finally:
            self.client.write = write_save

        return fp.getvalue()

    # XXX new function
    def do_history(self, **args):
        ''' list the history of the item
        '''
        if self.nodeid is None:
            return "[History: node doesn't exist]"

        l = ['<table width=100% border=0 cellspacing=0 cellpadding=2>',
            '<tr class="list-header">',
            '<td><span class="list-item"><strong>Date</strong></span></td>',
            '<td><span class="list-item"><strong>User</strong></span></td>',
            '<td><span class="list-item"><strong>Action</strong></span></td>',
            '<td><span class="list-item"><strong>Args</strong></span></td>']

        for id, date, user, action, args in self.cl.history(self.nodeid):
            l.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(
               date, user, action, args))
        l.append('</table>')
        return '\n'.join(l)

    # XXX new function
    def do_submit(self):
        ''' add a submit button for the item
        '''
        if self.nodeid:
            return '<input type="submit" value="Submit Changes">'
        elif self.form is not None:
            return '<input type="submit" value="Submit New Entry">'
        else:
            return '[Submit: not called from item]'


#
#   INDEX TEMPLATES
#
class IndexTemplateReplace:
    def __init__(self, globals, locals, props):
        self.globals = globals
        self.locals = locals
        self.props = props

    replace=re.compile(
        r'((<property\s+name="(?P<name>[^>]+)">(?P<text>.+?)</property>)|'
        r'(?P<display><display\s+call="(?P<command>[^"]+)">))', re.I|re.S)
    def go(self, text):
        return self.replace.sub(self, text)

    def __call__(self, m, filter=None, columns=None, sort=None, group=None):
        if m.group('name'):
            if m.group('name') in self.props:
                text = m.group('text')
                replace = IndexTemplateReplace(self.globals, {}, self.props)
                return replace.go(m.group('text'))
            else:
                return ''
        if m.group('display'):
            command = m.group('command')
            return eval(command, self.globals, self.locals)
        print '*** unhandled match', m.groupdict()

class IndexTemplate(TemplateFunctions):
    def __init__(self, client, templates, classname):
        self.client = client
        self.templates = templates
        self.classname = classname

        # derived
        self.db = self.client.db
        self.cl = self.db.classes[self.classname]
        self.properties = self.cl.getprops()

        TemplateFunctions.__init__(self)

    col_re=re.compile(r'<property\s+name="([^>]+)">')
    def render(self, filterspec={}, filter=[], columns=[], sort=[], group=[],
            show_display_form=1, nodeids=None, show_customization=1):
        self.filterspec = filterspec

        w = self.client.write

        # get the filter template
        try:
            filter_template = open(os.path.join(self.templates,
                self.classname+'.filter')).read()
            all_filters = self.col_re.findall(filter_template)
        except IOError, error:
            if error.errno not in (errno.ENOENT, errno.ESRCH): raise
            filter_template = None
            all_filters = []

        # XXX deviate from spec here ...
        # load the index section template and figure the default columns from it
        template = open(os.path.join(self.templates,
            self.classname+'.index')).read()
        all_columns = self.col_re.findall(template)
        if not columns:
            columns = []
            for name in all_columns:
                columns.append(name)
        else:
            # re-sort columns to be the same order as all_columns
            l = []
            for name in all_columns:
                if name in columns:
                    l.append(name)
            columns = l

        # display the filter section
        if (show_display_form and hasattr(self.client, 'FILTER_POSITION') and
                self.client.FILTER_POSITION in ('top and bottom', 'top')):
            w('<form action="index">\n')
            self.filter_section(filter_template, filter, columns, group,
                all_filters, all_columns, show_customization)
            # make sure that the sorting doesn't get lost either
            if sort:
                w('<input type="hidden" name=":sort" value="%s">'%
                    ','.join(sort))
            w('</form>\n')


        # now display the index section
        w('<table width=100% border=0 cellspacing=0 cellpadding=2>\n')
        w('<tr class="list-header">\n')
        for name in columns:
            cname = name.capitalize()
            if show_display_form:
                sb = self.sortby(name, filterspec, columns, filter, group, sort)
                anchor = "%s?%s"%(self.classname, sb)
                w('<td><span class="list-header"><a href="%s">%s</a></span></td>\n'%(
                    anchor, cname))
            else:
                w('<td><span class="list-header">%s</span></td>\n'%cname)
        w('</tr>\n')

        # this stuff is used for group headings - optimise the group names
        old_group = None
        group_names = []
        if group:
            for name in group:
                if name[0] == '-': group_names.append(name[1:])
                else: group_names.append(name)

        # now actually loop through all the nodes we get from the filter and
        # apply the template
        if nodeids is None:
            nodeids = self.cl.filter(filterspec, sort, group)
        for nodeid in nodeids:
            # check for a group heading
            if group_names:
                this_group = [self.cl.get(nodeid, name) for name in group_names]
                if this_group != old_group:
                    l = []
                    for name in group_names:
                        prop = self.properties[name]
                        if isinstance(prop, hyperdb.Link):
                            group_cl = self.db.classes[prop.classname]
                            key = group_cl.getkey()
                            value = self.cl.get(nodeid, name)
                            if value is None:
                                l.append('[unselected %s]'%prop.classname)
                            else:
                                l.append(group_cl.get(self.cl.get(nodeid,
                                    name), key))
                        elif isinstance(prop, hyperdb.Multilink):
                            group_cl = self.db.classes[prop.classname]
                            key = group_cl.getkey()
                            for value in self.cl.get(nodeid, name):
                                l.append(group_cl.get(value, key))
                        else:
                            value = self.cl.get(nodeid, name)
                            if value is None:
                                value = '[empty %s]'%name
                            else:
                                value = str(value)
                            l.append(value)
                    w('<tr class="section-bar">'
                      '<td align=middle colspan=%s><strong>%s</strong></td></tr>'%(
                        len(columns), ', '.join(l)))
                    old_group = this_group

            # display this node's row
            replace = IndexTemplateReplace(self.globals, locals(), columns)
            self.nodeid = nodeid
            w(replace.go(template))
            self.nodeid = None

        w('</table>')

        # display the filter section
        if (show_display_form and hasattr(self.client, 'FILTER_POSITION') and
                self.client.FILTER_POSITION in ('top and bottom', 'bottom')):
            w('<form action="index">\n')
            self.filter_section(filter_template, filter, columns, group,
                all_filters, all_columns, show_customization)
            # make sure that the sorting doesn't get lost either
            if sort:
                w('<input type="hidden" name=":sort" value="%s">'%
                    ','.join(sort))
            w('</form>\n')


    def filter_section(self, template, filter, columns, group, all_filters,
            all_columns, show_customization):

        w = self.client.write

        if template and filter:
            # display the filter section
            w('<table width=100% border=0 cellspacing=0 cellpadding=2>')
            w('<tr class="location-bar">')
            w(' <th align="left" colspan="2">Filter specification...</th>')
            w('</tr>')
            replace = IndexTemplateReplace(self.globals, locals(), filter)
            w(replace.go(template))
            w('<tr class="location-bar"><td width="1%%">&nbsp;</td>')
            w('<td><input type="submit" name="action" value="Redisplay"></td></tr>')
            w('</table>')

        # now add in the filter/columns/group/etc config table form
        w('<input type="hidden" name="show_customization" value="%s">' %
            show_customization )
        w('<table width=100% border=0 cellspacing=0 cellpadding=2>\n')
        names = []
        for name in self.properties.keys():
            if name in all_filters or name in all_columns:
                names.append(name)
        if show_customization:
            action = '-'
        else:
            action = '+'
            # hide the values for filters, columns and grouping in the form
            # if the customization widget is not visible
            for name in names:
                if all_filters and name in filter:
                    w('<input type="hidden" name=":filter" value="%s">' % name)
                if all_columns and name in columns:
                    w('<input type="hidden" name=":columns" value="%s">' % name)
                if all_columns and name in group:
                    w('<input type="hidden" name=":group" value="%s">' % name)

        # TODO: The widget style can go into the stylesheet
        w('<th align="left" colspan=%s>'
          '<input style="height : 1em; width : 1em; font-size: 12pt" type="submit" name="action" value="%s">&nbsp;View '
          'customisation...</th></tr>\n'%(len(names)+1, action))

        if not show_customization:
            w('</table>\n')

        w('<tr class="location-bar"><th>&nbsp;</th>')
        for name in names:
            w('<th>%s</th>'%name.capitalize())
        w('</tr>\n')

        # Filter
        if all_filters:
            w('<tr><th width="1%" align=right class="location-bar">'
              'Filters</th>\n')
            for name in names:
                if name not in all_filters:
                    w('<td>&nbsp;</td>')
                    continue
                if name in filter: checked=' checked'
                else: checked=''
                w('<td align=middle>\n')
                w(' <input type="checkbox" name=":filter" value="%s" '
                  '%s></td>\n'%(name, checked))
            w('</tr>\n')

        # Columns
        if all_columns:
            w('<tr><th width="1%" align=right class="location-bar">'
              'Columns</th>\n')
            for name in names:
                if name not in all_columns:
                    w('<td>&nbsp;</td>')
                    continue
                if name in columns: checked=' checked'
                else: checked=''
                w('<td align=middle>\n')
                w(' <input type="checkbox" name=":columns" value="%s"'
                  '%s></td>\n'%(name, checked))
            w('</tr>\n')

            # Grouping
            w('<tr><th width="1%" align=right class="location-bar">'
              'Grouping</th>\n')
            for name in names:
                prop = self.properties[name]
                if name not in all_columns:
                    w('<td>&nbsp;</td>')
                    continue
                if name in group: checked=' checked'
                else: checked=''
                w('<td align=middle>\n')
                w(' <input type="checkbox" name=":group" value="%s"'
                  '%s></td>\n'%(name, checked))
            w('</tr>\n')

        w('<tr class="location-bar"><td width="1%">&nbsp;</td>')
        w('<td colspan="%s">'%len(names))
        w('<input type="submit" name="action" value="Redisplay"></td>')
        w('</tr>\n')
        w('</table>\n')


    def sortby(self, sort_name, filterspec, columns, filter, group, sort):
        l = []
        w = l.append
        for k, v in filterspec.items():
            k = urllib.quote(k)
            if type(v) == type([]):
                w('%s=%s'%(k, ','.join(map(urllib.quote, v))))
            else:
                w('%s=%s'%(k, urllib.quote(v)))
        if columns:
            w(':columns=%s'%','.join(map(urllib.quote, columns)))
        if filter:
            w(':filter=%s'%','.join(map(urllib.quote, filter)))
        if group:
            w(':group=%s'%','.join(map(urllib.quote, group)))
        m = []
        s_dir = ''
        for name in sort:
            dir = name[0]
            if dir == '-':
                name = name[1:]
            else:
                dir = ''
            if sort_name == name:
                if dir == '-':
                    s_dir = ''
                else:
                    s_dir = '-'
            else:
                m.append(dir+urllib.quote(name))
        m.insert(0, s_dir+urllib.quote(sort_name))
        # so things don't get completely out of hand, limit the sort to
        # two columns
        w(':sort=%s'%','.join(m[:2]))
        return '&'.join(l)

#
#   ITEM TEMPLATES
#
class ItemTemplateReplace:
    def __init__(self, globals, locals, cl, nodeid):
        self.globals = globals
        self.locals = locals
        self.cl = cl
        self.nodeid = nodeid

    replace=re.compile(
        r'((<property\s+name="(?P<name>[^>]+)">(?P<text>.+?)</property>)|'
        r'(?P<display><display\s+call="(?P<command>[^"]+)">))', re.I|re.S)
    def go(self, text):
        return self.replace.sub(self, text)

    def __call__(self, m, filter=None, columns=None, sort=None, group=None):
        if m.group('name'):
            if self.nodeid and self.cl.get(self.nodeid, m.group('name')):
                replace = ItemTemplateReplace(self.globals, {}, self.cl,
                    self.nodeid)
                return replace.go(m.group('text'))
            else:
                return ''
        if m.group('display'):
            command = m.group('command')
            return eval(command, self.globals, self.locals)
        print '*** unhandled match', m.groupdict()


class ItemTemplate(TemplateFunctions):
    def __init__(self, client, templates, classname):
        self.client = client
        self.templates = templates
        self.classname = classname

        # derived
        self.db = self.client.db
        self.cl = self.db.classes[self.classname]
        self.properties = self.cl.getprops()

        TemplateFunctions.__init__(self)

    def render(self, nodeid):
        self.nodeid = nodeid

        if (self.properties.has_key('type') and
                self.properties.has_key('content')):
            pass
            # XXX we really want to return this as a downloadable...
            #  currently I handle this at a higher level by detecting 'file'
            #  designators...

        w = self.client.write
        w('<form action="%s%s">'%(self.classname, nodeid))
        s = open(os.path.join(self.templates, self.classname+'.item')).read()
        replace = ItemTemplateReplace(self.globals, locals(), self.cl, nodeid)
        w(replace.go(s))
        w('</form>')


class NewItemTemplate(TemplateFunctions):
    def __init__(self, client, templates, classname):
        self.client = client
        self.templates = templates
        self.classname = classname

        # derived
        self.db = self.client.db
        self.cl = self.db.classes[self.classname]
        self.properties = self.cl.getprops()

        TemplateFunctions.__init__(self)

    def render(self, form):
        self.form = form
        w = self.client.write
        c = self.classname
        try:
            s = open(os.path.join(self.templates, c+'.newitem')).read()
        except:
            s = open(os.path.join(self.templates, c+'.item')).read()
        w('<form action="new%s" method="POST" enctype="multipart/form-data">'%c)
        for key in form.keys():
            if key[0] == ':':
                value = form[key].value
                if type(value) != type([]): value = [value]
                for value in value:
                    w('<input type="hidden" name="%s" value="%s">'%(key, value))
        replace = ItemTemplateReplace(self.globals, locals(), None, None)
        w(replace.go(s))
        w('</form>')

#
# $Log: not supported by cvs2svn $
# Revision 1.39  2001/11/03 01:43:47  richard
# Ahah! Fixed the lynx problem - there was a hidden input field misplaced.
#
# Revision 1.38  2001/10/31 06:58:51  richard
# Added the wrap="hard" attribute to the textarea of the note field so the
# messages wrap sanely.
#
# Revision 1.37  2001/10/31 06:24:35  richard
# Added do_stext to htmltemplate, thanks Brad Clements.
#
# Revision 1.36  2001/10/28 22:51:38  richard
# Fixed ENOENT/WindowsError thing, thanks Juergen Hermann
#
# Revision 1.35  2001/10/24 00:04:41  richard
# Removed the "infinite authentication loop", thanks Roch'e
#
# Revision 1.34  2001/10/23 22:56:36  richard
# Bugfix in filter "widget" placement, thanks Roch'e
#
# Revision 1.33  2001/10/23 01:00:18  richard
# Re-enabled login and registration access after lopping them off via
# disabling access for anonymous users.
# Major re-org of the htmltemplate code, cleaning it up significantly. Fixed
# a couple of bugs while I was there. Probably introduced a couple, but
# things seem to work OK at the moment.
#
# Revision 1.32  2001/10/22 03:25:01  richard
# Added configuration for:
#  . anonymous user access and registration (deny/allow)
#  . filter "widget" location on index page (top, bottom, both)
# Updated some documentation.
#
# Revision 1.31  2001/10/21 07:26:35  richard
# feature #473127: Filenames. I modified the file.index and htmltemplate
#  source so that the filename is used in the link and the creation
#  information is displayed.
#
# Revision 1.30  2001/10/21 04:44:50  richard
# bug #473124: UI inconsistency with Link fields.
#    This also prompted me to fix a fairly long-standing usability issue -
#    that of being able to turn off certain filters.
#
# Revision 1.29  2001/10/21 00:17:56  richard
# CGI interface view customisation section may now be hidden (patch from
#  Roch'e Compaan.)
#
# Revision 1.28  2001/10/21 00:00:16  richard
# Fixed Checklist function - wasn't always working on a list.
#
# Revision 1.27  2001/10/20 12:13:44  richard
# Fixed grouping of non-str properties (thanks Roch'e Compaan)
#
# Revision 1.26  2001/10/14 10:55:00  richard
# Handle empty strings in HTML template Link function
#
# Revision 1.25  2001/10/09 07:25:59  richard
# Added the Password property type. See "pydoc roundup.password" for
# implementation details. Have updated some of the documentation too.
#
# Revision 1.24  2001/09/27 06:45:58  richard
# *gak* ... xmp is Old Skool apparently. Am using pre again by have the option
# on the plain() template function to escape the text for HTML.
#
# Revision 1.23  2001/09/10 09:47:18  richard
# Fixed bug in the generation of links to Link/Multilink in indexes.
#   (thanks Hubert Hoegl)
# Added AssignedTo to the "classic" schema's item page.
#
# Revision 1.22  2001/08/30 06:01:17  richard
# Fixed missing import in mailgw :(
#
# Revision 1.21  2001/08/16 07:34:59  richard
# better CGI text searching - but hidden filter fields are disappearing...
#
# Revision 1.20  2001/08/15 23:43:18  richard
# Fixed some isFooTypes that I missed.
# Refactored some code in the CGI code.
#
# Revision 1.19  2001/08/12 06:32:36  richard
# using isinstance(blah, Foo) now instead of isFooType
#
# Revision 1.18  2001/08/07 00:24:42  richard
# stupid typo
#
# Revision 1.17  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.16  2001/08/01 03:52:23  richard
# Checklist was using wrong name.
#
# Revision 1.15  2001/07/30 08:12:17  richard
# Added time logging and file uploading to the templates.
#
# Revision 1.14  2001/07/30 06:17:45  richard
# Features:
#  . Added ability for cgi newblah forms to indicate that the new node
#    should be linked somewhere.
# Fixed:
#  . Fixed the agument handling for the roundup-admin find command.
#  . Fixed handling of summary when no note supplied for newblah. Again.
#  . Fixed detection of no form in htmltemplate Field display.
#
# Revision 1.13  2001/07/30 02:37:53  richard
# Temporary measure until we have decent schema migration.
#
# Revision 1.12  2001/07/30 01:24:33  richard
# Handles new node display now.
#
# Revision 1.11  2001/07/29 09:31:35  richard
# oops
#
# Revision 1.10  2001/07/29 09:28:23  richard
# Fixed sorting by clicking on column headings.
#
# Revision 1.9  2001/07/29 08:27:40  richard
# Fixed handling of passed-in values in form elements (ie. during a
# drill-down)
#
# Revision 1.8  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.7  2001/07/29 05:36:14  richard
# Cleanup of the link label generation.
#
# Revision 1.6  2001/07/29 04:06:42  richard
# Fixed problem in link display when Link value is None.
#
# Revision 1.5  2001/07/28 08:17:09  richard
# fixed use of stylesheet
#
# Revision 1.4  2001/07/28 07:59:53  richard
# Replaced errno integers with their module values.
# De-tabbed templatebuilder.py
#
# Revision 1.3  2001/07/25 03:39:47  richard
# Hrm - displaying links to classes that don't specify a key property. I've
# got it defaulting to 'name', then 'title' and then a "random" property (first
# one returned by getprops().keys().
# Needs to be moved onto the Class I think...
#
# Revision 1.2  2001/07/22 12:09:32  richard
# Final commit of Grande Splite
#
# Revision 1.1  2001/07/22 11:58:35  richard
# More Grande Splite
#
#
# vim: set filetype=python ts=4 sw=4 et si
