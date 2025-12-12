{
  description = "DeMoD Camera Setup - RTSP streaming with MediaMTX and security tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Map Nix system to MediaMTX architecture
        archMap = {
          "aarch64-linux" = "arm64";
          "armv7l-linux" = "armv7";
          "riscv64-linux" = "riscv64";
          "x86_64-linux" = "amd64";
        };
        mediamtxArch = archMap.${system} or (throw "Unsupported system: ${system}");

        version = "1.13.1";
        mediamtx = pkgs.stdenv.mkDerivation rec {
          pname = "mediamtx";
          inherit version;
          src = pkgs.fetchurl {
            url = "https://github.com/bluenviron/mediamtx/releases/download/v${version}/mediamtx_v${version}_linux_${mediamtxArch}.tar.gz";
            sha256 = {
              arm64 = "sha256-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"; # Update after first build
              armv7 = "sha256-YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY";
              riscv64 = "sha256-ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ";
              amd64 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
            }.${mediamtxArch} or (throw "Add SHA256 for ${mediamtxArch}");
          };

          sourceRoot = ".";
          nativeBuildInputs = [ pkgs.autoPatchelfHook ];
          buildInputs = [ pkgs.stdenv.cc.cc.lib ];

          installPhase = ''
            mkdir -p $out/bin
            cp mediamtx $out/bin/
            cp mediamtx.yml $out/
          '';

          meta = with pkgs.lib; {
            description = "Ready-to-use RTSP server and proxy";
            homepage = "https://github.com/bluenviron/mediamtx";
            license = licenses.mit;
            platforms = [ system ];
          };
        };

        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          # No external deps needed — all stdlib
        ]);

        demod-camera-setup = pkgs.stdenv.mkDerivation {
          pname = "demod-camera-setup";
          version = "0.1.0";
          src = ./.;

          buildInputs = [ pythonEnv mediamtx pkgs.v4l-utils pkgs.bash ];

          installPhase = ''
            mkdir -p $out/bin $out/share/demod-camera-setup

            # Copy Python modules
            cp utils.py $out/share/demod-camera-setup/
            cp security_checker.py $out/share/demod-camera-setup/
            cp config.py $out/share/demod-camera-setup/

            # Copy shell scripts
            cp start.sh $out/share/demod-camera-setup/
            cp setup.sh $out/share/demod-camera-setup/

            # Example config
            cp config.jsonc.example $out/share/demod-camera-setup/config.jsonc

            # Wrapper scripts
            substituteAll ${./wrapper.sh} $out/bin/demod-setup \
              --subst-var-by mediamtx ${mediamtx}/bin/mediamtx \
              --subst-var-by share $out/share/demod-camera-setup

            substituteAll ${./start-wrapper.sh} $out/bin/demod-start \
              --subst-var-by share $out/share/demod-camera-setup

            substituteAll ${./security-wrapper.sh} $out/bin/demod-security \
              --subst-var-by share $out/share/demod-camera-setup

            chmod +x $out/bin/*
          '';

          meta = with pkgs.lib; {
            description = "DeMoD Camera Setup - Secure RTSP streaming toolkit";
            license = licenses.gpl3;
            maintainers = [ "DeMoD LLC" ];
            platforms = platforms.linux;
          };
        };

      in
      {
        packages = {
          default = demod-camera-setup;
          inherit mediamtx;
        };

        apps = {
          setup = flake-utils.lib.mkApp { drv = demod-camera-setup; name = "demod-setup"; };
          start = flake-utils.lib.mkApp { drv = demod-camera-setup; name = "demod-start"; };
          security = flake-utils.lib.mkApp { drv = demod-camera-setup; name = "demod-security"; };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.v4l-utils
            pkgs.wget
            pkgs.tar
            pkgs.gnugrep
            pkgs.gawk
            pkgs.which
            mediamtx
          ];

          shellHook = ''
            export PATH="$PATH:${mediamtx}/bin"
            echo "DeMoD Camera Setup devShell"
            echo "Run: ./setup.sh  → Full install"
            echo "     ./start.sh  → Single cam stream"
            echo "     python3 security_checker.py → TUI"
            echo "     python3 config.py → Web UI"
          '';
        };
      });
}
