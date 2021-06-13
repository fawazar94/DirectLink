import globalPluginHandler
import ui
import re
import api
import os
from textInfos import POSITION_SELECTION
from scriptHandler import script

def getSelectedText() -> str:
	"""Retrieve the selected text.
	If the selected text is missing - extract the text from the clipboard.
	If the clipboard is empty or contains no text data - announce a warning.
	@return: selected text, text from the clipboard, or an empty string
	@rtype: str
	"""
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
		obj = treeInterceptor
	try:
		info = obj.makeTextInfo(POSITION_SELECTION)
	except (RuntimeError, NotImplementedError):
		info = None
	if not info or info.isCollapsed:
		try:
			text = api.getClipData()
		except Exception:
			text = ''
		if not text or not isinstance(text, str):
			# Translators: User has pressed the shortcut key for translating selected text,
			# but no text was actually selected and clipboard is clear
			ui.message("There is no selected text, the clipboard is also empty, or its content is not text!")
			return ''
		return text
	return info.text


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def isLink(self, match):
		text1 = re.match(r"^https:\/\/(?:www\.dropbox|drive\.google|1drv)\.(com|ms)\/", match)
		if text1:
			global domain
			domain = text1.group()
		return text1

	def convertDB(self, dbLink):
		dbLink = dbLink.replace("?dl=0", '')
		dbLink = dbLink.replace("www", "dl")
		return dbLink

	@script(
		description="Converts the given link to a direct link",
		gesture="kb:alt+nvda+l",
		category="DirectLink"
	)
	def script_convertingLink(self, gesture):
		global link
		link = getSelectedText()
		if self.isLink(link):
			if domain == "https://www.dropbox.com/":
				ui.message("the link is dropbox")
				link = self.convertDB(link)
				api.copyToClip(link)
		else:
			ui.message("not dropbox link")

	@script(
		description="open the selected link in browser",
		gesture="kb:alt+nvda+k",
		category="DirectLink"
	)
	def script_openInBrowser(self, gesture):
		os.startfile(link)
