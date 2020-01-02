with import <nixpkgs> {};

let
  python = let
    packageOverrides = self: super: {
      trezor = super.trezor.overridePythonAttrs(old: rec {
        version = "master";
        src =  ./.;
        doCheck = true; # set to false if you want to skip tests
        checkPhase = ''
          runHook preCheck
          pytest tests/ --ignore tests/test_tx_api.py
          runHook postCheck
        '';
      });
    };
  in pkgs.python3.override {inherit packageOverrides; self = python;};

in python.withPackages(ps:[ps.trezor])

