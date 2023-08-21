from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import xml.etree.ElementTree as ElementTree
from pathlib import Path
import pysubs2
import glob


OUT_FORMAT = 'ass' # ass or srt

def load_xml(xml):
    if not isinstance(xml, bytes):
        xml = xml.encode('utf-8')
    root = ElementTree.fromstring(xml)
    return root


def decrypt_capt(key, iv, data_b64):
    data = b64decode(data_b64)
    key = key.encode()
    iv = iv.encode()
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    pt = unpad(cipher.decrypt(data), AES.block_size)
    return pt.decode()


def XMLtoASS(document, key, iv):
    root = load_xml(document)
    height = root.find('note').attrib['height']
    width = root.find('note').attrib['width']
    
    dia_list = root.findall('dia')
    subs = pysubs2.SSAFile()
    subs.styles = {}
    styleMap = {}
    
    subs.info['PlayResY'] = height
    subs.info['PlayResX'] = width
    subs.info['YCbCr Matrix'] = 'TV.709'

    for num, dia in enumerate(dia_list):
        start = dia.findtext('st').split(':')
        end = dia.findtext('et').split(':')
        capt = dia.findtext('con')
        capt_dec = decrypt_capt(key, iv, capt)

        style = dia.find('style')

        font = style.find('font')
        color = style.find('color')
        scale = style.find('scale')
        border = style.find('border')
        position = style.find('position')

        if ElementTree.tostring(style) in styleMap:
            styleName = styleMap[ElementTree.tostring(style)]
        else:
            assStyle = pysubs2.SSAStyle(fontname=font.attrib['name'], fontsize=float(font.attrib['size']), bold=font.attrib['bold'] == 1,
                                        italic=font.attrib['italic'] == 1, underline=font.attrib['underline'] == 1, strikeout=font.attrib['strikeout'] == 1, spacing=float(font.attrib['spacing']), angle=float(font.attrib['angle']),
                                        scalex=float(scale.attrib['x']), scaley=float(scale.attrib['y']), primarycolor=color.attrib['primary'], secondarycolor=color.attrib['secondary'], outlinecolor=color.attrib['outline'], backcolor=color.attrib['back'],
                                        borderstyle=border.attrib['style'], outline=float(border.attrib['outline']), shadow=float(border.attrib['shadow']),
                                        alignment=int(position.attrib['alignment']), marginl=int(position.attrib['ml']), marginr=int(position.attrib['mr']), marginv=int(position.attrib['mv']))
            styleName = 'Style' + str(len(styleMap))
            subs.styles[styleName] = assStyle
            styleMap[ElementTree.tostring(style)] = styleName

        startTime = pysubs2.make_time(h=int(start[0]), m=int(start[1]), s=int(
            start[2].split('.')[0]), ms=10*int(start[2].split('.')[1]))
        endTime = pysubs2.make_time(h=int(end[0]), m=int(end[1]), s=int(
            end[2].split('.')[0]), ms=10*int(end[2].split('.')[1]))
        assLine = pysubs2.SSAEvent(
            start=startTime, end=endTime, text=capt_dec, style=styleName)
        subs.insert(0, assLine)

    subs.sort()
    return subs.to_string(OUT_FORMAT)


def processFile(filename):
    id, keyiv, lang = Path(filename).stem.split('_')
    key = keyiv[:16]
    iv = keyiv[16:]
    with open(filename, 'r', encoding='utf-8') as f:
        document = f.read()
    ass = XMLtoASS(document, key, iv)
    filename = str(Path(filename).parent) + f'/{id}_{lang}.{OUT_FORMAT}'
    print(filename)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(ass)

if __name__ == "__main__":
    for file in glob.glob('*.xml'):
        processFile(file)
