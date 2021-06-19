#directLink
#Converts dropbox, google drive or oneDrive links to direct links, and opens Whatsapp chats with the given number.
#copyright 2021 Fawaz Abdul rahman, released under GPL

import globalPluginHandler
import ui
import re
import api
import os
from textInfos import POSITION_SELECTION
from scriptHandler import script
import addonHandler
addonHandler.initTranslation() 

#the following function was taken with modification from Quick Dictionary addon by Oleksandr Gryshchenko
def getSelectedText() -> str:
	"""Retrieve the selected text.
	If the selected text is missing - extract the text from the clipboard.
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
			return ''
		return text
	return info.text


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	converted =None
	def isLink(self, match):
		text1 = re.match(r"https:\/\/(?:www\.dropbox|drive\.google|1drv)\.(com|ms)\/", match)
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

	def convert1d(self, dLink):
		import base64
		byte64 =base64.b64encode(bytes(dLink, 'utf-8'))
		dLink =byte64.decode('utf-8').replace('/', '_').replace('+', "-").rstrip("=")
		dLink =f"https://api.onedrive.com/v1.0/shares/u!{dLink}/root/content"
		return dLink

	def convertWP(self, wNumber):
		wNumber = wNumber.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')
		wNumber = f"https://api.whatsapp.com/send?phone={wNumber}"
		return wNumber

	@script(
		description=_("Converts the given link to a direct link."),
		gesture="kb:alt+nvda+l",
		category="DirectLink"
	)
	def script_convertingLink(self, gesture):
		global link
		link = getSelectedText()
		link.strip()
		if link ==self.converted:
			ui.message(_("The link has been converted previously, press NVDA+alt+shift+l to open it in browser."))
		else:
			if self.isLink(link):
				if domain == "https://www.dropbox.com/":
					link = self.convertDB(link)
					self.converted =link
					api.copyToClip(link)
					ui.message(_("The Dropbox link has been converted and copied to the clipboard, press NVDA+alt+shift+l to open it in browser."))
				elif domain =='https://drive.google.com/':
					link =self.convertGD(link)
					self.converted =link
					api.copyToClip(link)
					ui.message(_("The Google Drive link has been converted and copied to the clipboard, press nvda+alt+shift+l to open it in browser."))
				elif domain == 'https://1drv.ms/':
					link =self.convert1d(link)
					self.converted =link
					api.copyToClip(link)
					ui.message(_("The oneDrive link has been converted and copied to the clipboard, press nvda+alt+shift+l to open it in browser."))
			elif self.isNumber(link):
				link =self.convertWP(link)
				self.converted =link
				api.copyToClip(link)
				ui.message(_("The WhatsApp link has been generated and copied to the clipboard, press NVDA+alt+shift+l to open it in browser."))
			else:
				ui.message(_("Please select or copy a dropbox link, a google drive link or a oneDrive link to convert, or a WhatsApp number to chat with."))

	@script(
		description=_("opens the converted link in browser."),
		gesture="kb:alt+shift+nvda+l",
		category="DirectLink"
	)
	def script_openInBrowser(self, gesture):
		os.startfile(link)
