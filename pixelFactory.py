import math
import random
import copy
import numpy
from shapely.geometry import Polygon, LineString, Point, box, MultiPolygon
from PIL import Image, ImageDraw
from typing import Union, List, Dict, Tuple, Any

class PixelAlgo:
    def __init__(self):
        self._2DRTM = lambda theta, x, y, dx, dy: (
            (x - dx) * math.cos(theta) + (y - dy) * math.sin(theta) + dx,
            (y - dy) * math.cos(theta) - (x - dx) * math.sin(theta) + dy,
        )

    def rotate(self, px: Image.Image, mk: Dict, degree: float, expand=True) -> Tuple:
        """
        Parameter
        ---------
        mk
            a list of markings
        """
        if expand:
            # expand img, make sure img does not suffer losses after
            # rotates
            x_min, y_min, x_max, y_max = self.getBound(mk)
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
            bound = self.getBound(mk)

            # remove extra paddings
            px = px.crop(bound)
            shf[0], shf[1] = bound[0], bound[1]
            for item in mk:
                item['param'] -= shf
            return (px, mk)
        else:
            raise Exception("Not implemented")

    def noise(self, px: Image, snr: float, n_type='bw') -> Image.Image:
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

    def getBound(self, mk: Dict):
        x_min, y_min = numpy.min(mk['param'], axis=1)
        x_max, y_max = numpy.max(mk['param'], axis=1)

class PixelFactory:
    supportedType = ['point', 'line', 'polygon', 'ellipse']

    def __init__(self):
        """
        https://blog.csdn.net/maitianpt/article/details/84983599
        """
        self._algo = PixelAlgo()  # pixel processor

    def rotate(self, px: Image.Image, mk: Dict, degree: float, expand=True) -> ():
        """
        roate image

        Parameter
        ---------
        shapes:
            a group of markings
        expand:
            if true, will make sure object will not suffer losses on edge
        """
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
        return self._algo.noise(px, snr, n_type)

    def pasteRegion(self, bg: Image.Image, bgMk: List[Dict],
        fg: Image.Image, fgMk: Dict, pos: Tuple) -> Tuple:
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
            foreground marking
        pos
            a tulpes of corrdinate
        """
        resPx = bg.copy()
        resMk = []
        resPx.paste(fg, pos, fg.getchannel(3))

        if fgMk is not None:
            resPa = fgMk['param'].copy() + numpy.asarray(pos) # fg points
            return (resPx, resMk)

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

    def parseToCsts(self, mk, imgSize) -> Tuple:
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
        tmp = filter(lambda tmp: tmp["type"] in supportedType[2:] , mk)
        assert tmp, "Such shape is not unsupported for copy"

        px = px.crop((x_min, y_min, x_max, y_max))
        shf = numpy.array([x_min, y_min])
        return (px, shf)


    def _pastePolyToPoly(self, bgMk: List[Dict], fgMk: Dict, frSize: Tuple) -> List[Dict]:
        """
        paste foreground polygon on background polygon at `pos` position

        Parameter
        ---------
        frSize
            frame size of the image
        """
        fgPol = Polygon(fgMk['param'])            # foreground polygon
        frPol = box(0, 0, frSize[0], frSize[1])   # image frame polygon
        resMk = []

        # ignore any foreground that is out side of image frame or
        # background makring that is empty
        ## NOTE: a.difference(b) is slower compare to binary predicates
        if not (frPol.disjoint(fgPol) or frPol.touches(fgPol) or bgMk is None):
            if frPol.overlaps(fgPol):
                # partial of foreground is outside of frame
                fgPol = frPol.intersection(fgPol)
            for mk in bgMk:
                bgPol = Polygon(mk['param'])
                obj_cp = None # object that needs copy
                if fgPol.disjoint(bgPol) or fgPol.touches(bgPol):
                    # completely isolate or outer_cut
                    obj_cp = bgPol
                elif fgPol.contains(bgPol):
                    # foreground cover background completely
                    obj_cp = fgPol
                else:
                    obj_cp = bgPol.difference(fgPol)

                if isinstance(obj_cp, Polygon):
                    obj_cp = [obj_cp]
                for geo in obj_cp:
                    param = numpy.array(geo.exterior.coords)
                    if len(geo.interiors) > 0:
                        param = numpy.append([param], geo.interiors)
                    resMk.append({'param': param, 'type': 'polygon'})
            resMk.append({
                'param': fgMk['param'], 'type': 'polygon'
            })
        elif bgMk is not None:
            return copy.deepcopy(bgMk)

        return resMk


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
            if mk['type'] in supportedType[: 2]:
                continue
            ImageDraw.Draw(mask).polygon(mk['param'].flatten().tolist(), outline=255, fill=255)

        # get indidual channel, merge then together
        r, g, b, _ = px.split()
        a = mask.getchannel(0)  # similar to .split()
        return Image.merge("RGBA", [r, g, b, a])
