import globalVars
import globalPluginHandler

if globalVars.appArgs.secure:
	GlobalPlugin = globalPluginHandler.globalPlugin
else:
	from . import DirectLink
	GlobalPlugin = DirectLink.GlobalPlugin