{
  description = "A fast, searchable window switcher for the Niri Wayland compositor";

  inputs = {
    niri-seek.url = "github:pyluyten/alttablavistababy";
    niri-seek.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          pygobject3
          pycairo
        ]);
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "niriseek";
          version = "0.1.0";
          src = ./.;

          nativeBuildInputs = with pkgs; [
            wrapGAppsHook4
            gobject-introspection
            makeWrapper
          ];

          buildInputs = with pkgs; [
            gtk4
            libadwaita
            graphene
            pango
            gdk-pixbuf
            pythonEnv
          ];

          installPhase = ''
            mkdir -p $out/share/niriseek $out/bin
            cp niri-seek.py $out/share/niriseek/niri-seek.py

            makeWrapper ${pythonEnv}/bin/python3 $out/bin/niriseek \
              --add-flags "$out/share/niriseek/niri-seek.py" \
              --prefix PATH : "${pkgs.niri}/bin"
          '';
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/niriseek";
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.default ];
        };
      }
    );
}
