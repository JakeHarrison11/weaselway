#include <glib.h>

#include "monitor-layout.h"

static void
test_side_by_side(void)
{
    DISPLAY_CONTROL_MONITOR_LAYOUT monitors[] = {
        { .Left = -1920, .Top = 0, .Width = 1920, .Height = 1080 },
        { .Left = 0, .Top = 0, .Width = 2560, .Height = 1440 },
    };
    DISPLAY_CONTROL_MONITOR_LAYOUT_PDU layout = {
        .NumMonitors = G_N_ELEMENTS(monitors),
        .Monitors = monitors,
    };
    int width, height;

    g_assert_true(monitor_layout_extent(&layout, &width, &height));
    g_assert_cmpint(width, ==, 4480);
    g_assert_cmpint(height, ==, 1440);
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
    int width, height;

    g_assert_true(monitor_layout_extent(&layout, &width, &height));
    g_assert_cmpint(width, ==, 1920);
    g_assert_cmpint(height, ==, 2160);
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
    int width, height;

    g_assert_false(monitor_layout_extent(&layout, &width, &height));
    layout.NumMonitors = 0;
    g_assert_false(monitor_layout_extent(&layout, &width, &height));
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/monitor-layout/side-by-side", test_side_by_side);
    g_test_add_func("/monitor-layout/vertical", test_vertical_layout);
    g_test_add_func("/monitor-layout/rejects-unsupported", test_rejects_unsupported_layouts);
    return g_test_run();
}
