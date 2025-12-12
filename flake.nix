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
        
        # Fetch SHA256 hashes automatically using nix-prefetch-url
        # Run: nix-prefetch-url --unpack <URL> to get these
        mediamtx = pkgs.stdenv.mkDerivation rec {
          pname = "mediamtx";
          inherit version;
          
          src = pkgs.fetchurl {
            url = "https://github.com/bluenviron/mediamtx/releases/download/v${version}/mediamtx_v${version}_linux_${mediamtxArch}.tar.gz";
            sha256 = {
              arm64 = "0000000000000000000000000000000000000000000000000000"; # TODO: Fill in
              armv7 = "0000000000000000000000000000000000000000000000000000"; # TODO: Fill in
              riscv64 = "0000000000000000000000000000000000000000000000000000"; # TODO: Fill in
              amd64 = "0000000000000000000000000000000000000000000000000000"; # TODO: Fill in
            }.${mediamtxArch};
          };

          sourceRoot = ".";
          
          nativeBuildInputs = [ pkgs.autoPatchelfHook ];
          buildInputs = [ pkgs.stdenv.cc.cc.lib ];

          installPhase = ''
            runHook preInstall
            
            mkdir -p $out/bin $out/share/mediamtx
            install -Dm755 mediamtx $out/bin/mediamtx
            install -Dm644 mediamtx.yml $out/share/mediamtx/mediamtx.yml
            
            runHook postInstall
          '';

          meta = with pkgs.lib; {
            description = "Ready-to-use RTSP server and proxy";
            homepage = "https://github.com/bluenviron/mediamtx";
            license = licenses.mit;
            platforms = platforms.linux;
            mainProgram = "mediamtx";
          };
        };

        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          # Add any future dependencies here
        ]);

        demod-camera-setup = pkgs.stdenv.mkDerivation rec {
          pname = "demod-camera-setup";
          version = "0.1.0";
          src = ./.;

          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ pythonEnv mediamtx pkgs.v4l-utils ];

          installPhase = ''
            runHook preInstall
            
            mkdir -p $out/{bin,share/demod-camera-setup,share/doc/demod-camera-setup}

            # Copy Python modules
            install -Dm644 utils.py $out/share/demod-camera-setup/utils.py
            install -Dm644 security_checker.py $out/share/demod-camera-setup/security_checker.py
            install -Dm644 config.py $out/share/demod-camera-setup/config.py

            # Copy shell scripts (make executable)
            install -Dm755 start.sh $out/share/demod-camera-setup/start.sh
            install -Dm755 setup.sh $out/share/demod-camera-setup/setup.sh

            # Example config
            install -Dm644 config.jsonc.example $out/share/demod-camera-setup/config.jsonc.example

            # Create wrapper scripts with proper shebangs
            cat > $out/bin/demod-setup <<'EOF'
            #!${pkgs.bash}/bin/bash
            set -euo pipefail
            cd ${placeholder "out"}/share/demod-camera-setup
            exec ./setup.sh "$@"
            EOF

            cat > $out/bin/demod-start <<'EOF'
            #!${pkgs.bash}/bin/bash
            set -euo pipefail
            cd ${placeholder "out"}/share/demod-camera-setup
            exec ./start.sh "$@"
            EOF

            cat > $out/bin/demod-security <<'EOF'
            #!${pkgs.python311}/bin/python3
            import sys
            import os
            sys.path.insert(0, '${placeholder "out"}/share/demod-camera-setup')
            os.chdir('${placeholder "out"}/share/demod-camera-setup')
            import security_checker
            EOF

            cat > $out/bin/demod-config <<'EOF'
            #!${pkgs.python311}/bin/python3
            import sys
            import os
            sys.path.insert(0, '${placeholder "out"}/share/demod-camera-setup')
            os.chdir('${placeholder "out"}/share/demod-camera-setup')
            import config
            EOF

            chmod +x $out/bin/*

            # Wrap binaries to ensure PATH includes necessary tools
            for prog in demod-setup demod-start demod-security demod-config; do
              wrapProgram $out/bin/$prog \
                --prefix PATH : ${pkgs.lib.makeBinPath [ 
                  pkgs.v4l-utils 
                  pkgs.coreutils 
                  pkgs.gnugrep 
                  pkgs.gawk 
                  mediamtx 
                  pkgs.findutils
                  pkgs.util-linux
                ]}
            done
            
            runHook postInstall
          '';

          meta = with pkgs.lib; {
            description = "DeMoD Camera Setup - Secure RTSP streaming toolkit";
            longDescription = ''
              A comprehensive toolkit for setting up secure RTSP camera streaming
              using MediaMTX with multiple configuration interfaces (CLI, TUI, Web).
            '';
            homepage = "https://github.com/demod/camera-setup"; # Update with actual URL
            license = licenses.gpl3Only;
            maintainers = with maintainers; [ ]; # Add maintainer info
            platforms = platforms.linux;
            mainProgram = "demod-start";
          };
        };

      in
      {
        packages = {
          default = demod-camera-setup;
          inherit mediamtx;
        };

        apps = {
          default = flake-utils.lib.mkApp { 
            drv = demod-camera-setup; 
            name = "demod-start"; 
          };
          setup = flake-utils.lib.mkApp { 
            drv = demod-camera-setup; 
            name = "demod-setup"; 
          };
          start = flake-utils.lib.mkApp { 
            drv = demod-camera-setup; 
            name = "demod-start"; 
          };
          security = flake-utils.lib.mkApp { 
            drv = demod-camera-setup; 
            name = "demod-security"; 
          };
          config = flake-utils.lib.mkApp { 
            drv = demod-camera-setup; 
            name = "demod-config"; 
          };
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
            pkgs.util-linux
            mediamtx
          ];

          shellHook = ''
            export PATH="$PATH:${mediamtx}/bin"
            echo "╔════════════════════════════════════════╗"
            echo "║   DeMoD Camera Setup - Dev Shell      ║"
            echo "╚════════════════════════════════════════╝"
            echo ""
            echo "Available commands:"
            echo "  ./setup.sh                  → Full system install"
            echo "  ./start.sh                  → Single camera stream"
            echo "  python3 security_checker.py → TUI security checker"
            echo "  python3 config.py           → Web UI (port 8000)"
            echo ""
            echo "MediaMTX: ${mediamtx}/bin/mediamtx"
          '';
        };

        # Optional: Add formatter
        formatter = pkgs.nixpkgs-fmt;
      });
}
