from pixelFactory import PixelFactory
import base64
import json
import os
import shutil
import io
import re
import random
import numpy
import copy

from PIL import Image, ExifTags

class LabelMeHandler:
    def __init__(self, path: str):
        """
        Parameter
        ---------
        path
            path to the source folder
        """
        self.fName = {}
        self.srcDir = path
        self._curF = ""
        self._px = None
        self._mk = None

        assert os.path.exists(path), 'Path {} not exist'.format(path)

    def loadData(self, pxExt: [], mkExt: []):
        """
            generator operation
            read file data from self.fName

            Usage
            -----
                for _ in loadData():
                    px, mk = retrive()
        """
        not_import = self._fileExt(pxExt, mkExt)
        print('File that will be omitted', not_import)
        for name in self.fName:
            self._px = Image.open(os.path.join(self.srcDir, "{}.{}".format(name, self.fName[name][0])))
            self._mk = open(
                os.path.join(self.srcDir, "{}.{}".format(name, self.fName[name][1])), 'rb'
            ).read()
            self._mk = json.loads(self._mk)
            self._pcsBforUse()
            self._curF = name

            yield (self._px, self._mk)

    def dumpImage(self, name=None, pxExt='jpg', path=None):
        """
        if `path` is None, use sorce director which the file is read
        if `name` is None, use original file name
        """

        if path is None:
            path = self.srcDir
        if name is None:
            name = self._curF
        if pxExt == 'jpg':
            path = '{}.{}'.format(os.path.join(path, name), pxExt)
            self._px.convert('RGB').save(path)
        else:
            raise Exception('Not implemented')

    def dumpMarking(self, name=None, mkExt='json', path=None):
        if path is None:
            path = self.srcDir
        if name is None:
            name = self._curF

        path = "{}.{}".format(os.path.join(path, name), mkExt)
        mk = copy.deepcopy(self._mk)
        if mkExt == 'json':
            self._pcsBforDump_json()
            with open(path, "w+") as f:
                json.dump(mk, f, indent=2)
        elif mkExt == 'csv':
            # self
            ret = self._pcsBforDump_scv(mk)
            import csv
            with open(path, 'a+', newline='') as f:
                wr = csv.writer(f)
                wr.writerows(ret)

    def update(self, px: Image, mk: [], path=None):
        '''
        add new shape to Shapes, and update image

        Parameter
        ---------
        px
            a PIL image
        path
            path to folder. If is None, keep original data
        '''

        self._px = px
        self._mk['shapes'].extend(mk)
        if path is not None:
            self._mk['imagePath'] = path

        # save image data
        # https://www.jianshu.com/p/2ff8e6f98257
        buf = io.BytesIO()
        self._px.convert('RGB').save(buf, format='JPEG')  # save as byte data
        self._mk['imageData'] = base64.b64encode(buf.getvalue()).decode('ascii')
        self._mk['imageHeight'] = self._px.size[1]
        self._mk['imageWidth'] = self._px.size[0]

    def retrive(self, imgMode='RGBA', rgxMode='tail_num') -> []:
        '''
        return a tuple. A image with given mode, and list of grouped makrings

        Parameter
        ---------
        rexMode
            regular expression string
            `tail_num`, group them according to a non-negative integer at the end of label
            `label`, group them according to string
        '''
        regex = ''
        lb_map = {}
        gp = []
        if rgxMode == None:
            gp = self._mk['shapes']
        elif rgxMode == 'tail_num':
            pat = re.compile(r'\d*$') # digit string in the end
            for sh in self._mk['shapes']:
                # parse integer in tail
                tmp = pat.search(sh['label']).group()
                lb_map.setdefault(tmp, []).append(sh)
            gp = list(lb_map.values())
        elif rgxMode == 'label':
            for sh in self._mk['shapes']:
                lb_map.setdefault(sh['label'], []).append(sh)
            gp = list(lb_map.values())
        else:
            raise Exception('Not implemented')

        if self._px.mode == imgMode:
            return (self._px, gp)
        else:
            return (self._px.convert(imgMode), gp)

    def _pcsBforUse(self):
        try:
            # in case auto rotate
            for k, v in  ExifTags.TAGS.items():
                if v == 'Orientation':
                    exif = self._px._getexif()
                    if exif[k] == 8:
                        self._px = self._px.rotate(90, expand=True)
                    elif exif[k] == 3:
                        self._px = self._px.rotate(180, expand=True)
                    elif exif[k] == 6:
                        self._px = self._px.rotate(270, expand=True)
        except Exception:
            pass
        self._px = self._px.convert('RGBA')

        for item in self._mk['shapes']:
            item['param'] = numpy.array(item.pop('points'))
            item['type'] = item.pop('shape_type')
            if len(item['param']) == 2:
                item['type'] = 'line'
            elif len(item['param']) < 2:
                item['type'] = 'point'
                item['param'] = item['param'][0]

    def _pcsBforDump_json(self, mk):
        # reverse of _pcsBforUse()
        for item in mk['shapes']:
            item['points'] = item.pop('param').tolist()
            if item['type'] == 'point':
                item['points'] = [item['points']]
            item['shape_type'] = 'polygon'
            item.pop('type')

    def _pcsBforDump_scv(self, mk):
        ret = []
        for item in mk['shapes']:
            sub = [self._curF]
            sub.append(item['type'])
            if item['type'] == 'point':
                sub.append(item['param'][0])
                sub.append(item['param'][1])
            else:
                for pt in item['param']:
                    sub.append(pt[0])
                    sub.append(pt[1])
            ret.append(sub)
        return ret

    def _fileExt(self, pxExt: [], mkExt: []):
        """
        file name will load to self.fName. Return file name that will
        not be imported
        """
        pxExt = list(map(lambda x: x.upper(), pxExt))
        mkExt = list(map(lambda x: x.upper(), mkExt))

        not_import = []  # file that will not be import
        for item in os.listdir(self.srcDir):
            items = item.split(".")
            if len(items) < 2:
                continue
            elif self.fName.get(items[0]) is None:
                self.fName[items[0]] = [None, None]

            if items[1].upper() in pxExt:
                self.fName[items[0]][0] = items[1]
            elif items[1].upper() in mkExt:
                self.fName[items[0]][1] = items[1]
            else:
                self.fName.pop(items[0])
                not_import.append(item)

        # validation check
        for item in list(self.fName.items()):
            if item[1][0] is None:
                self.fName.pop(item[0])
                not_import.append("{}.{}".format(item[0], item[1][1]))
            elif item[1][1] is None:
                self.fName.pop(item[0])
                not_import.append("{}.{}".format(item[0], item[1][0]))

        return not_import

