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
import wx
from gui import settingsDialogs
from config import conf

# Keep a reference to the running plugin instance so the settings panel can update it.
currentPlugin = None

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

	def __init__(self):
		super().__init__()
		# Persisted settings
		if 'directLink' not in conf:
			conf['directLink'] = {}
		dl = conf['directLink']
		self.preferDeepLinkWA = bool(dl.get('preferDeepLinkWA', False))
		self.preferDeepLinkTG = bool(dl.get('preferDeepLinkTG', False))

		# Register the running instance
		global currentPlugin
		currentPlugin = self

	def isLink(self, match):
		# keep the original domain detection logic for now
		text1 = re.match(r"https:\/\/(?:www\.dropbox|drive\.google|1drv|.*?sharepoint)\.(com|ms)\/", match)
		if text1:
			global domain
			domain = text1.group()
		return text1

	def isNumber(self, wNumber):
		# keep permissive number check, we will further validate international format in converters
		text1 = re.match(r"^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$", wNumber)
		return text1

	# --- helpers for Phase 1 (no external deps, minimal surface) ---
	def _cleanDigits(self, s: str) -> str:
		# remove spaces, hyphens, parentheses, dots
		return s.replace('-', '').replace('(', '').replace(')', '').replace('.', '').replace(' ', '')

	def _normalizeInternational(self, raw: str):
		"""
		Normalize phone input to two forms:
		- waDigits: international number *without* '+' or '00' (for wa.me)
		- plusForm: international number *with* '+' (for t.me/+)
		Returns (waDigits, plusForm) or raises ValueError if no country code is present.
		"""
		s = self._cleanDigits(raw).strip()
		if not s:
			raise ValueError("empty")

		# accept +<digits> or 00<digits>; reject local numbers in this phase
		if s.startswith('+'):
			digits = s[1:]
		elif s.startswith('00'):
			# convert 00CC... -> CC...
			digits = s[2:]
		else:
			# no country code provided
			raise ValueError("missingCountryCode")

		if not digits.isdigit():
			raise ValueError("invalidChars")

		# basic sanity window for E.164 length without '+'
		if not (8 <= len(digits) <= 15):
			raise ValueError("badLength")

		return digits, f"+{digits}"

	# --- file host converters ---

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

	# --- messaging converters (Phase 1 behavior) ---

	def convertWP(self, wNumber):
		digits, _ = self._normalizeInternational(wNumber)

		if self.preferDeepLinkWA:
			return f"whatsapp://send?phone={digits}"
		return f"https://wa.me/{digits}"

	def convertTelegram(self, telegram):
		digits, plusForm = self._normalizeInternational(telegram)

		if self.preferDeepLinkTG:
			return f"tg://resolve?phone={digits}"
		return f"https://t.me/+{digits}"

	@script(
		# translators: appears in the NVDA input help.
		description=_("Converts the given link to a direct link."),
		gesture="kb:alt+nvda+l",
		category="DirectLink"
	)
	def script_convertingLink(self, gesture):
		global link
		link = getSelectedText()
		link = link.strip()  # Phase 1 fix: assign back so whitespace is trimmed
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
				# Phase 1: only generate when an international country code is present
				try:
					link = self.convertWP(link)
				except ValueError:
					# translators: the message will be announced when a local number is detected without a country code
					ui.message(_("Please include your country code (start with + or 00) to generate a WhatsApp link."))
					return
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
		link = link.strip()  # Phase 1 fix: trim whitespace
		try:
			link = link.split()[0]
		except:
			ui.message(_("Your clipboard is empty or does not contain text."))
		else:
			if link == self.converted:
				ui.message(_("The Telegram link has been previously generated, press NVDA+alt+o to open it in browser."))
			else:
				if self.isNumber(link):
					# Phase 1: only generate when an international country code is present
					try:
						link = self.convertTelegram(link)
					except ValueError:
						ui.message(_("Please include your country code (start with + or 00) to generate a Telegram link."))
						return
					api.copyToClip(link)
					self.converted = link
					# translators: the message announces after converting a number to a telegram link
					ui.message(_("The phone number has been converted, press NVDA+Alt+O to open the link."))
				elif re.search(r"^@?\w{5,32}$", link):
					username = link[1:] if link.startswith("@") else link
					if self.preferDeepLinkTG:
						link = f"tg://resolve?domain={username}"
					else:
						link = f"https://t.me/{username}"
					self.converted = link
					api.copyToClip(link)
					ui.message(_("The username has been converted, press NVDA+alt+o to open the link."))
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
		try:
			os.startfile(self.converted)
		except:
			# translators: this message  announces if there is no successfully converted link in the clibboard.
			ui.message(_("No link has been converted."))


class DirectLinkSettingsPanel(settingsDialogs.SettingsPanel):
	# translators: Settings panel title shown in NVDA Preferences > Settings.
	title = _("DirectLink")

	def makeSettings(self, sizer):
		self.chkWA = wx.CheckBox(self, label=_("Prefer app deep links for WhatsApp"))
		self.chkTG = wx.CheckBox(self, label=_("Prefer app deep links for Telegram"))

		if 'directLink' not in conf:
			conf['directLink'] = {}
		dl = conf['directLink']

		self.chkWA.SetValue(bool(dl.get('preferDeepLinkWA', False)))
		self.chkTG.SetValue(bool(dl.get('preferDeepLinkTG', False)))

		helpTxt = wx.StaticText(
			self,
			label=_("When off, links open via the web. When on, links open in the installed app if available.")
		)

		sizer.Add(self.chkWA, flag=wx.ALL, border=5)
		sizer.Add(self.chkTG, flag=wx.ALL, border=5)
		sizer.Add(helpTxt, flag=wx.ALL, border=5)

	def onSave(self):
		if 'directLink' not in conf:
			conf['directLink'] = {}
		dl = conf['directLink']
		dl['preferDeepLinkWA'] = self.chkWA.GetValue()
		dl['preferDeepLinkTG'] = self.chkTG.GetValue()
		conf.save()

		# Apply immediately to the running plugin instance if available
		try:
			if currentPlugin is not None:
				currentPlugin.preferDeepLinkWA = self.chkWA.GetValue()
				currentPlugin.preferDeepLinkTG = self.chkTG.GetValue()
		except Exception:
			pass

		try:
			super().onSave()
		except Exception:
			pass


# Register panel with NVDA Settings (reload-safe)
if not any(
	getattr(panel, "__name__", "") == "DirectLinkSettingsPanel"
	for panel in settingsDialogs.NVDASettingsDialog.categoryClasses
):
	settingsDialogs.NVDASettingsDialog.categoryClasses.append(DirectLinkSettingsPanel)
