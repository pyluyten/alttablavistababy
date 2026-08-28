let
  pkgs = import <nixpkgs> {};
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    pygobject3
    pycairo
  ]);
in
{
  niri-seek = pkgs.stdenv.mkDerivation {
    name = "niri-seek";
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
      # Copy python source to /share to protect it from wrapGAppsHook shell patching
      mkdir -p $out/share/niri-seek $out/bin
      cp niri-seek.py $out/share/niri-seek/niri-seek.py

      # Create the wrapped shell executable in /bin
      makeWrapper ${pythonEnv}/bin/python3 $out/bin/niri-seek \
        --add-flags "$out/share/niri-seek/niri-seek.py" \
        --prefix PATH : "${pkgs.niri}/bin"
    '';
  };
}
