{ pkgs ? import <nixpkgs> { } }:
(
  pkgs.stdenv.mkDerivation {
    name = "darker-test";
    buildInputs = [ pkgs.python310 pkgs.git ];
  }
)
