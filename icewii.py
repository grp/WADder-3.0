import os, hashlib, struct, subprocess, fnmatch, shutil
import wx
import png
from Struct import Struct

def be16(x):
	return (x >> 8) | (x << 8)
 
def be32(x):
	return (x>>24) | ((x<<8) & 0x00FF0000) | ((x>>8) & 0x0000FF00) | (x<<24)

def align(x, boundary):
	return x + (x % boundary)

class TPL(): #single texture only for now, do we need more?
	class TPLHeader(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.magic = Struct.uint32
			self.ntextures = Struct.uint32
			self.header_size = Struct.uint32
	class TPLTexture(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.header_offset = Struct.uint32
			self.pallete_offset = Struct.uint32
	class TexHeader(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.height = Struct.uint16
			self.width = Struct.uint16
			self.format = Struct.uint32
			self.data_off = Struct.uint32
			self.wrap = Struct.uint32[2]
			self.filter = Struct.uint32[2]
			self.lod_bias = Struct.float
			self.edge_lod = Struct.uint8
			self.min_lod = Struct.uint8
			self.max_lod = Struct.uint8
			self.unpacked = Struct.uint8
	def __init__(self, file):
		self.file = file
	def toTPL(self, outfile, width = 0, height = 0):
		head = self.TPLHeader()
		head.magic = 0x0020AF30
		head.ntextures = 1
		head.header_size = 0x0C
		
		tex = self.TPLTexture()
		tex.header_offset = 0x14
		tex.pallete_offset = 0
		
		img = wx.Image(self.file, wx.BITMAP_TYPE_ANY)
		if(width !=0 and height != 0 and (width != img.GetWidth() or height != img.GetHeight())):
			img.Rescale(width, height)
		w = img.GetWidth()
		h = img.GetHeight()
		
		texhead = self.TexHeader()
		texhead.height = h
		texhead.width = w
		texhead.format = 6
		texhead.data_off = 0x14 + len(texhead) + 8
		texhead.wrap = [0, 0]
		texhead.filter = [1, 1]
		texhead.lod_bias = 0
		texhead.edge_lod = 0
		texhead.min_lod = 0
		texhead.max_lod = 0
		texhead.unpacked = 0
		
		tpldata = self.toRGBA8((w, h), img, img.HasAlpha())
		
		f = open(outfile, "wb")
		f.write(head.pack())
		f.write(tex.pack())
		f.write(texhead.pack())
		f.write(struct.pack(">" + str(align(w, 4) * align(h, 4) * 4) + "B", *tpldata))
		f.close()
		
		open("test.bin", "wb").write(struct.pack(str(align(w, 4) * align(h, 4) * 4) + "B", *tpldata)) #">" + 
	def toRGBA8(self, (w, h), img, alpha):
		out = [0 for i in range(align(w, 4) * align(h, 4) * 4)]
		i = z = 0
		lr = la = lb = lg = [0 for i in range(32)]
		for y in range(0, h, 4):
			for x in range(0, w, 4):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 4):
						if(y1 >= h or x1 >= w):
							lr[z] = lg[z] = lb[z] = la[z] = 0
						else:
							lr[z] = img.GetRed(x1, y1)
							lg[z] = img.GetGreen(x1, y1)
							lb[z] = img.GetBlue(x1, y1)
							if(alpha == True):
								la[z] = img.GetAlpha(x1, y1)
							else:
								la[z] = 255
						z += 1
				
				if(z == 16):
					for iv in range(16):
						out[i] = lr[iv]
						i += 1
						out[i] = la[iv]
						i += 1
					for iv in range(16):
						out[i] = lb[iv]
						i += 1
						out[i] = lg[iv]
						i += 1
					z = 0
		return out
	def toPNG(self, outfile):
		data = open(self.file).read()
		
		header = self.TPLHeader()
		textures = []
		pos = 0
		
		header.unpack(data[pos:pos + len(header)])
		pos += len(header)
		
		for i in range(header.ntextures):
			tmp = self.TPLTexture()
			tmp.unpack(data[pos:pos + len(tmp)])
			textures.append(tmp)
			pos += len(tmp)
		
		for i in range(header.ntextures):
			head = textures[i]
			tex = self.TexHeader()
			tex.unpack(data[head.header_offset:head.header_offset + len(tex)])
			w = tex.width
			h = tex.height
			
			print(tex.format)
		
			if(tex.format == 0): #I4, 4-bit
				tpldata = struct.unpack(">" + str((w * h) / 2) + "B", data[tex.data_off:tex.data_off + ((w * h) / 2)])
				rgbdata = self.I4((w, h), tpldata)
			
			elif(tex.format == 1): #I8, 8-bit
				tpldata = struct.unpack(">" + str(w * h) + "B", data[tex.data_off:tex.data_off + (w * h * 1)])
				rgbdata = self.I8((w, h), tpldata)
			elif(tex.format == 2): #IA4, 8-bit
				tpldata = struct.unpack(">" + str(w * h) + "B", data[tex.data_off:tex.data_off + (w * h * 1)])
				rgbdata = self.IA4((w, h), tpldata)
			
			elif(tex.format == 4): #RGB565, 16-bit
				tpldata = struct.unpack(">" + str(w * h) + "H", data[tex.data_off:tex.data_off + (w * h * 2)])
				rgbdata = self.RGB565((w, h), tpldata)
			elif(tex.format == 5): #RGB5A3, 16-bit
				tpldata = struct.unpack(">" + str(w * h) + "H", data[tex.data_off:tex.data_off + (w * h * 2)])
				rgbdata = self.RGB5A3((w, h), tpldata)
			elif(tex.format == 3): #IA8, 16-bit
				tpldata = struct.unpack(">" + str(w * h) + "H", data[tex.data_off:tex.data_off + (w * h * 2)])
				rgbdata = self.IA8((w, h), tpldata)
			
			elif(tex.format == 6): #RGBA8, 32-bit, but for easyness's sake lets do it with 16-bit
				tpldata = struct.unpack(">" + str(w * h * 2) + "H", data[tex.data_off:tex.data_off + (w * h * 4)])
				rgbdata = self.RGBA8((w, h), tpldata)
				
			else:
				raise TypeError("Unsupported TPL Format: " + str(tex.format))
		
		output = png.Writer(width = w, height = h, alpha = True, bitdepth = 8)
		output.write(open(outfile, "wb"), rgbdata)
	def toScreen(self):		
		class imp(wx.Panel):
			def __init__(self, parent, id, im):
				wx.Panel.__init__(self, parent, id)
				w = im.GetWidth()
				h = im.GetHeight()
				wx.StaticBitmap(self, -1, im, ( ((max(w, 300) - w) / 2), ((max(h, 200) - h) / 2) ), (w, h))

		self.toPNG("tmp.png")
		img = wx.Image("tmp.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
		w = img.GetWidth()
		h = img.GetHeight()
		app = wx.App(redirect = True)
		frame = wx.Frame(None, -1, "TPL (" + str(w) + ", " + str(h) + ")", size = (max(w, 300), max(h, 200)))
		image = imp(frame, -1, img)
		frame.Show(True)
		app.MainLoop()
		os.unlink("tmp.png")
	def RGBA8(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 4):
				for iv in range(2):
					for y1 in range(y, y + 4):
						for x1 in range(x, x + 4):
							if(y1 >= h or x1 >= w):
								continue
							pixel = jar[i]
							i += 1
							
							if(iv == 0):
								r = (pixel >> 0) & 0xFF
								a = (pixel >> 8) & 0xFF
								out[y1][(x1 * 4) + 0] = r
								out[y1][(x1 * 4) + 3] = a
							else:
								g = (pixel >> 8) & 0xFF
								b = (pixel >> 0) & 0xFF
								out[y1][(x1 * 4) + 1] = g
								out[y1][(x1 * 4) + 2] = b
		return out
	def RGB5A3(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 4):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 4):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						if(pixel & (1 << 15)): #RGB555
							r = (((pixel >> 10) & 0x1F) * 255) / 31
							g = (((pixel >> 5) & 0x1F) * 255) / 31
							b = (((pixel >> 0) & 0x1F) * 255) / 31
							a = 255
						else: #RGB4A3
							r = (((pixel >> 8) & 0x0F) * 255) / 15
							g = (((pixel >> 4) & 0x0F) * 255) / 15
							b = (((pixel >> 0) & 0x0F) * 255) / 15
							a = 255 - (((pixel >> 12) & 0x07) * 64) / 7

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
		return out
	def RGB565(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 4):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 4):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						r = ((pixel >> 11) & 0x1F) << 3
						g = ((pixel >> 5) & 0x3F) << 2
						b = ((pixel >> 0) & 0x1F) << 3
						a = 255

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
		return out
	def I4(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 8):
			for x in range(0, w, 8):
				for y1 in range(y, y + 8):
					for x1 in range(x, x + 8, 2):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						
						r = (pixel >> 4) * 255 / 15
						g = (pixel >> 4) * 255 / 15
						b = (pixel >> 4) * 255 / 15
						a = 255

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
						
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						r = (pixel & 0x0F) * 255 / 15
						g = (pixel & 0x0F) * 255 / 15
						b = (pixel & 0x0F) * 255 / 15
						a = 255

						out[y1][((x1 + 1) * 4) + 0] = r
						out[y1][((x1 + 1) * 4) + 1] = g
						out[y1][((x1 + 1) * 4) + 2] = b
						out[y1][((x1 + 1) * 4) + 3] = a
		return out
	def IA4(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 8):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 8):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						r = (pixel & 0x0F) * 255 / 15
						g = (pixel & 0x0F) * 255 / 15
						b = (pixel & 0x0F) * 255 / 15
						a = 255 - ((pixel & 0xFF) * 255 / 15)

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
		return out
	def I8(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 8):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 8):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						r = pixel
						g = pixel
						b = pixel
						a = 255

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
		return out
	def IA8(self, (w, h), jar):
		out = [[0 for i in range(w * 4)] for i in range(h)]
		i = 0
		for y in range(0, h, 4):
			for x in range(0, w, 4):
				for y1 in range(y, y + 4):
					for x1 in range(x, x + 4):
						if(y1 >= h or x1 >= w):
							continue
						pixel = jar[i]
						i += 1
						
						r = pixel >> 8
						g = pixel >> 8
						b = pixel >> 8
						a = 255 - (pixel & 0xFF)

						out[y1][(x1 * 4) + 0] = r
						out[y1][(x1 * 4) + 1] = g
						out[y1][(x1 * 4) + 2] = b
						out[y1][(x1 * 4) + 3] = a
		return out
		
