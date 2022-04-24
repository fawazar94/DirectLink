# directLink
# Converts dropbox, google drive or oneDrive links to direct links,
# and opens Whatsapp and Telegram chats with the given number.
# copyright 2021 Fawaz Abdul rahman, released under GPL


import globalPluginHandler
import ui
import re
import api
import os
from textInfos import POSITION_SELECTION
from scriptHandler import script
import addonHandler
addonHandler.initTranslation()


# the following function was taken with modification from Quick Dictionary addon by Oleksandr Gryshchenko
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
	converted = None

	def isLink(self, match):
		text1 = re.match(r"https:\/\/(?:www\.dropbox|drive\.google|1drv|.*?sharepoint)\.(com|ms)\/", match)
		if text1:
			global domain
			domain = text1.group()
		return text1

	def isNumber(self, wNumber):
		text1 = re.match(r"^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$", wNumber)
		return text1

	def convertDB(self, dbLink):
		dbLink = dbLink.replace("?dl=0", "?dl=1")
		return dbLink

	def convertGD(self, dLink):
		GDLink = 'https://drive.google.com/uc?export=download&id='
		fileID = re.search(r"d\/(.*?)\/", dLink)
		if fileID:
			fileID = fileID.group()
			fileID = fileID[2:-1]
			dLink = GDLink + fileID
		else:
			fileID = re.search(r"=(.*?)(\/|&)", dLink)
			fileID = fileID.group()
			fileID = fileID[1:-1]
			dLink = GDLink + fileID
		return dLink

	def convert1d(self, dLink):
		import base64
		byte64 = base64.b64encode(bytes(dLink, 'utf-8'))
		dLink = byte64.decode('utf-8').replace('/', '_').replace('+', "-").rstrip("=")
		dLink = f"https://api.onedrive.com/v1.0/shares/u!{dLink}/root/content"
		return dLink

	def convert1DBus(self, dLink):
		dLink = dLink.rsplit('?', 1)[0]
		dLink = dLink + "?download=1"
		return dLink

	def convertWP(self, wNumber):
		wNumber = wNumber.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')
		wNumber = f"https://api.whatsapp.com/send?phone={wNumber}"
		return wNumber

	def convertTelegram(self, telegram):
		# for telegram phone numbers
		telegram = telegram.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')
		telegram = f"https://t.me/+{telegram}"
		return telegram


	@script(
		# translators: appears in the NVDA input help.
		description=_("Converts the given link to a direct link."),
		gesture="kb:alt+nvda+l",
		category="DirectLink"
	)
	def script_convertingLink(self, gesture):
		global link
		link = getSelectedText()
		link.strip()
		if link == self.converted:
			ui.message(_("The link has been previously converted, press NVDA+alt+o to open it in browser."))
		else:
			if self.isLink(link):
				if domain == "https://www.dropbox.com/":
					link = self.convertDB(link)
					self.converted = link
					api.copyToClip(link)
					# translators: the message will be announced when a user converts a dropbox link.
					ui.message(_("The Dropbox link has been converted and copied to the clipboard, press NVDA+alt+o to open it in browser."))
				elif domain == 'https://drive.google.com/':
					link = self.convertGD(link)
					self.converted = link
					api.copyToClip(link)
					# translaters: the message will be announced when a user converts a Google Drive link.
					ui.message(_("The Google Drive link has been converted and copied to the clipboard, press nvda+alt+o to open it in browser."))
				elif domain == 'https://1drv.ms/':
					link = self.convert1d(link)
					self.converted = link
					api.copyToClip(link)
					# translators: the message will be announced when a user converts a oneDrive link.
					ui.message(_("The oneDrive link has been converted and copied to the clipboard, press nvda+alt+o to open it in browser."))
				else:
					link = self.convert1DBus(link)
					self.converted = link
					api.copyToClip(link)
					# translators: same as oneDrive message but for oneDrive business links.
					ui.message(_("the oneDrive link has been converted and copied to the clipboard, press alt+nvda+o to open it in browser"))
			elif self.isNumber(link):
				link = self.convertWP(link)
				self.converted = link
				api.copyToClip(link)
				# translators: the message will be announced when a user converts a whatsapp number.
				ui.message(_("The WhatsApp link has been generated and copied to the clipboard, press NVDA+alt+o to open it in browser."))
			else:
				# translators: the message will be announced when there is nothing selected, or the clipboard is empty,
				# or if the selected or copied text not a supported service link nor phone number.
				ui.message(_("Please select or copy a dropbox link, a google drive link or a oneDrive link to convert, or a WhatsApp number to chat with."))

	@script(
		# translators: appears in the NVDA input help
		description=_("Converts a username or a number to a Telegram link"),
		gesture="kb:nvda+alt+t",
		category="DirectLink"
	)
	def script_telegram(self, gesture):
		global link
		link = getSelectedText()
		try:
			link = link.split()[0]
		except:
			ui.message(_("Your clipboard is empty or does not contain text."))
		else:
			if link == self.converted:
				ui.message(_("The Telegram link has been previously generated, press NVDA+alt+o to open it in browser."))
			else:
				if self.isNumber(link):
					link = self.convertTelegram(link)
					api.copyToClip(link)
					self.converted = link
					# translators: the message announces after converting a number to a telegram link
					ui.message(_("The phone number has been converted, press NVDA+Alt+O to open the link in browser."))
				elif re.search(r"^\w{5,32}$", link):
					link = f"https://t.me/{link}"
					self.converted = link
					api.copyToClip(link)
					# translators: the message announces when the user converts a username to telegram link
					ui.message(_("The username has been converted, press NVDA+alt+o to open the link in browser."))
				else:
					# translators: the message announces when the selection is not a valid number or a username
					ui.message(_("Select a valid phone number or username to generate its Telegram link."))

	@script(
		# translators: appears in the NVDA input help
		description=_("Opens the converted link in browser."),
		gesture="kb:nvda+alt+o",
		category="DirectLink"
	)
	def script_openInBrowser(self, gesture):
		os.startfile(link)
