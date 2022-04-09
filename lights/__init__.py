"""transit tiles
"""
import typing as T
import time

import lifxlan  # type: ignore

# 3 * 16-bit HSB \in [0, 2 ** 16) as well as Kelvin \in [1500-9000]
Value = int

Pixel = T.NewType("Pixel", T.Tuple[Value, Value, Value, int])
Frame = T.NewType("Frame", T.List[T.List[Pixel]])


class Tiles(T.Protocol):
    """for lifxlan.TileChain"""

    def get_canvas_dimensions(self) -> T.Tuple[int, int]:
        """e.g. (8, 8) for each tile"""

    def get_power(self) -> Value:
        """returns brightness level
        """

    def get_tilechain_colors(self) -> Frame:
        """what's currently painted?"""

    def project_matrix(self, frame: Frame, forms: int = 0, rapid: bool = False) -> None:
        """paints w/o waiting for ack if rapid=True (forms to spec SLA-like limit)"""

    def set_power(self, tiles_on: T.Union[bool, Value]) -> None:
        """turn on, off, or in between
        """


def rainbow(lifx: Tiles, duration_ms: int = 100, stop_after_n: int = 0) -> None:
    """if stop_after_n=0 (the default) will loop forever"""

    def starts(height: int, width: int) -> Frame:
        """initial frame
        """
        hue = 0
        temp = 4500
        limit = 65535
        rows: T.List[T.List[Pixel]] = []
        for _ in range(height):
            row: T.List[Pixel] = []
            for _ in range(width):
                row.append(Pixel((hue, limit, limit, temp)))
                hue += int(float(limit) / (height * width))
            rows.append(row)
        return Frame(rows)

    def cycle(prev: Frame) -> Frame:
        """next frame f(prev)
        """
        rows = [prev[-1]]
        for row in prev[:-1]:
            rows.append(row)
        return Frame(rows)

    def loop(first: Frame, steps: int = duration_ms) -> Frame:
        """paint n frames, returns last
        """
        frame = first
        for _ in range(steps):
            frame = cycle(frame)
            lifx.project_matrix(frame, duration_ms, rapid=True)
            time.sleep(max(duration_ms / 2000.0, 0.05))
        return frame

    def fix(first: Frame, height: int, width: int) -> Frame:
        """colors come back in single row instead of grid -- WTF?
        """
        if len(first) == height:
            return first
        row = first[0]
        grid: T.List[T.List[Pixel]] = []
        for index in range(0, len(first[0]), width):
            grid.append(row[index:index + width])
        return Frame(grid)

    height, width = lifx.get_canvas_dimensions()
    colors = lifx.get_tilechain_colors()
    grid = fix(colors, height, width)
    power = lifx.get_power()
    lifx.set_power(True)
    try:
        # every ~100ms, cycle frame
        first = starts(height, width)
        i = 1
        while i != stop_after_n:
            first = loop(first)
            i += 1
    except KeyboardInterrupt as err:
        print(err)
        return
    finally:
        lifx.project_matrix(grid)
        lifx.set_power(power)
