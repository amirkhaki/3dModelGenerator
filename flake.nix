{
  description = "3D Model Generator - Development Shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonEnv = pkgs.python313.withPackages (ps: with ps; [
          flask
          openai
          requests
          python-dotenv
          pip
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            
          ];

          FLASK_ENV = "development";
          FLASK_DEBUG = "1";
        };
      }
    );
}
