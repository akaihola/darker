{ pkgs ? import <nixpkgs> { }, pythonVersion ? "python311" }:
(
  pkgs.stdenv.mkDerivation {
    name = "darker-test";
    buildInputs = [ pkgs.${pythonVersion} pkgs.git ];
  }
)
