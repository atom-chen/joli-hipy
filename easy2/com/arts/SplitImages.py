# -*- coding: utf-8 -*-
# @Time    : 2019/5/20 5:21 PM
# @Author  : Joli
# @Email   : 99755349@qq.com

import biplist
from PIL import Image
import os

# 拆分图片-TexturePacker
from jonlin.utils import FS

def tp(plistpath, imagepath=None, outputdir=None, fixwhite=True):
    print(plistpath)
    if imagepath is None:
        imagepath = plistpath.replace('.plist', '.png')
    if not os.path.isfile(imagepath):
        return
    try:
        plist = biplist.readPlist(plistpath)
        if 'frames' not in plist:
            return
    except:
        return

    if outputdir is None:
        outputdir = plistpath.replace('.plist', '_images')
    if not os.path.isdir(outputdir):  # 如果不存在该目录
        os.makedirs(outputdir)  # 新建一个目录

    src_img = Image.open(imagepath)  # 打开图像
    for k, v in plist['frames'].items():
        if 'frame' not in v:
            return
        if not k.endswith('.png'):
            continue
        frame = str(v['frame']).replace('{', '').replace('}', '').split(',')
        w = int(frame[3] if v['rotated'] else frame[2])
        h = int(frame[2] if v['rotated'] else frame[3])
        rect = (int(frame[0]), int(frame[1]), int(frame[0]) + w, int(frame[1]) + h)
        cell_img = src_img.crop(rect)
        if not cell_img:
            continue
        if v['rotated']:
            # box_img = box_img.rotate(90)
            cell_img = cell_img.transpose(Image.ROTATE_90)
        outfile = os.path.join(outputdir, k)
        if fixwhite:
            frame = str(v['sourceSize']).replace('{', '').replace('}', '').split(',')
            w, h = int(frame[0]), int(frame[1])
            frame = str(v['sourceColorRect']).replace('{', '').replace('}', '').split(',')
            x, y = int(frame[0]), int(frame[1])
            rect = (x, y, x + cell_img.width, y + cell_img.height)
            item_img = Image.new('RGBA', size=(w, h))
            item_img.paste(cell_img, rect)
            item_img.save(outfile)
        else:
            cell_img.save(outfile)
    # print('split texturepacker images done', plistpath)

# 拆分图片-spine
def spine(atlaspath, imagepath=None, outputdir=None, fixwhite=True):
    with open(atlaspath, 'r') as fp:
        atlases, atlas, header, frames, frame = [], None, None, None, None
        for line in fp.readlines():
            if line.isspace():
                header, frames = {}, []
                atlas = {'header': header, 'frames': frames}
                atlases.append(atlas)
                continue
            line = ''.join(line.split())  # 去除空格
            if not line:
                continue
            pos = line.find(':')
            if header is not None:
                if -1 == pos:
                    header['image'] = line
                else:
                    pos += 1
                    if line.startswith('size'):
                        header['size'] = tuple([int(x) for x in line[pos:].split(',')])
                    elif line.startswith('format'):
                        header['format'] = line[pos:]
                    elif line.startswith('filter'):
                        header['filter'] = tuple([x for x in line[pos:].split(',')])
                    elif line.startswith('repeat'):
                        header['repeat'] = line[pos:]
                        header = None
            else:
                if -1 == pos:
                    frame = {'name': line}
                    frames.append(frame)
                else:
                    pos += 1
                    if line.startswith('rotate'):
                        frame['rotate'] = False if line[pos:] == 'false' else True
                    elif line.startswith('xy'):
                        frame['xy'] = tuple([int(x) for x in line[pos:].split(',')])
                    elif line.startswith('size'):
                        frame['size'] = tuple([int(x) for x in line[pos:].split(',')])
                    elif line.startswith('orig'):
                        frame['orig'] = tuple([int(x) for x in line[pos:].split(',')])
                    elif line.startswith('offset'):
                        frame['offset'] = tuple([int(x) for x in line[pos:].split(',')])
                    elif line.startswith('index'):
                        frame['index'] = int(line[pos:])
    for atlas in atlases:
        if not atlas['frames']:
            continue
        image_name = atlas['header']['image']
        atlas_dir = os.path.dirname(atlaspath)
        if imagepath is None:
            imagepath = os.path.join(atlas_dir, image_name)
        if not os.path.isfile(imagepath):
            continue
        if outputdir is None:
            outputdir = os.path.join(atlas_dir, FS.filename(image_name) + '_images')
        image = Image.open(imagepath)
        for frame in atlas['frames']:
            if 'xy' not in frame:
                continue
            x, y = frame['xy']
            w, h = frame['size']
            if frame['rotate']:
                w, h = h, w
            rect = (x, y, x + w, y + h)
            item_img = image.crop(rect)
            if frame['rotate']:
                # item_img = item_img.rotate(270)
                item_img = item_img.transpose(Image.ROTATE_270)
            if fixwhite:
                x, y = frame['offset']
                y = frame['orig'][1] - y - item_img.size[1]
                rect = (x, y, x+item_img.size[0], y+item_img.size[1])
                item_box = Image.new('RGBA', size=frame['orig'])
                item_box.paste(item_img, rect)
                item_img = item_box
            item_path = os.path.join(outputdir, frame['name'] + '.png')
            FS.make_parent(item_path)
            item_img.save(item_path)
    # print('split spine images done')

# 拆分图片-layask
def laya_sk(skpath, imagepath=None, outputdir=None):
    from jonlin.utils import Bit
    with open(skpath, 'rb') as fp:
        ba = Bit.ByteArray().init_buffer(fp.read())
        ani_version = ba.read_utf8()
        ani_classname = ba.read_utf8()
        ani_names = ba.read_utf8()
        ani_count = ba.read_u8()
        pub_data_pos = ba.read_u32()
        ext_data_pos = ba.read_u32()
        # print(pub_data_pos, ext_data_pos)
        ba.set_position(ext_data_pos)
        ext_buffer = ba.read_bytes(ba.get_available())
        ba = Bit.ByteArray().init_buffer(ext_buffer)
        tex_count = ba.read_int()
        tex_array = ba.read_utf8().split('\n')
        tex_books = {}
        tex_frames = []
        for i in range(tex_count):
            tex_name = tex_array[i * 2 + 1]
            tex_books[tex_name] = tex_array[i * 2]
            x = ba.read_float()
            y = ba.read_float()
            w = ba.read_float()
            h = ba.read_float()
            fx = ba.read_float()
            fy = ba.read_float()
            fw = ba.read_float()
            fh = ba.read_float()
            # print(tex_name, x, y, w, h, fx, fy, fw, fh)
            tex_frames.append((tex_name, x, y, w, h, fx, fy, fw, fh))
        # crop images
        atlas_root = os.path.dirname(skpath)
        if outputdir is None:
            imagesdir = os.path.join(atlas_root, FS.filename(skpath) + '_images')
        else:
            imagesdir = outputdir
        # if not os.path.isdir(imagesdir):
        #     os.makedirs(imagesdir)
        image_map = {}
        for src in set(tex_books.values()):
            image_map[src] = Image.open(os.path.join(atlas_root, src))
        for frame in tex_frames:
            tex_name = frame[0]
            x = frame[1]
            y = frame[2]
            w = frame[3]
            h = frame[4]
            rect = (x, y, x + w, y + h)
            image = image_map[tex_books[tex_name]]
            item_img = image.crop(rect)
            item_src = os.path.join(imagesdir, tex_name + '.png')
            FS.make_parent(item_src)
            item_img.save(item_src)

# 拆分图片-atlas
def laya_atlas():
    pass