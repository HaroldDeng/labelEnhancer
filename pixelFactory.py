import math
import random
from shapely.geometry import Polygon, LineString, Point, box
import copy
import re
import numpy
from PIL import Image
from PIL import ImageDraw
from typing import Union
from typing import List
from typing import Dict
from typing import Tuple

class PixelUtil:
    def __init__(arg):
        pass
    def getBound(self, mk) -> ():
        """
        return minimum bounding region, left and up use flooring function,
        bottom and right use ceilling function

        Parameter
        ---------
        mk:
            one or a iterable of markings
        """
        if isinstance(mk, dict):
            mk = [mk]
        pts = []
        for item in mk:
            if item['type'] == 'point':
                pts.append(item['param'])
            elif item['type'] == 'line' or item['type'] == 'polygon':
                pts.extend(item['param'])
            elif item['type'] == 'ellipse':
                # ellipse's x = a*cos(t)
                # ellipse's y = b*cos(t)
                x_shf, y_shf = item['param'][0]
                a, b = item['param'][1]
                pts.append(numpy.array([x_shf + a, y_shf])) # right
                pts.append(numpy.array([x_shf, y_shf + b])) # top
                pts.append(numpy.array([x_shf - a, y_shf])) # left
                pts.append(numpy.array([x_shf, y_shf - b])) # bottom
            else:
                # ignore
                pass

        pts = numpy.array(pts)
        x_min, y_min = numpy.floor(numpy.min(pts, axis=(0))).astype(numpy.int)
        x_max, y_max = numpy.ceil(numpy.max(pts, axis=(0))).astype(numpy.int)
        return (x_min, y_min, x_max, y_max)


