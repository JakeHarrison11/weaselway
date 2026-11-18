#ifndef WEASELWAY_MONITOR_LAYOUT_H
#define WEASELWAY_MONITOR_LAYOUT_H

#include <stdbool.h>
#include <stdint.h>

#include <freerdp/channels/disp.h>
#include <freerdp/settings.h>

#include "rdp.h"

#define WEASELWAY_MAX_DESKTOP_DIMENSION 8192

/* Keep the primary output first; normalize the rectangles to the desktop origin. */
bool monitor_layout_parse(const DISPLAY_CONTROL_MONITOR_LAYOUT_PDU *pdu, struct rdp_layout *layout);
bool monitor_layout_from_client(const rdpMonitor *monitors, unsigned count, struct rdp_layout *layout);

#endif
