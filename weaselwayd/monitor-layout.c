#include "monitor-layout.h"

bool
monitor_layout_parse(const DISPLAY_CONTROL_MONITOR_LAYOUT_PDU *pdu,
                     struct monitor monitors[RDP_MAX_OUTPUTS], int *count)
{
    int64_t left = INT64_MAX, top = INT64_MAX, right = INT64_MIN, bottom = INT64_MIN;

    if (!pdu || !pdu->Monitors || !monitors || !count || pdu->NumMonitors == 0 ||
        pdu->NumMonitors > RDP_MAX_OUTPUTS)
        return false;

    for (unsigned i = 0; i < pdu->NumMonitors; i++) {
        const DISPLAY_CONTROL_MONITOR_LAYOUT *monitor = &pdu->Monitors[i];
        int64_t monitor_right = (int64_t)monitor->Left + monitor->Width;
        int64_t monitor_bottom = (int64_t)monitor->Top + monitor->Height;

        if (monitor->Width == 0 || monitor->Height == 0 ||
            monitor->Width > WEASELWAY_MAX_DESKTOP_DIMENSION ||
            monitor->Height > WEASELWAY_MAX_DESKTOP_DIMENSION)
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

    *count = (int)pdu->NumMonitors;
    for (unsigned i = 0; i < pdu->NumMonitors; i++) {
        const DISPLAY_CONTROL_MONITOR_LAYOUT *m = &pdu->Monitors[i];
        struct monitor current = {
            .x = (int)((int64_t)m->Left - left),
            .y = (int)((int64_t)m->Top - top),
            .width = (int)m->Width,
            .height = (int)m->Height,
            .width_mm = m->PhysicalWidth >= 10 && m->PhysicalWidth <= 10000
                            ? m->PhysicalWidth
                            : 0,
            .height_mm = m->PhysicalHeight >= 10 && m->PhysicalHeight <= 10000
                             ? m->PhysicalHeight
                             : 0,
        };

        for (unsigned j = 0; j < i; j++) {
            const struct monitor *r = &monitors[j];

            if (current.x < r->x + r->width && r->x < current.x + current.width &&
                current.y < r->y + r->height && r->y < current.y + current.height)
                return false;
        }
        monitors[i] = current;
    }
    return true;
}
