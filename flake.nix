{
  description = "Flake for fuzz loop";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  inputs.systems.url = "github:nix-systems/default";
  inputs.flake-utils = {
    url = "github:numtide/flake-utils";
    inputs.systems.follows = "systems";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgsUnfree = import nixpkgs {
          inherit system;
          config = {
            allowUnfreePredicate =
              pkg:
              builtins.elem (pkgs.lib.getName pkg) [
                "claude-code"
              ];
          };
        };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgsUnfree; [
            claude-code
            go
            python3
            uv
          ];
        };
      }
    );
}
