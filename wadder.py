#----------------------------------------------------------------------
# WADder 3.0 pre-alpha
#----------------------------------------------------------------------

import os, wx, hashlib, shutil
from Struct import Struct
import icewii as wii

def debug(text):
	if text != "":
		print text #comment this out to not debug
		pass
		
def clean():
	try:
		shutil.rmtree("wadunpack")
		os.unlink("in.wad")
		os.unlink("out.wad")
		os.unlink("tmp.png")
	except OSError:
		pass
		
def doApp(self): #we can ignore self
	global wadder
	
	dol = wadder.opttab.dol.GetValue()
	if(os.path.exists(dol) != True and dol != ""):
		wx.MessageBox('DOL selected must exist.', 'Error', wx.OK | wx.ICON_ERROR)
		return
		
	titleid = wadder.opttab.titleid.GetValue()
	if(len(titleid) != 4 and titleid != ""):
		wx.MessageBox('Title ID must be four letters and/or numbers.', 'Error', wx.OK | wx.ICON_ERROR)
		return
		
	wad = wadder.wadtab.wad.GetValue()
	if(os.path.exists(wad) != True):
		wx.MessageBox('WAD selected must exist and WAD must be entered.', 'Error', wx.OK | wx.ICON_ERROR)
		return
		
	sound = wadder.opttab.sound.GetValue()
	if(os.path.exists(sound) != True and sound != ""):
		wx.MessageBox('Sound selected must exist.', 'Error')
		return
		
	title = wadder.titletab.channame.GetValue()
	if(len(title) > 20):
		wx.MessageBox('Title must not be longer than 20 characters.', 'Error', wx.OK | wx.ICON_ERROR)
		return
		
	langs = []
	langs.append(wadder.titletab.jap.GetValue())
	langs.append(wadder.titletab.eng.GetValue())
	langs.append(wadder.titletab.get.GetValue())
	langs.append(wadder.titletab.fra.GetValue())
	langs.append(wadder.titletab.spa.GetValue())
	langs.append(wadder.titletab.ita.GetValue())
	langs.append(wadder.titletab.dut.GetValue())
	for i in range(7):
		if(len(langs[i]) > 20):
			wx.MessageBox('Specific Language title must not be longer than 20 characters.', 'Error', wx.OK | wx.ICON_ERROR)
			return
	
	doWADder(wad, titleid, title, sound, dol, nandloader, langs)

	
def doWADder(wad, titleid = "", title = "Channel by WADder", sound = "", dol = "", nandloader = "", langs = [], loop = 0):
	shutil.copy(wad, "in.wad")
	
	wii.WAD("in.wad").unpack("wadunpack")
	wii.U8(wii.IMET("wadunpack/00000000.app").remove()).unpack()
	wii.U8(wii.LZ77(wii.IMD5("wadunpack/00000000_app_out/meta/banner.bin").remove()).remove()).unpack()
	wii.U8(wii.LZ77(wii.IMD5("wadunpack/00000000_app_out/meta/icon.bin").remove()).remove()).unpack()
	
	#do sound stuff, dis is teh hard partz
		
	imedit = ImageEditor(redirect=True)
	imedit.MainLoop()

	wii.IMD5(wii.LZ77(wii.U8("wadunpack/00000000_app_out/meta/banner_bin_out").pack()).add()).add()
	wii.IMD5(wii.LZ77(wii.U8("wadunpack/00000000_app_out/meta/icon_bin_out").pack()).add()).add()
	wii.IMET(wii.U8("wadunpack/00000000_app_out").pack()).add(os.path.getsize("wadunpack/00000000_app_out/meta/icon.bin"), os.path.getsize("wadunpack/00000000_app_out/meta/banner.bin"), os.path.getsize("wadunpack/00000000_app_out/meta/sound.bin"), title, langs)
	
	if(dol != ""):
		if(nandloader != ""):
			shutil.copy("wadunpack/00000000.app", "00000000.app")
			shutil.rmtree("wadunpack")
			os.mkdir("wadunpack")
			shutil.copy("00000000.app", "wadunpack/00000000.app")
			shutil.copytree("data/" + nandloader, "wadunpack")
		if(nandloader == "Comex"):
			dolpath = "00000002.app"
		else:
			dolpath = "00000001.app"
		shutil.copy(dol, "wadunpack/" + dolpath)

	wii.WAD("wadunpack").pack("out.wad", titleid)
	
	dlg = wx.FileDialog(self, "Save completed WAD...", "", "", "Wii Channels (*.wad)|*.wad|All Files (*.*)|*.*", wx.SAVE)
	if dlg.ShowModal() == wx.ID_OK:
		shutil.move("out.wad", dlg.GetPath())
	dlg.Destroy()
	



