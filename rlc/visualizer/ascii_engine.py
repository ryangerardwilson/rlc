from __future__ import annotations


def render_bars(
    width: int,
    height: int,
    levels: list[float] | None = None,
    peaks: list[float] | None = None,
) -> list[str]:
    if width < 2 or height < 2:
        return [" " * max(1, width) for _ in range(max(1, height))]

    bands = max(4, min(64, width // 2))
    if not levels:
        levels = [0.0] * bands
    if not peaks:
        peaks = [0.0] * len(levels)

    sampled_levels = _resample(levels, bands)
    sampled_peaks = _resample(peaks, bands)
    glyphs = " .,:-=+*#%@"

    canvas = [[" " for _ in range(width)] for _ in range(height)]
    for i, level in enumerate(sampled_levels):
        filled = level * (height - 1)
        x0 = i * 2
        x1 = min(width - 1, x0 + 1)

        for y in range(height):
            from_bottom = (height - 1) - y
            diff = filled - from_bottom
            if diff <= 0:
                continue
            if diff >= 1:
                ch = glyphs[-1]
            else:
                idx = min(len(glyphs) - 1, max(1, int(diff * (len(glyphs) - 1))))
                ch = glyphs[idx]
            canvas[y][x0] = ch
            canvas[y][x1] = ch

        peak_row = (height - 1) - int(sampled_peaks[i] * (height - 1))
        if 0 <= peak_row < height:
            canvas[peak_row][x0] = "|"
            canvas[peak_row][x1] = "|"

    return ["".join(row) for row in canvas]


def _resample(levels: list[float], bands: int) -> list[float]:
    if len(levels) == bands:
        return [min(1.0, max(0.0, v)) for v in levels]
    if len(levels) == 1:
        v = min(1.0, max(0.0, levels[0]))
        return [v for _ in range(bands)]

    out: list[float] = []
    src_max = len(levels) - 1
    for i in range(bands):
        pos = (i * src_max) / max(1, bands - 1)
        lo = int(pos)
        hi = min(src_max, lo + 1)
        frac = pos - lo
        v = levels[lo] * (1.0 - frac) + levels[hi] * frac
        out.append(min(1.0, max(0.0, v)))
    return out
