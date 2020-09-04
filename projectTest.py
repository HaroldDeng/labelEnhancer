import numpy as np
from pixelFactory import PixelFactory
from matplotlib import pyplot

# poly = [
#     Polygon([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]),
#     Polygon([(6, 6), (6, 7), (7, 7), (7, 6), (6, 6)]),
#     Polygon([(5, 4), (6, 5), (7, 4)]),
#     Polygon([(0, 8), (1, 5), (2, 7), (3, 5), (4, 8)]),
#     Polygon([(5, 3), (5, 8), (10, 8), (10, 3)]),
#     Polygon([(4, 0), (8, 0), (8, 5), (4, 5), (4, 4), (6, 4), (6, 3), (4, 3)]),
#     Polygon([(4, 4), (4, 3), (10, 3), (10, 4)]),
#     Polygon([(-1, 4), (-1, 3), (6, 3), (6, 4)]),
#     Polygon([(3, 3), (4, 4), (5, 3)]),
#     Polygon([(3, 4), (4, 5), (5, 4)]),
#     Polygon([(4, 4), (5, 4), (5, 2)]),
#     Polygon([(4, 5), (5, 5), (5, 3)]),
#     Polygon([(3, 4), (4, 4), (4, 2)]),
# ]


pf = None

def _pastePolyToPoly_test():
    # # _pastePolyToPoly(self, bgMk: List[Dict], fgMk: Dict, frSize: Tuple) -> List[Dict]
    fgMk = {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]), 'type': 'polygon'}
    bgMk = {'param': np.array([(6, 6), (6, 7), (7, 7), (7, 6), (6, 6)]), 'type': 'polygon'}
    assert len(pf._pastePolyToPoly(None, fgMk, (0, 0))) == 0
    assert len(pf._pastePolyToPoly(None, fgMk, (94523, 172323))) == 0

    # completely seperate
    bgMk = {'param': np.array([(6, 6), (6, 7), (7, 7), (7, 6), (6, 6)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    # print(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)))
    # exit()
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # one point
    bgMk = {'param': np.array([(5, 4), (6, 5), (7, 4)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # two points
    bgMk = {'param': np.array([(0, 8), (1, 5), (2, 7), (3, 5), (4, 8)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # outer-cut a line
    bgMk = {'param': np.array([(5, 3), (5, 8), (10, 8), (10, 3), (5, 3)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # two lines
    bgMk = {'param': np.array([(4, 0), (8, 0), (8, 5), (4, 5), (4, 4), (6, 4), (6, 3), (4, 3), (4, 0)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (4, 5), (4, 4), (5, 4), (5, 3), (4, 3), (4, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    ret = pf._pastePolyToPoly([fgMk], bgMk, (20, 20))
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # fgMk is on top of bgMk, but not cut though
    bgMk = {'param': np.array([(4, 4), (4, 3), (10, 3), (10, 4)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 5), (5, 5), (5, 4), (4, 4), (4, 3), (5, 3), (5, 0), (0, 0)]), 'type': 'polygon'},
        bgMk
    ]
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # fgMk cut though bgMk
    bgMk = {'param': np.array([(-1, 4), (-1, 3), (6, 3), (6, 4)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 3), (5, 3), (5, 0), (0, 0)]), 'type': 'polygon'},
        {'param': np.array([(0, 4), (0, 5), (5, 5), (5, 4), (0, 4)]), 'type': 'polygon'},
        bgMk
    ]
    assert _oneToOneMatch(pf._pastePolyToPoly([fgMk], bgMk, (20, 20)), ans)

    # fgMk innear cut though bgMk
    bgMk = {'param': np.array([(3, 4), (4, 5), (5, 4), (3, 4)]), 'type': 'polygon'}
    ans = [
        {'param': np.array([(0, 0), (0, 3), (5, 3), (5, 0), (0, 0)]), 'type': 'polygon'},
        {'param': np.array([(0, 4), (0, 5), (5, 5), (5, 4), (0, 4)]), 'type': 'polygon'},
        bgMk
    ]
    ret = pf._pastePolyToPoly([fgMk], bgMk, (20, 20))

    # pyplot.plot(fgMk['param'][:,0].tolist(), fgMk['param'][:,1].tolist(), 'b-')
    # pyplot.plot(bgMk['param'][:,0].tolist(), bgMk['param'][:,1].tolist(), 'g-')
    # pyplot.plot(ret[0]['param'][:,0].tolist(), ret[0]['param'][:,1].tolist(), 'r-')
    # pyplot.show()
    # pyplot.plot([p[0] for p in f?g.exterior.coords], [p[1] for p in fg.exterior.coords], 'b-')


def _oneToOneMatch(obj1, obj2):
    return len(obj1) == len(obj2) and all([
        np.array_equal(a.pop('param'), b.pop('param')) for a, b in zip(obj1, obj2)
    ])

if __name__ == '__main__':
    pf = PixelFactory()
    _pastePolyToPoly_test()


    print('Tests passed!')