class ImagePanel(wx.Panel):
	def __init__(self, parent, id, dir):
		wx.Panel.__init__(self, parent, id)
		self.dir = dir
		
		tpls = sorted(os.listdir(dir))
		self.list = wx.ListBox(self, -1, (5, 2), (260, 250), choices = tpls)
		
		repbtn = wx.Button(self, -1, "Replace", (5, 260), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.replacebutton, repbtn)
		
		extbtn = wx.Button(self, -1, "Extract", (95, 260), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.extractbutton, extbtn)
		
		viewbtn = wx.Button(self, -1, "Preview", (185, 260), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.viewbutton, viewbtn)
		
		self.Show(True)
	def replacebutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a an image to replace...", "", "", "PNG images (*.png)|*.png|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			wii.TPL(dlg.GetPath()).toTPL(self.dir + "/" + self.list.GetStringSelection())
		dlg.Destroy()
	def viewbutton(self, evt):
		wii.TPL(self.dir + "/" + self.list.GetStringSelection()).toScreen()
	def extractbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a location to save...", "", "", "PNG images (*.png)|*.png|All Files (*.*)|*.*", wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			wii.TPL(self.dir + "/" + self.list.GetStringSelection()).toPNG(dlg.GetPath())
		dlg.Destroy()



class ImageUI(wx.Frame):
    def __init__(self, parent, title):
		wx.Frame.__init__(self, parent, -1, title, (-1, -1), (300, 400))
		panel = wx.Panel(self)
		
		self.gobtn = wx.Button(panel, -1, "Continue", (70, 350), (160, -1))
		self.Bind(wx.EVT_BUTTON, self.close, self.gobtn)
		
		self.Show(True)
    def close(self, evt):
        self.Close()


class ImageEditor(wx.App):
	def OnInit(self):
		debug("Starting Image Editor")
		
		frame = ImageUI(None, "Image Editor")
        
		nb = wx.Notebook(frame, -1, (5, 5), (280, 330))
		
		self.bannertab = ImagePanel(nb, -1, "wadunpack/00000000_app_out/meta/banner_bin_out/arc/timg")
   		nb.AddPage(self.bannertab, "Banner")
   		
   		self.icontab = ImagePanel(nb, -1, "wadunpack/00000000_app_out/meta/icon_bin_out/arc/timg")
   		nb.AddPage(self.icontab, "Icon")

		return True



		
class WADPanel(wx.Panel):
	def __init__(self, parent, id):
		wx.Panel.__init__(self, parent, id)
		
		wx.StaticText(self, -1, "WAD to edit:", (5, 30))
		#wx.StaticText(self, -1, "Edit the...", (5, 60))
		
		#self.banner = wx.RadioButton(self, -1, "banner,", (90, 60), style = wx.RB_GROUP)
		#self.icon = wx.RadioButton(self, -1, "icon,", (165, 60))
		#self.both = wx.RadioButton(self, -1, "both,", (225, 60))
		#self.both.SetValue(True)
		#self.neither = wx.RadioButton(self, -1, "or neither?", (285, 60))
		
		wadbtn = wx.Button(self, -1, "Browse...", (340, 30), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.wadbutton, wadbtn)
		self.wad = wx.TextCtrl(self, -1, "", (90, 30), (245, -1))
		
		self.Show(True)
	def wadbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a WAD to edit...", "", "", "WAD Files (*.wad)|*.wad|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.wad.SetValue(dlg.GetPath())
		dlg.Destroy()
   

class TitlePanel(wx.Panel):
	def __init__(self, parent, id):
		wx.Panel.__init__(self, parent, id)

		wx.StaticText(self, -1, "All Languages:", (5, 23))
		wx.StaticText(self, -1, "(this must be filled in)", (280, 23))
		wx.StaticText(self, -1, "Want to change a specific language?", (5, 60))
		wx.StaticText(self, -1, "English:", (5, 84))
		wx.StaticText(self, -1, "Spanish:", (5, 109))
		wx.StaticText(self, -1, "Japanese:", (5, 134))
		wx.StaticText(self, -1, "German:", (5, 159))
		wx.StaticText(self, -1, "French:", (220, 84))
		wx.StaticText(self, -1, "Italian:", (220, 109))
		wx.StaticText(self, -1, "Dutch:", (220, 134))
		
		self.channame = wx.TextCtrl(self, -1, "", (125, 20), (150, -1))
		self.eng = wx.TextCtrl(self, -1, "", (65, 80), (140, -1))
		self.spa = wx.TextCtrl(self, -1, "", (65, 105), (140, -1))
		self.jap = wx.TextCtrl(self, -1, "", (65, 130), (140, -1))
		self.ger = wx.TextCtrl(self, -1, "", (65, 155), (140, -1))
		self.fra = wx.TextCtrl(self, -1, "", (270, 80), (140, -1))
		self.ita = wx.TextCtrl(self, -1, "", (270, 105), (140, -1))
		self.dut = wx.TextCtrl(self, -1, "", (270, 130), (140, -1))
		
		pass
		
