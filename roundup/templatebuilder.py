# $Id: templatebuilder.py,v 1.7 2001-07-30 00:06:52 richard Exp $
import errno

preamble = """ 
# Do Not Edit (Unless You Want To)
# This file automagically generated by roundup.htmldata.makeHtmlBase
# 
"""

def makeHtmlBase(templateDir):
    """ make a htmlbase.py file in the given templateDir, from the
        contents of templateDir/html """
    import os, glob, re
    print "packing up templates in", templateDir
    filelist = glob.glob(os.path.join(templateDir, 'html', '*'))
    filelist = filter(os.path.isfile, filelist) # only want files
    filelist.sort()
    fd = open(os.path.join(templateDir, 'htmlbase.py'), 'w')
    fd.write(preamble)
    for file in filelist:
        mangled_name = os.path.basename(re.sub(r'\.', 'DOT', file))
        fd.write('%s = """'%mangled_name)
        fd.write(open(file).read())
        fd.write('"""\n\n')
    fd.close()

def installHtmlBase(template, installDir):
    """ passed a template package and an installDir, unpacks the html files into
      the installdir """
    import os,sys,re

    tdir = __import__('roundup.templates.%s.htmlbase'%template).templates
    if hasattr(tdir, template):
        tmod = getattr(tdir, template)
    else:
        raise "TemplateError", "couldn't find roundup.template.%s.htmlbase"%template
    htmlbase = tmod.htmlbase
    installDir = os.path.join(installDir, 'html')
    try:
        os.makedirs(installDir)
    except OSError, error:
        if error.errno != errno.EEXIST: raise

#    print "installing from", htmlbase.__file__, "into", installDir
    modulecontents = dir(htmlbase)
    for mangledfile in modulecontents:
        if mangledfile[0] == "_": 
            continue
        filename = re.sub('DOT', '.', mangledfile)
        outfile = os.path.join(installDir, filename)
        outfd = open(outfile, 'w')
        data = getattr(htmlbase, mangledfile)
        outfd.write(data)
    


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        makeHtmlBase(sys.argv[1])
    elif len(sys.argv) == 3:
        installHtmlBase(sys.argv[1], sys.argv[2])
    else:
        raise "what you talkin about willis?"

#
# $Log: not supported by cvs2svn $
# Revision 1.6  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
#
#
# vim: set filetype=python ts=4 sw=4 et si
