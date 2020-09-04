pixelFactory accept a map of a list of maps
[
  # group 1
  [
    {"shape": "???", "param": numpy.ndarray, },
  ],
]




polygon-polygon intersection
    - disjoin                [ignore] # disjoin()
    - outer-cut              [ignore] # touches()
        - points
        - lines
    - intersect              [process] # overlap()
        - no cut through               #
        - cut through                  #
    - inner-cut              [process]
        - points                       #
        - lines                        #
    - enclose                [todo]

touches()    - a touches outside of b
overlap()    - partial a inside b
within()     - a inside b        a.within(b) eq. b.contains(a)
contains()   - a inside b
disjoin()    - completely isolates
intersects() - invert of  disjoin()
intersection() => Empty, Point, MultiPoints, Linestring, MultiLineString, Polygon, MultiPoygons


crosses()    - not for poly-poly