class PixelAlgo:
    def __init__(self, _u:PixelUtil):
        self._2DRTM = lambda theta, x, y, dx, dy: (
            (x - dx) * math.cos(theta) + (y - dy) * math.sin(theta) + dx,
            (y - dy) * math.cos(theta) - (x - dx) * math.sin(theta) + dy,
        )
        self._util = _u

    def rotate(self, px: Image, mk, degree: float, expand=True) -> ():
        """
        Parameter
        ---------
        mk
            a list of markings
        """
        if expand:
            # expand img, make sure img does not suffer losses after
            # rotates
            x_min, y_min, x_max, y_max = self._util.getBound(mk)
            side = math.ceil(math.sqrt((x_max - x_min) ** 2 + (y_max - y_min) ** 2))
            shf = numpy.array([(side - x_max + x_min) >> 1, (side - y_max + y_min) >> 1])
            px2 = Image.new("RGBA", (side, side), color=(0, 0, 0, 0))
            px2.paste(px, box=(shf[0], shf[1]))

            # rotate image and markings
            px = px2.rotate(degree)
            r = math.radians(degree)
            c, s = math.cos(r), math.sin(r)
            rtm2D = numpy.array([[c, -s], [s, c]])
            mk = copy.deepcopy(mk)

            # shfit from center of the image to (0, 0), then
            # use rotational matrix
            shf2 = numpy.array([side // 2, side // 2])
            for item in mk:
                item['param'] = numpy.dot(item['param'] + shf - shf2, rtm2D) + shf2
            bound = self._util.getBound(mk)

            # remove extra paddings
            px = px.crop(bound)
            shf[0], shf[1] = bound[0], bound[1]
            for item in mk:
                item['param'] -= shf
            return (px, mk)
        else:
            raise Exception("Not implemented")

    def noise(self, px: Image, snr: float, n_type='bw') -> Image:
        """
        """
        if n_type == 'bw':
            px = numpy.array(px)
            ms = numpy.random.choice([0, 1, 2], size=(px.shape[0], px.shape[1]),
                p=[(1 - snr)/2.0, (1 - snr)/2.0, snr])
            r, g, b = px[:,:,0], px[:,:,1], px[:,:,2]
            r[ms == 0] = 0; r[ms == 1] = 255
            g[ms == 0] = 0; g[ms == 1] = 255
            b[ms == 0] = 0; b[ms == 1] = 255

        img = Image.fromarray(px)
        return img

class PixelFactory:
    def __init__(self):
        """
        https://blog.csdn.net/maitianpt/article/details/84983599
        """
        self.supportedType = ['point', 'line', 'polygon', 'ellipse']
        self._patt = None  # patterm to split marked objects
        self._algo = None  # pixel processor
        self._util = PixelUtil() # utility class

    def rotate(self, px: Image, mk, degree: float, expand=True) -> ():
        """
        roate image

        Parameter
        ---------
        shapes:
            a group of markings
        expand:
            if true, will make sure object will not suffer losses on edge
        """
        if not self._algo:
            self._algo = PixelAlgo(self._util)
        if isinstance(mk, dict):
            return self._algo.rotate(px, [mk], degree, expand)
        else:
            return self._algo.rotate(px, mk, degree, expand)

    def noise(self, px: Image, snr: float, n_type='bw') -> Image:
        """
        add noise to the image. Return a copy of img with noise

        Parameter
        ---------
        snr:
            signal-noise ratio, float between 0 and 1
        n_type:
            type of noise
            `bw`, black and white aka. salt & pepper
        """
        if not self._algo:
            self._algo = PixelAlgo(self._util)
        return self._algo.noise(px, snr, n_type)

    def pasteRegion(self, bg: Image.Image, bgMk: List[Dict],
        fg: Image.Image, fgMk: List[Dict], pos: Tuple) -> Tuple:
        """
        paste `fg` images in `bg` at `pos` with given mode
        Return one or a iterable of tules contains final image and markings

        Parameter
        ---------
        bg
            background, PIL Image in RGBA mode
        bgMk
            background markings
        fg
            foreground, PIL Image in RGBA mode
        fgMk
            foreground markings
        pos
            a tulpes of corrdinate
        """
        resPx = copy.copy(bg)
        resMk = None
        resPx.paste(fg, pos, fg.getchannel(3))
        resPa = fgMk.copy() + numpy.asarray(pos)

        if bgMk is None:
            resMk = []
        else:
            resMk = []
            fgPol = Polygon(resPa)
            i = 0
            while i < len(bgMk):
                bgPol = Polygon(bgMk[i]['param'])
                if fgPol.disjoin(bgPol) or fgPol.touches(bgPol):
                    # completely isolate or outer_cut
                    i += 1
                    continue
                for geo in bgPol.difference(fgPol):
                    pass


        resMk.append({"param": resPa, "shape": "polygon"})


    def copyRegion(self, px: Image, mk) -> []:
        """
        return a tuple contains cuted image, and final markings.

        Parameter
        ---------
        px
            a PIL image in RGBA mode
        mk
            one or a list of markings
        """
        final_mk = copy.deepcopy(mk)
        if isinstance(mk, dict):
            px, shf = self._copy(px, [mk])
            final_mk['param'] -= shf
        else:
            px, shf = self._copy(px, mk)
            for tmp in final_mk:
                tmp['param'] -= shf
        return (px, final_mk)

    def parseToCsts(self, mk, imgSize) -> ():
        """
        return a list of constrains in the format of
        [[Polygon(), ], [LineString(), ], [Point()], Polygon()]
        the last polygon object is the bounding box of image
        Parameter
        ---------
        mk:
            markings, accept a map, a list of map, a list of list of map
        """
        assert isinstance(imgSize, tuple), "Image size should be a tuple"
        if isinstance(mk, dict):
            mk = [mk]
        csts = [[], [], []]
        for item in mk:
            if isinstance(item, dict):
                item = [item]
            for sub in item:
                if sub['type'] == 'polygon':
                    csts[0].append(Polygon(sub['param']))
                elif sub['type'] == 'line':
                    csts[1].append(LineString(sub['param']))
                elif sub['type'] == 'point':
                    csts[2].append(Point(sub['param']))
                elif sub['type'] == 'ellipse':
                    # TODO: for furture use
                    raise Exception("Not implemented")
        fram = box(imgSize[0], imgSize[1], imgSize[2], imgSize[3])

        return (csts[0], csts[1], csts[2], fram)

    def constrainsCheck(
        self, mk: dict, csts, imgSize=None, overlap=0.0, within=1.0
    ) -> bool:
        """
        check if new shape matches constrains.
        return true if it pass the check, false otherwise

        Parameter
        ---------
        mk:
            marking
        csts:
            points of constrains or a list of iteratable of predefine shapely object
            [numpy.ndarray, ] or [[Polygon(), ], [LineString(), ], [Point(), ], Polygon()]
            the last object in predefine shapely is boundary of image
        imgSize:
            size of the image. It will be omited if `csts` is a list of iteratable of
            predefine shapely object
        overlap:
            percentage of area that `csts` will be cover by `pts`, float between 0 and 1
        within:
            percentage of area that `pts will be inside the image, float between 0 and 1

        """
        poly, line, poin, fram = None, None, None, None
        if type(csts[-1]) is Polygon:
            poly, line, poin, fram = csts[0], csts[1], csts[2], csts[3]
        else:
            poly, line, poin, fram = self.parseToCsts(csts, imgSize)

        if mk['type'] == 'polygon':
            new = Polygon(mk['param'])
            return not (
                # check polygon-polygon intersection
                any(filter(lambda pol: pol.intersection(
                    new).area > (pol.area * overlap), poly))
                # check polygon-line intersection
                or any(filter(lambda lin: lin.intersection(new).length > (lin.length * overlap), line))
                # check polygon-point intersection
                or any(filter(lambda poi: poi.intersects(new) and (not overlap), poin))
                # check out of frameS
                or fram.intersection(new).area < (within * new.area)
            )

        elif mk['type'] == 'line':
            new = LineString(pts)
            return not (
                # check line-ploygon intersection
                any(filter(lambda pol: pol.intersection(
                    new).length > pol.length * overlap, poly))
                # check line-line intersection
                or any(filter(lambda lin: lin.intersects(new) and (not overlap), line))
                # check line-point intersection
                or any(filter(lambda poi: poi.intersects(new) and (not overlap), poin))
                or fram.intersects(new).length < within * new.length
            )

        elif mk['type'] == 'point':
            new = Point(pts[0])
            return not (
                # check point-ploygon intersection
                any(filter(lambda pol: pol.intersects(new) and (not overlap), poly))
                # check point-line intersection
                or any(filter(lambda lin: lin.intersects(new) and (not overlap), line))
                # check point-point intersection
                or any(filter(lambda poi: poi.intersects(new) and (not overlap), poin))
                or (fram.intersects(new) and (not within))
                # ??? NOT ALLOW keypoint out of frame
            )
        else:
            raise Exception('Not implemented')

    def constrainsPlace(
        self, pts: [], csts, imgSize=None, overlap=0.0, within=1.0
    ) -> []:
        raise Exception("Not implemented")
        """
        place new shape according to constrains
        Note, this function does not repeat functionality of `constrainsCheck()`

        Parameters detail see `constrainsCheck()`
        """
        if len(pts) <= 2:
            # ???
            return

        poly, line, poin, fram = None, None, None, None
        if type(csts[-1]) is Polygon:
            poly, line, poin, fram = csts[0], csts[1], csts[2], csts[3]
        else:
            poly, line, poin, fram = self.parseToCsts(csts, imgSize)

        new = Polygon(pts)
        if any(map(lambda pol: pol.intersection(new).area == min(pol.area, new.area), poly)):
            raise Warning("An polygon completely within another polygon is unsupported")
        else:
            i = 0
            while i < len(poly):
                diff = poly[i].difference(new)
                print(diff)

    def paramCheck(self, px, mk) -> bool:
        """
        validate if image and markings meets PixelFactory's requirements
        """
        pxVaild = False
        mkVaild = False
        # image check
        if not isinstance(px, Image.Image):
            print('Warnning: image should be a PIL image')
        elif px.mode != 'RGBA':
            print('Warnning: image should be in RGBA mode')
        else:
            pxVaild = True

        # marking check
        if not isinstance(mk, list):
            mk = [dict]
        if any(map(lambda sub: not isinstance(sub, dict), mk)):
            print('Warnning: makrings should be a dict or a list of dicts')
        elif any(map(lambda sub: sub.get('type') == None or sub.get('param') == None, mk)):
            print('Warnning: markings should constain both keys \'type\' and \'param\'')
        elif any(map(lambda sub: not isinstance(sub['param'], numpy.ndarray), mk)):
            print('Warnning: markings\' keys \'param\' should accept numpy arrays')
        elif any(map(lambda sub: not sub['type'] in self.supportedType, mk)):
            print('Warnning: markings type not supported')
        else:
            mkVaild = True

        return pxVaild and mkVaild

    def _copy(self, px: Image, mk) -> []:
        """
        copy the region that bounded by `pts`
        return a tulpe contains carved region, and shifted pixel

        Parameter
        ---------
        px:
            an PIL image
        mk:
            makrings, should be a iterable of dicts
        """
        # find the boundary of cut region
        x_min, y_min, x_max, y_max = self._util.getBound(mk)
        # point and line don't have any area
        tmp = filter(lambda tmp: tmp["type"] in self.supportedType[2:] , mk)
        assert tmp, "Such shape is not unsupported for copy"

        px = px.crop((x_min, y_min, x_max, y_max))
        shf = numpy.array([x_min, y_min])
        return (px, shf)


    def masking(self, px: Image, gp: list, alpha=0):
        """
            create mask from pts, pixels' alpha bound by points is set to
            `alpha`, otherwise set to 255

            Parameter
            ---------
            gp
                group of markings of px
            alpha
                tansparency of pixel that outside of mask region,
                range from 0 to 255 inclusively
        """
        # create a blank mask in L mode, then draw the polygon according to
        # points, pixel within or along the polygon is visable
        mask = Image.new("L", px.size, color=alpha)
        for mk in gp:
            if mk['type'] in self.supportedType[: 2]:
                continue
            ImageDraw.Draw(mask).polygon(mk['param'].flatten().tolist(), outline=255, fill=255)

        # get indidual channel, merge then together
        r, g, b, _ = px.split()
        a = mask.getchannel(0)  # similar to .split()
        return Image.merge("RGBA", [r, g, b, a])
