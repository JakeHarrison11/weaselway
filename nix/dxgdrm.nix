{ pkgs, dxgdrm }:

let
  inherit (dxgdrm.inputs.wsl-kernel.lib) releases;
  packages = dxgdrm.packages.${pkgs.stdenv.hostPlatform.system};
  withMultiOutput =
    release:
    packages."dxgdrm-${release}".overrideAttrs (old: {
      # mkModules copies the external module into M after preBuild. Reuse its
      # kernel/DRM setup and patch just that module before the external build.
      buildPhase =
        let
          writable = "chmod -R u+w M";
        in
        assert pkgs.lib.hasInfix writable old.buildPhase;
        builtins.replaceStrings [ writable ] [
          ''
            ${writable}
            ${pkgs.buildPackages.patch}/bin/patch -d M -p1 < ${./dxgdrm-multi-output.patch}
          ''
        ] old.buildPhase;
    });
in
pkgs.symlinkJoin {
  name = "weaselway-dxgdrm-all";
  paths = map withMultiOutput releases;
}
