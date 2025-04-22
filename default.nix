{ pkgs ? import <nixpkgs> { } }:
(
  pkgs.stdenv.mkDerivation {
    name = "darker-test";
    buildInputs = [ pkgs.python311 pkgs.git pkgs.uv ];
    shellHook = ''
      export PY_IGNORE_IMPORTMISMATCH=1
    '';
  }
)