class WAD():
	def __init__(self, f):
		self.f = f
	def unpack(self, fn = ""):
		if(fn != ""):
			subprocess.call(["./wadunpacker", self.f, fn])
			return fn
		else:
			subprocess.call(["./wadunpacker", self.f, os.dirname(self.f) + os.basename(self.f).replace(".", "_") + "_out"])
			return self.f
	def pack(self, fn = "", titleid = ""):
		os.chdir(self.f)	
		for fname in os.listdir("."):
			if fnmatch.fnmatch(fname, '*.tik'):
   				tik = fname
			if fnmatch.fnmatch(fname, '*.tmd'):
   				tmd = fname
			if fnmatch.fnmatch(fname, '*.cert'):
   				cert = fname
   		shutil.copy("../common-key.bin", "common-key.bin")
		if(fn != ""):
			if(titleid == ""):
				subprocess.call(["../wadpacker", tik, tmd, cert, "../" + fn, "-sign"])
			else:
				subprocess.call(["../wadpacker", tik, tmd, cert, "../" + fn, "-sign", "-i", titleid])
		else:
			if(self.f[len(self.f):4] == "_out"):
				outfile = os.dirname(self.f) + os.basename(self.f).replace("_", ".")[len(os.basename(self.f)) - 4:]
			else:
				outfile = self.f + ".wad"

			if(titleid == ""):
				subprocess.call(["../wadpacker", tik, tmd, cert, "../" + outfile, "-sign"])
			else:
				subprocess.call(["../wadpacker", tik, tmd, cert, "../" + outfile, "-sign", "-i", titleid])
		os.unlink("common-key.bin")
		os.chdir("..")
		return self.f
	