if __name__ == '__main__':
    # create a tmp folder, or empty it
    # use to keep tmp files or data
    if os.path.exists('tmp'):
        shutil.rmtree('tmp')
    os.mkdir('tmp')

    lmh = LabelMeHandler('E:\imageEnhancer\imgs')
    pixFac = PixelFactory()

    for _ in lmh.loadData(['jpg'], ['json']):
        px, mk = lmh.retrive(imgMode='RGBA', rgxMode='label')
        print(mk)
        exit()
        carvReg = []  # a list of carved regions
        for gp in mk:
            if len(gp) == 0:
                continue
            px_car, gp_car = pixFac.copyRegion(px, gp)
            px_car = pixFac.masking(px_car, gp_car, 0)
            carvReg.append((px_car, gp_car))

        for px_car, mk_car in carvReg:
            px_car = pixFac.noise(px_car, random.random())
            px_car, mk_car = pixFac.rotate(px_car, mk_car, random.random() * 360)

            pixFac.pasteRegion(px, mk, px_car, mk_car, (100, 100), (1, ))
            if tmp is not None:
                lmh.update(tmp[0], tmp[1])
                px, mk = lmh.retrive(imgMode='RGBA', rgxMode='label')

        lmh.dumpMarking(path='./tmp', mkExt='jpg')
        lmh.dumpImage(path='./tmp')
