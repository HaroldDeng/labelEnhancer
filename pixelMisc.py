class PixelMisc:
    def __init__(self):
        pass

    def validateMarkedPixel(self, _mp):
        """
        validate if image and markings meets PixelFactory's requirements
        """
        pxVaild = False
        mkVaild = False
        # image check
        if not isinstance(_mp.pixel, Image.Image):
            print('ERROR: image should be a PIL image')
        elif _mp.pixel.mode != 'RGBA':
            print('ERROR: image should be in RGBA mode')
        else:
            pxVaild = True

        # marking check
        elif mk.get('type') is None or mk.get('param') is None:
            # numpy gets confused with == operator
            print('Warnning: markings should constain both keys \'type\' and \'param\'')
        elif not isinstance(mk['param'], numpy.ndarray):
            print('Warnning: marking\'s keys \'param\' accept a numpy array')
        elif not mk['type'] in self.supportedType:
            print('Warnning: markings type not supported')
        else:
            mkVaild = True

        return pxVaild and mkVaild