class U8():
	class U8Header(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.tag = Struct.string(4)
			self.rootnode_offset = Struct.uint32
			self.header_size = Struct.uint32
			self.data_offset = Struct.uint32
			self.zeroes = Struct.string(16)
	class U8Node(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.type = Struct.uint16
			self.name_offset = Struct.uint16
			self.data_offset = Struct.uint32
			self.size = Struct.uint32
	def __init__(self, f):
		self.f = f
		print f
	def _pack(self, file, recursion, is_root = 0): #internal
		node = self.U8Node()
		node.name_offset = len(self.strings)
		if(is_root != 1):
			self.strings += (file)
			self.strings += ("\x00")
		
		if(os.path.isdir(file)):
			node.type = 0x0100
			self.data_offset = recursion
			recursion += 1
			files = sorted(os.listdir(file))
			if(sorted(files) == ["banner.bin", "icon.bin", "sound.bin"]):
				files = ["icon.bin", "banner.bin", "sound.bin"]
				
			oldsz = len(self.nodes)
			if(is_root != 1):
				self.nodes.append(node)
			
			os.chdir(file)
			for entry in files:
				if(entry != ".DS_Store" and entry[len(entry) - 4:] != "_out"):
					self._pack(entry, recursion)
			os.chdir("..")

			self.nodes[oldsz].size = len(self.nodes) + 1
		else:
			f = open(file, "rb")
			data = f.read()
			f.close()
			sz = len(data)
			while len(data) % 32 != 0:
				data += "\x00"
			self.data += data
			node.data_offset = len(data)
			node.size = sz
			node.type = 0x0000
			if(is_root != 1):
				self.nodes.append(node)
				
	def pack(self, fn = ""):
		header = self.U8Header()
		self.rootnode = self.U8Node()
		
		header.tag = "U\xAA8-"
		header.rootnode_offset = 0x20
		header.zeroes = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		
		self.nodes = []
		self.strings = "\x00"
		self.data = ""
		origdir = os.getcwd()
		os.chdir(self.f)
		self._pack(".", 0, 1)
		os.chdir(origdir)
		
		header.header_size = (len(self.nodes) + 1) * len(self.rootnode) + len(self.strings)
		header.data_offset = align(header.header_size + header.rootnode_offset, 0x40)
		self.rootnode.size = len(self.nodes) + 1
		self.rootnode.type = 0x0100
		
		for node in self.nodes:
			node.data_offset += header.data_offset
			
		if(fn == ""):
			if(self.f[len(self.f) - 4:] == "_out"):
				fn = os.path.dirname(self.f) + "/" + os.path.basename(self.f)[:len(os.path.basename(self.f)) - 4].replace("_", ".")
			else:
				fn = self.f
		print fn
			
		f = open(fn, "wb")
		f.write(header.pack())
		f.write(self.rootnode.pack())
		for node in self.nodes:
			f.write(node.pack())
		f.write(self.strings)
		f.write("\x00" * (header.data_offset - header.rootnode_offset - header.header_size))
		f.write(self.data)
		f.close()
		
		return fn
	def unpack(self, fn = ""):
		data = open(self.f).read()
		
		offset = 0
		
		header = self.U8Header()
		header.unpack(data[offset:len(header)])
		offset += len(header)
		
		if(header.tag != "U\xAA8-"):
			raise NameError("Bad U8 Tag")
		offset = header.rootnode_offset
		
		rootnode = self.U8Node()
		rootnode.unpack(data[offset:offset + len(rootnode)])
		offset += len(rootnode)
		
		nodes = []
		for i in xrange(rootnode.size - 1):
			node = self.U8Node()
			node.unpack(data[offset:offset + len(node)])
			offset += len(node)
			nodes.append(node)
		
		strings = data[offset:offset + header.data_offset - len(header) - (len(rootnode) * rootnode.size)]
		offset += len(strings)
		
		if(fn == ""):
			fn = os.path.dirname(self.f) + "/" + os.path.basename(self.f).replace(".", "_") + "_out"
		try:
			origdir = os.getcwd()
			os.mkdir(fn)
		except:
			pass
		os.chdir(fn)
		
		
		recursion = [rootnode.size]
		counter = 0
		for node in nodes:
			counter += 1
			name = strings[node.name_offset:].split('\0', 1)[0]
			
			if(node.type == 0x0100): #folder
				recursion.append(node.size)
				try:
					os.mkdir(name)
				except:
					pass
				os.chdir(name)
				continue
			elif(node.type == 0): #file
				file = open(name, "wb")
				file.write(data[node.data_offset:node.data_offset + node.size])
				offset += node.size
			else: #unknown
				pass #ignore
				
			sz = recursion.pop()
			if(sz == counter + 1):
				os.chdir("..")
			else:
				recursion.append(sz)
		os.chdir("..")
		
		os.chdir(origdir)
		return fn
		

		
class IMD5():
	class IMD5Header(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.tag = Struct.string(4)
			self.size = Struct.uint32
			self.zeroes = Struct.uint8[8]
			self.hash = Struct.string(16)
	def __init__(self, f):
		self.f = f
		print(f)
	def add(self, fn = ""):
		data = open(self.f, "rb").read()
		
		imd5 = self.IMD5Header()
		for i in range(8):
			imd5.zeroes[i] = 0x00
		imd5.tag = "IMD5"
		imd5.size = len(data)
		imd5.crypto = str(hashlib.md5(data).digest())
		#data = imd5.pack() + data
		
		if(fn != ""):
			open(fn, "wb").write(data)
			return fn
		else:
			open(self.f, "wb").write(data)
			return self.f
	def remove(self, fn = ""):
		data = open(self.f, "rb").read()
		imd5 = self.IMD5Header()
		
		if(data[:4] != "IMD5"):
				if(fn != ""):
					open(fn, "wb").write(data)
					return fn
				else:
					return self.f
		data = data[len(imd5):]
		
		if(fn != ""):
			open(fn, "wb").write(data)
			return fn
		else:
			open(self.f, "wb").write(data)
			return self.f
		
class IMET():
	class IMETHeader(Struct):
		__endian__ = Struct.BE
		def __format__(self):
			self.zeroes = Struct.uint8[64]
			self.tag = Struct.string(4)
			self.unk = Struct.uint64
			self.sizes = Struct.uint32[3] #icon, banner, sound
			self.flag1 = Struct.uint32
			self.names = Struct.string(0x2A << 1, encoding = 'utf-16-be', stripNulls = True)[7]
			self.zeroes2 = Struct.uint8[904]
			self.crypto = Struct.string(16)
	def __init__(self, f):
		self.f = f
	def add(self, iconsz, bannersz, soundsz, name = ">_>", fn = ""): #mode is add or remove
		data = open(self.f, "rb").read()
		imet = self.IMETHeader()
		
		for i in imet.zeroes:
			imet.zeroes[i] = 0x00
		imet.tag = "IMET"
		imet.unk = 0x0000060000000003
		imet.sizes[0] = iconsz
		imet.sizes[1] = bannersz
		imet.sizes[2] = soundsz
		for i in range(0, len(imet.names)):
			imet.names[i] = name
		for i in imet.zeroes2:
			imet.zeroes2[i] = 0x00
		imet.crypto = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		imet.crypto = str(hashlib.md5(imet.pack()[0x40:0x600]).digest())
		data = imet.pack() + data
		
		if(fn != ""):
			open(fn, "wb").write(data)
			return fn
		else:
			open(self.f, "wb").write(data)
			return self.f
		
	def remove(self, fn = ""):
		data = open(self.f, "rb").read()
		if(data[0x80:0x84] == "IMET"):
			data = data[0x640:]
		elif(data[0x40:0x44] == "IMET"):
			data = data[0x640:]
		else:
			if(fn != ""):
				open(fn, "wb").write(data)
				return fn
			else:
				return self.f
		if(fn != ""):
			open(fn, "wb").write(data)
			return fn
		else:
			open(self.f, "wb").write(data)
			return self.f
	
	
class LZ77():
	class WiiLZ77:
		TYPE_LZ77 = 1
		def __init__(self, file, offset):
			self.file = file
			self.offset = offset
 
			self.file.seek(self.offset)
 
			hdr = struct.unpack("<I",self.file.read(4))[0]
			self.uncompressed_length = hdr>>8
			self.compression_type = hdr>>4 & 0xF
 
			if self.compression_type != self.TYPE_LZ77:
				raise ValueError("Unsupported compression method %d"%self.compression_type)
 
		def uncompress(self):
			dout = ""
 
			self.file.seek(self.offset + 0x4)
 
			while len(dout) < self.uncompressed_length:
				flags = struct.unpack("<B",self.file.read(1))[0]
 
				for i in range(8):
					if flags & 0x80:
						info = struct.unpack(">H",self.file.read(2))[0]
						num = 3 + ((info>>12)&0xF)
						disp = info & 0xFFF
						ptr = len(dout) - (info & 0xFFF) - 1
						for i in range(num):
							dout += dout[ptr]
							ptr+=1
							if len(dout) >= self.uncompressed_length:
								break
					else:
						dout += self.file.read(1)
					flags <<= 1
					if len(dout) >= self.uncompressed_length:
						break
			self.data = dout
			return self.data

	def __init__(self, f):
		self.f = f
	def remove(self, fn = ""):
		file = open(self.f, "rb")
 		hdr = file.read(4)
 		if hdr != "LZ77":
 			if(fn == ""):
				return self.f
			else:
				data = open(self.f, "rb").read()
				open(fn, "wb").write(data)
		unc = self.WiiLZ77(file, file.tell())
		data = unc.uncompress()
		file.close()
		
		if(fn != ""):
			open(fn, "wb").write(data)
			return fn
		else:
			open(self.f, "wb").write(data)
			return self.f
	def add(self, fn = ""):
		if(fn != ""):
			#subprocess.call(["./gbalzss", self.f, fn, "-pack"])
			return fn
		else:
			#subprocess.call(["./gbalzss", self.f, self.f, "-pack"])
			return self.f

	
