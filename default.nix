with import <nixpkgs> {};
stdenv.mkDerivation {
    name = "darker-test";
    buildInputs = [ python310 git ];
}
