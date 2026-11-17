#ifndef WEASELWAY_MONITOR_LAYOUT_H
#define WEASELWAY_MONITOR_LAYOUT_H

#include <stdbool.h>
#include <stdint.h>

#include <freerdp/channels/disp.h>

#define WEASELWAY_MAX_MONITORS 16
#define WEASELWAY_MAX_DESKTOP_DIMENSION 8192

/* Find the desktop bounds that contain every monitor in a layout. */
bool monitor_layout_extent(const DISPLAY_CONTROL_MONITOR_LAYOUT_PDU *layout, int *width,
                           int *height);

#endif
