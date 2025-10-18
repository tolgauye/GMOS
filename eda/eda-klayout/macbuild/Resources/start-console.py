#!/Applications/klayout.app/Contents/MacOS/klayout -b -r
import readline
import code
import sys
import os
pwd = os.getcwd()
sys.path.append(pwd)

variables = globals().copy()
variables.update(locals())
shell = code.InteractiveConsole(variables)
cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
banner = "Python %s on %s\n%s\n(%s)" % (sys.version, sys.platform,
    cprt, "KLayout Python Console")
exit_msg = 'now exiting %s...' % "KLayout Python Console"
shell.interact(banner, exit_msg)
