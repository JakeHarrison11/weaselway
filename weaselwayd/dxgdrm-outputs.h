#ifndef WEASELWAY_DXGDRM_OUTPUTS_H
#define WEASELWAY_DXGDRM_OUTPUTS_H

#include "dxgdrm_drm.h"

/* The distro installer can still build against the last released header. */
#ifndef DRM_IOCTL_DXGDRM_SET_OUTPUTS
#define DXGDRM_MAX_OUTPUTS 4
struct drm_dxgdrm_output_mode {
    __u32 width, height, refresh_mhz, pad;
};
struct drm_dxgdrm_set_outputs {
    __u32 count, pad;
    struct drm_dxgdrm_output_mode modes[DXGDRM_MAX_OUTPUTS];
};
struct drm_dxgdrm_bind_output {
    __u32 index, pad;
};
#define DRM_IOCTL_DXGDRM_SET_OUTPUTS \
    DRM_IOW(DRM_COMMAND_BASE + 0x07, struct drm_dxgdrm_set_outputs)
#define DRM_IOCTL_DXGDRM_BIND_OUTPUT \
    DRM_IOW(DRM_COMMAND_BASE + 0x08, struct drm_dxgdrm_bind_output)
#endif

#endif
