{ pkgs ? import <nixpkgs> { }, pythonVersion ? "python310" }:
(
  pkgs.stdenv.mkDerivation {
    name = "darker-test";
    buildInputs = [ pkgs.${pythonVersion} pkgs.git ];
  }
)