class OptPanel(wx.Panel):
	def __init__(self, parent, id):
		wx.Panel.__init__(self, parent, id)
		
		wx.StaticText(self, -1, "Unique Title ID:", (5, 15))
		self.titleid = wx.TextCtrl(self, -1, "", (110, 10), (40, -1))
		
		wx.StaticText(self, -1, "NAND Loader:", (35, 75))
		self.nandloader = wx.ComboBox(self, -1, "comex", (125, 73), style = wx.CB_READONLY | wx.CB_DROPDOWN, choices = ["comex", "Waninkoko"])
		
		wx.StaticText(self, -1, "New DOL:", (5, 43))
		dolbtn = wx.Button(self, -1, "Browse...", (340, 40), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.dolbutton, dolbtn)
		self.dol = wx.TextCtrl(self, -1, "", (90, 40), (245, -1))
		
		wx.StaticText(self, -1, "New Sound:", (5, 103))
		soundbtn = wx.Button(self, -1, "Browse...", (340, 100), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.soundbutton, soundbtn)
		self.sound = wx.TextCtrl(self, -1, "", (90, 100), (245, -1))
		#self.loop = wx.CheckBox(self, -1, "Loop Sound. Windows only, might not work :(.", (50, 130))
		
		wx.StaticText(self, -1, "These are optional. Fill them in only if you want to change them.", (5, 180))
		
	def soundbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a sound...", "", "", "MP3 Files (*.mp3)|*.mp3|WAV Files (*.wav)|*.wav|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.sound.SetValue(dlg.GetPath())
		dlg.Destroy()
	def dolbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a DOL...", "", "", "Wii executables (*.dol)|*.dol|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.dol.SetValue(dlg.GetPath())
		dlg.Destroy()
		
class ExPanel(wx.Panel):
	def __init__(self, parent, id):
		wx.Panel.__init__(self, parent, id)
		
		wx.StaticText(self, -1, "banner.bin:", (5, 43))
		bannerbtn = wx.Button(self, -1, "Browse...", (340, 40), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.bannerbutton, bannerbtn)
		self.banner = wx.TextCtrl(self, -1, "", (80, 40), (245, -1))
		
		wx.StaticText(self, -1, "icon.bin:", (5, 73))
		iconbtn = wx.Button(self, -1, "Browse...", (340, 70), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.iconbutton, iconbtn)
		self.icon = wx.TextCtrl(self, -1, "", (80, 70), (245, -1))
		
		wx.StaticText(self, -1, "sound.bin:", (5, 103))
		soundbtn = wx.Button(self, -1, "Browse...", (340, 100), (80, -1))
		self.Bind(wx.EVT_BUTTON, self.soundbutton, soundbtn)
		self.sound = wx.TextCtrl(self, -1, "", (80, 100), (245, -1))
		
		wx.StaticText(self, -1, "Just pick any of the ones you want to change! All are optional.", (5, 180))
	def soundbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a source...", "", "", "Wii Chanels (*.wad)|*.wad|00000000.app (*.app)|*.app|Opening.bnr (*.bnr)|*.bnr|bin Files (*.bin)|*.bin|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.sound.SetValue(dlg.GetPath())
		dlg.Destroy()
	def bannerbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a source...", "", "", "Wii Chanels (*.wad)|*.wad|00000000.app (*.app)|*.app|Opening.bnr (*.bnr)|*.bnr|bin Files (*.bin)|*.bin|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.banner.SetValue(dlg.GetPath())
		dlg.Destroy()
	def iconbutton(self, evt):
		dlg = wx.FileDialog(self, "Choose a source...", "", "", "Wii Chanels (*.wad)|*.wad|00000000.app (*.app)|*.app|Opening.bnr (*.bnr)|*.bnr|bin Files (*.bin)|*.bin|All Files (*.*)|*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.icon.SetValue(dlg.GetPath())
		dlg.Destroy()

class WADderUI(wx.Frame):
    def __init__(self, parent, title):
		wx.Frame.__init__(self, parent, -1, title, (150, 150), (437, 300))
		panel = wx.Panel(self)
		
		self.gobtn = wx.Button(panel, -1, "Create WAD!", (130, 250), (160, -1))
		self.Bind(wx.EVT_BUTTON, doApp, self.gobtn)
		
		self.Show(True)
		
    def close(self, evt):
        self.Close()


class WADder(wx.App):
	def OnInit(self):
		debug("Starting WADder 3.0 PREALPHA")
		
		frame = WADderUI(None, "WADder 3.0 by [ icefire ] PREALPHA")
        
		nb = wx.Notebook(frame, -1, (5, 5), (430, 240))
		
		self.wadtab = WADPanel(nb, -1)
   		nb.AddPage(self.wadtab, "WAD")
   		
   		self.titletab = TitlePanel(nb, -1)
   		nb.AddPage(self.titletab, "Title")
   		
   		self.opttab = OptPanel(nb, -1)
   		nb.AddPage(self.opttab, "Options")
   		
   		self.extab = ExPanel(nb, -1)
   		nb.AddPage(self.extab, "Exchange")
		
		return True

clean()
wadder = WADder(redirect=True)
wadder.MainLoop()



