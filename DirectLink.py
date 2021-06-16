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
		text1 = re.match(r"https:\/\/(?:www\.dropbox|drive\.google)\.com\/", match)
		if text1:
			global domain
			domain = text1.group()
		return text1

	def isNumber(self, wNumber):
		text1 = re.match(r"^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$", wNumber)
		return text1

	def convertDB(self, dbLink):
		dbLink = dbLink.replace("www", "dl").replace("?dl=0", '')
		return dbLink

	def convertGD(self, dLink):
		GDLink ='https://drive.google.com/uc?export=download&id='
		fileID =re.search(r"d\/(.*?)\/", dLink)
		if fileID:
			fileID =fileID.group()
			fileID =fileID[2:-1]
			dLink =GDLink+fileID
		else:
			fileID =re.search(r"=(.*?)(\/|&)", dLink)
			fileID =fileID.group()
			fileID =fileID[1:-1]
			dLink =GDLink+fileID
		return dLink

	def convertWP(self, wNumber):
		wNumber = wNumber.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')
		wNumber = f"https://api.whatsapp.com/send?phone={wNumber}"
		return wNumber

	@script(
		description="Converts the given link to a direct link",
		gesture="kb:alt+nvda+l",
		category="DirectLink"
	)
	def script_convertingLink(self, gesture):
		global link
		link = getSelectedText()
		link.strip()
		if self.isLink(link):
			if domain == "https://www.dropbox.com/":
				link = self.convertDB(link)
				api.copyToClip(link)
				ui.message("the Dropbox link has been converted and copied to the clipboard, press nvda+alt+shift+l to open in browser")
			elif domain =='https://drive.google.com/':
				link =self.convertGD(link)
				api.copyToClip(link)
				ui.message("The Google Drive link has been converted and copied to the clipboard, press nvda+alt+shift+l to open in browser")
		elif self.isNumber(link):
			link =self.convertWP(link)
			api.copyToClip(link)
			ui.message("to open the whatsApp chat in the browser with the selected number, press nvda+alt+shift+l")
		else:
			ui.message("please select or copy a dropbox or a google drive link to convert, or a whatsApp number to chat with.")

	@script(
		description="open the selected link in browser",
		gesture="kb:alt+shift+nvda+l",
		category="DirectLink"
	)
	def script_openInBrowser(self, gesture):
		os.startfile(link)
