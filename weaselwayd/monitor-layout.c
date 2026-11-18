#include "monitor-layout.h"

bool
monitor_layout_parse(const DISPLAY_CONTROL_MONITOR_LAYOUT_PDU *pdu, struct rdp_layout *layout)
{
    int64_t left = INT64_MAX, top = INT64_MAX, right = INT64_MIN, bottom = INT64_MIN;
    unsigned primary = 0;

    if (!pdu->Monitors || pdu->NumMonitors == 0 || pdu->NumMonitors > RDP_MAX_OUTPUTS)
        return false;

    for (unsigned i = 0; i < pdu->NumMonitors; i++) {
        const DISPLAY_CONTROL_MONITOR_LAYOUT *monitor = &pdu->Monitors[i];
        int64_t monitor_right = (int64_t)monitor->Left + monitor->Width;
        int64_t monitor_bottom = (int64_t)monitor->Top + monitor->Height;

        if (monitor->Width == 0 || monitor->Height == 0)
            return false;
        if (monitor->Flags & DISPLAY_CONTROL_MONITOR_PRIMARY)
            primary = i;
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

    *layout = (struct rdp_layout) {
        .count = pdu->NumMonitors,
        .width = (int)(right - left),
        .height = (int)(bottom - top),
    };
    for (unsigned i = 0; i < layout->count; i++) {
        const DISPLAY_CONTROL_MONITOR_LAYOUT *m = &pdu->Monitors[i];
        unsigned slot = i == primary ? 0 : i < primary ? i + 1 : i;
        struct rdp_rect rect = { (int)(m->Left - left), (int)(m->Top - top),
                                 (int)m->Width, (int)m->Height };

        for (unsigned j = 0; j < i; j++) {
            unsigned previous = j == primary ? 0 : j < primary ? j + 1 : j;
            const struct rdp_rect *r = &layout->outputs[previous];

            if (rect.x < r->x + r->width && r->x < rect.x + rect.width &&
                rect.y < r->y + r->height && r->y < rect.y + rect.height)
                return false;
        }
        layout->outputs[slot] = rect;
    }
    return true;
}

bool
monitor_layout_from_client(const rdpMonitor *monitors, unsigned count, struct rdp_layout *layout)
{
    DISPLAY_CONTROL_MONITOR_LAYOUT rectangles[RDP_MAX_OUTPUTS] = { 0 };
    DISPLAY_CONTROL_MONITOR_LAYOUT_PDU pdu = { .NumMonitors = count, .Monitors = rectangles };

    if (!monitors || count < 2 || count > RDP_MAX_OUTPUTS)
        return false;

    for (unsigned i = 0; i < count; i++) {
        const rdpMonitor *m = &monitors[i];
        if (m->width <= 0 || m->height <= 0)
            return false;
        rectangles[i] = (DISPLAY_CONTROL_MONITOR_LAYOUT) {
            .Flags = m->is_primary ? DISPLAY_CONTROL_MONITOR_PRIMARY : 0,
            .Left = m->x, .Top = m->y, .Width = (UINT32)m->width, .Height = (UINT32)m->height,
        };
    }
    return monitor_layout_parse(&pdu, layout);
}
