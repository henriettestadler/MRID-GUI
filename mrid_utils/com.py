import numpy as np

def get_cy_trapezoid(b, a, h):
    # Trapezoid centroid calculation
    #        a
    #     ________
    #    /|       \
    #   / |        \
    #  /  |h  .C    \
    # /___|__________\
    # .        b

    cy = (b + 2 * a) * h / (3 * (b + a))

    return cy


def get_cy_triangle(h):
    return h / 3


def get_dist_to_deepest_ch(mrid_dict, offset=11):
    """
    Returns the distance from the deepest channel to the CoM of the deepest pattern
    """
    deepest_pattern = mrid_dict["dimensions"][-1, :]
    b, a, h = deepest_pattern

    if a > 0:
        cy = get_cy_trapezoid(b, a, h)
    else:
        cy = get_cy_triangle(h)

    dist = h - cy + offset
    return dist


def get_centomass(mrid_wafer_dimensions, intersegment_lengths):
    """
    mrid_wafer_dimensions: dimension vector of each pattern in mrid (num_patterns-by-3), dorsal-to-ventral, each row represents b,a,h; a=0 for triangular patterns
    intersegment_lengths: inter-pattern(segment) lengths starting from dorsal to ventral patterns
    """
    num_patterns = len(mrid_wafer_dimensions)
    c2c = np.zeros((num_patterns - 1,))

    bundle_l = 0
    ticks = [bundle_l]
    for i in range(num_patterns - 1):
        b, a, h = mrid_wafer_dimensions[i, :]
        b2, a2, h2 = mrid_wafer_dimensions[i + 1, :]

        if a > 0:
            cy = get_cy_trapezoid(b, a, h)
        else:
            cy = get_cy_triangle(h)

        bundle_l = bundle_l + cy
        ticks.append(bundle_l)

        distCy = h - cy
        bundle_l = bundle_l + distCy
        ticks.append(bundle_l)

        bundle_l = bundle_l + intersegment_lengths[i]
        ticks.append(bundle_l)

        if a2 > 0:
            cy2 = get_cy_trapezoid(b2, a2, h2)
        #             distCy2=cy2
        else:
            cy2 = get_cy_triangle(h2)
        #             distCy2=cy2
        c2c[i] = distCy + intersegment_lengths[i] + cy2

    b, a, h = mrid_wafer_dimensions[-1, :]
    if a > 0:
        cy = get_cy_trapezoid(b, a, h)
    else:
        cy = get_cy_triangle(h)

    bundle_l = bundle_l + cy
    ticks.append(bundle_l)

    distCy = h - cy
    bundle_l = bundle_l + distCy
    ticks.append(bundle_l)

    return c2c, ticks