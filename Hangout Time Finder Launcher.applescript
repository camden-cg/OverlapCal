on run
	set projectPath to do shell script "/usr/bin/dirname " & quoted form of (POSIX path of (path to me))
	set scriptPath to projectPath & "/hangout_finder.py"

	try
		set pythonPath to do shell script "/bin/sh -c " & quoted form of "for candidate in '/Library/Frameworks/Python.framework/Versions/Current/bin/python3' '/opt/homebrew/bin/python3' '/usr/local/bin/python3' '/usr/bin/python3'; do if [ -x \"$candidate\" ] && \"$candidate\" -c 'import tkinter' >/dev/null 2>&1; then printf '%s' \"$candidate\"; exit 0; fi; done; exit 1"
	on error
		display dialog "Python 3 with Tkinter is required to run Hangout Time Finder." with title "Python not found" buttons {"OK"} default button 1
		return
	end try

	do shell script "nohup " & quoted form of pythonPath & " " & quoted form of scriptPath & " >/dev/null 2>&1 </dev/null &"
end run
