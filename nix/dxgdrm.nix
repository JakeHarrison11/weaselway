{ pkgs, dxgdrm }:

dxgdrm.packages.${pkgs.stdenv.hostPlatform.system}.dxgdrm-all
