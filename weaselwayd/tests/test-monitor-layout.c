#include <glib.h>

#include "monitor-layout.h"

static void
test_side_by_side(void)
{
    DISPLAY_CONTROL_MONITOR_LAYOUT monitors[] = {
        { .Left = -1920, .Top = 0, .Width = 1920, .Height = 1080 },
        { .Flags = DISPLAY_CONTROL_MONITOR_PRIMARY, .Width = 2560, .Height = 1440 },
    };
    DISPLAY_CONTROL_MONITOR_LAYOUT_PDU layout = {
        .NumMonitors = G_N_ELEMENTS(monitors),
        .Monitors = monitors,
    };
    struct rdp_layout result;

    g_assert_true(monitor_layout_parse(&layout, &result));
    g_assert_cmpuint(result.count, ==, 2);
    g_assert_cmpint(result.width, ==, 4480);
    g_assert_cmpint(result.height, ==, 1440);
    g_assert_cmpint(result.outputs[0].x, ==, 1920);
    g_assert_cmpint(result.outputs[0].width, ==, 2560);
    g_assert_cmpint(result.outputs[1].x, ==, 0);
    g_assert_cmpint(result.outputs[1].height, ==, 1080);

    layout.NumMonitors = 1;
    layout.Monitors = &monitors[1];
    g_assert_true(monitor_layout_parse(&layout, &result));
    g_assert_cmpuint(result.count, ==, 1);
    g_assert_cmpint(result.width, ==, 2560);
    g_assert_cmpint(result.outputs[0].x, ==, 0);
    g_assert_cmpint(result.outputs[1].width, ==, 0);
}

static void
test_vertical_layout(void)
{
    DISPLAY_CONTROL_MONITOR_LAYOUT monitors[] = {
        { .Left = 0, .Top = -1080, .Width = 1920, .Height = 1080 },
        { .Left = 0, .Top = 0, .Width = 1920, .Height = 1080 },
    };
    DISPLAY_CONTROL_MONITOR_LAYOUT_PDU layout = {
        .NumMonitors = G_N_ELEMENTS(monitors),
        .Monitors = monitors,
    };
    struct rdp_layout result;

    g_assert_true(monitor_layout_parse(&layout, &result));
    g_assert_cmpint(result.width, ==, 1920);
    g_assert_cmpint(result.height, ==, 2160);
    g_assert_cmpint(result.outputs[0].y, ==, 0);
    g_assert_cmpint(result.outputs[1].y, ==, 1080);
}

static void
test_client_monitor_data(void)
{
    rdpMonitor monitors[] = {
        { .width = 3840, .height = 2160, .is_primary = TRUE },
        { .x = 3840, .y = 326, .width = 2560, .height = 1440 },
    };
    struct rdp_layout result;

    g_assert_true(monitor_layout_from_client(monitors, G_N_ELEMENTS(monitors), &result));
    g_assert_cmpuint(result.count, ==, 2);
    g_assert_cmpint(result.width, ==, 6400);
    g_assert_cmpint(result.height, ==, 2160);
    g_assert_cmpint(result.outputs[0].width, ==, 3840);
    g_assert_cmpint(result.outputs[1].x, ==, 3840);
    g_assert_cmpint(result.outputs[1].y, ==, 326);
    g_assert_cmpint(result.outputs[1].height, ==, 1440);

    monitors[1].x = monitors[1].y = 0;
    g_assert_false(monitor_layout_from_client(monitors, G_N_ELEMENTS(monitors), &result));
}

static void
test_rejects_unsupported_layouts(void)
{
    DISPLAY_CONTROL_MONITOR_LAYOUT monitors[] = {
        { .Left = 0, .Top = 0, .Width = 8192, .Height = 1080 },
        { .Left = 8192, .Top = 0, .Width = 8192, .Height = 1080 },
    };
    DISPLAY_CONTROL_MONITOR_LAYOUT_PDU layout = {
        .NumMonitors = G_N_ELEMENTS(monitors),
        .Monitors = monitors,
    };
    struct rdp_layout result;

    g_assert_false(monitor_layout_parse(&layout, &result));
    monitors[0].Width = 1024;
    monitors[1].Width = 1024;
    monitors[1].Left = 512;
    g_assert_false(monitor_layout_parse(&layout, &result));
    layout.NumMonitors = 0;
    g_assert_false(monitor_layout_parse(&layout, &result));
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/monitor-layout/side-by-side", test_side_by_side);
    g_test_add_func("/monitor-layout/vertical", test_vertical_layout);
    g_test_add_func("/monitor-layout/client-monitor-data", test_client_monitor_data);
    g_test_add_func("/monitor-layout/rejects-unsupported", test_rejects_unsupported_layouts);
    return g_test_run();
}
