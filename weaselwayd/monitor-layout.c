#include "monitor-layout.h"

bool
monitor_layout_extent(const DISPLAY_CONTROL_MONITOR_LAYOUT_PDU *layout, int *width, int *height)
{
    int64_t left = 0, top = 0, right = 0, bottom = 0;

    if (!layout || !layout->Monitors || layout->NumMonitors == 0 ||
        layout->NumMonitors > WEASELWAY_MAX_MONITORS || !width || !height)
        return false;

    for (uint32_t i = 0; i < layout->NumMonitors; i++) {
        const DISPLAY_CONTROL_MONITOR_LAYOUT *monitor = &layout->Monitors[i];
        int64_t monitor_right = (int64_t)monitor->Left + monitor->Width;
        int64_t monitor_bottom = (int64_t)monitor->Top + monitor->Height;

        if (monitor->Width == 0 || monitor->Height == 0)
            return false;
        if (monitor->Left < left)
            left = monitor->Left;
        if (monitor->Top < top)
            top = monitor->Top;
        if (monitor_right > right)
            right = monitor_right;
        if (monitor_bottom > bottom)
            bottom = monitor_bottom;
    }

    if (right <= left || bottom <= top ||
        right - left > WEASELWAY_MAX_DESKTOP_DIMENSION ||
        bottom - top > WEASELWAY_MAX_DESKTOP_DIMENSION)
        return false;

    *width = (int)(right - left);
    *height = (int)(bottom - top);
    return true;
}
